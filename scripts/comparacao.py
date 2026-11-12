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
        "modo": "itens",
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


# ================================================================ Modo "contagem" (por unidade territorial)
# Razão OSM ÷ oficial em cinco classes; as cores (escala viridis, legível para daltônicos) são as
# mesmas no mapa do PDF e no mapa interativo, porque vão gravadas no arquivo de comparação.
CLASSES_RAZAO = [(25, "menos de 25%", "#440154"), (50, "25 a 50%", "#3B528B"), (75, "50 a 75%", "#21908C"),
                 (100, "75 a 100%", "#5DC863"), (float("inf"), "100% ou mais", "#FDE725")]
SEM_BASE = ("sem itens na base", "#BDBDBD")


def classe_razao(razao: float | None) -> tuple[str, str]:
    if razao is None:
        return SEM_BASE
    return next((rotulo, cor) for limite, rotulo, cor in CLASSES_RAZAO if razao < limite)


def _caixa(poligonos: list) -> tuple[float, float, float, float]:
    xs = [p[0] for pol in poligonos for p in pol[0]]
    ys = [p[1] for pol in poligonos for p in pol[0]]
    return min(xs), min(ys), max(xs), max(ys)


def montar_contagem(fonte: dict, totais: dict[str, float], unidades: list[dict], feicoes: list[dict]) -> dict:
    """Comparação por contagem: em cada unidade (setor censitário), quantos objetos há no
    OpenStreetMap e quantos itens a base oficial conta. totais: unidade -> total oficial."""
    from comum import dentro, poligonos_de
    formas = []
    for u in unidades:
        pols = poligonos_de(u["geometry"])
        formas.append((u["properties"], pols, _caixa(pols)))
    contagem, fora = [0] * len(formas), 0
    for f in feicoes:
        x, y = ponto_representativo(f["geometry"])
        for k, (_, pols, (x0, y0, x1, y1)) in enumerate(formas):
            if x0 <= x <= x1 and y0 <= y <= y1 and any(
                    dentro(x, y, pol[:1]) and not any(dentro(x, y, [furo]) for furo in pol[1:]) for pol in pols):
                contagem[k] += 1
                break
        else:
            fora += 1
    linhas = []
    for (props, _, _), osm, u in zip(formas, contagem, unidades):
        oficial = totais.get(props["setor"], 0)
        razao = round(100 * osm / oficial, 1) if oficial else None
        rotulo, cor = classe_razao(razao)
        linhas.append({"unidade": props["setor"], "situacao": props.get("situacao", ""), "oficial": int(oficial), "osm": osm,
                       "razao": razao, "classe": rotulo, "cor": cor, "geometry": u["geometry"], "n": None})
    # numeradas da maior falta para a menor: é a ordem de prioridade do mapeamento
    for n, linha in enumerate(sorted(linhas, key=lambda l: l["osm"] - l["oficial"]), 1):
        linha["n"] = n
    t_of, t_osm = sum(l["oficial"] for l in linhas), sum(l["osm"] for l in linhas)
    return {
        "modo": "contagem",
        "fonte": {"nome": fonte.get("nome", ""), "orgao": fonte.get("orgao", ""), "data_acesso": str(fonte.get("data_acesso", ""))},
        "rotulos": {"oficial": fonte.get("rotulo_oficial", "Itens na base oficial"),
                    "osm": fonte.get("rotulo_osm", "Objetos no OpenStreetMap")},
        "unidades": sorted(linhas, key=lambda l: l["n"]), "fora": fora,
        "resumo": {"oficial": t_of, "osm": t_osm, "cobertura": round(100 * t_osm / t_of, 1) if t_of else None,
                   "unidades": len(linhas), "abaixo_da_metade": sum(1 for l in linhas if l["razao"] is not None and l["razao"] < 50)},
    }


# ================================================================ Modo "nomes" (logradouros)
TIPOS_LOGRADOURO = {r"\bav\b": "avenida", r"\br\b": "rua", r"\bpca\b": "praca", r"\btv\b": "travessa",
                    r"\bal\b": "alameda", r"\brod\b": "rodovia", r"\bestr\b": "estrada", r"\bcel\b": "coronel",
                    r"\bcap\b": "capitao", r"\bpe\b": "padre", r"\bpres\b": "presidente", r"\bver\b": "vereador"}


def nome_de_rua(nome: str) -> str:
    from comum import normalizar_nome
    t = normalizar_nome(nome)
    for padrao, troca in TIPOS_LOGRADOURO.items():
        t = re.sub(padrao, troca, t)
    return t


def montar_nomes(fonte: dict, oficiais: list[dict], feicoes: list[dict], geometrias: list[dict]) -> dict:
    """Comparação por nomes: cada logradouro com nome na base oficial existe, com o mesmo nome, no
    OpenStreetMap? oficiais: [{"nome", "km"}]; geometrias: faces de logradouro (para o mapa)."""
    from difflib import SequenceMatcher
    nomes_osm: dict[str, str] = {}
    for f in feicoes:
        nome = f["properties"]["tags"].get("name", "")
        if nome:
            nomes_osm.setdefault(nome_de_rua(nome), nome)
    def miolo(chave: str) -> str:
        """O nome sem o tipo de logradouro: é ele que distingue uma rua da outra."""
        return re.sub(r"^(rua|avenida|praca|travessa|alameda|rodovia|estrada|acesso|saida)\s+", "", chave)

    # "SEM DENOMINACAO" é como a base oficial marca a via sem nome: não é um nome a procurar no mapa.
    oficiais = [o for o in oficiais if "sem denominacao" not in nome_de_rua(o["nome"])]
    usados, linhas, n = set(), [], 0
    for o in oficiais:
        chave = nome_de_rua(o["nome"])
        linha = {"nome": o["nome"], "km": o.get("km"), "n": None, "nome_osm": "", "motivo": ""}
        if chave in nomes_osm:
            usados.add(chave)
            linha.update(situacao="ambas", nome_osm=nomes_osm[chave])
        else:
            n += 1
            # Pista de grafia: só pelo miolo do nome e só se ele for longo o bastante ("Rua A" e
            # "Rua Z" são parecidas no texto e nada têm a ver uma com a outra).
            m = miolo(chave)
            parecido = max(((SequenceMatcher(None, m, miolo(k)).ratio(), k) for k in nomes_osm), default=(0, ""))
            motivo = (f"nome parecido no OSM: \"{nomes_osm[parecido[1]]}\" (conferir a grafia)"
                      if parecido[0] >= 0.8 and len(m) >= 5
                      else "nenhuma via com este nome no OSM: sem nome no mapa ou não mapeada")
            linha.update(situacao="so_oficial", n=n, motivo=motivo)
        linhas.append(linha)
    so_osm = [{"nome": original} for chave, original in sorted(nomes_osm.items(), key=lambda kv: kv[1]) if chave not in usados]
    situacao_de = {nome_de_rua(l["nome"]): l["situacao"] for l in linhas}
    n_of, n_ambas = len(linhas), sum(1 for l in linhas if l["situacao"] == "ambas")
    return {
        "modo": "nomes",
        "fonte": {"nome": fonte.get("nome", ""), "orgao": fonte.get("orgao", ""), "data_acesso": str(fonte.get("data_acesso", ""))},
        "oficiais": linhas, "so_osm": so_osm,
        "faces": [{"geometry": g["geometry"], "nome": g["properties"].get("nome", ""),
                   "situacao": (situacao_de.get(nome_de_rua(g["properties"]["nome"]), "sem_nome")
                                if g["properties"].get("nome") else "sem_nome")} for g in geometrias],
        "resumo": {"oficial": n_of, "osm": len(nomes_osm), "ambas": n_ambas, "so_oficial": n_of - n_ambas,
                   "so_osm": len(so_osm), "cobertura": round(100 * n_ambas / n_of, 1) if n_of else None},
    }


CORES_NOMES = {"ambas": ("Nome nas duas fontes", "#1B7837"), "so_oficial": ("Nome só na base oficial", "#C62828"),
               "sem_nome": ("Sem nome na base oficial", "#9E9E9E")}


# ================================================================ Saídas, por modo
def quadro(comp: dict) -> str:
    modo = comp.get("modo", "itens")
    if modo == "itens":
        return quadro_resumo(comp)
    r, f = comp["resumo"], comp["fonte"]
    if modo == "contagem":
        linhas = [(f"{comp['rotulos']['oficial']} ({texto_md(f['orgao'])})", numero(r["oficial"], 0)),
                  (comp["rotulos"]["osm"], numero(r["osm"], 0)),
                  ("Setores com menos da metade mapeada", f"{r['abaixo_da_metade']} de {r['unidades']}"),
                  ("**Razão do mapa** (OpenStreetMap ÷ base oficial)", f"**{porcentagem(r['cobertura'])}**")]
    else:
        linhas = [(f"Logradouros com nome na base oficial ({texto_md(f['orgao'])})", numero(r["oficial"], 0)),
                  ("Nomes de via no OpenStreetMap", numero(r["osm"], 0)),
                  ("Nome nas duas fontes", numero(r["ambas"], 0)),
                  ("Nome só na base oficial (falta no mapa)", numero(r["so_oficial"], 0)),
                  ("Nome só no OpenStreetMap (falta na base ou a conferir)", numero(r["so_osm"], 0)),
                  ("**Cobertura do mapa** (nas duas ÷ base oficial)", f"**{porcentagem(r['cobertura'])}**")]
    corpo = "\n".join(f"| {a} | {b} |" for a, b in linhas)
    nota = (f"\n{comp['fora']} objeto(s) do OpenStreetMap ficam fora de todos os setores e não entram na conta.\n"
            if comp.get("fora") else "")
    return f"| Comparação com a base oficial | Quantidade |\n|:--|--:|\n{corpo}\n{nota}"


def tabela_faltas(comp: dict, maximo: int = 60) -> str:
    """O que falta no mapa: itens só na base (itens), setores por ordem de falta (contagem) ou
    logradouros cujo nome não está no OpenStreetMap (nomes)."""
    modo = comp.get("modo", "itens")
    if modo == "itens":
        return tabela_so_oficial(comp, maximo)
    if modo == "contagem":
        linhas = comp["unidades"][:maximo]
        r = comp["rotulos"]
        partes = ["\n**Setores censitários, da maior falta para a menor.** O número é o do setor no mapa de comparação.\n",
                  f"| Nº | Setor | Situação | {r['oficial']} | {r['osm']} | Razão |\n|:-|:----|:--|--:|--:|--:|\n"
                  + "\n".join(f"| {l['n']} | {l['unidade']} | {texto_md(l['situacao'])} | {numero(l['oficial'], 0)} | "
                              f"{numero(l['osm'], 0)} | {porcentagem(l['razao'])} |" for l in linhas) + "\n"]
        if len(comp["unidades"]) > maximo:
            partes.append(f"\n… e mais {len(comp['unidades']) - maximo} (lista completa no arquivo de comparação).\n")
        return "\n".join(partes)
    faltam = [o for o in comp["oficiais"] if o["situacao"] == "so_oficial"]
    if not faltam:
        return ""
    partes = [f"\n**Só na base oficial: logradouros cujo nome não está no mapa** ({len(faltam)}).\n",
              "| Nº | Logradouro | Faces (km) | Pista |\n|:-|:------|--:|:--------|\n"
              + "\n".join(f"| {o['n']} | {texto_md(o['nome'])} | {numero(o['km'] or 0, 2)} | {texto_md(o['motivo'])} |"
                          for o in faltam[:maximo]) + "\n"]
    if len(faltam) > maximo:
        partes.append(f"\n… e mais {len(faltam) - maximo} (lista completa no arquivo de comparação, em Dados para download).\n")
    return "\n".join(partes)


def tabela_sobras(comp: dict, maximo: int = 40) -> str:
    """O que só está no OpenStreetMap."""
    modo = comp.get("modo", "itens")
    if modo == "itens":
        return tabela_so_osm(comp, maximo)
    if modo != "nomes" or not comp["so_osm"]:
        return ""
    nomes = [texto_md(o["nome"]) for o in comp["so_osm"]]
    resto = f" … e mais {len(nomes) - maximo}." if len(nomes) > maximo else ""
    return (f"\n**Só no OpenStreetMap: nomes de via sem logradouro igual na base oficial** ({len(nomes)}). Podem ser vias "
            "rurais ou novas, ou grafias diferentes: conferir.\n\n" + "; ".join(nomes[:maximo]) + "." + resto + "\n")


def geojson_modo(comp: dict) -> str:
    """Arquivo de comparação para o mapa interativo e para download. Nos modos por contagem e por
    nomes, cada feição leva o rótulo e a cor da sua classe: site e PDF usam a mesma legenda."""
    modo = comp.get("modo", "itens")
    if modo == "itens":
        return geojson(comp)
    feicoes = []
    if modo == "contagem":
        for u in comp["unidades"]:
            feicoes.append({"type": "Feature", "geometry": u["geometry"],
                            "properties": {"rotulo": u["classe"], "cor": u["cor"], "n": u["n"], "unidade": u["unidade"],
                                           "situacao": u["situacao"], "oficial": u["oficial"], "osm": u["osm"], "razao": u["razao"]}})
    else:
        for f in comp["faces"]:
            rotulo, cor = CORES_NOMES[f["situacao"]]
            feicoes.append({"type": "Feature", "geometry": f["geometry"],
                            "properties": {"rotulo": rotulo, "cor": cor, "nome": f["nome"], "situacao": f["situacao"]}})
    linhas = ",\n".join(json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in feicoes)
    return '{"type":"FeatureCollection","features":[\n' + linhas + "\n]}\n"


def csv_modo(comp: dict) -> str:
    modo = comp.get("modo", "itens")
    if modo == "itens":
        return csv_texto(comp)
    saida = io.StringIO()
    w = csv.writer(saida, lineterminator="\n")
    if modo == "contagem":
        w.writerow(["numero", "setor", "situacao", "total_oficial", "total_osm", "razao_pct", "classe"])
        for u in comp["unidades"]:
            w.writerow([u["n"], u["unidade"], u["situacao"], u["oficial"], u["osm"],
                        "" if u["razao"] is None else u["razao"], u["classe"]])
    else:
        w.writerow(["situacao", "numero", "logradouro_oficial", "faces_km", "nome_osm", "pista"])
        for o in comp["oficiais"]:
            w.writerow([o["situacao"], o["n"] or "", o["nome"], o["km"] or "", o["nome_osm"], o["motivo"]])
        for o in comp["so_osm"]:
            w.writerow(["so_osm", "", "", "", o["nome"], ""])
    return saida.getvalue()


def resumo_curto(comp: dict | None) -> str:
    """Cobertura para a tabela-síntese: "3 de 15 (20%)" ou, por contagem, "5.972 de 10.225 (58,4%)"."""
    if not comp:
        return "—"
    r = comp["resumo"]
    encontrados = r["osm"] if comp.get("modo") == "contagem" else r["ambas"]
    return f"{numero(encontrados, 0)} de {numero(r['oficial'], 0)} ({porcentagem(r['cobertura'])})"
