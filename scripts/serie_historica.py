"""Série histórica dos indicadores de um município, refeita a partir do Git.

Os retratos do OSM (dados/osm/) e as bases oficiais (dados/oficiais/) ficam versionados
no repositório do município. Este script percorre os commits que mudaram o retrato,
extrai o estado do repositório em cada um e recalcula os indicadores com o motor
ATUAL, de modo que toda a série usa o mesmo método. Nada precisa ser anotado à parte.

Uso:
  python ../atlas-motor/scripts/serie_historica.py                       # imprime a série
  python ../atlas-motor/scripts/serie_historica.py --saida serie.csv     # grava em CSV
Colunas: commit, data_commit, base_osm, tema, total, com_nome, C_t, Q_t, oficiais,
correspondidos, km_vias, km_pavimento, motor.

Os números são agregados (sem dado pessoal). Antes de publicar a série de um município,
confirme com a coordenação e com o parceiro (os repositórios municipais são privados).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from comum import argumento_local, ler_config, ler_temas, versao_motor
from indicadores import calcular

CAMPOS = ["commit", "data_commit", "base_osm", "tema", "total", "com_nome", "C_t", "Q_t", "oficiais",
          "correspondidos", "km_vias", "km_pavimento", "motor"]


def git(local: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=local, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def commits_do_retrato(local: Path) -> list[tuple[str, str]]:
    saida = git(local, "log", "--reverse", "--format=%H %cs", "--", "dados/osm/retrato.json")
    return [tuple(l.split(" ", 1)) for l in saida.splitlines() if l.strip()]


def extrair(local: Path, commit: str, destino: Path) -> None:
    """Estado do repositório no commit (só o necessário), sem tocar na cópia de trabalho."""
    dados = subprocess.run(["git", "archive", "--format=zip", commit, "atlas.toml", "temas.toml", "dados"],
                           cwd=local, capture_output=True, check=True).stdout
    zipfile.ZipFile(io.BytesIO(dados)).extractall(destino)


def contar_com_nome(local: Path, tema_id: str) -> int:
    arq = local / "dados" / "osm" / f"{tema_id}.geojson"
    if not arq.exists():
        return 0
    return sum(1 for f in json.loads(arq.read_text(encoding="utf-8"))["features"] if f["properties"]["tags"].get("name"))


def serie(local: Path) -> list[dict]:
    linhas = []
    for commit, data in commits_do_retrato(local):
        with tempfile.TemporaryDirectory() as tmp:
            estado = Path(tmp)
            extrair(local, commit, estado)
            config = ler_config(estado)
            retrato = json.loads((estado / "dados" / "osm" / "retrato.json").read_text(encoding="utf-8"))
            for t in ler_temas(estado):
                if not (estado / "dados" / "osm" / f"{t.id}.geojson").exists():
                    continue
                res = calcular(estado, t, config)
                comp = res.get("completude") or {}
                linhas.append({
                    "commit": commit[:10], "data_commit": data,
                    "base_osm": retrato.get("temas", {}).get(t.id, {}).get("base_osm") or retrato.get("base_osm", ""),
                    "tema": t.id, "total": res["total"], "com_nome": contar_com_nome(estado, t.id),
                    "C_t": comp.get("C_t", ""), "Q_t": comp.get("Q_t", ""), "oficiais": comp.get("oficiais", ""),
                    "correspondidos": comp.get("correspondidos", ""), "km_vias": res.get("km_vias", ""),
                    "km_pavimento": res.get("km_pavimento", ""), "motor": versao_motor()})
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumento_local(ap)
    ap.add_argument("--saida", type=Path, help="arquivo CSV (padrão: imprime na tela)")
    args = ap.parse_args()
    local = args.local.resolve()
    try:
        linhas = serie(local)
    except subprocess.CalledProcessError as e:
        print(f"Erro do git: {e.stderr or e}", file=sys.stderr)
        return 1
    destino = args.saida.open("w", encoding="utf-8", newline="") if args.saida else sys.stdout
    w = csv.DictWriter(destino, fieldnames=CAMPOS)
    w.writeheader()
    w.writerows(linhas)
    if args.saida:
        destino.close()
        print(f"{len(linhas)} linha(s) em {args.saida}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
