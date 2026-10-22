"""Indicadores de completude e de preenchimento de cada tema.

Temas com base oficial (temas.toml: referencia = <pasta em dados/oficiais/>):
  C_t = itens oficiais com correspondente no OSM / itens oficiais
  Q_t = correspondidos com os atributos essenciais (nome e endereço) / correspondidos
  Correspondência: mesmo item a até distancia_max_m e similaridade de nome >= similaridade_min
  (atlas.toml), pareando cada objeto do OSM no máximo uma vez. A similaridade é a maior entre a
  do nome normalizado inteiro e a das palavras distintivas (nome contido no outro: 0,95).
Todos os temas: total de objetos e proporção com nome. Com indicadores = ["servico"] no catálogo:
  endereço e horário; com ["vias"]: comprimento total e proporção com pavimento informado.

Uso como módulo (construir.py) ou direto, para conferir no terminal:
  python <motor>/scripts/indicadores.py --local <município> [--tema educacao]
"""
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

from comum import (Tema, argumento_local, distancia_m, ler_config, ler_csv, ler_temas, ler_toml,
                   normalizar_nome, ponto_representativo)


def ler_feicoes(local: Path, tema_id: str) -> list[dict]:
    arq = local / "dados" / "osm" / f"{tema_id}.geojson"
    if not arq.exists():
        return []
    return json.loads(arq.read_text(encoding="utf-8"))["features"]


# Palavras que dizem o tipo do lugar ou ligam o nome, não qual lugar é ("Colégio Dimensão" e
# "COLEGIO DIMENSAO ENSINO FUNDAMENTAL E MEDIO" têm a mesma palavra distintiva: dimensao).
GENERICAS = set("""
a as o os e de da das do dos em no na
escola escolas estadual municipal particular privada publica colegio instituto centro educacional
educacao ensino infantil fundamental medio tecnica creche unidade basica saude posto hospital
""".split())


def palavras_distintivas(nome: str, ignorar: frozenset[str] = frozenset()) -> set[str]:
    return {p for p in normalizar_nome(nome).split() if p not in GENERICAS | ignorar and len(p) > 1}


def similaridade(a: str, b: str, ignorar: frozenset[str] = frozenset()) -> float:
    """Semelhança de dois nomes, de 0 a 1: a maior entre a do texto normalizado inteiro e a das
    palavras distintivas (fração das palavras do nome mais curto que estão no outro).

    Um nome contido no outro (palavras do mais curto todas no mais longo) vale 0,95, abaixo de
    um nome igual (1,0), que tem a preferência quando os dois disputam o mesmo objeto. Uma única
    palavra em comum só conta se tiver 4 letras ou mais. `ignorar`: palavras que não distinguem
    neste município (as do nome dele: "Colégio Gama de São Gotardo" não é o "Centro de Ensino
    Superior de São Gotardo").
    """
    texto = SequenceMatcher(None, normalizar_nome(a), normalizar_nome(b)).ratio()
    pa, pb = palavras_distintivas(a, ignorar), palavras_distintivas(b, ignorar)
    menor = min(len(pa), len(pb))
    comuns = pa & pb
    if not menor or (menor == 1 and max(map(len, comuns), default=0) < 4):
        return texto
    return max(texto, 0.95 * len(comuns) / menor)


def correspondencias(oficiais: list[dict], feicoes: list[dict], dist_max: float, sim_min: float,
                     municipio: str = "") -> list[tuple]:
    """Pares (índice oficial, índice feição, distância, similaridade), um para um.

    oficiais: dicts com 'nome', 'lat', 'lon' (floats ou None). municipio: nome do município,
    cujas palavras não contam como distintivas.
    """
    ignorar = frozenset(normalizar_nome(municipio).split())
    pontos = [ponto_representativo(f["geometry"]) for f in feicoes]
    candidatos = []
    for i, o in enumerate(oficiais):
        if o.get("lat") is None or o.get("lon") is None:
            continue
        for j, f in enumerate(feicoes):
            nome = f["properties"]["tags"].get("name", "")
            if not nome:
                continue
            d = distancia_m(o["lon"], o["lat"], *pontos[j])
            if d > dist_max:
                continue
            s = similaridade(o["nome"], nome, ignorar)
            if s >= sim_min:
                candidatos.append((i, j, d, s))
    pares, usados_o, usados_f = [], set(), set()
    for i, j, d, s in sorted(candidatos, key=lambda c: (-c[3], c[2])):
        if i not in usados_o and j not in usados_f:
            pares.append((i, j, d, s))
            usados_o.add(i)
            usados_f.add(j)
    return sorted(pares)


def ler_oficial(local: Path, base: str) -> tuple[dict, list[dict]] | None:
    pasta = local / "dados" / "oficiais" / base
    if not (pasta / "fonte.toml").exists():
        return None
    fonte = ler_toml(pasta / "fonte.toml")
    col = fonte["colunas"]
    _, linhas = ler_csv(pasta / fonte["arquivo"])
    itens = []
    for linha in linhas:
        def num(chave):
            try:
                return float(linha[col[chave]])
            except (TypeError, ValueError, KeyError):
                return None
        itens.append({"id": linha.get(col["id"], ""), "nome": linha.get(col["nome"], ""),
                      "lat": num("lat"), "lon": num("lon")})
    return fonte, itens


def comprimento_m(geometria: dict) -> float:
    if geometria["type"] != "LineString":
        return 0.0
    c = geometria["coordinates"]
    return sum(distancia_m(*a, *b) for a, b in zip(c, c[1:]))


def calcular(local: Path, tema: Tema, config: dict) -> dict:
    feicoes = ler_feicoes(local, tema.id)
    tags = [f["properties"]["tags"] for f in feicoes]
    total = len(feicoes)
    res = {"tema": tema.id, "total": total, "linhas": []}

    def pct(n, d):
        return round(100 * n / d, 1) if d else None

    com_nome = sum(1 for t in tags if t.get("name"))
    res["linhas"].append(("Objetos no OpenStreetMap", str(total)))
    res["linhas"].append(("Com nome", f"{com_nome} ({pct(com_nome, total)}%)" if total else "—"))
    if "servico" in tema.indicadores:
        com_horario = sum(1 for t in tags if t.get("opening_hours"))
        com_endereco = sum(1 for t in tags if t.get("addr:street"))
        res["linhas"].append(("Com endereço (rua)", f"{com_endereco} ({pct(com_endereco, total)}%)" if total else "—"))
        res["linhas"].append(("Com horário de funcionamento", f"{com_horario} ({pct(com_horario, total)}%)" if total else "—"))
    if "vias" in tema.indicadores:
        vias = [f for f in feicoes if "highway" in f["properties"]["tags"]]
        km = sum(comprimento_m(f["geometry"]) for f in vias) / 1000
        km_pav = sum(comprimento_m(f["geometry"]) for f in vias if f["properties"]["tags"].get("surface")) / 1000
        res["linhas"].append(("Comprimento de vias", f"{km:.1f} km"))
        res["linhas"].append(("Com tipo de pavimento informado", f"{km_pav:.1f} km ({pct(km_pav, km)}%)" if km else "—"))
        res["km_vias"], res["km_pavimento"] = round(km, 2), round(km_pav, 2)

    if tema.referencia != "interno":
        oficial = ler_oficial(local, tema.referencia)
        if oficial is None:
            res["completude"] = None
            res["linhas"].append(("Completude em relação à base oficial", f"base '{tema.referencia}' ainda não carregada"))
        else:
            fonte, itens = oficial
            cc = config["completude"]
            pares = correspondencias(itens, feicoes, cc["distancia_max_m"], cc["similaridade_min"],
                                     config["municipio"]["nome"])
            correspondidos = {i for i, _, _, _ in pares}
            completos = sum(1 for _, j, _, _ in pares
                            if tags[j].get("name") and tags[j].get("addr:street"))
            sem_coord = sum(1 for o in itens if o["lat"] is None or o["lon"] is None)
            c_t, q_t = pct(len(pares), len(itens)), pct(completos, len(pares))
            res["completude"] = {"C_t": c_t, "Q_t": q_t, "oficiais": len(itens), "correspondidos": len(pares),
                                 "sem_coordenada": sem_coord, "fonte": fonte["nome"], "data_acesso": str(fonte["data_acesso"])}
            res["linhas"].append((f"Itens na base oficial ({fonte['nome']})", str(len(itens))))
            res["linhas"].append(("Completude C_t (com correspondente no OSM)", f"{len(pares)} ({c_t}%)"))
            res["linhas"].append(("Qualidade Q_t (nome e endereço)", f"{completos} ({q_t}%)" if pares else "—"))
            res["lacunas"] = [o for i, o in enumerate(itens) if i not in correspondidos]
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tema", action="append")
    argumento_local(ap)
    args = ap.parse_args()
    local = args.local.resolve()
    config = ler_config(local)
    for t in ler_temas(local):
        if args.tema and t.id not in args.tema:
            continue
        r = calcular(local, t, config)
        print(f"\n{t.numero}. {t.titulo}")
        for rotulo, valor in r["linhas"]:
            print(f"  {rotulo}: {valor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
