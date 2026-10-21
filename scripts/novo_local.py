"""Cria o repositório do atlas de um município novo a partir de modelo-local/.

Busca no OpenStreetMap (Overpass), pelo código IBGE, a relação do limite municipal,
a caixa envolvente, o Wikidata e a sede (place=city|town com o nome do município),
e preenche o modelo. Sem rede, informe --relacao, --bbox e --sede-bbox; como as caixas
começam com sinal de menos, use o sinal de igual: --bbox=-19.45,-46.54,-19.04,-46.08.

Uso (da pasta que contém o atlas-motor):
  python atlas-motor/scripts/novo_local.py --nome "São Gotardo" --ibge 3162104
  python atlas-motor/scripts/novo_local.py --nome "São Gotardo" --ibge 3162104 --baixar --git
Opções: --uf (padrão MG), --slug (padrão: nome sem acentos), --destino (padrão: ../atlas-<slug>
ao lado do motor), --baixar (primeiro retrato do OSM), --git (git init e primeiro commit).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

from comum import MOTOR, versao_motor

MODELO = MOTOR / "modelo-local"
SERVIDORES = {"overpass": {"servidores": ["https://overpass-api.de/api/interpreter",
                                          "https://overpass.openstreetmap.fr/api/interpreter"],
                           "tempo_limite": 90}}


def slug(nome: str) -> str:
    t = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def caixa(valor: str) -> list[float]:
    partes = [float(x) for x in valor.replace(" ", "").split(",")]
    if len(partes) != 4:
        raise argparse.ArgumentTypeError("use sul,oeste,norte,leste")
    return partes


def buscar_no_osm(nome: str, ibge: str) -> dict:
    from baixar_osm import consultar              # só com rede
    bruto, _ = consultar(SERVIDORES, f'relation["boundary"="administrative"]["admin_level"="8"]'
                                     f'["IBGE:GEOCODIGO"="{ibge}"];out tags bb;')
    rels = [e for e in bruto["elements"] if e["type"] == "relation"]
    if not rels:
        sys.exit(f"Nenhum limite municipal com IBGE:GEOCODIGO={ibge} no OSM. Use --sem-rede com --relacao e --bbox.")
    rel = rels[0]
    if slug(rel["tags"].get("name", "")) != slug(nome):
        print(f"Aviso: no OSM, o município {ibge} se chama '{rel['tags'].get('name')}'.", file=sys.stderr)
    b = rel["bounds"]
    bbox = [round(b["minlat"] - 0.0005, 4), round(b["minlon"] - 0.0005, 4),
            round(b["maxlat"] + 0.0005, 4), round(b["maxlon"] + 0.0005, 4)]
    s, o, n, l = bbox
    bruto, _ = consultar(SERVIDORES, f'node({s},{o},{n},{l})[place~"^(city|town)$"]["name"="{rel["tags"].get("name", nome)}"];out;')
    sedes = [e for e in bruto["elements"] if e["type"] == "node"]
    if sedes:
        lat, lon = sedes[0]["lat"], sedes[0]["lon"]
    else:
        print("Aviso: sede não encontrada (place=city|town com o nome do município); usei o centro da caixa.",
              file=sys.stderr)
        lat, lon = (s + n) / 2, (o + l) / 2
    sede = [round(lat - 0.015, 4), round(lon - 0.017, 4), round(lat + 0.015, 4), round(lon + 0.017, 4)]
    return {"relacao": rel["id"], "bbox": bbox, "sede_bbox": sede, "wikidata": rel["tags"].get("wikidata", "")}


def criar(destino: Path, trocas: dict[str, str]) -> None:
    shutil.copytree(MODELO, destino)
    (destino / "gitignore").rename(destino / ".gitignore")
    for arq in destino.rglob("*"):
        if arq.is_file() and arq.suffix in {".toml", ".md", ".qmd", ".yml", ".csv"} or arq.name == ".gitignore":
            texto = arq.read_text(encoding="utf-8")
            for marca, valor in trocas.items():
                texto = texto.replace(marca, valor)
            arq.write_text(texto, encoding="utf-8", newline="\n")
    prancha = (MOTOR / "modelos" / "prancha.qmd").read_text(encoding="utf-8")
    for marca, valor in {"@@NUMERO@@": "1", "@@TITULO@@": "Localização e limites", "@@ID@@": "localizacao",
                         "@@TEXTO@@": f"{trocas['@@NOME@@']} fica em {trocas['@@UF@@']}. O mapa mostra o limite do "
                                      "município no OpenStreetMap, a sede e os distritos, povoados e localidades registrados."}.items():
        prancha = prancha.replace(marca, valor)
    (destino / "atlas" / "pranchas" / "01-localizacao.qmd").write_text(prancha, encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nome", required=True)
    ap.add_argument("--ibge", required=True)
    ap.add_argument("--uf", default="MG")
    ap.add_argument("--slug")
    ap.add_argument("--destino", type=Path)
    ap.add_argument("--sem-rede", action="store_true", help="não consultar o OSM (informe --relacao, --bbox, --sede-bbox)")
    ap.add_argument("--relacao", type=int)
    ap.add_argument("--bbox", type=caixa)
    ap.add_argument("--sede-bbox", type=caixa)
    ap.add_argument("--wikidata", default="")
    ap.add_argument("--baixar", action="store_true", help="baixar o primeiro retrato do OSM")
    ap.add_argument("--git", action="store_true", help="git init e primeiro commit")
    args = ap.parse_args()

    if not re.fullmatch(r"\d{7}", args.ibge):
        sys.exit("--ibge deve ter 7 dígitos")
    s = args.slug or slug(args.nome)
    destino = (args.destino or MOTOR.parent / f"atlas-{s}").resolve()
    if destino.exists() and any(destino.iterdir()):
        sys.exit(f"{destino} já existe e não está vazio.")
    if args.sem_rede:
        if not (args.relacao and args.bbox and args.sede_bbox):
            sys.exit("--sem-rede exige --relacao, --bbox e --sede-bbox")
        dados = {"relacao": args.relacao, "bbox": args.bbox, "sede_bbox": args.sede_bbox, "wikidata": args.wikidata}
    else:
        dados = buscar_no_osm(args.nome, args.ibge)
        for chave in ("relacao", "bbox", "sede_bbox"):
            if getattr(args, chave.replace("-", "_")):
                dados[chave] = getattr(args, chave)
    if destino.exists():
        destino.rmdir()
    criar(destino, {
        "@@NOME@@": args.nome, "@@UF@@": args.uf, "@@IBGE@@": args.ibge, "@@SLUG@@": s,
        "@@RELACAO@@": str(dados["relacao"]), "@@WIKIDATA@@": dados["wikidata"],
        "@@BBOX@@": str(dados["bbox"]), "@@SEDE_BBOX@@": str(dados["sede_bbox"]),
        "@@MOTOR@@": versao_motor(), "@@DATA@@": date.today().isoformat(),
    })
    print(f"Criado: {destino}")
    if args.baixar:
        if subprocess.run([sys.executable, str(MOTOR / "scripts" / "baixar_osm.py"), "--local", str(destino)]).returncode:
            return 1
    if args.git:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=destino, check=True)
        subprocess.run(["git", "add", "-A"], cwd=destino, check=True)
        subprocess.run(["git", "commit", "-q", "-m", f"[CONFIG] Cria o atlas de {args.nome} (motor {versao_motor()})"],
                       cwd=destino, check=True)
    print("Próximos passos: conferir atlas.toml (sede_bbox, registro), rodar validar.py, criar o repositório "
          f"youthmappers-ufv/atlas-{s} (privado) e seguir docs/configuracao-github.md do motor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
