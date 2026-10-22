"""Muda a versão do atlas-motor usada por um município, no atlas.toml e nos workflows.

Uso: python ../atlas-motor/scripts/atualizar_motor.py --versao v0.3.0
Faça num PR próprio ([CONFIG] Motor v0.3.0), depois de ler o CHANGELOG.md do motor.
"""
from __future__ import annotations

import argparse
import re
import sys

from comum import argumento_local

RE_VERSAO = re.compile(r"^v\d+\.\d+\.\d+$")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--versao", required=True)
    argumento_local(ap)
    args = ap.parse_args()
    if not RE_VERSAO.match(args.versao):
        print("Versão no formato vX.Y.Z (ex.: v0.3.0).", file=sys.stderr)
        return 2
    local = args.local.resolve()
    atlas = local / "atlas.toml"
    texto, n = re.subn(r'(?m)^(\s*versao\s*=\s*")[^"]*(")', rf"\g<1>{args.versao}\g<2>", atlas.read_text(encoding="utf-8"))
    if n != 1:
        print("Não encontrei motor.versao no atlas.toml.", file=sys.stderr)
        return 1
    atlas.write_text(texto, encoding="utf-8", newline="\n")
    trocados = 0
    for wf in sorted((local / ".github" / "workflows").glob("*.yml")):
        t, k = re.subn(r"(youthmappers-ufv/atlas-motor/\.github/workflows/[\w.-]+@)\S+", rf"\g<1>{args.versao}",
                       wf.read_text(encoding="utf-8"))
        if k:
            wf.write_text(t, encoding="utf-8", newline="\n")
            trocados += k
    readme, no_readme = local / "README.md", ""    # badge fixo da versão (município privado)
    if readme.exists():
        t, k = re.subn(r"(img\.shields\.io/badge/motor-)v\d+\.\d+\.\d+(-)", rf"\g<1>{args.versao}\g<2>",
                       readme.read_text(encoding="utf-8"))
        if k:
            t = re.sub(r"\[!\[motor v\d+\.\d+\.\d+\]", f"[![motor {args.versao}]", t)
            readme.write_text(t, encoding="utf-8", newline="\n")
            no_readme = " e o badge do README"
    print(f"Motor {args.versao}: atlas.toml, {trocados} chamada(s) nos workflows{no_readme}. Rode validar.py e abra o PR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
