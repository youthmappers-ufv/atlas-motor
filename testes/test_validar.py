"""Testes do validador: cada teste planta um defeito numa CÓPIA do município de
exemplo (testes/exemplo/) e confere que validar.py o acusa; o exemplo limpo passa."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
EXEMPLO = MOTOR / "testes" / "exemplo"
sys.path.insert(0, str(MOTOR / "scripts"))

from validar import verificar  # noqa: E402

IGNORAR = shutil.ignore_patterns("_construcao", ".quarto", "__pycache__")
LINHA_OK = "LC-2027-001,2027-02-10,educacao,E.E. Major Exemplo,confirmado,node/13188586822,,-19.20,-46.25,"


class ValidadorComDefeitosPlantados(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.local = Path(self._tmp.name) / "atlas-exemplo"
        shutil.copytree(EXEMPLO, self.local, ignore=IGNORAR)

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------ utilidades
    def arq(self, rel: str) -> Path:
        return self.local / rel

    def acrescentar(self, rel: str, texto: str) -> None:
        with self.arq(rel).open("a", encoding="utf-8", newline="") as f:
            f.write(texto + "\n")

    def trocar(self, rel: str, antes: str, depois: str, todas: bool = False) -> None:
        conteudo = self.arq(rel).read_text(encoding="utf-8")
        self.assertIn(antes, conteudo, f"o teste espera encontrar {antes!r} em {rel}")
        self.arq(rel).write_text(conteudo.replace(antes, depois, -1 if todas else 1), encoding="utf-8")

    def erros(self) -> list[str]:
        return verificar(self.local).erros

    def assertAcusa(self, trecho: str):
        erros = self.erros()
        self.assertTrue(any(trecho in e for e in erros), f"esperado erro com {trecho!r}; veio: {erros}")

    # ------------------------------------------------------------ casos
    def test_exemplo_limpo_passa(self):
        self.assertEqual(self.erros(), [])

    def test_linha_valida_de_campo_passa(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK)
        self.assertEqual(self.erros(), [], "id de nó do OSM com 11 dígitos não pode ser confundido com CPF")

    def test_email_em_dado_curado(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK[:-1] + "falar com fulano@exemplo.com")
        self.assertAcusa("contém um e-mail")

    def test_cpf_em_dado_curado(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK[:-1] + "responsável 123.456.789-09")
        self.assertAcusa("parece conter um CPF")

    def test_telefone_em_dado_curado(self):
        for tel in ("(34) 99999-1234", "34 3855-1234", "+55 34 99999 1234", "fone 3855-1234", "whatsapp 999991234"):
            with self.subTest(tel=tel):
                self.tearDown()
                self.setUp()
                self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK + "ligar " + tel)
                self.assertAcusa("parece conter um telefone")

    def test_numeros_que_nao_sao_telefone_passam(self):
        for txt in ("obras de 1990-2000", "CEP 38810-000", "cnes 2209411", "visto em 2027-02-10", '"R$ 1.234,56"'):
            with self.subTest(txt=txt):
                self.tearDown()
                self.setUp()
                self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK + txt)
                self.assertEqual(self.erros(), [])

    def test_virgula_sem_aspas(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK + "custo R$ 1.234,56")
        self.assertAcusa("mais valores que colunas")

    def test_coluna_diferente_do_esquema(self):
        self.trocar("dados/curados/eventos-culturais.csv", "fonte,url", "fonte,email")
        self.assertAcusa("[curados] eventos-culturais.csv: colunas")

    def test_coordenada_fora_do_municipio(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK.replace("-19.20,-46.25", "-22.90,-43.20"))
        self.assertAcusa("fora da área do município")

    def test_valor_fora_da_lista(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK.replace(",confirmado,", ",talvez,"))
        self.assertAcusa("'situacao' = 'talvez'")

    def test_tema_inexistente(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK.replace(",educacao,", ",esportes,"))
        self.assertAcusa("não é tema do atlas")

    def test_chave_repetida(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK)
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK)
        self.assertAcusa("chave 'LC-2027-001' repetida")

    def test_data_invalida(self):
        self.acrescentar("dados/curados/levantamentos-campo.csv", LINHA_OK.replace("2027-02-10", "10/02/2027"))
        self.assertAcusa("não é data válido")

    def test_csv_sem_esquema(self):
        self.arq("dados/curados/sem-esquema.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        self.assertAcusa("sem-esquema.csv: sem esquema")

    def test_esquema_proprio_do_municipio_vale(self):
        self.arq("dados/esquemas/podas.toml").write_text(
            'arquivo = "podas.csv"\nchave = "id"\n[[coluna]]\nnome = "id"\ntipo = "texto"\nobrigatoria = true\n',
            encoding="utf-8")
        self.arq("dados/curados/podas.csv").write_text("id\nP1\n", encoding="utf-8")
        self.assertEqual(self.erros(), [])

    def test_base_oficial_sem_licenca(self):
        self.trocar("dados/oficiais/inep/fonte.toml", 'licenca = "dados sintéticos de teste"\n', "")
        self.assertAcusa("falta 'licenca'")

    def test_base_oficial_com_coluna_errada(self):
        self.trocar("dados/oficiais/inep/fonte.toml", 'nome = "escola"', 'nome = "nome_escola"')
        self.assertAcusa("coluna para 'nome' (nome_escola) não está no CSV")

    def test_tema_desconhecido_sem_dados_de_prancha_propria(self):
        self.acrescentar("temas.toml", '\n[tema.esportes]\nsituacao = "em-andamento"')
        self.assertAcusa("prancha própria precisa de")

    def test_prancha_propria_completa_passa(self):
        self.acrescentar("temas.toml", '\n[tema.feiras]\nnumero = 20\ntitulo = "Feiras"\nconsulta = "feiras.overpassql"\n'
                                      'situacao = "em-andamento"')
        self.arq("consultas/feiras.overpassql").write_text('(node({{bbox}})[amenity=marketplace];);\n', encoding="utf-8")
        self.arq("atlas/pranchas/20-feiras.qmd").write_text("# Feiras\n\n{{< include ../_gerado/feiras.md >}}\n",
                                                           encoding="utf-8")
        self.arq("dados/osm/feiras.geojson").write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")
        retrato = json.loads(self.arq("dados/osm/retrato.json").read_text(encoding="utf-8"))
        retrato["temas"]["feiras"] = {"feicoes": 0}
        self.arq("dados/osm/retrato.json").write_text(json.dumps(retrato), encoding="utf-8")
        self.assertEqual(self.erros(), [])

    def test_prancha_propria_com_cor_mapa_e_indicadores(self):
        self.acrescentar("temas.toml", '\n[tema.feiras]\nnumero = 20\ntitulo = "Feiras"\nconsulta = "feiras.overpassql"\n'
                                      'cor = "#7A1C1C"\nmapa = "linhas"\nindicadores = ["servico", "voos"]')
        self.assertAcusa("indicador 'voos'")

    def test_cor_invalida_no_tema(self):
        self.acrescentar("temas.toml", '\n[tema.saude]\ncor = "vermelho"')
        self.assertAcusa("cor 'vermelho'")

    def test_consulta_propria_sem_bbox(self):
        self.arq("consultas/educacao.overpassql").write_text('(nwr(-20,-47,-19,-46)[amenity=school];);\n', encoding="utf-8")
        self.assertAcusa("não usa {{bbox}}")

    def test_prancha_ativa_sem_arquivo(self):
        self.acrescentar("temas.toml", '\n[tema.saude]\nsituacao = "em-andamento"')
        self.assertAcusa("falta atlas/pranchas/04-saude.qmd")

    def test_prancha_sobrando(self):
        self.trocar("temas.toml", '[tema.educacao]\nsituacao = "em-andamento"', '[tema.educacao]\nsituacao = "planejado"')
        self.assertAcusa("atlas/pranchas/03-educacao.qmd não corresponde a tema ativo")

    def test_tema_ativo_sem_retrato(self):
        self.arq("dados/osm/educacao.geojson").unlink()
        self.assertAcusa("falta dados/osm/educacao.geojson")

    def test_geojson_com_feicao_repetida(self):
        arq = self.arq("dados/osm/educacao.geojson")
        dados = json.loads(arq.read_text(encoding="utf-8"))
        dados["features"].append(dados["features"][0])
        arq.write_text(json.dumps(dados), encoding="utf-8")
        self.assertAcusa("repetido")
        self.assertAcusa("mas retrato.json diz")

    def test_versao_do_motor_divergente(self):
        self.trocar(".github/workflows/verificar.yml", "verificar.yml@v", "verificar.yml@v9.9-", todas=False)
        self.assertAcusa("chama o motor em v9.9-")

    def test_versao_do_motor_sem_tres_partes(self):
        self.trocar("atlas.toml", 'versao = "v0.2.0"', 'versao = "v1.1"')
        self.assertAcusa("vX.Y.Z")

    def test_slug_invalido(self):
        self.trocar("atlas.toml", 'slug = "exemplo"', 'slug = "Exemplo Cidade"')
        self.assertAcusa("publicacao.slug")

    def test_marcas_de_conflito(self):
        self.acrescentar("atlas/index.qmd", "<<<<<<< HEAD\nversão A\n=======\nversão B\n>>>>>>> outra")
        self.assertAcusa("marcas de conflito")

    def test_hospedagem_desconhecida(self):
        self.trocar("atlas.toml", 'hospedagem = "pages"', 'hospedagem = "ftp"')
        self.assertAcusa("publicacao.hospedagem deve ser")

    def test_hospedagem_artefato_sem_url_passa(self):
        self.trocar("atlas.toml", 'hospedagem = "pages"', 'hospedagem = "artefato"')
        self.trocar("atlas.toml", 'url = "https://youthmappers-ufv.github.io/atlas-exemplo/"', 'url = ""')
        self.assertEqual(self.erros(), [])

    def test_pages_sem_url(self):
        self.trocar("atlas.toml", 'url = "https://youthmappers-ufv.github.io/atlas-exemplo/"', 'url = ""')
        self.assertAcusa("publicacao.url deve ser")

    def test_url_sem_barra_final(self):
        self.trocar("atlas.toml", 'atlas-exemplo/"', 'atlas-exemplo"')
        self.assertAcusa("publicacao.url deve ser")

    def test_dominio_com_protocolo(self):
        self.trocar("atlas.toml", 'dominio = ""', 'dominio = "https://atlas.exemplo.mg.gov.br/"')
        self.assertAcusa("publicacao.dominio deve ser")

    def test_dominio_valido_passa(self):
        self.trocar("atlas.toml", 'dominio = ""', 'dominio = "atlas.exemplo.mg.gov.br"')
        self.assertEqual(self.erros(), [])

    def test_coordenacao_vazia(self):
        self.trocar("atlas.toml", 'coordenacao = "Rodrigo Smarzaro"', 'coordenacao = " "')
        self.assertAcusa("publicacao.coordenacao deve ser")

    def test_sem_coordenacao_passa(self):
        self.trocar("atlas.toml", 'coordenacao = "Rodrigo Smarzaro"', "")
        self.assertEqual(self.erros(), [])

    def avisos(self) -> list[str]:
        return verificar(self.local).avisos

    def test_citacao_coerente_passa(self):
        self.assertEqual([a for a in self.avisos() if "[citacao]" in a], [])

    def test_sem_citation_cff(self):
        self.arq("CITATION.cff").unlink()
        self.assertTrue(any("falta CITATION.cff" in a for a in self.avisos()))

    def test_citation_de_outro_atlas(self):
        self.trocar("CITATION.cff", "Atlas Colaborativo de Exemplo", "Atlas Colaborativo de Outro")
        self.assertTrue(any("o título deveria ser" in a for a in self.avisos()))

    def test_coordenacao_fora_do_citation(self):
        self.trocar("atlas.toml", 'coordenacao = "Rodrigo Smarzaro"', 'coordenacao = "Maria Souza"')
        self.assertTrue(any("(Maria Souza) não está entre os autores" in a for a in self.avisos()))

    def test_chave_antiga_de_publicacao(self):
        self.acrescentar("atlas.toml", "ativa = true")
        self.assertAcusa("publicacao.ativa saiu na v0.5.0")

    def test_hashtag_sem_cerquilha(self):
        self.trocar("atlas.toml", 'projeto = "#ymufv-atlas"', 'projeto = "ymufv-atlas"')
        self.assertAcusa("hashtags.projeto")

    # ------------------------------------------------------------ identidade/
    def tema(self, brand: str, imagens: dict[str, bytes]) -> None:
        (self.local / "identidade" / "marca").mkdir(parents=True, exist_ok=True)
        (self.local / "identidade" / "_brand.yml").write_text(brand, encoding="utf-8")
        for nome, conteudo in imagens.items():
            (self.local / "identidade" / nome).write_bytes(conteudo)

    BRAND = 'meta:\n  name: Prefeitura X\nlogo:\n  images:\n    p: marca/pref.png\ncolor:\n  primary: "#1B6E3A"\n'
    PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20

    def test_tema_valido_passa(self):
        self.tema(self.BRAND, {"marca/pref.png": self.PNG})
        self.assertEqual(self.erros(), [])

    def test_tema_com_logo_do_motor_passa(self):
        self.tema(self.BRAND.replace("marca/pref.png", "marca/ymufv_logo.png"), {})
        self.assertEqual(self.erros(), [])

    def test_tema_jpeg_com_extensao_png(self):
        self.tema(self.BRAND, {"marca/pref.png": self.JPEG})
        self.assertAcusa("o conteúdo não é PNG")

    def test_tema_logo_inexistente(self):
        self.tema(self.BRAND, {})
        self.assertAcusa("cita marca/pref.png")

    def test_tema_cor_invalida(self):
        self.tema(self.BRAND.replace("#1B6E3A", "#1B6E3"), {"marca/pref.png": self.PNG})
        self.assertAcusa("cor '#1B6E3' inválida")

    def test_pasta_antiga_tema(self):
        (self.local / "tema").mkdir()
        self.assertAcusa("passou a se chamar identidade/")

    def test_tema_imagens_sem_brand_avisa(self):
        (self.local / "identidade" / "marca").mkdir(parents=True, exist_ok=True)
        (self.local / "identidade" / "marca" / "pref.png").write_bytes(self.PNG)
        r = verificar(self.local)
        self.assertEqual(r.erros, [])
        self.assertTrue(any("falta identidade/_brand.yml" in a for a in r.avisos))


if __name__ == "__main__":
    unittest.main()
