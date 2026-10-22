"""Testes da identidade visual: tradução do _brand.yml para o LaTeX (scripts/identidade.py) e
aplicação da identidade do município na construção (construir.aplicar_identidade)."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MOTOR / "scripts"))

from identidade import cor, fonte, logos, tex  # noqa: E402

TEM_YAML = importlib.util.find_spec("yaml") is not None

MARCA = {
    "meta": {"name": "Prefeitura de Teste & Cia"},
    "logo": {"images": {"prefeitura": "marca/pref.png", "programa": "marca/ymufv_logo.png"}, "medium": "prefeitura"},
    "color": {"palette": {"verde": "#1B6E3A"}, "primary": "verde", "secondary": "#8a4b1f"},
    "typography": {"base": "Fonte Inexistente", "headings": {"family": "Outra Fonte"}},
}


class TraducaoDoBrand(unittest.TestCase):
    def test_cor_da_paleta_e_hexadecimal(self):
        self.assertEqual(cor(MARCA, "primary"), "1B6E3A")
        self.assertEqual(cor(MARCA, "secondary"), "8A4B1F")

    def test_cor_ausente_ou_invalida_usa_a_do_programa(self):
        self.assertEqual(cor(MARCA, "tertiary"), "BC9C38")
        self.assertEqual(cor({"color": {"primary": "vermelho"}}, "primary"), "304068")

    def test_fonte_com_reservas_em_ordem(self):
        t = fonte("setmainfont", ["A", "B", "A", None])
        self.assertEqual(t, r"\IfFontExistsTF{A}{\setmainfont{A}}{\IfFontExistsTF{B}{\setmainfont{B}}{}}")

    def test_logos_da_capa_na_ordem(self):
        self.assertEqual(logos(MARCA), ["marca/pref.png", "marca/ymufv_logo.png"])
        self.assertEqual(logos({"logo": {"medium": "marca/a.png"}}), ["marca/a.png"])
        self.assertEqual(logos({}), [])

    def test_tex_completo(self):
        t = tex(MARCA)
        self.assertIn(r"\definecolor{atlasprimaria}{HTML}{1B6E3A}", t)
        self.assertIn(r"\definecolor{atlasdestaque}{HTML}{BC9C38}", t)
        self.assertIn(r"\IfFontExistsTF{Fonte Inexistente}{\setmainfont{Fonte Inexistente}}", t)
        self.assertIn(r"\IfFontExistsTF{Outra Fonte}{\setsansfont{Outra Fonte}}", t)
        self.assertIn(r"{\IfFontExistsTF{TeX Gyre Heros}", t)
        self.assertIn(r"\includegraphics[height=2.2cm]{marca/pref.png}\hspace{1.2cm}", t)
        self.assertIn(r"\newcommand{\atlasmarca}{Prefeitura de Teste \& Cia}", t)


@unittest.skipUnless(TEM_YAML, "PyYAML ausente (requirements.txt)")
class TemaDoMunicipio(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.local, self.livro = base / "atlas-teste", base / "livro"
        shutil.copytree(MOTOR / "livro", self.livro)
        (self.local / "identidade" / "marca").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_padrao_do_motor_sem_tema(self):
        from construir import aplicar_identidade
        aplicar_identidade(self.local, self.livro)
        t = (self.livro / "identidade.tex").read_text(encoding="utf-8")
        self.assertIn("{304068}", t)
        self.assertIn("marca/ymufv_logo.png", t)

    def test_tema_do_municipio_substitui_o_padrao(self):
        from construir import aplicar_identidade
        tema = self.local / "identidade"
        (tema / "marca" / "pref.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
        (tema / "LEIAME.md").write_text("instruções", encoding="utf-8")
        (tema / "_brand.yml").write_text(
            'meta:\n  name: Prefeitura X\nlogo:\n  images:\n    p: marca/pref.png\n'
            'color:\n  primary: "#1B6E3A"\n', encoding="utf-8")
        aplicar_identidade(self.local, self.livro)
        t = (self.livro / "identidade.tex").read_text(encoding="utf-8")
        self.assertIn("{1B6E3A}", t)
        self.assertIn("{marca/pref.png}", t)
        self.assertTrue((self.livro / "marca" / "pref.png").exists())
        self.assertFalse((self.livro / "LEIAME.md").exists(), "instruções de identidade/ não entram no livro")

    def test_logo_inexistente_interrompe(self):
        from construir import aplicar_identidade
        (self.local / "identidade" / "_brand.yml").write_text(
            "logo:\n  images:\n    p: marca/falta.png\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as e:
            aplicar_identidade(self.local, self.livro)
        self.assertIn("marca/falta.png", str(e.exception))


class ModeloDoLivro(unittest.TestCase):
    def test_estilo_usa_so_cores_do_tema(self):
        """atlas-estilo.tex e a capa não definem cor nem fonte: tudo vem de identidade.tex."""
        for nome in ("atlas-estilo.tex", "before-body.tex"):
            texto = (MOTOR / "livro" / nome).read_text(encoding="utf-8")
            self.assertNotIn(r"\definecolor", texto, nome)
            self.assertNotRegex(texto, r"\\set(main|sans|mono)font", nome)
            self.assertNotRegex(texto, r"\{HTML\}|#[0-9A-Fa-f]{6}", nome)

    def test_scss_sem_cores_fixas(self):
        texto = (MOTOR / "livro" / "estilo.scss").read_text(encoding="utf-8")
        self.assertNotRegex(texto, r"#[0-9A-Fa-f]{3,6}\b", "cores fixas no scss anulam o _brand.yml no site")

    def test_quarto_usa_brand_e_estilo(self):
        texto = (MOTOR / "livro" / "_quarto.modelo.yml").read_text(encoding="utf-8")
        self.assertIn("theme: [cosmo, brand, estilo.scss]", texto)
        self.assertIn("include-in-header: atlas-estilo.tex", texto)
        self.assertIn("template-partials: [before-body.tex]", texto)


if __name__ == "__main__":
    unittest.main()
