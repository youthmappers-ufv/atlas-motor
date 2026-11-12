"""Testes do download e preparo das bases oficiais (baixar_bases.py, sem rede) e das
comparações por contagem e por nomes."""
from __future__ import annotations

import io
import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MOTOR / "scripts"))

from baixar_bases import geometria_gpkg, gravar_fonte, ler_dbf, linhas_shp  # noqa: E402
from comparacao import (classe_razao, csv_modo, geojson_modo, montar_contagem, montar_nomes, nome_de_rua, quadro,  # noqa: E402
                        resumo_curto, tabela_faltas, tabela_sobras)
from comum import ler_toml  # noqa: E402
from validar import verificar  # noqa: E402

QUADRA = [(-46.0, -19.0), (-45.99, -19.0), (-45.99, -18.99), (-46.0, -18.99), (-46.0, -19.0)]


def wkb_poligono(anel) -> bytes:
    return (struct.pack("<BII", 1, 3, 1) + struct.pack("<I", len(anel))
            + b"".join(struct.pack("<dd", x, y) for x, y in anel))


class FormatosDosOrgaos(unittest.TestCase):
    def test_geometria_de_geopackage(self):
        cabecalho = b"GP" + bytes([0, 0b00000011]) + struct.pack("<i", 4674) + struct.pack("<4d", 0, 0, 0, 0)
        g = geometria_gpkg(cabecalho + wkb_poligono(QUADRA))
        self.assertEqual(g["type"], "Polygon")
        self.assertEqual(g["coordinates"][0][0], [-46.0, -19.0])
        multi = struct.pack("<BII", 1, 6, 2) + wkb_poligono(QUADRA) + wkb_poligono(QUADRA)
        self.assertEqual(geometria_gpkg(cabecalho + multi)["type"], "MultiPolygon")
        with self.assertRaises(ValueError):
            geometria_gpkg(b"XX" + bytes(40))

    def test_linha_de_shapefile_e_cabecalho_de_dbf(self):
        pontos = [(-46.0, -19.0), (-46.001, -19.0), (-46.002, -19.001)]
        registro = (struct.pack("<i", 3) + struct.pack("<4d", 0, 0, 0, 0) + struct.pack("<ii", 1, len(pontos))
                    + struct.pack("<i", 0) + b"".join(struct.pack("<dd", x, y) for x, y in pontos))
        self.assertEqual(linhas_shp(registro), [[[-46.0, -19.0], [-46.001, -19.0], [-46.002, -19.001]]])
        self.assertEqual(linhas_shp(struct.pack("<i", 1) + bytes(16)), [], "ponto não é linha")
        campo = lambda nome, tam: nome.encode().ljust(11, b"\0") + b"C" + bytes(4) + bytes([tam]) + bytes(15)  # noqa: E731
        dbf = bytes(4) + struct.pack("<IHH", 7, 32 + 2 * 32 + 1, 77) + bytes(20) + campo("CD_SETOR", 16) + campo("NM_LOG", 60) + b"\r"
        campos, n, tam_cab, tam_reg = ler_dbf(io.BytesIO(dbf))
        self.assertEqual((campos, n, tam_cab, tam_reg), ([("CD_SETOR", 16), ("NM_LOG", 60)], 7, 97, 77))

    def test_fonte_toml_gravado_e_legivel(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp:
            gravar_fonte(Path(tmp), {"nome": 'Base "X"', "data_acesso": date(2026, 11, 12), "filtro_osm": ["highway"]},
                         {"nome": "logradouro"})
            fonte = ler_toml(Path(tmp) / "fonte.toml")
            self.assertEqual(fonte["nome"], 'Base "X"')
            self.assertEqual(str(fonte["data_acesso"]), "2026-11-12")
            self.assertEqual(fonte["filtro_osm"], ["highway"])
            self.assertEqual(fonte["colunas"], {"nome": "logradouro"})


def predio(osm: str, x: float, y: float) -> dict:
    return {"type": "Feature", "properties": {"osm": osm, "tags": {"building": "yes"}},
            "geometry": {"type": "Point", "coordinates": [x, y]}}


def via(osm: str, nome: str) -> dict:
    return {"type": "Feature", "properties": {"osm": osm, "tags": {"highway": "residential", "name": nome}},
            "geometry": {"type": "LineString", "coordinates": [[-46.0, -19.0], [-46.001, -19.0]]}}


class PorContagem(unittest.TestCase):
    def setUp(self):
        outra = [(x + 0.02, y) for x, y in QUADRA]
        unidades = [{"type": "Feature", "properties": {"setor": "A", "situacao": "Urbana"},
                     "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in QUADRA]]}},
                    {"type": "Feature", "properties": {"setor": "B", "situacao": "Rural"},
                     "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in outra]]}}]
        feicoes = [predio("way/1", -45.995, -18.995), predio("way/2", -45.996, -18.996), predio("way/3", -45.975, -18.995),
                   predio("way/4", -45.5, -18.5)]
        fonte = {"nome": "CNEFE", "orgao": "IBGE", "data_acesso": "2026-11-12", "rotulo_oficial": "Endereços",
                 "rotulo_osm": "Edificações"}
        self.comp = montar_contagem(fonte, {"A": 4, "B": 10}, unidades, feicoes)

    def test_conta_por_unidade_e_numera_pela_falta(self):
        por = {u["unidade"]: u for u in self.comp["unidades"]}
        self.assertEqual((por["A"]["osm"], por["A"]["razao"], por["B"]["osm"], por["B"]["razao"]), (2, 50.0, 1, 10.0))
        self.assertEqual(por["B"]["n"], 1, "o setor com a maior falta vem primeiro")
        self.assertEqual(self.comp["fora"], 1, "objeto fora de todos os setores não entra na conta")
        self.assertEqual(self.comp["resumo"], {"oficial": 14, "osm": 3, "cobertura": 21.4, "unidades": 2, "abaixo_da_metade": 1})
        self.assertEqual(resumo_curto(self.comp), "3 de 14 (21,4%)")

    def test_classes_e_saidas(self):
        self.assertEqual(classe_razao(10.0)[0], "menos de 25%")
        self.assertEqual(classe_razao(100.0)[0], "100% ou mais")
        self.assertEqual(classe_razao(None)[0], "sem itens na base")
        self.assertIn("| Endereços (IBGE) | 14 |", quadro(self.comp))
        self.assertIn("| 1 | B | Rural | 10 | 1 | 10% |", tabela_faltas(self.comp))
        self.assertEqual(tabela_sobras(self.comp), "")
        feicoes = json.loads(geojson_modo(self.comp))["features"]
        self.assertEqual({f["properties"]["rotulo"] for f in feicoes}, {"menos de 25%", "50 a 75%"})
        self.assertTrue(all(f["properties"]["cor"].startswith("#") for f in feicoes), "a cor da classe vai no arquivo")
        self.assertEqual(csv_modo(self.comp).splitlines()[1], "1,B,Rural,10,1,10.0,menos de 25%")


class PorNomes(unittest.TestCase):
    def setUp(self):
        oficiais = [{"nome": "RUA DOUTOR JOSE SILVA", "km": 0.5}, {"nome": "AVENIDA DOS CAFEICULTORES", "km": 1.0},
                    {"nome": "RUA DAS FLORES", "km": 0.2}]
        feicoes = [via("way/1", "Rua Dr. José Silva"), via("way/2", "Avenida dos Cafeicultures"), via("way/3", "Rua Nova")]
        faces = [{"type": "Feature", "properties": {"nome": "RUA DAS FLORES"},
                  "geometry": {"type": "LineString", "coordinates": [[-46.0, -19.0], [-46.001, -19.0]]}},
                 {"type": "Feature", "properties": {"nome": ""},
                  "geometry": {"type": "LineString", "coordinates": [[-46.0, -19.0], [-46.001, -19.0]]}}]
        self.comp = montar_nomes({"nome": "Faces", "orgao": "IBGE", "data_acesso": "2026-11-12"}, oficiais, feicoes, faces)

    def test_nomes_iguais_apesar_da_grafia(self):
        self.assertEqual(nome_de_rua("R. Dr. José Silva"), nome_de_rua("RUA DOUTOR JOSE SILVA"))
        self.assertEqual(nome_de_rua("Av. Brasil"), "avenida brasil")

    def test_situacoes_e_pistas(self):
        por = {o["nome"]: o for o in self.comp["oficiais"]}
        self.assertEqual(por["RUA DOUTOR JOSE SILVA"]["situacao"], "ambas")
        self.assertIn("Avenida dos Cafeicultures", por["AVENIDA DOS CAFEICULTORES"]["motivo"], "grafia parecida vira pista")
        self.assertIn("nenhuma via com este nome", por["RUA DAS FLORES"]["motivo"])
        self.assertEqual(sorted(o["nome"] for o in self.comp["so_osm"]), ["Avenida dos Cafeicultures", "Rua Nova"])
        self.assertEqual(self.comp["resumo"]["cobertura"], 33.3)
        self.assertEqual([f["situacao"] for f in self.comp["faces"]], ["so_oficial", "sem_nome"])
        self.assertIn("| 2 | RUA DAS FLORES | 0,20 |", tabela_faltas(self.comp))
        self.assertIn("Rua Nova", tabela_sobras(self.comp))
        self.assertEqual(len(json.loads(geojson_modo(self.comp))["features"]), 2)

    def test_rua_de_uma_letra_e_sem_denominacao(self):
        comp = montar_nomes({"nome": "Faces", "orgao": "IBGE"}, [{"nome": "RUA A", "km": 1.0}, {"nome": "RUA SEM DENOMINACAO 2", "km": 1.0}],
                            [via("way/1", "Rua Z")], [])
        self.assertEqual([o["nome"] for o in comp["oficiais"]], ["RUA A"], "via sem denominação não é nome a procurar")
        self.assertIn("nenhuma via com este nome", comp["oficiais"][0]["motivo"], "Rua A e Rua Z não são grafias uma da outra")


class ValidadorDosModos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.local = Path(self._tmp.name) / "exemplo"
        shutil.copytree(MOTOR / "testes" / "exemplo", self.local, ignore=shutil.ignore_patterns("_construcao"))

    def tearDown(self):
        self._tmp.cleanup()

    def base(self, nome: str, fonte: str, arquivo: str, conteudo: str) -> None:
        pasta = self.local / "dados" / "oficiais" / nome
        pasta.mkdir(parents=True)
        (pasta / "fonte.toml").write_text(
            'nome = "X"\norgao = "IBGE"\nurl = "https://exemplo.org"\ndata_acesso = 2026-11-12\nlicenca = "livre"\n'
            f'arquivo = "{arquivo}"\n' + fonte, encoding="utf-8")
        (pasta / arquivo).write_text(conteudo, encoding="utf-8")

    def test_contagem_e_unidades_validas(self):
        self.base("setores", 'papel = "unidades"\n', "setores.geojson", '{"type":"FeatureCollection","features":[]}')
        self.base("cnefe", 'comparacao = "contagem"\nunidades = "setores"\n[colunas]\nunidade = "setor"\ntotal = "enderecos"\n',
                  "enderecos.csv", "setor,enderecos\nA,10\n")
        self.assertEqual(verificar(self.local).erros, [])

    def test_contagem_sem_unidades_e_modo_desconhecido(self):
        self.base("cnefe", 'comparacao = "contagem"\nunidades = "setores"\n[colunas]\nunidade = "setor"\ntotal = "enderecos"\n',
                  "enderecos.csv", "setor,enderecos\nA,10\n")
        self.base("outra", 'comparacao = "area"\n', "x.csv", "a\n1\n")
        erros = "\n".join(verificar(self.local).erros)
        self.assertIn("pede 'unidades'", erros)
        self.assertIn("comparacao 'area'", erros)


class ServidorAtrasado(unittest.TestCase):
    """baixar_osm: resposta com a base velha não é aceita se outro servidor está em dia."""

    def consultar(self, bases: list[str]):
        import baixar_osm
        from unittest import mock
        respostas = iter(bases)

        class Resposta(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def abrir(req, timeout=0):
            return Resposta(json.dumps({"elements": [], "osm3s": {"timestamp_osm_base": next(respostas)}}).encode())
        config = {"overpass": {"servidores": ["https://a.exemplo/api", "https://b.exemplo/api"], "tempo_limite": 5}}
        with mock.patch.object(baixar_osm.urllib.request, "urlopen", abrir), mock.patch.object(baixar_osm.time, "sleep"):
            return baixar_osm.consultar(config, "node(1);")

    def test_passa_para_o_servidor_em_dia(self):
        from datetime import datetime, timezone
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        resposta, servidor = self.consultar(["2020-01-01T00:00:00Z", hoje])
        self.assertEqual((resposta["osm3s"]["timestamp_osm_base"], servidor), (hoje, "https://b.exemplo/api"))

    def test_sem_servidor_em_dia_vale_o_mais_recente(self):
        resposta, _ = self.consultar(["2020-01-01T00:00:00Z", "2021-01-01T00:00:00Z", "2020-06-01T00:00:00Z",
                                      "2020-07-01T00:00:00Z"])
        self.assertEqual(resposta["osm3s"]["timestamp_osm_base"], "2021-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
