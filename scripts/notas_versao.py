"""Notas de uma versão do motor, tiradas do CHANGELOG.md, e a regra de release automático.

O workflow de release (.github/workflows/release.yml) usa este script para o texto do release
no GitHub e para decidir se uma tag dispara o release sozinha: só as versões maiores
(vX.0.0, X >= 1); as demais são publicadas à mão (Actions > Release > Run workflow).

Uso:
  python scripts/notas_versao.py v0.9.0                 # imprime as notas da versão
  python scripts/notas_versao.py v1.0.0 --automatico    # sai com 0 se a tag dispara o release sozinha
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
RE_SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def automatico(tag: str) -> bool:
    """Versão maior (vX.0.0 com X >= 1): o release sai sozinho com a tag."""
    m = RE_SEMVER.match(tag)
    return bool(m) and int(m[1]) >= 1 and m[2] == "0" and m[3] == "0"


def notas(tag: str, changelog: str) -> str:
    """A seção "## <tag> — <data>" do CHANGELOG, sem o título."""
    m = re.search(rf"^## {re.escape(tag)}(?: — [^\n]*)?\n(.*?)(?=^## |\Z)", changelog, re.MULTILINE | re.DOTALL)
    if not m:
        raise LookupError(f"{tag} não está no CHANGELOG.md")
    return m[1].strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tag")
    ap.add_argument("--automatico", action="store_true", help="só dizer (código de saída) se o release é automático")
    args = ap.parse_args()
    if not RE_SEMVER.match(args.tag):
        print(f"{args.tag} não é uma versão semântica (vX.Y.Z)", file=sys.stderr)
        return 2
    if args.automatico:
        return 0 if automatico(args.tag) else 1
    try:
        print(notas(args.tag, (MOTOR / "CHANGELOG.md").read_text(encoding="utf-8")), end="")
    except LookupError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
