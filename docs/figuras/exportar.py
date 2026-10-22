"""Exporta os diagramas .svg desta pasta para PDF (vetorial, para LaTeX) e PNG (2x).

O SVG é a fonte: edite-o e rode de novo. Usa o Chrome ou o Edge sem janela (nenhuma
biblioteca extra). Uso: python docs/figuras/exportar.py [arquivo.svg ...]
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PASTA = Path(__file__).resolve().parent
NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]


def navegador() -> str:
    for n in NAVEGADORES:
        if Path(n).exists() or shutil.which(n):
            return n
    sys.exit("Não encontrei Chrome, Chromium nem Edge.")


def exportar(svg: Path, nav: str) -> None:
    texto = svg.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', texto)
    if not m:
        sys.exit(f"{svg.name}: sem viewBox")
    larg, alt = int(m.group(1)), int(m.group(2))
    pagina = (f"<!doctype html><meta charset='utf-8'><style>@page{{size:{larg}px {alt}px;margin:0}}"
              f"html,body{{margin:0}}svg{{display:block;width:{larg}px;height:{alt}px}}</style>"
              + texto.split("?>", 1)[-1])
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "pagina.html"
        html.write_text(pagina, encoding="utf-8")
        base = [nav, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/perfil"]
        subprocess.run(base + [f"--print-to-pdf={svg.with_suffix('.pdf')}", html.as_uri()],
                       check=True, capture_output=True)
        subprocess.run(base + ["--force-device-scale-factor=2", f"--window-size={larg},{alt}",
                               "--hide-scrollbars", f"--screenshot={svg.with_suffix('.png')}", html.as_uri()],
                       check=True, capture_output=True)
    print(f"{svg.name} -> {svg.with_suffix('.pdf').name}, {svg.with_suffix('.png').name}")


def main() -> int:
    nav = navegador()
    alvos = [Path(a).resolve() for a in sys.argv[1:]] or sorted(PASTA.glob("*.svg"))
    for svg in alvos:
        exportar(svg, nav)
    return 0


if __name__ == "__main__":
    sys.exit(main())
