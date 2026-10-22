"""Testes dos scripts de manutenção (novo_local, ativar_tema, atualizar_motor), da
combinação catálogo + município e da coerência entre o modelo municipal e o motor."""
from __future__ import annotations

import csv
import io
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
                          encoding="utf-8", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})


class ComMunicipio(unittest.TestCase):
    """Base: pasta temporária e um município novo criado por novo_local.py."""

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


class Scripts(ComMunicipio):
    def test_novo_local_cria_repositorio_valido(self):
        local = self.novo()
        texto = (local / "atlas.toml").read_text(encoding="utf-8")
        self.assertIn('nome = "Cidade Teste"', texto)
        self.assertIn(f'versao = "{versao_motor()}"', texto)
        self.assertIn('slug = "cidade-teste"', texto)
        self.assertIn('hospedagem = "pages"', texto)
        self.assertIn('url = "https://youthmappers-ufv.github.io/atlas-cidade-teste/"', texto)
        self.assertTrue((local / ".gitignore").exists())
        self.assertTrue((local / "atlas" / "pranchas" / "01-localizacao.qmd").exists())
        restos = [p for p in local.rglob("*") if p.is_file() and "@@" in p.read_text(encoding="utf-8", errors="ignore")]
        self.assertEqual(restos, [], "marcadores @@ não substituídos")
        self.assertEqual(verificar(local).erros, [])

    def test_novo_local_privado_sem_pages(self):
        destino = self.dir / "atlas-privado"
        r = rodar("novo_local.py", "--nome", "Cidade Teste", "--ibge", "1234567", "--sem-rede", "--relacao", "42",
                  "--bbox=-19.3,-46.4,-19.1,-46.2", "--sede-bbox=-19.21,-46.31,-19.19,-46.29",
                  "--destino", str(destino), "--privado")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('hospedagem = "artefato"', (destino / "atlas.toml").read_text(encoding="utf-8"))
        self.assertEqual(verificar(destino).erros, [])

    def test_novo_local_nao_sobrescreve(self):
        self.novo()
        r = rodar("novo_local.py", "--nome", "Cidade Teste", "--ibge", "1234567", "--sem-rede", "--relacao", "42",
                  "--bbox=-19.3,-46.4,-19.1,-46.2", "--sede-bbox=-19.21,-46.31,-19.19,-46.29",
                  "--destino", str(self.dir / "atlas-cidade-teste"))
        self.assertNotEqual(r.returncode, 0)

    def test_agendamento_proprio_por_municipio(self):
        from novo_local import horario
        local = self.novo()
        hora, minuto = horario("cidade-teste")
        for wf in ("publicar.yml", "atualizar-dados.yml"):
            texto = (local / ".github" / "workflows" / wf).read_text(encoding="utf-8")
            self.assertRegex(texto, rf'cron: "{minuto} {hora} \d+ \* \*"')
        horarios = {horario(s) for s in ("rio-paranaiba", "sao-gotardo", "carmo-do-paranaiba", "patos-de-minas")}
        self.assertEqual(len(horarios), 4, "municípios da região não podem coincidir no agendamento")
        self.assertTrue(all(8 <= h <= 11 and 0 <= m <= 59 for h, m in horarios))

    def test_quarto_sem_site_url_quando_hospedagem_artefato(self):
        import tomllib
        from construir import escrever_quarto
        config = tomllib.loads((MOTOR / "testes" / "exemplo" / "atlas.toml").read_text(encoding="utf-8"))
        escrever_quarto(self.dir, config, [])
        self.assertIn("site-url: https://youthmappers-ufv.github.io/atlas-exemplo/",
                      (self.dir / "_quarto.yml").read_text(encoding="utf-8"))
        config["publicacao"].update(hospedagem="artefato", url="")
        escrever_quarto(self.dir, config, [])
        self.assertNotIn("site-url", (self.dir / "_quarto.yml").read_text(encoding="utf-8"),
                         "o Quarto recusa site-url vazio")

    def test_limpar_preserva_cache_do_quarto(self):
        from construir import limpar
        livro = self.dir / "livro"
        for rel in (".quarto/cache/kv", "_site/index.html", "pranchas/01.qmd", "_gerado/a.md", "index.qmd"):
            (livro / rel).parent.mkdir(parents=True, exist_ok=True)
            (livro / rel).write_text("x", encoding="utf-8")
        limpar(livro)
        self.assertEqual(sorted(p.name for p in livro.iterdir()), [".quarto", "_site"])
        self.assertTrue((livro / ".quarto" / "cache" / "kv").exists())

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


INEP_CABECALHO = ("Restrição de Atendimento,Escola,Código INEP,UF,Município,Localização,Localidade Diferenciada,"
                  "Categoria Administrativa,Endereço,Telefone,Dependência Administrativa,Categoria Escola Privada,"
                  "Conveniada Poder Público,Regulamentação pelo Conselho de Educação,Porte da Escola,"
                  "Etapas e Modalidade de Ensino Oferecidas,Outras Ofertas Educacionais,Latitude,Longitude")
INEP_LINHAS = [   # sintéticas, no formato do Catálogo de Escolas
    'ESCOLA EM FUNCIONAMENTO E SEM RESTRIÇÃO DE ATENDIMENTO,EM CENTRO,30000001,MG,Cidade Teste,Urbana,Não,Pública,'
    '"RUA A, 10 CENTRO. 38800-000 Cidade Teste - MG.",(34) 99999-0000,Municipal,Não Informado,Não,Sim,,'
    '"Educação Infantil, Ensino Fundamental",,-19.2001,-46.3001',
    'ESCOLA PARALISADA,EE FAZENDA,30000002,MG,Cidade Teste,Rural,Não Informado,Pública,'
    '"FAZ B, 0 38800-000 Cidade Teste - MG.",,Estadual,Não Informado,Não,,,,,                              ,   ',
    'ESCOLA EM FUNCIONAMENTO E SEM RESTRIÇÃO DE ATENDIMENTO,EM SEM PONTO,30000003,MG,Cidade Teste,Urbana,Não,Pública,'
    '"RUA C, 5 38800-000 Cidade Teste - MG.",,Municipal,Não Informado,Não,Sim,,Ensino Fundamental,,      ,      ',
    'ESCOLA EM FUNCIONAMENTO E SEM RESTRIÇÃO DE ATENDIMENTO,CRECHE LONGE,30000004,MG,Cidade Teste,Urbana,Não,Pública,'
    '"RUA D, 1 38800-000 Cidade Teste - MG.",,Municipal,Não Informado,Não,Sim,,Educação Infantil,,-18.5,-46.3',
    'ESCOLA EM FUNCIONAMENTO E SEM RESTRIÇÃO DE ATENDIMENTO,EM VIZINHA,30000005,MG,Outra Cidade,Urbana,Não,Pública,'
    '"RUA E, 2 38800-000 Outra Cidade - MG.",,Municipal,Não Informado,Não,Sim,,Ensino Fundamental,,-19.25,-46.35',
    'ESCOLA EM FUNCIONAMENTO E SEM RESTRIÇÃO DE ATENDIMENTO,EM HOMONIMA,30000006,SP,Cidade Teste,Urbana,Não,Pública,'
    '"RUA F, 3 11000-000 Cidade Teste - SP.",,Municipal,Não Informado,Não,Sim,,Ensino Fundamental,,-23.5,-46.6',
]


class PrepararBase(ComMunicipio):
    """preparar_base.py, com o arquivo no formato do órgão e defeitos plantados."""

    def original(self, linhas=INEP_LINHAS, cabecalho=INEP_CABECALHO, separador=",", codificacao="utf-8-sig") -> Path:
        texto = "\n".join([cabecalho, *linhas]) + "\n"
        if separador == ";":   # como nas exportações com vírgula decimal
            saida = io.StringIO()
            w = csv.writer(saida, delimiter=";", lineterminator="\n")
            for campos in csv.reader(io.StringIO(texto)):
                w.writerow([c.replace(".", ",") if re.fullmatch(r"-?\d+\.\d+", c) else c for c in campos])
            texto = saida.getvalue()
        arq = self.dir / "baixado.csv"
        arq.write_bytes(texto.encode(codificacao))
        return arq

    def preparar(self, local: Path, arq: Path, *extra: str) -> subprocess.CompletedProcess:
        return rodar("preparar_base.py", "inep", str(arq), "--data", "2026-10-22", "--local", str(local), *extra)

    def escolas(self, local: Path) -> list[dict]:
        with (local / "dados" / "oficiais" / "inep" / "escolas.csv").open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_inep_filtra_municipio_e_paralisadas_e_tira_telefone(self):
        local = self.novo()
        r = self.preparar(local, self.original())
        self.assertEqual(r.returncode, 0, r.stderr)
        escolas = self.escolas(local)
        self.assertEqual([e["codigo_inep"] for e in escolas], ["30000001", "30000003", "30000004"])
        self.assertNotIn("telefone", " ".join(escolas[0]).lower())
        self.assertNotIn("99999", (local / "dados" / "oficiais" / "inep" / "escolas.csv").read_text(encoding="utf-8"))
        self.assertEqual((escolas[0]["latitude"], escolas[0]["longitude"]), ("-19.2001", "-46.3001"))
        self.assertEqual((escolas[1]["latitude"], escolas[1]["longitude"]), ("", ""))
        self.assertIn("EM SEM PONTO", r.stdout)                 # avisa quem está sem coordenada
        self.assertIn("CRECHE LONGE", r.stdout)                 # e quem está fora da área
        fonte = (local / "dados" / "oficiais" / "inep" / "fonte.toml").read_text(encoding="utf-8")
        self.assertIn("data_acesso = 2026-10-22", fonte)
        self.assertIn("1 escolas paralisadas retiradas", fonte)
        rel = verificar(local)
        self.assertEqual(rel.erros, [])
        self.assertTrue(any("fora da área" in a for a in rel.avisos))

    def test_inep_todas_mantem_paralisadas(self):
        local = self.novo()
        self.assertEqual(self.preparar(local, self.original(), "--todas").returncode, 0)
        self.assertIn("30000002", [e["codigo_inep"] for e in self.escolas(local)])

    def test_inep_latin1_com_ponto_e_virgula_e_virgula_decimal(self):
        local = self.novo()
        r = self.preparar(local, self.original(separador=";", codificacao="cp1252"))
        self.assertEqual(r.returncode, 0, r.stderr)
        escolas = self.escolas(local)
        self.assertEqual(escolas[0]["escola"], "EM CENTRO")
        self.assertEqual((escolas[0]["latitude"], escolas[0]["longitude"]), ("-19.2001", "-46.3001"))
        self.assertEqual(verificar(local).erros, [])

    def test_formato_mudado_nao_grava_nada(self):
        local = self.novo()
        r = self.preparar(local, self.original(cabecalho=INEP_CABECALHO.replace("Latitude", "Lat")))
        self.assertEqual(r.returncode, 2)
        self.assertIn("faltam as colunas: Latitude", r.stderr)
        self.assertFalse((local / "dados" / "oficiais" / "inep").exists())

    def test_fora_do_municipio_ou_sem_arquivo(self):
        r = self.preparar(self.dir, self.original())
        self.assertEqual(r.returncode, 2)
        self.assertIn("falta atlas.toml", r.stderr)
        r = self.preparar(self.novo(), self.dir / "nao-existe.csv")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Arquivo não encontrado", r.stderr)

    def test_arquivo_de_outro_municipio(self):
        local = self.novo()
        r = self.preparar(local, self.original(linhas=INEP_LINHAS[4:5]))
        self.assertEqual(r.returncode, 2)
        self.assertIn("Nenhuma linha de Cidade Teste", r.stderr)

    def test_nao_substitui_sem_pedir(self):
        local = self.novo()
        self.assertEqual(self.preparar(local, self.original()).returncode, 0)
        r = self.preparar(local, self.original(linhas=INEP_LINHAS[:1]))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(self.escolas(local)), 3)
        self.assertEqual(self.preparar(local, self.original(linhas=INEP_LINHAS[:1]), "--substituir").returncode, 0)
        self.assertEqual(len(self.escolas(local)), 1)


class CatalogoDeTemas(unittest.TestCase):
    """Todo tema do catálogo traz o que o motor precisa para gerar a prancha sem código novo."""

    def test_campos_completos_e_validos(self):
        import tomllib
        from validar import erros_visuais
        catalogo = tomllib.loads((MOTOR / "catalogo" / "temas.toml").read_text(encoding="utf-8"))["tema"]
        ids, numeros = set(), set()
        for t in catalogo:
            with self.subTest(tema=t.get("id")):
                faltam = {"id", "numero", "titulo", "consulta", "referencia", "recorte", "cor", "mapa", "indicadores"} - set(t)
                self.assertEqual(faltam, set())
                self.assertEqual(erros_visuais(t), [])
                self.assertTrue((MOTOR / "catalogo" / "consultas" / t["consulta"]).is_file())
                self.assertNotIn(t["id"], ids)
                self.assertNotIn(t["numero"], numeros)
                self.assertLess(t["numero"], 20, "números 20 em diante são das pranchas próprias dos municípios")
                ids.add(t["id"]); numeros.add(t["numero"])

    def test_trechos_somam_a_prancha_inteira(self):
        from comum import Tema
        from construir import TRECHOS, trecho_tema, trechos_tema
        tema = Tema(id="educacao", numero=3, titulo="Educação", situacao="em-andamento", consulta="",
                    referencia="inep", recorte="ambos")
        res = {"linhas": [("Objetos no OpenStreetMap", "3")], "lacunas": [{"id": "1", "nome": "E.E. X"}]}
        figuras = [("educacao-municipio.png", "Educação: município", "municipio")]
        config = {"publicacao": {"atribuicao": "© OSM"}}
        partes = trechos_tema(tema, res, figuras, {}, config)
        self.assertEqual(tuple(partes), TRECHOS)
        self.assertEqual(partes["mapa-sede"], "", "recorte sem mapa fica vazio, para o include não falhar")
        self.assertIn("educacao-municipio.png", partes["mapa-municipio"])
        self.assertIn("E.E. X", partes["lacunas"])
        inteira = trecho_tema(tema, res, figuras, {}, config)
        self.assertEqual(inteira, "\n".join(p for p in partes.values() if p))
        ordem = [inteira.index(x) for x in ("educacao-municipio.png", "Pontos cheios", "Indicador", "E.E. X", "Fonte:")]
        self.assertEqual(ordem, sorted(ordem), "ordem da prancha: mapas, legenda, indicadores, lacunas, fonte")


class ModeloCoerenteComMotor(unittest.TestCase):
    def test_chamadas_apontam_para_workflows_do_motor(self):
        reutilizaveis = {p.name for p in (MOTOR / ".github" / "workflows").glob("*.yml")}
        for wf in (MOTOR / "modelo-local" / ".github" / "workflows").glob("*.yml"):
            nomes = re.findall(r"atlas-motor/\.github/workflows/([\w.-]+)@", wf.read_text(encoding="utf-8"))
            self.assertTrue(nomes, f"{wf.name} não chama o motor")
            for nome in nomes:
                self.assertIn(nome, reutilizaveis, f"{wf.name} chama {nome}, que não existe no motor")
                self.assertIn("workflow_call", (MOTOR / ".github" / "workflows" / nome).read_text(encoding="utf-8"))

    def test_publicacao_respeita_hospedagem(self):
        """Todo passo que envia ao gh-pages depende de publicacao.hospedagem = "pages" e usa o
        token do próprio repositório (nada de chave de deploy nem repositório externo)."""
        texto = (MOTOR / ".github" / "workflows" / "publicar.yml").read_text(encoding="utf-8")
        passos = [p for p in re.split(r"\n      - (?=name:|uses:)", texto) if "actions-gh-pages" in p]
        self.assertEqual(len(passos), 2)
        for p in passos:
            self.assertIn("steps.local.outputs.hospedagem == 'pages'", re.search(r"\n\s+if: (.+)", p).group(1))
            self.assertIn("github_token:", p)
            self.assertNotIn("external_repository", p)
            self.assertNotIn("deploy_key", p)
        self.assertIn("print(f\"hospedagem=", texto)

    def test_versao_no_formato(self):
        self.assertRegex(versao_motor(), r"^v\d+\.\d+\.\d+$")

    def test_versao_registrada_no_changelog(self):
        self.assertIn(f"## {versao_motor()}", (MOTOR / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_citation_na_versao(self):
        self.assertIn(f"version: {versao_motor()}\n", (MOTOR / "CITATION.cff").read_text(encoding="utf-8"))


class SerieHistorica(unittest.TestCase):
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


class GanchoPrePush(unittest.TestCase):
    """O gancho instalado no município bloqueia o push quando o validador acusa erro."""

    def test_push_com_dado_pessoal_e_bloqueado(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "atlas-exemplo"
            shutil.copytree(MOTOR / "testes" / "exemplo", local, ignore=shutil.ignore_patterns("_construcao"))
            env = {**os.environ, "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
                   "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                   "GIT_COMMITTER_EMAIL": "t@t"}
            def git(*a):
                return subprocess.run(["git", *a], cwd=local, capture_output=True, text=True, env=env)
            git("init", "-q", "-b", "main")
            git("add", "-A")
            git("commit", "-q", "-m", "inicial")
            subprocess.run(["git", "init", "-q", "--bare", str(Path(tmp) / "remoto.git")], check=True)
            git("remote", "add", "origin", str(Path(tmp) / "remoto.git"))
            self.assertEqual(rodar("instalar_ganchos.py", "--local", str(local)).returncode, 0)
            self.assertEqual(git("push", "-q", "origin", "main").returncode, 0, "push limpo deve passar")
            with (local / "dados" / "curados" / "levantamentos-campo.csv").open("a", encoding="utf-8") as f:
                f.write("LC-2027-001,2027-02-10,educacao,E.E. X,confirmado,node/1,,-19.20,-46.25,fulano@exemplo.com\n")
            git("commit", "-qam", "dado pessoal")
            self.assertNotEqual(git("push", "-q", "origin", "main").returncode, 0, "push com e-mail deve ser bloqueado")


def tag_disponivel(tag: str) -> bool:
    return subprocess.run(["git", "-C", str(MOTOR), "rev-parse", "--verify", "-q", f"refs/tags/{tag}"],
                          capture_output=True).returncode == 0


class VersaoDeclarada(unittest.TestCase):
    """Localmente, os scripts rodam na versão do motor declarada no atlas.toml do município."""
    ANTIGA = "v0.3.0"                    # qualquer tag anterior à versão atual

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.local = self.dir / "atlas-exemplo"
        shutil.copytree(MOTOR / "testes" / "exemplo", self.local, ignore=shutil.ignore_patterns("_construcao"))
        self.env = {**__import__("os").environ, "ATLAS_MOTOR_CACHE": str(self.dir / "cache"),
                    "PYTHONIOENCODING": "utf-8"}
        self.env.pop("ATLAS_MOTOR_ATUAL", None)

    def tearDown(self):
        self._tmp.cleanup()

    def declarar(self, versao: str) -> None:
        arq = self.local / "atlas.toml"
        arq.write_text(re.sub(r'(?m)^versao = "[^"]+"', f'versao = "{versao}"', arq.read_text(encoding="utf-8")),
                       encoding="utf-8")

    def validar(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPTS / "validar.py"), "--local", str(self.local), *extra],
                              capture_output=True, text=True, encoding="utf-8", env=self.env)

    def test_versao_antiga_vem_da_tag(self):
        if not tag_disponivel(self.ANTIGA):
            self.skipTest(f"tag {self.ANTIGA} ausente (checkout raso)")
        self.declarar(self.ANTIGA)
        r = self.validar()
        self.assertIn(f"declara o motor {self.ANTIGA}", r.stderr)
        self.assertTrue((self.dir / "cache" / self.ANTIGA / "scripts" / "validar.py").exists())
        self.assertEqual((self.dir / "cache" / self.ANTIGA / "VERSAO").read_text(encoding="utf-8").strip(), self.ANTIGA)

    def test_motor_atual_ignora_a_declarada(self):
        self.declarar(self.ANTIGA)
        r = self.validar("--motor-atual")
        self.assertNotIn("declara o motor", r.stderr)
        self.assertFalse((self.dir / "cache").exists())

    def test_tag_inexistente_explica_o_que_fazer(self):
        self.declarar("v9.9.9")
        r = self.validar()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fetch --tags", r.stderr)


if __name__ == "__main__":
    unittest.main()
