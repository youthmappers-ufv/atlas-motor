"""Testes da normalização de nomes e da correspondência OSM × base oficial."""
from __future__ import annotations

import sys
import unittest
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from comum import dentro, distancia_m, normalizar_nome  # noqa: E402
from indicadores import correspondencias, similaridade  # noqa: E402


def texto(a: str, b: str) -> float:
    """Semelhança só do texto normalizado inteiro (a regra anterior)."""
    return SequenceMatcher(None, normalizar_nome(a), normalizar_nome(b)).ratio()


def feicao(nome: str, lon: float, lat: float) -> dict:
    return {"geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"tags": {"name": nome}}}


class Nomes(unittest.TestCase):
    def test_abreviacoes_e_acentos(self):
        self.assertEqual(normalizar_nome("E.E. Prof. João Gonçalves"), "escola estadual professor joao goncalves")
        self.assertEqual(normalizar_nome("UBS Centro"), "unidade basica de saude centro")
        self.assertEqual(normalizar_nome("Igreja N. Sra. do Rosário"), "igreja nossa senhora do rosario")


class Correspondencia(unittest.TestCase):
    LON, LAT = -46.2411, -19.1965
    D100 = 100 / 111320          # ~100 m em latitude

    def test_mesmo_item_perto_e_nome_parecido(self):
        o = [{"nome": "EE Major Silvestre", "lon": self.LON, "lat": self.LAT}]
        f = [feicao("Escola Estadual Major Silvestre", self.LON, self.LAT + self.D100)]
        self.assertEqual(len(correspondencias(o, f, 150, 0.6)), 1)

    def test_longe_demais(self):
        o = [{"nome": "EE Major Silvestre", "lon": self.LON, "lat": self.LAT}]
        f = [feicao("Escola Estadual Major Silvestre", self.LON, self.LAT + 2 * self.D100)]
        self.assertEqual(correspondencias(o, f, 150, 0.6), [])

    def test_nome_diferente(self):
        o = [{"nome": "EE Major Silvestre", "lon": self.LON, "lat": self.LAT}]
        f = [feicao("Creche Municipal Maria Mãe de Deus", self.LON, self.LAT)]
        self.assertEqual(correspondencias(o, f, 150, 0.6), [])

    def test_um_para_um(self):
        o = [{"nome": "EE Major Silvestre", "lon": self.LON, "lat": self.LAT},
             {"nome": "E.E. Major Silvestre", "lon": self.LON, "lat": self.LAT}]
        f = [feicao("Escola Estadual Major Silvestre", self.LON, self.LAT)]
        self.assertEqual(len(correspondencias(o, f, 150, 0.6)), 1)

    def test_nome_curto_contido_no_oficial(self):
        o = [{"nome": "INSTITUTO EDUCACIONAL EQUIPE SG - ALEGRIA DE SABER", "lon": self.LON, "lat": self.LAT},
             {"nome": "COLEGIO DIMENSAO ENSINO FUNDAMENTAL E MEDIO", "lon": self.LON + 0.01, "lat": self.LAT}]
        f = [feicao("Alegria de Saber", self.LON, self.LAT + self.D100 / 4),
             feicao("Colégio Dimensão", self.LON + 0.01, self.LAT)]
        self.assertEqual([(i, j) for i, j, _, _ in correspondencias(o, f, 150, 0.6)], [(0, 0), (1, 1)])

    def test_palavras_sem_bonus(self):
        """Só tipo, palavra curta ou meia coincidência: fica a semelhança do texto inteiro."""
        for a, b in [("Escola Municipal", "Escola Municipal Santa Rita"),        # só palavras genéricas
                     ("EM Sol", "Escola Sol Nascente"),                         # uma palavra de 3 letras
                     ("EM Santa Rita", "EM Santa Luzia Maria")]:                # metade das palavras
            with self.subTest(a=a, b=b):
                self.assertEqual(similaridade(a, b), texto(a, b))

    def test_nome_do_municipio_nao_distingue(self):
        a, b = "COLEGIO GAMA DE SAO GOTARDO", "Centro de Ensino Superior de São Gotardo"
        self.assertGreater(similaridade(a, b), texto(a, b))                     # "sao gotardo" em comum
        self.assertEqual(similaridade(a, b, frozenset({"sao", "gotardo"})), texto(a, b))
        o = [{"nome": a, "lon": self.LON, "lat": self.LAT}]
        f = [feicao(b, self.LON, self.LAT)]
        self.assertEqual(correspondencias(o, f, 150, 0.62, "São Gotardo"), [])
        self.assertEqual(len(correspondencias(o, f, 150, 0.62)), 1)

    def test_nome_igual_tem_preferencia_sobre_contido(self):
        o = [{"nome": "EM Alegria de Saber", "lon": self.LON, "lat": self.LAT}]
        f = [feicao("Alegria", self.LON, self.LAT), feicao("Escola Municipal Alegria de Saber", self.LON, self.LAT + self.D100)]
        self.assertEqual([j for _, j, _, _ in correspondencias(o, f, 150, 0.6)], [1])

    def test_nome_contido_mas_longe_nao_corresponde(self):
        o = [{"nome": "COLEGIO DIMENSAO ENSINO FUNDAMENTAL E MEDIO", "lon": self.LON, "lat": self.LAT}]
        f = [feicao("Colégio Dimensão", self.LON, self.LAT + 2 * self.D100)]
        self.assertEqual(correspondencias(o, f, 150, 0.6), [])

    def test_item_sem_coordenada_nao_corresponde(self):
        o = [{"nome": "EE Major Silvestre", "lon": None, "lat": None}]
        f = [feicao("Escola Estadual Major Silvestre", self.LON, self.LAT)]
        self.assertEqual(correspondencias(o, f, 150, 0.6), [])


class Geometria(unittest.TestCase):
    def test_distancia(self):
        self.assertAlmostEqual(distancia_m(-46.0, -19.0, -46.0, -19.01), 1112, delta=3)

    def test_ponto_no_poligono(self):
        quadrado = [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]
        self.assertTrue(dentro(0.5, 0.5, quadrado))
        self.assertFalse(dentro(1.5, 0.5, quadrado))


if __name__ == "__main__":
    unittest.main()
