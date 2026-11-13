"""Testes da v0.14.0: classes de cor dos temas, atalhos para o editor do OpenStreetMap, índice do
Mapa geral, grade de coordenadas dos mapas e contorno do estado para o encarte (sem rede)."""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MOTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MOTOR / "scripts"))

import baixar_bases  # noqa: E402
import construir  # noqa: E402
from comparacao import link_editor, tabela_so_oficial, tabela_so_osm  # noqa: E402
from comum import Tema, casa_regras, classe_do_objeto, ler_temas, ler_toml  # noqa: E402
from validar import erros_visuais  # noqa: E402

EXEMPLO = MOTOR / "testes" / "exemplo"
CLASSES = (("Lavoura", "#E3B23C", ("landuse=farmland|orchard",)), ("Mata", "#1B7837", ("natural=wood", "landuse=forest")))


def tema(**extra) -> Tema:
    return Tema(id="uso", numero=11, titulo="Uso do solo", situacao="publicado", consulta="uso.overpassql",
                referencia="interno", recorte="municipio", **extra)


class ClassesDeCor(unittest.TestCase):
    def test_regras(self):
        self.assertTrue(casa_regras({"landuse": "orchard"}, ["landuse=farmland|orchard"]))
        self.assertFalse(casa_regras({"landuse": "orchards"}, ["landuse=farmland|orchard"]), "o valor casa inteiro")
        self.assertTrue(casa_regras({"healthcare": "clinic"}, ["healthcare"]), "só a chave: qualquer valor")
        self.assertFalse(casa_regras({"amenity": "school"}, []))

    def test_vale_a_primeira_classe_que_casa(self):
        self.assertEqual(classe_do_objeto(CLASSES, {"landuse": "farmland"}), ("Lavoura", "#E3B23C"))
        self.assertEqual(classe_do_objeto(CLASSES, {"landuse": "forest"}), ("Mata", "#1B7837"))
        self.assertIsNone(classe_do_objeto(CLASSES, {"landuse": "quarry"}), "sem classe: fica na cor do tema")
        self.assertIsNone(tema().classe({"landuse": "farmland"}), "tema sem classes")
        self.assertEqual(tema(classes=CLASSES).classe({"natural": "wood"})[0], "Mata")

    def test_catalogo_traz_as_classes_do_uso_do_solo(self):
        uso = next(t for t in ler_temas(EXEMPLO) if t.id == "uso-do-solo")
        self.assertGreaterEqual(len(uso.classes), 6)
        self.assertEqual(uso.classe({"landuse": "orchard"})[0], "Café, pomar e outras culturas perenes")
        cores = [c for _, c, _ in uso.classes]
        self.assertEqual(len(cores), len(set(cores)), "cada classe com a sua cor")
        for t in ler_toml(MOTOR / "catalogo" / "temas.toml")["tema"]:
            self.assertEqual(erros_visuais(t), [], t["id"])

    def test_validador_recusa_classe_malformada(self):
        erros = erros_visuais({"classe": [{"rotulo": "Lavoura", "cor": "amarelo", "filtro": ["landuse=farmland"]},
                                          {"rotulo": "Mata", "cor": "#1B7837", "filtro": "natural=wood"},
                                          {"cor": "#000000", "filtro": ["a=b"]}]})
        self.assertEqual(len(erros), 3)
        self.assertIn("#RRGGBB", erros[0])
        self.assertIn("lista de regras", erros[1])
        self.assertIn("rotulo", erros[2])


class AtalhosParaOEditor(unittest.TestCase):
    def test_link(self):
        self.assertEqual(link_editor("way/123"), "https://www.openstreetmap.org/edit?editor=id&way=123")
        self.assertEqual(link_editor(lat=-19.19, lon=-46.2412345),
                         "https://www.openstreetmap.org/edit?editor=id#map=19/-19.19000/-46.24123")
        self.assertEqual(link_editor("way/1); alert(1"), "", "identificador estranho não vira endereço")
        self.assertEqual(link_editor(), "")

    def test_tabelas(self):
        comp = {"oficiais": [{"situacao": "so_oficial", "n": 1, "id": "31", "nome": "EM A", "motivo": "não mapeado",
                              "lat": -19.2, "lon": -46.2},
                             {"situacao": "so_oficial", "n": 2, "id": "32", "nome": "EM B", "motivo": "sem coordenada",
                              "lat": None, "lon": None}],
                "so_osm": [{"osm": "node/7", "nome": "Escola X", "lat": -19.2, "lon": -46.2}]}
        faltas = tabela_so_oficial(comp)
        self.assertIn("| não mapeado | [mapear](https://www.openstreetmap.org/edit?editor=id#map=19/-19.20000/-46.20000) |", faltas)
        self.assertIn("| sem coordenada | — |", faltas, "sem coordenada não há onde abrir o editor")
        self.assertIn("[editar](https://www.openstreetmap.org/edit?editor=id&node=7)", tabela_so_osm(comp))


class IndiceDoMapaGeral(unittest.TestCase):
    def test_tamanho(self):
        self.assertEqual(construir.tamanho_legivel(10_000), "", "arquivo leve não leva aviso")
        self.assertEqual(construir.tamanho_legivel(430 * 1024), "430 KB")
        self.assertEqual(construir.tamanho_legivel(3_100_000), "3,1 MB")

    def test_indice(self):
        with tempfile.TemporaryDirectory() as pasta:
            downloads = Path(pasta)
            (downloads / "educacao.geojson").write_text("{}", encoding="utf-8")
            (downloads / "uso.geojson").write_bytes(b" " * (400 * 1024))
            educacao = Tema(id="educacao", numero=3, titulo="Educação", situacao="publicado", consulta="e.overpassql",
                            referencia="inep", recorte="ambos")
            uso = tema(mapa="areas", classes=CLASSES)
            sem_dados = Tema(id="saude", numero=4, titulo="Saúde", situacao="publicado", consulta="s.overpassql",
                             referencia="interno", recorte="ambos")
            comp = {"modo": "itens", "fonte": {"orgao": "INEP", "nome": "Catálogo de Escolas"}}
            indice = construir.indice_geral([(educacao, {"comparacao": comp}), (uso, {}), (sem_dados, {})], downloads)
        self.assertEqual(indice["limite"], "_gerado/downloads/limite.geojson")
        self.assertEqual([t["id"] for t in indice["temas"]], ["educacao", "uso"], "tema sem arquivo fica fora")
        e, u = indice["temas"]
        self.assertTrue(e["inicial"], "pontos e leve: abre marcado")
        self.assertEqual(e["prancha"], "pranchas/03-educacao.html")
        self.assertEqual(e["comparacao"], {"arquivo": "_gerado/downloads/educacao-comparacao.geojson", "modo": "itens",
                                           "rotulo": "Faltam no mapa (INEP)"})
        self.assertFalse(u["inicial"], "áreas: só quando o leitor marca")
        self.assertEqual(u["tamanho"], "400 KB")
        self.assertEqual(u["classes"][0], ["Lavoura", "#E3B23C", ["landuse=farmland|orchard"]])
        self.assertNotIn("comparacao", u)
        json.dumps(indice)                        # vai para um arquivo JSON

    def test_trecho_do_capitulo(self):
        com_site = construir.trecho_mapa_geral("https://exemplo.org/atlas/")
        self.assertIn('class="atlas-mapa atlas-mapa-geral"', com_site)
        self.assertIn('data-indice="_gerado/downloads/mapa-geral.json"', com_site)
        self.assertIn("<https://exemplo.org/atlas/mapa-geral.html>", com_site, "o PDF diz onde o mapa está")
        self.assertIn("na versão em site", construir.trecho_mapa_geral(""))

    def test_classes_no_mapa_da_prancha(self):
        html_tema = construir.mapa_interativo(tema(mapa="areas", classes=(("Café \"fino\"", "#A6532B", ("landuse=orchard",)),)), False)
        self.assertIn("data-classes=", html_tema)
        self.assertNotIn('"fino"', html_tema, "aspas das classes escapadas no atributo")
        self.assertNotIn("data-classes", construir.mapa_interativo(tema(), False))

    def test_livro(self):
        modelo = (MOTOR / "livro" / "_quarto.modelo.yml").read_text(encoding="utf-8")
        self.assertIn("    - mapa-geral.qmd\n", modelo)
        self.assertIn("_gerado/mapa-geral.md", (MOTOR / "livro" / "mapa-geral.qmd").read_text(encoding="utf-8"))
        script = (MOTOR / "livro" / "mapa.html").read_text(encoding="utf-8")
        self.assertIn("atlas-mapa-geral", script)
        self.assertNotIn("innerHTML", script, "dados do OSM e das bases entram como texto, nunca como HTML")


class GradeDeCoordenadas(unittest.TestCase):
    def setUp(self):
        try:
            import mapas
        except ImportError:                       # sem matplotlib
            self.skipTest("matplotlib não instalado")
        self.mapas = mapas

    def test_passo(self):
        self.assertEqual(self.mapas.passo_da_grade(0.40), 300, "município: 5 minutos")
        self.assertEqual(self.mapas.passo_da_grade(0.03), 30, "sede: 30 segundos")
        self.assertEqual(self.mapas.passo_da_grade(0.0001), 5, "nunca abaixo do menor passo")

    def test_rotulo(self):
        self.assertEqual(self.mapas.rotulo_da_grade(-69300, "lat", 300), "19°15′S")
        self.assertEqual(self.mapas.rotulo_da_grade(-166470, "lon", 30), "46°14′30″W")
        self.assertEqual(self.mapas.rotulo_da_grade(3600, "lat", 3600), "1°00′N")

    def test_sem_contorno_do_estado_nao_ha_encarte(self):
        with tempfile.TemporaryDirectory() as pasta:
            self.assertEqual(self.mapas.ler_uf(Path(pasta)), [])


class ContornoDoEstado(unittest.TestCase):
    def test_base_uf(self):
        malha = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"codarea": "31"},
             "geometry": {"type": "Polygon", "coordinates": [[[-51, -23], [-40, -23], [-40, -14], [-51, -14], [-51, -23]]]}}]}
        with tempfile.TemporaryDirectory() as pasta:
            local, cache = Path(pasta) / "municipio", Path(pasta) / "cache.geojson"
            cache.write_bytes(gzip.compress(json.dumps(malha).encode()))   # a API responde compactada
            with mock.patch.object(baixar_bases, "baixar", return_value=cache):
                resumo = baixar_bases.base_uf(local, {"municipio": {"uf": "MG", "ibge": 3155504}}, False)
            self.assertIn("MG", resumo)
            fonte = ler_toml(local / "dados" / "oficiais" / "uf" / "fonte.toml")
            self.assertEqual((fonte["arquivo"], fonte["papel"], fonte["orgao"]), ("uf.geojson", "encarte", "IBGE"))
            gravado = json.loads((local / "dados" / "oficiais" / "uf" / "uf.geojson").read_text(encoding="utf-8"))
            self.assertEqual(gravado["features"][0]["properties"], {"uf": "MG"})

    def test_malha_vazia_e_erro(self):
        with tempfile.TemporaryDirectory() as pasta:
            cache = Path(pasta) / "cache.geojson"
            cache.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
            with mock.patch.object(baixar_bases, "baixar", return_value=cache), self.assertRaises(ValueError):
                baixar_bases.base_uf(Path(pasta) / "m", {"municipio": {"uf": "MG"}}, False)


if __name__ == "__main__":
    unittest.main()
