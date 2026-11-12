"""Comparação entre o OpenStreetMap e a base oficial de um tema (modo "itens").

Toda prancha mostra os dados do OpenStreetMap; a base oficial, quando existe, entra como
comparação, nunca no lugar deles. Este módulo junta as duas fontes numa estrutura só, de onde
saem o mapa de comparação (mapas.py), o quadro-resumo e as tabelas (construir.py), o mapa
interativo do site e os arquivos para download. Site e PDF nunca divergem: leem o mesmo dado.

Cada item recebe uma situação:
  ambas       item oficial com correspondente no OSM;
  so_oficial  item oficial sem correspondente (lacuna do mapa), com número e motivo provável;
  so_osm      objeto do OSM sem item oficial (base desatualizada, objeto fora do cadastro ou
              erro no mapa: a conferir).
O fonte.toml da base pode dizer quais objetos do OSM ela cobre (filtro_osm): o Catálogo de
Escolas não lista universidades, que por isso ficam fora da comparação, e não "só no OSM".

Só biblioteca padrão.
"""
from __future__ import annotations

import csv
import io
import json
import re

from comum import numero, ponto_representativo, porcentagem, texto_md

SITUACOES_COMPARACAO = {"ambas": "Nas duas fontes", "so_oficial": "Só na base oficial", "so_osm": "Só no OpenStreetMap"}


def no_escopo(tags: dict, filtro: list[str] | None) -> bool:
    """O objeto do OSM é do tipo que a base oficial cobre? filtro: ["amenity=school|kindergarten", ...]
    (chave=valor, com alternativas separadas por |; basta uma regra casar). Sem filtro: todos."""
    if not filtro:
        return True
    for regra in filtro:
        chave, _, valores = regra.partition("=")
        if chave in tags and (not valores or re.fullmatch(valores, tags[chave])):
            return True
    return False


def montar(fonte: dict, itens: list[dict], feicoes: list[dict], pares: list[tuple], motivos: dict[int, str],
           fora_escopo: int = 0) -> dict:
    """Estrutura da comparação. feicoes: só as do escopo da base; pares: (i oficial, j feição, d, s)."""
    par_de_oficial = {i: (j, d) for i, j, d, _ in pares}
    oficiais, numero_lacuna = [], 0
    for i, o in enumerate(itens):
        linha = {"id": o["id"], "nome": o["nome"], "lat": o["lat"], "lon": o["lon"]}
        if i in par_de_oficial:
            j, d = par_de_oficial[i]
            f = feicoes[j]["properties"]
            linha.update(situacao="ambas", n=None, osm=f["osm"], nome_osm=f["tags"].get("name", ""),
                         distancia_m=round(d), motivo="")
        else:
            numero_lacuna += 1
            linha.update(situacao="so_oficial", n=numero_lacuna, osm="", nome_osm="", distancia_m=None,
                         motivo=motivos.get(i, ""))
        oficiais.append(linha)
    pareadas = {j for _, j, _, _ in pares}
    so_osm = []
    for j, f in enumerate(feicoes):
        if j not in pareadas:
            lon, lat = ponto_representativo(f["geometry"])
            so_osm.append({"osm": f["properties"]["osm"], "nome": f["properties"]["tags"].get("name", ""),
                           "lon": round(lon, 7), "lat": round(lat, 7)})
    n_of, n_osm, n_ambas = len(itens), len(feicoes), len(pares)
    return {
        "fonte": {"nome": fonte.get("nome", ""), "orgao": fonte.get("orgao", ""),
                  "data_acesso": str(fonte.get("data_acesso", ""))},
        "oficiais": oficiais, "so_osm": so_osm, "fora_escopo": fora_escopo,
        "resumo": {"oficial": n_of, "osm": n_osm, "ambas": n_ambas, "so_oficial": n_of - n_ambas,
                   "so_osm": n_osm - n_ambas, "cobertura": round(100 * n_ambas / n_of, 1) if n_of else None},
    }


def quadro_resumo(comp: dict) -> str:
    """Quadro-resumo, igual em todas as pranchas com base oficial (Markdown)."""
    r, f = comp["resumo"], comp["fonte"]
    linhas = [
        (f"Itens na base oficial ({texto_md(f['orgao'] or f['nome'])})", str(r["oficial"])),
        ("Objetos no OpenStreetMap (do tipo que a base cobre)", str(r["osm"])),
        ("Nas duas fontes", str(r["ambas"])),
        ("Só na base oficial (falta no mapa)", str(r["so_oficial"])),
        ("Só no OpenStreetMap (falta na base ou a conferir)", str(r["so_osm"])),
        ("**Cobertura do mapa** (nas duas ÷ base oficial)", f"**{porcentagem(r['cobertura'])}**"),
    ]
    corpo = "\n".join(f"| {a} | {b} |" for a, b in linhas)
    nota = (f"\nOutros {comp['fora_escopo']} objeto(s) do tema no OpenStreetMap são de tipos que a base oficial "
            "não cobre e ficam fora da comparação.\n") if comp["fora_escopo"] else ""
    return f"| Comparação com a base oficial | Quantidade |\n|:--|--:|\n{corpo}\n{nota}"


def tabela_so_oficial(comp: dict, maximo: int = 60) -> str:
    lacunas = [o for o in comp["oficiais"] if o["situacao"] == "so_oficial"]
    if not lacunas:
        return ""
    partes = [f"\n**Só na base oficial: itens sem correspondente no mapa** ({len(lacunas)}). "
              "O número é o do item no mapa de comparação.\n",
              # traços na proporção das larguras (nº 6%, código 14%, nome 32%, motivo 48%)
              "| Nº | Código | Nome | Motivo provável |\n|:-|:---|:-------|:-----------|\n"
              + "\n".join(f"| {o['n']} | {texto_md(o['id'])} | {texto_md(o['nome'])} | {texto_md(o['motivo'])} |"
                          for o in lacunas[:maximo]) + "\n"]
    if len(lacunas) > maximo:
        partes.append(f"\n… e mais {len(lacunas) - maximo} (lista completa no arquivo de comparação, em Dados para download).\n")
    return "\n".join(partes)


def tabela_so_osm(comp: dict, maximo: int = 40) -> str:
    itens = comp["so_osm"]
    if not itens:
        return ""
    partes = [f"\n**Só no OpenStreetMap: objetos sem item na base oficial** ({len(itens)}). Podem ser novos, "
              "estar fora do cadastro ou ser erro no mapa: conferir.\n",
              "| Objeto no OSM | Nome no mapa |\n|:----|:--------|\n"
              + "\n".join(f"| [{o['osm']}](https://www.openstreetmap.org/{o['osm']}) | {texto_md(o['nome']) or '*sem nome*'} |"
                          for o in itens[:maximo]) + "\n"]
    if len(itens) > maximo:
        partes.append(f"\n… e mais {len(itens) - maximo} (lista completa no arquivo de comparação, em Dados para download).\n")
    return "\n".join(partes)


def geojson(comp: dict) -> str:
    """Pontos da comparação (uma feição por linha): itens oficiais com coordenada e objetos só no OSM.
    Da base oficial saem só código, nome e situação."""
    feicoes = []
    for o in comp["oficiais"]:
        if o["lat"] is None or o["lon"] is None:
            continue
        feicoes.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [o["lon"], o["lat"]]},
                        "properties": {"fonte": "oficial", "situacao": o["situacao"], "n": o["n"], "codigo": o["id"],
                                       "nome": o["nome"], "osm": o["osm"], "motivo": o["motivo"]}})
    for o in comp["so_osm"]:
        feicoes.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [o["lon"], o["lat"]]},
                        "properties": {"fonte": "osm", "situacao": "so_osm", "n": None, "codigo": "", "nome": o["nome"],
                                       "osm": o["osm"], "motivo": ""}})
    linhas = ",\n".join(json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in feicoes)
    return '{"type":"FeatureCollection","features":[\n' + linhas + "\n]}\n"


def csv_texto(comp: dict) -> str:
    """A comparação inteira em CSV, inclusive os itens oficiais sem coordenada."""
    saida = io.StringIO()
    w = csv.writer(saida, lineterminator="\n")
    w.writerow(["situacao", "numero", "codigo_oficial", "nome_oficial", "objeto_osm", "nome_osm", "distancia_m",
                "latitude", "longitude", "motivo_provavel"])
    for o in comp["oficiais"]:
        w.writerow([o["situacao"], o["n"] or "", o["id"], o["nome"], o["osm"], o["nome_osm"],
                    "" if o["distancia_m"] is None else o["distancia_m"], o["lat"] or "", o["lon"] or "", o["motivo"]])
    for o in comp["so_osm"]:
        w.writerow(["so_osm", "", "", "", o["osm"], o["nome"], "", o["lat"], o["lon"], ""])
    return saida.getvalue()


def resumo_curto(comp: dict | None) -> str:
    """Cobertura para a tabela-síntese: "3 de 15 (20%)"."""
    if not comp:
        return "—"
    r = comp["resumo"]
    return f"{r['ambas']} de {numero(r['oficial'], 0)} ({porcentagem(r['cobertura'])})"
