"""Testes da comparação entre o OpenStreetMap e a base oficial (duas fontes) e das áreas."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MOTOR / "scripts"))

from comparacao import csv_texto, geojson, montar, no_escopo, quadro_resumo, tabela_so_oficial, tabela_so_osm  # noqa: E402
from comum import Tema, area_m2, ler_config, ler_temas, ponto_representativo  # noqa: E402
from indicadores import calcular  # noqa: E402


def ponto(osm: str, lon: float, lat: float, **tags) -> dict:
    return {"type": "Feature", "properties": {"osm": osm, "tags": tags},
            "geometry": {"type": "Point", "coordinates": [lon, lat]}}


FONTE = {"nome": "Catálogo de Escolas", "orgao": "INEP", "data_acesso": "2026-10-22"}
OFICIAIS = [{"id": "1", "nome": "EM A", "lat": -19.0, "lon": -46.0},
            {"id": "2", "nome": "EM B", "lat": -19.1, "lon": -46.1},
            {"id": "3", "nome": "EM C", "lat": None, "lon": None}]
FEICOES = [ponto("node/1", -46.0, -19.0, name="Escola Municipal A"), ponto("node/2", -46.2, -19.2, name="Escola Nova")]


class Comparacao(unittest.TestCase):
    def setUp(self):
        self.comp = montar(FONTE, OFICIAIS, FEICOES, [(0, 0, 12.0, 0.95)], {1: "não mapeado", 2: "sem coordenada"},
                           fora_escopo=1)

    def test_cada_item_tem_uma_situacao(self):
        self.assertEqual([o["situacao"] for o in self.comp["oficiais"]], ["ambas", "so_oficial", "so_oficial"])
        self.assertEqual([o["n"] for o in self.comp["oficiais"]], [None, 1, 2], "as lacunas são numeradas na ordem da base")
        self.assertEqual([o["osm"] for o in self.comp["so_osm"]], ["node/2"])
        self.assertEqual(self.comp["resumo"], {"oficial": 3, "osm": 2, "ambas": 1, "so_oficial": 2, "so_osm": 1,
                                               "cobertura": 33.3})

    def test_quadro_e_tabelas(self):
        quadro = quadro_resumo(self.comp)
        self.assertIn("| Itens na base oficial (INEP) | 3 |", quadro)
        self.assertIn("**33,3%**", quadro)
        self.assertIn("Outros 1 objeto(s)", quadro, "o que a base não cobre fica fora da comparação, e isso é dito")
        self.assertIn("| 1 | 2 | EM B | não mapeado |", tabela_so_oficial(self.comp))
        self.assertIn("[node/2](https://www.openstreetmap.org/node/2) | Escola Nova |", tabela_so_osm(self.comp))

    def test_arquivos_de_comparacao(self):
        feicoes = json.loads(geojson(self.comp))["features"]
        self.assertEqual(sorted(f["properties"]["situacao"] for f in feicoes), ["ambas", "so_oficial", "so_osm"],
                         "item oficial sem coordenada não vai para o mapa")
        self.assertEqual({k for f in feicoes for k in f["properties"]},
                         {"fonte", "situacao", "n", "codigo", "nome", "osm", "motivo"},
                         "da base oficial saem só código, nome e situação")
        linhas = csv_texto(self.comp).splitlines()
        self.assertEqual(len(linhas), 1 + 3 + 1, "o CSV traz todos os itens oficiais, com ou sem coordenada, e os só no OSM")
        self.assertTrue(linhas[3].startswith("so_oficial,2,3,EM C"))

    def test_escopo_da_base(self):
        filtro = ["amenity=school|kindergarten"]
        self.assertTrue(no_escopo({"amenity": "school"}, filtro))
        self.assertFalse(no_escopo({"amenity": "university"}, filtro))
        self.assertTrue(no_escopo({"amenity": "university"}, None), "sem filtro, tudo entra")
        self.assertTrue(no_escopo({"healthcare": "clinic"}, ["healthcare"]), "só a chave: qualquer valor")


class NoMunicipioDeExemplo(unittest.TestCase):
    def test_calcular_traz_a_comparacao_so_com_base_oficial(self):
        local = MOTOR / "testes" / "exemplo"
        config = ler_config(local)
        temas = {t.id: t for t in ler_temas(local)}
        educacao = calcular(local, temas["educacao"], config)
        r = educacao["comparacao"]["resumo"]
        self.assertEqual(r["ambas"] + r["so_oficial"], r["oficial"])
        self.assertEqual(r["ambas"] + r["so_osm"], r["osm"])
        self.assertEqual(educacao["completude"]["C_t"], r["cobertura"])
        self.assertNotIn("comparacao", calcular(local, temas["localizacao"], config), "tema sem base: só o OpenStreetMap")

    def test_prancha_com_duas_fontes_cita_as_duas(self):
        from construir import TRECHOS, trechos_tema
        local = MOTOR / "testes" / "exemplo"
        config = ler_config(local)
        tema = {t.id: t for t in ler_temas(local)}["educacao"]
        partes = trechos_tema(tema, calcular(local, tema, config), [("e.png", "x", "comparacao-municipio")], {}, config)
        self.assertEqual(tuple(partes), TRECHOS)
        self.assertIn("e.png", partes["comparacao-municipio"])
        self.assertIn("Comparação com a base oficial", partes["resumo"])
        self.assertIn("Fontes: OpenStreetMap", partes["fonte"])
        self.assertIn("acesso em", partes["fonte"])
        self.assertIn('data-comparacao="../_gerado/downloads/educacao-comparacao.geojson"', partes["interativo"])


class Areas(unittest.TestCase):
    QUADRA = [[-46.0, -19.0], [-45.999, -19.0], [-45.999, -18.999], [-46.0, -18.999], [-46.0, -19.0]]

    def test_area_de_poligono_e_multipoligono(self):
        um = {"type": "Polygon", "coordinates": [self.QUADRA]}
        lado_lat, lado_lon = 111.19, 111.19 * 0.9455        # 0,001 grau em metros, a 19 graus de latitude
        self.assertAlmostEqual(area_m2(um), lado_lat * lado_lon, delta=40)
        dois = {"type": "MultiPolygon", "coordinates": [[self.QUADRA], [[[x + 0.01, y] for x, y in self.QUADRA]]]}
        self.assertAlmostEqual(area_m2(dois), 2 * area_m2(um), delta=1)
        self.assertEqual(area_m2({"type": "Point", "coordinates": [0, 0]}), 0.0)
        x, y = ponto_representativo(dois)
        self.assertTrue(-46.001 < x < -45.98 and -19.001 < y < -18.998)

    def test_relacao_multipoligono_vira_area(self):
        from baixar_osm import geometria
        membro = {"type": "way", "role": "outer", "geometry": [{"lon": x, "lat": y} for x, y in self.QUADRA]}
        g = geometria({"type": "relation", "id": 1, "tags": {"type": "multipolygon", "natural": "wood"}, "members": [membro]})
        self.assertEqual(g["type"], "Polygon")
        sem_tipo = geometria({"type": "relation", "id": 2, "tags": {"route": "bus"}, "members": [membro]})
        self.assertEqual(sem_tipo["type"], "Point", "relação que não é área continua como ponto")

    def test_indicador_de_areas_e_de_linhas(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp)
            (local / "dados" / "osm").mkdir(parents=True)
            feicoes = [{"type": "Feature", "properties": {"osm": "way/1", "tags": {"natural": "water"}},
                        "geometry": {"type": "Polygon", "coordinates": [self.QUADRA]}},
                       {"type": "Feature", "properties": {"osm": "way/2", "tags": {"waterway": "stream", "name": "Córrego X"}},
                        "geometry": {"type": "LineString", "coordinates": [[-46.0, -19.0], [-46.0, -18.991]]}}]
            (local / "dados" / "osm" / "hidrografia.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": feicoes}), encoding="utf-8")
            tema = Tema(id="hidrografia", numero=10, titulo="Hidrografia", situacao="em-andamento", consulta="",
                        referencia="interno", recorte="municipio", mapa="areas", indicadores=("areas", "linhas"))
            linhas = dict(calcular(local, tema, {"municipio": {"nome": "X"}})["linhas"])
            self.assertEqual(linhas["Área mapeada"], "1,2 ha")
            self.assertEqual(linhas["Comprimento das linhas (dentro do município)"], "1,0 km")
            self.assertEqual(linhas["Comprimento com nome"], "1,0 km (100%)")


if __name__ == "__main__":
    unittest.main()
