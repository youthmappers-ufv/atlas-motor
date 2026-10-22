"""Identidade visual do atlas: do _brand.yml para o tema.tex do PDF.

O _brand.yml é a fonte única de cores, fontes e logos. O Quarto o aplica no site; este módulo
o traduz para o LaTeX (tema.tex), que livro/atlas-estilo.tex e a capa usam. O tema padrão
(programa) fica em livro/_brand.yml; um município troca o tema com tema/_brand.yml.

Cores lidas: primary, secondary, tertiary, light, foreground (nome da paleta ou hexadecimal).
Fontes: typography.base, headings e monospace, cada uma com reservas se não estiver instalada.
Logos da capa: todos os de logo.images, na ordem (ou o logo medium/large, se não houver).

Exige o PyYAML (requirements.txt), como o resto da construção.
"""
from __future__ import annotations

from pathlib import Path

CORES = {  # chave do _brand.yml: (nome no LaTeX, padrão do programa)
    "primary": ("atlasprimaria", "304068"),
    "secondary": ("atlassecundaria", "7A1C1C"),
    "tertiary": ("atlasdestaque", "BC9C38"),
    "light": ("atlasclaro", "F4F1E8"),
    "foreground": ("atlastexto", "222222"),
}
RESERVAS_TEXTO = ["Source Sans 3", "Source Sans Pro", "TeX Gyre Heros"]
RESERVAS_CODIGO = ["Source Code Pro", "DejaVu Sans Mono"]


def ler_marca(livro: Path) -> dict:
    import yaml                                   # só na construção (requirements.txt)
    return yaml.safe_load((livro / "_brand.yml").read_text(encoding="utf-8")) or {}


def cor(marca: dict, chave: str) -> str:
    cores = marca.get("color") or {}
    valor = cores.get(chave)
    valor = (cores.get("palette") or {}).get(valor, valor)      # nome da paleta ou hexadecimal
    if not isinstance(valor, str) or not valor.startswith("#"):
        return CORES[chave][1]
    return valor.lstrip("#").upper()


def familia(marca: dict, chave: str) -> str | None:
    tipo = (marca.get("typography") or {}).get(chave)
    return tipo.get("family") if isinstance(tipo, dict) else tipo


def fonte(comando: str, preferidas: list[str]) -> str:
    """\\setmainfont (ou outro) com a primeira fonte instalada; sem nenhuma, fica a padrão."""
    vistas, texto = [], ""
    for nome in preferidas:
        if nome and nome not in vistas:
            vistas.append(nome)
    for nome in reversed(vistas):
        texto = f"\\IfFontExistsTF{{{nome}}}{{\\{comando}{{{nome}}}}}{{{texto}}}"
    return texto


def logos(marca: dict) -> list[str]:
    logo = marca.get("logo") or {}
    if isinstance(logo, str):
        return [logo]
    imagens = logo.get("images") or {}
    caminho = lambda v: (v.get("path") if isinstance(v, dict) else v)  # noqa: E731
    if imagens:
        return [caminho(v) for v in imagens.values() if caminho(v)]
    for chave in ("large", "medium", "small"):
        if logo.get(chave):
            return [caminho(logo[chave])]
    return []


def tex(marca: dict) -> str:
    def esc(s: str) -> str:
        return s.replace("\\", "").replace("{", "").replace("}", "").replace("&", "\\&").replace("%", "\\%")
    linhas = ["% Gerado de _brand.yml por scripts/tema.py (atlas-motor); não editar."]
    linhas += [f"\\definecolor{{{nome}}}{{HTML}}{{{cor(marca, chave)}}}" for chave, (nome, _) in CORES.items()]
    base, titulos = familia(marca, "base"), familia(marca, "headings")
    linhas.append(fonte("setmainfont", [base, *RESERVAS_TEXTO]))
    linhas.append(fonte("setsansfont", [titulos, base, *RESERVAS_TEXTO]))
    linhas.append(fonte("setmonofont", [familia(marca, "monospace"), *RESERVAS_CODIGO]))
    imagens = "\\hspace{1.2cm}".join(f"\\includegraphics[height=2.2cm]{{{l}}}" for l in logos(marca))
    linhas.append(f"\\newcommand{{\\atlaslogos}}{{{imagens}}}")
    linhas.append(f"\\newcommand{{\\atlasmarca}}{{{esc(str((marca.get('meta') or {}).get('name', '')))}}}")
    return "\n".join(linhas) + "\n"


def gerar(livro: Path) -> list[str]:
    """Grava livro/tema.tex e devolve os logos citados que não existem no livro."""
    marca = ler_marca(livro)
    (livro / "tema.tex").write_text(tex(marca), encoding="utf-8", newline="\n")
    return [l for l in logos(marca) if not (livro / l).is_file()]
