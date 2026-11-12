"""Mapas das pranchas (PNG), com layout cartográfico: limite, objetos do tema, legenda,
escala, norte e atribuição. Precisa do matplotlib (requirements.txt).

Dois mapas por recorte:
  desenhar             o tema no OpenStreetMap (pontos, linhas ou áreas, conforme o catálogo);
  desenhar_comparacao  as duas fontes, nos temas com base oficial: itens nas duas, só no
                       OpenStreetMap e só na base oficial (estes numerados, como na tabela).

Usado por construir.py; direto: python <motor>/scripts/mapas.py --local <município> --tema educacao
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from comparacao import CLASSES_RAZAO, CORES_NOMES, SEM_BASE  # noqa: E402
from comum import (Tema, area_m2, argumento_local, ler_config, ler_limite, ler_temas, linhas_de, poligonos_de,  # noqa: E402
                   ponto_representativo)
from indicadores import calcular, ler_feicoes  # noqa: E402

# Cores fixas do mapa (fundo, limite, textos); a cor dos objetos vem do tema (catálogo: cor).
BORDO, CINZA, CLARO, AGUA, VIA_FUNDO = "#7A1C1C", "#303030", "#F4F1E8", "#3A7BD5", "#C9C9C9"
FALTA = "#C62828"                                 # itens só na base oficial (lacunas do mapa)
ROTULOS_MAX = 14                                  # acima disso os nomes não cabem no mapa


def caixa(recorte: str, config: dict) -> tuple[float, float, float, float]:
    return tuple(config["municipio"]["sede_bbox" if recorte == "sede" else "bbox"])


def na_caixa(x: float, y: float, cx: tuple) -> bool:
    s, o, n, l = cx
    return o <= x <= l and s <= y <= n


def _base(local: Path, recorte: str, config: dict, vias_de_fundo: bool):
    """Figura com o limite, as vias de referência e, no município, os nomes das localidades."""
    s, o, n, l = caixa(recorte, config)
    fx = math.cos(math.radians((s + n) / 2))
    largura = 7.0
    fig, ax = plt.subplots(figsize=(largura, largura * (n - s) / ((l - o) * fx)), dpi=200)
    ax.set_xlim(o, l)
    ax.set_ylim(s, n)
    ax.set_aspect(1 / fx)
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    ax.add_patch(plt.Rectangle((o, s), l - o, n - s, color="#FFFFFF", zorder=0))
    for anel in ler_limite(local):
        xs, ys = zip(*anel)
        ax.fill(xs, ys, color=CLARO, zorder=1)
        ax.plot(xs, ys, color=BORDO, lw=1.2, ls=(0, (5, 2)), zorder=6)
    if vias_de_fundo:
        for f in ler_feicoes(local, "sistema-viario"):
            hw = f["properties"]["tags"].get("highway", "")
            if recorte != "sede" and not hw.startswith(("trunk", "primary", "secondary", "tertiary", "unclassified")):
                continue
            for linha in linhas_de(f["geometry"]):
                xs, ys = zip(*linha)
                ax.plot(xs, ys, color=VIA_FUNDO, lw=0.9 if recorte == "sede" else 0.35, zorder=1.5)
    if recorte != "sede":
        for f in ler_feicoes(local, "localizacao"):
            nome = f["properties"]["tags"].get("name")
            if nome and f["geometry"]["type"] == "Point":
                x, y = f["geometry"]["coordinates"]
                ax.text(x, y + (n - s) * 0.012, nome, ha="center", va="bottom", fontsize=6.5, color=CINZA,
                        style="italic", zorder=8)
    return fig, ax


def _legenda_de_fundo(itens: list, recorte: str, vias_de_fundo: bool) -> None:
    if vias_de_fundo:
        itens.append(Line2D([], [], color=VIA_FUNDO, lw=1.1, label="Vias (referência)"))
    if recorte != "sede":
        itens.append(Line2D([], [], color=BORDO, lw=1.2, ls=(0, (5, 2)), label="Limite do município"))


def _finalizar(fig, ax, itens: list, recorte: str, config: dict, saida: Path) -> Path:
    """Legenda (só do que aparece), escala (0,5 km na sede, 5 km no município), norte e atribuição."""
    s, o, n, l = caixa(recorte, config)
    fx = math.cos(math.radians((s + n) / 2))
    if itens:
        ax.legend(handles=itens, loc="upper left", fontsize=6.5, frameon=True, framealpha=0.92, facecolor="white",
                  edgecolor="#BBBBBB", borderpad=0.7, labelcolor=CINZA).set_zorder(9)
    km = 0.5 if recorte == "sede" else 5
    dx = km / (111.32 * fx)
    x0, y0 = o + (l - o) * 0.04, s + (n - s) * 0.04
    ax.plot([x0, x0 + dx], [y0, y0], color=CINZA, lw=2, zorder=7)
    ax.text(x0 + dx / 2, y0 + (n - s) * 0.012, f"{km:g} km".replace(".", ","), ha="center", va="bottom",
            fontsize=7, color=CINZA, zorder=7)
    ax.annotate("N", xy=(l - (l - o) * 0.04, n - (n - s) * 0.04), xytext=(l - (l - o) * 0.04, n - (n - s) * 0.12),
                ha="center", fontsize=9, fontweight="bold", color=CINZA,
                arrowprops=dict(arrowstyle="-|>", color=CINZA, lw=1.2), zorder=7)
    ax.text(l - (l - o) * 0.01, s + (n - s) * 0.01, config["publicacao"]["atribuicao"], ha="right", va="bottom",
            fontsize=5.5, color="#666666", zorder=7)
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, dpi=200)
    plt.close(fig)
    return saida


def _rotular(ax, pontos: list[tuple[float, float, str]], cx: tuple, cor: str = CINZA) -> None:
    """Nomes ao lado dos pontos, quando são poucos o bastante para caber (ROTULOS_MAX)."""
    s, o, n, l = cx
    visiveis = [(x, y, t) for x, y, t in pontos if t and na_caixa(x, y, cx)]
    if not visiveis or len(visiveis) > ROTULOS_MAX:
        return
    for x, y, texto in visiveis:
        direita = x < o + (l - o) * 0.72           # perto da borda direita, o nome vai para a esquerda
        ax.annotate(texto if len(texto) <= 34 else texto[:32] + "…", (x, y),
                    xytext=(5 if direita else -5, 4), textcoords="offset points", ha="left" if direita else "right",
                    fontsize=5.5, color=cor, zorder=8,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.75))


def desenhar(local: Path, tema: Tema, recorte: str, config: dict, saida: Path) -> Path:
    """O tema no OpenStreetMap."""
    cx = caixa(recorte, config)
    fundo = tema.mapa != "linhas"
    fig, ax = _base(local, recorte, config, fundo)
    cor = tema.cor
    cheios, vazios, tem = [], [], set()            # tem: o que foi desenhado, para a legenda
    for f in ler_feicoes(local, tema.id):
        g, tags = f["geometry"], f["properties"]["tags"]
        if linhas_de(g):
            for linha in linhas_de(g):
                xs, ys = zip(*linha)
                if "waterway" in tags:
                    ax.plot(xs, ys, color=AGUA, lw=0.7, zorder=2)
                    tem.add("agua")
                else:
                    principal = tags.get("highway", "").startswith(("trunk", "primary", "secondary"))
                    ax.plot(xs, ys, color=cor if tema.mapa in ("linhas", "areas") else "#9E9E9E",
                            lw=1.1 if principal else 0.4, zorder=3)
                    tem.add("linhas")
            continue
        if poligonos_de(g):
            agua = tags.get("natural") in ("water", "wetland") or "water" in tags
            for poligono in poligonos_de(g):
                xs, ys = zip(*poligono[0])
                ax.fill(xs, ys, color=AGUA if agua else cor, alpha=0.5 if tema.mapa == "areas" else 0.35, lw=0, zorder=2)
            tem.add("corpos" if agua else "areas")
            if tema.mapa == "areas":               # no mapa de áreas, a área é o objeto: sem ponto no centro
                continue
        x, y = ponto_representativo(g)
        (cheios if tags.get("name") else vazios).append((x, y, tags.get("name", "")))
    if cheios:
        ax.scatter([p[0] for p in cheios], [p[1] for p in cheios], s=22, color=cor, edgecolors="white",
                   linewidths=0.6, zorder=5)
    if vazios:
        ax.scatter([p[0] for p in vazios], [p[1] for p in vazios], s=14, facecolors="white", edgecolors=cor,
                   linewidths=0.9, zorder=5)
    if recorte == "sede":
        _rotular(ax, cheios, cx)

    itens = []
    if cheios:
        itens.append(Line2D([], [], marker="o", ls="", color=cor, markeredgecolor="white", markersize=5.5,
                            label="Com nome no mapa"))
    if vazios:
        itens.append(Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=cor, markersize=4.5,
                            label="Sem nome no mapa"))
    if "areas" in tem:
        itens.append(Patch(facecolor=cor, alpha=0.5 if tema.mapa == "areas" else 0.35, lw=0,
                           label="Áreas do tema" if tema.mapa == "areas" else "Área do objeto"))
    if "corpos" in tem:
        itens.append(Patch(facecolor=AGUA, alpha=0.5, lw=0, label="Corpos d'água"))
    if "linhas" in tem:
        itens.append(Line2D([], [], color=cor if tema.mapa in ("linhas", "areas") else "#9E9E9E", lw=1.1,
                            label="Vias do tema" if tema.mapa == "linhas" else "Linhas do tema"))
    if "agua" in tem:
        itens.append(Line2D([], [], color=AGUA, lw=0.9, label="Cursos d'água"))
    _legenda_de_fundo(itens, recorte, fundo)
    return _finalizar(fig, ax, itens, recorte, config, saida)


def desenhar_comparacao(local: Path, tema: Tema, recorte: str, config: dict, comp: dict, saida: Path) -> Path:
    """As duas fontes: itens nas duas, só no OpenStreetMap e só na base oficial (numerados)."""
    cx = caixa(recorte, config)
    modo = comp.get("modo", "itens")
    if modo == "contagem":
        return _comparacao_por_unidade(local, recorte, config, comp, saida)
    if modo == "nomes":
        return _comparacao_por_nomes(local, recorte, config, comp, saida)
    fig, ax = _base(local, recorte, config, True)
    cor = tema.cor
    ambas = [(o["lon"], o["lat"]) for o in comp["oficiais"] if o["situacao"] == "ambas" and o["lat"] is not None]
    so_osm = [(o["lon"], o["lat"]) for o in comp["so_osm"]]
    faltam = [(o["lon"], o["lat"], o["n"]) for o in comp["oficiais"] if o["situacao"] == "so_oficial" and o["lat"] is not None]
    if ambas:
        ax.scatter(*zip(*ambas), s=26, color=cor, edgecolors="white", linewidths=0.6, zorder=5)
    if so_osm:
        ax.scatter(*zip(*so_osm), s=20, facecolors="white", edgecolors=cor, linewidths=1.1, zorder=5)
    if faltam:
        ax.scatter([p[0] for p in faltam], [p[1] for p in faltam], s=30, marker="D", color=FALTA, edgecolors="white",
                   linewidths=0.6, zorder=6)
        for x, y, numero in faltam:
            if na_caixa(x, y, cx):
                ax.annotate(str(numero), (x, y), xytext=(4.5, 3.5), textcoords="offset points", fontsize=6.5,
                            fontweight="bold", color=FALTA, zorder=8,
                            bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.8))
    itens = []
    if ambas:
        itens.append(Line2D([], [], marker="o", ls="", color=cor, markeredgecolor="white", markersize=5.5,
                            label="Nas duas fontes"))
    if so_osm:
        itens.append(Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=cor, markersize=5,
                            label="Só no OpenStreetMap"))
    if faltam:
        itens.append(Line2D([], [], marker="D", ls="", color=FALTA, markeredgecolor="white", markersize=5.5,
                            label="Só na base oficial (nº da tabela)"))
    _legenda_de_fundo(itens, recorte, True)
    return _finalizar(fig, ax, itens, recorte, config, saida)


def _comparacao_por_unidade(local: Path, recorte: str, config: dict, comp: dict, saida: Path) -> Path:
    """Contagem: cada setor na cor da sua razão OpenStreetMap ÷ base oficial, com o número da tabela
    nos de maior falta que cabem no recorte."""
    cx = caixa(recorte, config)
    fig, ax = _base(local, recorte, config, recorte == "sede")
    classes = {}
    # Do maior para o menor: o setor rural que envolve a cidade é desenhado antes dos urbanos, que
    # ficam por cima dele (o contorno externo do setor rural cobre a área da cidade).
    for u in sorted(comp["unidades"], key=lambda u: -area_m2(u["geometry"])):
        for poligono in poligonos_de(u["geometry"]):
            xs, ys = zip(*poligono[0])
            ax.fill(xs, ys, facecolor=u["cor"], edgecolor="white", linewidth=0.5, zorder=2)
        classes[u["classe"]] = u["cor"]
    numerados = 0
    for u in comp["unidades"]:                    # já em ordem de falta
        x, y = ponto_representativo(u["geometry"])
        if numerados < 12 and na_caixa(x, y, cx):
            numerados += 1
            ax.annotate(str(u["n"]), (x, y), ha="center", va="center", fontsize=6.5, fontweight="bold", color=CINZA, zorder=8,
                        bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85))
    ordem = [rotulo for _, rotulo, _ in CLASSES_RAZAO] + [SEM_BASE[0]]
    itens = [Patch(facecolor=classes[r], edgecolor="white", label=f"{r} do total oficial" if "%" in r else r)
             for r in ordem if r in classes]
    _legenda_de_fundo(itens, recorte, recorte == "sede")
    return _finalizar(fig, ax, itens, recorte, config, saida)


def _comparacao_por_nomes(local: Path, recorte: str, config: dict, comp: dict, saida: Path) -> Path:
    """Nomes: as faces de logradouro da base oficial, na cor da situação do nome."""
    fig, ax = _base(local, recorte, config, True)
    presentes = set()
    for situacao, zorder in (("sem_nome", 3), ("ambas", 4), ("so_oficial", 5)):
        rotulo, cor = CORES_NOMES[situacao]
        for f in comp["faces"]:
            if f["situacao"] != situacao:
                continue
            for linha in linhas_de(f["geometry"]):
                xs, ys = zip(*linha)
                ax.plot(xs, ys, color=cor, lw=1.6 if situacao == "so_oficial" else 1.0, zorder=zorder)
            presentes.add(situacao)
    itens = [Line2D([], [], color=CORES_NOMES[s][1], lw=1.6, label=CORES_NOMES[s][0])
             for s in ("ambas", "so_oficial", "sem_nome") if s in presentes]
    _legenda_de_fundo(itens, recorte, True)
    return _finalizar(fig, ax, itens, recorte, config, saida)


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
        comp = calcular(local, t, config).get("comparacao")
        for rec in (("municipio", "sede") if t.recorte == "ambos" else (t.recorte,)):
            arq = desenhar(local, t, rec, config, local / "_construcao" / "figuras" / f"{t.id}-{rec}.png")
            print(arq.relative_to(local))
            if comp:
                arq = desenhar_comparacao(local, t, rec, config, comp,
                                          local / "_construcao" / "figuras" / f"{t.id}-{rec}-comparacao.png")
                print(arq.relative_to(local))
    return 0


if __name__ == "__main__":
    sys.exit(main())
