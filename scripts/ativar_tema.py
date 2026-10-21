"""Abre (ou muda a situação de) uma prancha no atlas de um município.

Atualiza [tema.<id>] no temas.toml e, se a prancha ficar ativa e ainda não existir,
cria atlas/pranchas/<nn>-<id>.qmd a partir de modelos/prancha.qmd.

Uso: python ../atlas-motor/scripts/ativar_tema.py educacao [--situacao publicado]
Depois: baixar_osm.py --tema <id>, escrever o texto da prancha, validar.py.
"""
from __future__ import annotations

import argparse
import re
import sys

from comum import MOTOR, SITUACOES, argumento_local, ler_temas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tema")
    ap.add_argument("--situacao", default="em-andamento", choices=SITUACOES)
    argumento_local(ap)
    args = ap.parse_args()
    local = args.local.resolve()
    temas = {t.id: t for t in ler_temas(local)}
    if args.tema not in temas:
        print(f"Tema '{args.tema}' não está no catálogo nem no temas.toml. Temas: {', '.join(temas)}", file=sys.stderr)
        return 2

    arq = local / "temas.toml"
    texto = arq.read_text(encoding="utf-8") if arq.exists() else ""
    secao = re.search(rf"^\[tema\.{re.escape(args.tema)}\][^\[]*", texto, re.MULTILINE)
    linha = f'situacao = "{args.situacao}"'
    if secao:
        bloco = secao.group(0)
        novo = re.sub(r'^situacao\s*=.*$', linha, bloco, flags=re.MULTILINE) if re.search(r"^situacao\s*=", bloco, re.MULTILINE) \
            else bloco.rstrip("\n") + f"\n{linha}\n\n"
        texto = texto[:secao.start()] + novo + texto[secao.end():]
    else:
        texto = texto.rstrip("\n") + f"\n\n[tema.{args.tema}]\n{linha}\n"
    arq.write_text(texto, encoding="utf-8", newline="\n")

    t = ler_temas(local)[[x.id for x in ler_temas(local)].index(args.tema)]
    prancha = local / "atlas" / "pranchas" / t.prancha
    if t.ativo and not prancha.exists():
        modelo = (MOTOR / "modelos" / "prancha.qmd").read_text(encoding="utf-8")
        for marca, valor in {"@@NUMERO@@": str(t.numero), "@@TITULO@@": t.titulo, "@@ID@@": t.id,
                             "@@TEXTO@@": "*Texto da prancha a escrever pela equipe.*"}.items():
            modelo = modelo.replace(marca, valor)
        prancha.parent.mkdir(parents=True, exist_ok=True)
        prancha.write_text(modelo, encoding="utf-8", newline="\n")
        print(f"Criada atlas/pranchas/{t.prancha}")
    if not t.ativo and prancha.exists():
        print(f"A prancha voltou a 'planejado': apague atlas/pranchas/{t.prancha} (o texto fica no histórico do Git).")
    print(f"{t.id}: situação '{t.situacao}'. Próximo: python {MOTOR.name}/scripts/baixar_osm.py --tema {t.id} "
          "e validar.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
