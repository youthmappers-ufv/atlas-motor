"""Testes dos scripts de manutenção (novo_local, ativar_tema, atualizar_motor), da
combinação catálogo + município e da coerência entre o modelo municipal e o motor."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
SCRIPTS = MOTOR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from comum import ler_temas, versao_motor  # noqa: E402
from validar import verificar  # noqa: E402


def rodar(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True,
                          encoding="utf-8")


class Scripts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def novo(self) -> Path:
        destino = self.dir / "atlas-cidade-teste"
        r = rodar("novo_local.py", "--nome", "Cidade Teste", "--ibge", "1234567", "--sem-rede", "--relacao", "42",
                  "--bbox=-19.3,-46.4,-19.1,-46.2", "--sede-bbox=-19.21,-46.31,-19.19,-46.29", "--destino", str(destino))
        self.assertEqual(r.returncode, 0, r.stderr)
        return destino

    def test_novo_local_cria_repositorio_valido(self):
        local = self.novo()
        texto = (local / "atlas.toml").read_text(encoding="utf-8")
        self.assertIn('nome = "Cidade Teste"', texto)
        self.assertIn(f'versao = "{versao_motor()}"', texto)
        self.assertIn('slug = "cidade-teste"', texto)
        self.assertTrue((local / ".gitignore").exists())
        self.assertTrue((local / "atlas" / "pranchas" / "01-localizacao.qmd").exists())
        restos = [p for p in local.rglob("*") if p.is_file() and "@@" in p.read_text(encoding="utf-8", errors="ignore")]
        self.assertEqual(restos, [], "marcadores @@ não substituídos")
        self.assertEqual(verificar(local).erros, [])

    def test_novo_local_nao_sobrescreve(self):
        self.novo()
        r = rodar("novo_local.py", "--nome", "Cidade Teste", "--ibge", "1234567", "--sem-rede", "--relacao", "42",
                  "--bbox=-19.3,-46.4,-19.1,-46.2", "--sede-bbox=-19.21,-46.31,-19.19,-46.29",
                  "--destino", str(self.dir / "atlas-cidade-teste"))
        self.assertNotEqual(r.returncode, 0)

    def test_ativar_tema(self):
        local = self.novo()
        r = rodar("ativar_tema.py", "saude", "--local", str(local))
        self.assertEqual(r.returncode, 0, r.stderr)
        temas = {t.id: t for t in ler_temas(local)}
        self.assertEqual(temas["saude"].situacao, "em-andamento")
        self.assertEqual(temas["saude"].referencia, "cnes")          # padrão do catálogo
        self.assertTrue((local / "atlas" / "pranchas" / "04-saude.qmd").exists())
        rodar("ativar_tema.py", "saude", "--situacao", "publicado", "--local", str(local))
        self.assertEqual({t.id: t for t in ler_temas(local)}["saude"].situacao, "publicado")
        self.assertEqual((local / "temas.toml").read_text(encoding="utf-8").count("[tema.saude]"), 1)

    def test_atualizar_motor(self):
        local = self.novo()
        r = rodar("atualizar_motor.py", "--versao", "v9.1.0", "--local", str(local))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('versao = "v9.1.0"', (local / "atlas.toml").read_text(encoding="utf-8"))
        for wf in (local / ".github" / "workflows").glob("*.yml"):
            self.assertIn("@v9.1.0", wf.read_text(encoding="utf-8"))
        self.assertFalse(any("chama o motor" in e for e in verificar(local).erros))

    def test_referencia_e_recorte_sobrescritos_pelo_municipio(self):
        local = self.novo()
        with (local / "temas.toml").open("a", encoding="utf-8") as f:
            f.write('\n[tema.educacao]\nsituacao = "planejado"\nreferencia = "inep-2027"\nrecorte = "sede"\n')
        t = {t.id: t for t in ler_temas(local)}["educacao"]
        self.assertEqual((t.referencia, t.recorte, t.situacao), ("inep-2027", "sede", "planejado"))


class ModeloCoerenteComMotor(unittest.TestCase):
    def test_chamadas_apontam_para_workflows_do_motor(self):
        reutilizaveis = {p.name for p in (MOTOR / ".github" / "workflows").glob("*.yml")}
        for wf in (MOTOR / "modelo-local" / ".github" / "workflows").glob("*.yml"):
            nomes = re.findall(r"atlas-motor/\.github/workflows/([\w.-]+)@", wf.read_text(encoding="utf-8"))
            self.assertTrue(nomes, f"{wf.name} não chama o motor")
            for nome in nomes:
                self.assertIn(nome, reutilizaveis, f"{wf.name} chama {nome}, que não existe no motor")
                self.assertIn("workflow_call", (MOTOR / ".github" / "workflows" / nome).read_text(encoding="utf-8"))

    def test_versao_no_formato(self):
        self.assertRegex(versao_motor(), r"^v\d+\.\d+\.\d+$")

    def test_versao_registrada_no_changelog(self):
        self.assertIn(f"## {versao_motor()}", (MOTOR / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_versao_com_metricas(self):
        arq = MOTOR / "pesquisa" / "dados" / "metricas-versoes.csv"
        self.assertTrue(arq.exists(), "falta pesquisa/dados/metricas-versoes.csv")
        self.assertIn(f"\n{versao_motor()},", arq.read_text(encoding="utf-8"),
                      "rode scripts/metricas_motor.py --registrar ao lançar a versão")

    def test_citation_na_versao(self):
        self.assertIn(f"version: {versao_motor()}\n", (MOTOR / "CITATION.cff").read_text(encoding="utf-8"))


class Pesquisa(unittest.TestCase):
    def test_metricas_medem_o_motor(self):
        from metricas_motor import CAMPOS, medir
        m = medir()
        self.assertEqual(set(CAMPOS), set(m))
        self.assertGreater(m["testes"], 0)
        self.assertGreater(m["regras_validador"], 10)
        self.assertEqual(m["pranchas_catalogo"], m["consultas"])

    def test_serie_historica_a_partir_do_git(self):
        import json
        from serie_historica import serie
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "atlas-exemplo"
            shutil.copytree(MOTOR / "testes" / "exemplo", local, ignore=shutil.ignore_patterns("_construcao"))
            def git(*a):
                subprocess.run(["git", *a], cwd=local, check=True, capture_output=True)
            git("init", "-q", "-b", "main")
            git("-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
            git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "retrato 1")
            # segundo retrato: uma escola a mais
            edu = local / "dados" / "osm" / "educacao.geojson"
            dados = json.loads(edu.read_text(encoding="utf-8"))
            dados["features"].append({"type": "Feature", "properties": {"osm": "node/99", "tags": {"amenity": "school",
                                      "name": "Escola Municipal Rural do Povoado"}},
                                      "geometry": {"type": "Point", "coordinates": [-46.2702, -19.2205]}})
            edu.write_text(json.dumps(dados), encoding="utf-8")
            ret = local / "dados" / "osm" / "retrato.json"
            r = json.loads(ret.read_text(encoding="utf-8"))
            r["temas"]["educacao"]["feicoes"] = 4
            ret.write_text(json.dumps(r), encoding="utf-8")
            git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "retrato 2")
            linhas = [l for l in serie(local) if l["tema"] == "educacao"]
        self.assertEqual([l["total"] for l in linhas], [3, 4])
        self.assertEqual([l["C_t"] for l in linhas], [66.7, 100.0], "a escola rural nova completa a base oficial")


if __name__ == "__main__":
    unittest.main()
