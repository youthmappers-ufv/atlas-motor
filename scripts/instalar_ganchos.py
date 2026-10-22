"""Instala no repositório de um município o gancho de pre-push que roda o validador.

O repositório do município é público: o que é enviado ao GitHub fica visível na hora, antes de
qualquer revisão ou CI. O gancho roda validar.py (inclusive as regras de dados pessoais) antes
de cada push e o interrompe se houver erro. Para pular uma vez (não recomendado):
git push --no-verify.

Uso (de dentro do repositório do município, uma vez por clone):
  python ../atlas-motor/scripts/instalar_ganchos.py
"""
from __future__ import annotations

import argparse
import stat
import subprocess
import sys
from pathlib import Path

from comum import MOTOR, argumento_local

GANCHO = """#!/bin/sh
# Gerado por atlas-motor/scripts/instalar_ganchos.py: valida o atlas antes de cada push.
# Para pular uma vez (não recomendado): git push --no-verify
raiz="$(git rev-parse --show-toplevel)"
motor="{motor}"
[ -f "$motor/scripts/validar.py" ] || motor="$raiz/../atlas-motor"
for py in python3 python py; do
  if "$py" -c "import tomllib" >/dev/null 2>&1; then
    exec "$py" "$motor/scripts/validar.py" --local "$raiz"
  fi
done
echo "pre-push: não achei Python 3.11+ ou o atlas-motor ($motor); a validação não rodou." >&2
echo "Ajuste o PATH ou, só desta vez, use git push --no-verify." >&2
exit 1
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumento_local(ap)
    args = ap.parse_args()
    local = args.local.resolve()
    r = subprocess.run(["git", "-C", str(local), "rev-parse", "--git-path", "hooks"], capture_output=True, text=True)
    if r.returncode or not (local / "atlas.toml").exists():
        sys.exit(f"{local} não parece ser o repositório Git de um município (falta .git ou atlas.toml).")
    ganchos = (local / r.stdout.strip()).resolve()
    ganchos.mkdir(parents=True, exist_ok=True)
    arq = ganchos / "pre-push"
    arq.write_text(GANCHO.format(motor=MOTOR.as_posix()), encoding="utf-8", newline="\n")
    arq.chmod(arq.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Gancho instalado: {arq}. O validador roda antes de cada push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
