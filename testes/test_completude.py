"""Testes da normalização de nomes e da correspondência OSM × base oficial."""
from __future__ import annotations

import sys
import unittest
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from comum import dentro, distancia_m, normalizar_nome  # noqa: E402
from indicadores import correspondencias, motivos_lacunas, similaridade  # noqa: E402


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


class MotivosLacunas(unittest.TestCase):
    """Motivo provável de cada item oficial sem correspondente (casos reais de Rio Paranaíba e São Gotardo)."""
    LON, LAT = -46.2411, -19.1965
    D100 = 100 / 111320
    LIMITE = [[(-46.30, -19.25), (-46.20, -19.25), (-46.20, -19.15), (-46.30, -19.15), (-46.30, -19.25)]]

    def motivo(self, oficial: dict, feicoes: list[dict], outros: list[dict] = ()) -> str:
        oficiais = [*outros, oficial]
        pares = correspondencias(oficiais, feicoes, 150, 0.6, "São Gotardo")
        m = motivos_lacunas(oficiais, feicoes, pares, 150, 0.6, "São Gotardo", self.LIMITE)
        self.assertEqual(set(m), {len(oficiais) - 1}, "só o item sem correspondente recebe motivo")
        return m[len(oficiais) - 1]

    def oficial(self, nome: str, dlat: float = 0.0, lon: float | None = None) -> dict:
        return {"nome": nome, "lon": self.LON if lon is None else lon, "lat": self.LAT + dlat}

    def test_sem_coordenada(self):
        o = {"nome": "EM Professor José Luiz de Araújo", "lon": None, "lat": None}
        self.assertEqual(self.motivo(o, []), "sem coordenada na base oficial")
        m = self.motivo(o, [feicao("Escola Estadual Professor José Luiz de Araújo", self.LON, self.LAT)])
        self.assertIn("no OSM há \"Escola Estadual Professor José Luiz de Araújo\"", m)

    def test_fora_do_municipio(self):
        self.assertEqual(self.motivo(self.oficial("Creche Municipal", lon=-46.10), []),
                         "coordenada oficial fora do município")

    def test_mesmo_nome_longe(self):
        f = [feicao("Centro Educacional Paulo Freire", self.LON, self.LAT + 8.26 * self.D100),
             feicao("Centro Vocacional Tecnológico", self.LON, self.LAT + 5.18 * self.D100)]
        m = self.motivo(self.oficial("CENTRO EDUCACIONAL PAULO FREIRE"), f)
        self.assertRegex(m, r"^nome semelhante no OSM a 8\d\d m \(\"Centro Educacional Paulo Freire\"; limite 150 m\)")

    def test_so_palavras_genericas_nao_sao_pista_de_longe(self):
        """O texto inteiro inflado pelas genéricas não aponta outra escola longe."""
        f = [feicao("Centro Vocacional Tecnológico", self.LON, self.LAT + 5 * self.D100),
             feicao("Colégio Dimensão", self.LON, self.LAT + 13 * self.D100)]
        for nome in ("CENTRO EDUCACIONAL PAULO FREIRE", "COLEGIO GAMA DE SAO GOTARDO"):
            with self.subTest(nome=nome):
                self.assertTrue(self.motivo(self.oficial(nome), f).endswith("não mapeado"))

    def test_objeto_perto_ja_pareado(self):
        outro = self.oficial("EE Major Silvestre")
        m = self.motivo(self.oficial("E.E. Major Silvestre", 0.1 * self.D100),
                        [feicao("Escola Estadual Major Silvestre", self.LON, self.LAT)], [outro])
        self.assertIn("já corresponde a outro item da base (EE Major Silvestre)", m)

    def test_pareado_com_nome_diferente_nao_e_candidato(self):
        outro = self.oficial("INSTITUTO EDUCACIONAL EQUIPE SG - ALEGRIA DE SABER")
        m = self.motivo(self.oficial("CESEC MARIA COELI FRANCO", 1.27 * self.D100),
                        [feicao("Alegria de Saber", self.LON, self.LAT)], [outro])
        self.assertTrue(m.endswith("não mapeado"), m)

    def test_objeto_perto_sem_nome(self):
        f = [{"geometry": {"type": "Point", "coordinates": [self.LON, self.LAT + 0.09 * self.D100]},
              "properties": {"tags": {"amenity": "school"}}}]
        self.assertEqual(self.motivo(self.oficial("EM Pres Tancredo Neves"), f),
                         "objeto sem nome no OSM a 9 m: provavelmente este, falta o nome")

    def test_objeto_perto_com_nome_diferente(self):
        f = [feicao("Centro Municipal de Educação Infantil Joana Darc", self.LON, self.LAT + 0.23 * self.D100)]
        m = self.motivo(self.oficial("CRECHE MUNICIPAL MARIA MAE DE DEUS"), f)
        self.assertTrue(m.startswith("\"Centro Municipal de Educação Infantil Joana Darc\" no OSM a 23 m, "
                                     "com nome diferente (semelhança 0,"), m)

    def test_nada_por_perto(self):
        self.assertEqual(self.motivo(self.oficial("EM Sonho Meu"), [feicao("EM Outra", self.LON, self.LAT + 3 * self.D100)]),
                         "nada deste tema no OSM até 150 m: não mapeado")

    def test_sem_limite_nao_acusa_fora(self):
        oficiais = [self.oficial("Creche Municipal", lon=-46.10)]
        self.assertTrue(motivos_lacunas(oficiais, [], [], 150, 0.6)[0].endswith("não mapeado"))


class Geometria(unittest.TestCase):
    def test_distancia(self):
        self.assertAlmostEqual(distancia_m(-46.0, -19.0, -46.0, -19.01), 1112, delta=3)

    def test_ponto_no_poligono(self):
        quadrado = [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]
        self.assertTrue(dentro(0.5, 0.5, quadrado))
        self.assertFalse(dentro(1.5, 0.5, quadrado))


if __name__ == "__main__":
    unittest.main()
