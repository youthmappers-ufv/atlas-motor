"""Monta o livro do atlas de um município e, se pedido, renderiza site e PDF.

Junta, em <município>/_construcao/livro/ (fora do Git):
  - o modelo do motor (livro/: método, dados, estilo e _quarto.modelo.yml);
  - os textos do município (atlas/: index.qmd e pranchas/);
  - os trechos gerados (_gerado/: mapas, indicadores, lacunas, downloads),
e escreve o _quarto.yml com o nome do município e as pranchas ativas.

Uso (de dentro do repositório do município, com o motor ao lado):
  python ../atlas-motor/scripts/construir.py                     # monta o livro
  python ../atlas-motor/scripts/construir.py --renderizar html   # ... e gera o site
  python ../atlas-motor/scripts/construir.py --renderizar todos  # ... site e PDF
  python ../atlas-motor/scripts/construir.py --baixar            # baixa um retrato novo antes
  python ../atlas-motor/scripts/construir.py --sem-mapas         # sem matplotlib
  python ../atlas-motor/scripts/construir.py --previa            # prévia ao vivo no navegador
Resultado: _construcao/livro/_site/ (site e atlas-<slug>.pdf).
Com a prévia aberta, pode rodar de novo o construir.py (sem --previa) em outro terminal
depois de mudar dados ou temas: o livro é atualizado no lugar e a prévia recarrega.

A versão mostrada no atlas vem de ATLAS_VERSAO (o CI usa a tag ou o commit) e da
versão do motor; sem a variável, usa o git describe do município.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from comparacao import csv_modo as csv_comparacao
from comparacao import geojson_modo as geojson_comparacao
from comparacao import quadro, resumo_curto, tabela_faltas, tabela_sobras
from comum import (MOTOR, argumento_local, data_br, ler_config, ler_temas, numero, porcentagem, sobrenome_e_prenome, texto_md,
                   tirar_somente_leitura, usar_versao_declarada, versao_motor)
from indicadores import calcular
from identidade import gerar as gerar_identidade
from validar import verificar

PRESERVAR = {".quarto", "_site", "_freeze"}


def tabela(linhas: list[tuple[str, str]]) -> str:
    corpo = "\n".join(f"| {a} | {b} |" for a, b in linhas)
    return f"| Indicador | Valor |\n|:--|--:|\n{corpo}\n"


TRECHOS = ("interativo", "mapa-municipio", "mapa-sede", "legenda", "indicadores", "comparacao-municipio",
           "comparacao-sede", "resumo", "lacunas", "so-osm", "fonte")


def trechos_tema(tema, res: dict, figuras: list[tuple[str, str, str]], retrato: dict, config: dict) -> dict[str, str]:
    """Partes geradas de uma prancha, cada uma incluível sozinha (_gerado/<tema>/<parte>.md).
    Partes que não se aplicam (ex.: mapa-sede num tema só do município) ficam vazias.

    Ordem: o tema no OpenStreetMap (mapa interativo no site, mapas, indicadores) e, havendo base
    oficial, a comparação das duas fontes (mapas de comparação, quadro-resumo, itens só na base
    oficial, objetos só no OpenStreetMap); por fim, a fonte. figuras: (arquivo, legenda, recorte),
    com recorte "municipio" ou "sede" (mapa do tema) ou "comparacao-municipio"/"comparacao-sede"."""
    t = dict.fromkeys(TRECHOS, "")
    comp = res.get("comparacao")
    t["interativo"] = mapa_interativo(tema, bool(comp))
    for arq, legenda, recorte in figuras:
        chave = recorte if recorte.startswith("comparacao-") else f"mapa-{recorte}"
        alt = f"Mapa: {legenda}".replace('"', "'")
        # No PDF o mapa ocupa no máximo metade da altura da página, para os indicadores (e a fonte)
        # caberem com ele; no site, a largura toda.
        # (só a altura no PDF: com largura e altura juntas a imagem seria esticada)
        imagem = f"![{legenda}](../_gerado/figuras/{arq}){{fig-alt=\"{alt}\""
        t[chave] = (f"::: {{.content-visible when-format=\"html\"}}\n{imagem} width=100%}}\n:::\n\n"
                    f"::: {{.content-visible unless-format=\"html\"}}\n{imagem} height=50%}}\n:::\n")
    # "legenda" fica vazia: a legenda é desenhada dentro de cada mapa (mapas.py). O trecho continua
    # existindo para as pranchas que o incluem em separado.
    t["indicadores"] = tabela(res["linhas"])
    if comp:
        t["resumo"] = "\n" + quadro(comp)
        t["lacunas"] = tabela_faltas(comp)
        t["so-osm"] = tabela_sobras(comp)
    elif res.get("lacunas"):                      # resultado sem a comparação montada (uso direto do módulo)
        t["lacunas"] = ("\n| Código | Nome | Motivo provável |\n|:---|:-------|:----------|\n" + "\n".join(
            f"| {texto_md(o['id'])} | {texto_md(o['nome'])} | {texto_md(o.get('motivo', ''))} |" for o in res["lacunas"]) + "\n")
    base = retrato.get("temas", {}).get(tema.id, {}).get("base_osm") or retrato.get("base_osm", "")
    osm = f"OpenStreetMap, dados de {data_br(base[:10]) or 'data desconhecida'} ({config['publicacao']['atribuicao']})"
    if comp:
        f = comp["fonte"]
        oficial = ", ".join(x for x in (f["orgao"], f["nome"]) if x)
        t["fonte"] = f"\n*Fontes: {osm}; {oficial}, acesso em {data_br(f['data_acesso'])}.*\n"
    else:
        t["fonte"] = f"\n*Fonte: {osm}.*\n"
    return t


def mapa_interativo(tema, com_comparacao: bool) -> str:
    """Mapa interativo da prancha, só no site: livro/mapa.js desenha em cada .atlas-mapa as camadas
    publicadas em _gerado/downloads/ (o mesmo dado dos mapas do PDF). Sem JavaScript, ficam os
    mapas estáticos logo abaixo."""
    comparacao = f' data-comparacao="../_gerado/downloads/{tema.id}-comparacao.geojson"' if com_comparacao else ""
    return ("::: {.content-visible when-format=\"html\"}\n```{=html}\n"
            f'<div class="atlas-mapa" data-tema="../_gerado/downloads/{tema.id}.geojson" '
            f'data-limite="../_gerado/downloads/limite.geojson" data-cor="{tema.cor}" data-forma="{tema.mapa}" '
            f'data-titulo="{tema.titulo.replace(chr(34), chr(39))}"{comparacao} role="region" '
            f'aria-label="Mapa interativo: {tema.titulo.replace(chr(34), chr(39))}"></div>\n'
            "```\n:::\n")


def sintese(resumo: list) -> str:
    """_gerado/pranchas.md: a síntese do atlas, uma linha por prancha, com o que há no OpenStreetMap
    e, nos temas com base oficial, a cobertura do mapa em relação a ela."""
    linhas = []
    for t, res in resumo:
        comp = res.get("comparacao")
        com_nome = next((v for r, v in res["linhas"] if r == "Com nome"), "—")
        base = (comp["fonte"]["orgao"] or comp["fonte"]["nome"]) if comp else ("—" if t.referencia == "interno" else "*a carregar*")
        linhas.append(f"| {t.numero} | [{t.titulo}](pranchas/{t.prancha}) | {numero(res['total'], 0)} | {com_nome} "
                      f"| {texto_md(base)} | {resumo_curto(comp)} |")
    return ("| Nº | Prancha | Objetos no OpenStreetMap | Com nome | Base oficial | Encontrados no mapa |\n"
            "|--:|:-----|---:|---:|:--|---:|\n" + "\n".join(linhas) + "\n")


def evolucao(local: Path, ativos: list, maximo: int = 6) -> str:
    """_gerado/evolucao.md: objetos no OpenStreetMap por tema nos últimos retratos versionados e,
    nos temas com base oficial, a cobertura. A série vem do histórico do Git do município
    (serie_historica.py); sem histórico (cópia sem Git ou clone raso), fica só o aviso."""
    try:
        from serie_historica import serie
        linhas = serie(local)
    except Exception:                             # sem git, clone raso, retrato antigo ilegível
        linhas = []
    # uma coluna por retrato (commit que mudou os dados), na ordem do histórico; os temas de um
    # mesmo retrato podem ter datas de base diferentes, e por isso a coluna leva a data do commit
    ultimo_do_dia = {l["data_commit"]: l["commit"] for l in linhas}      # dois retratos no mesmo dia: vale o último
    datas = [(commit, dia) for dia, commit in sorted(ultimo_do_dia.items())][-maximo:]
    if not datas:
        return "*Série indisponível nesta construção (sem o histórico do repositório).*\n"
    por = {(l["tema"], l["commit"]): l for l in linhas}

    def celula(tema, data):
        l = por.get((tema.id, data[0]))
        if not l:
            return "—"
        cobertura = f" ({porcentagem(l['C_t'])})" if l["C_t"] not in ("", None) else ""
        return f"{numero(l['total'], 0)}{cobertura}"

    cabecalho = "| Prancha | " + " | ".join(data_br(d[1]) for d in datas) + " |\n|:-----|" + "---:|" * len(datas)
    corpo = "\n".join(f"| {t.numero}. {t.titulo} | " + " | ".join(celula(t, d) for d in datas) + " |" for t in ativos)
    return (f"{cabecalho}\n{corpo}\n\nObjetos no OpenStreetMap em cada retrato; entre parênteses, nos temas com "
            "base oficial, a proporção dos itens oficiais encontrados no mapa.\n")


def trecho_tema(tema, res: dict, figuras: list[tuple[str, str, str]], retrato: dict, config: dict) -> str:
    """A prancha gerada inteira (_gerado/<tema>.md): todas as partes, na ordem."""
    return "\n".join(p for p in trechos_tema(tema, res, figuras, retrato, config).values() if p)


def versao_local(local: Path) -> str:
    """Versão mostrada no atlas: a tag da edição (ATLAS_VERSAO, no CI) ou o git describe. Um nome
    de branch em ATLAS_VERSAO (a publicação mensal sai da "main") não é versão: vale o describe,
    que diz a última edição e quantos commits vieram depois."""
    if re.fullmatch(r"v\d+\.\d+\.\d+\S*", os.environ.get("ATLAS_VERSAO", "")):
        return os.environ["ATLAS_VERSAO"]
    try:
        return subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=local,
                              capture_output=True, text=True, check=True).stdout.strip() or "desenvolvimento"
    except (OSError, subprocess.CalledProcessError):
        return "desenvolvimento"


def trecho_downloads(arquivos: list[tuple[str, str]], site: str) -> str:
    """_gerado/downloads.md: no site, links para os arquivos ao lado das páginas; no PDF, que circula
    fora do site, o endereço completo (ou só o nome do arquivo, se o atlas não tem site)."""
    no_site = "\n".join(f"- [{titulo}](_gerado/downloads/{arq})" for titulo, arq in arquivos)
    if site:
        fora = "\n".join(f"- [{titulo}]({site}_gerado/downloads/{arq})" for titulo, arq in arquivos)
    else:
        fora = "\n".join(f"- {titulo}: `{arq}`" for titulo, arq in arquivos)
    return (f"::: {{.content-visible when-format=\"html\"}}\n{no_site}\n:::\n\n"
            f"::: {{.content-visible unless-format=\"html\"}}\n{fora}\n:::\n")


def botao_pdf(slug: str) -> str:
    """Botão de baixar o atlas em PDF, só no site (o PDF fica na raiz do site, ao lado das páginas):
    o ícone que o Quarto põe na barra lateral passa despercebido."""
    return ("::: {.content-visible when-format=\"html\"}\n"
            f"<a class=\"btn btn-primary atlas-pdf\" href=\"atlas-{slug}.pdf\" download>"
            "<i class=\"bi bi-file-earmark-pdf\" aria-hidden=\"true\"></i> Baixar o atlas completo em PDF</a>\n"
            ":::\n")


def sobrenome_primeiro(nome: str) -> str:
    """Nome na entrada da ABNT: "Rodrigo Smarzaro" -> "SMARZARO, Rodrigo"."""
    sobrenome, prenome = sobrenome_e_prenome(nome)
    return f"{sobrenome.upper()}, {prenome}" if prenome else sobrenome.upper()


def dados_citacao(config: dict) -> dict:
    """Partes da referência do atlas, comuns à ABNT e ao BibLaTeX."""
    mun, pub = config["municipio"], config["publicacao"]
    autoria, coord = pub.get("autoria", "Programa Youthmappers UFV"), pub.get("coordenacao", "")
    orgao, _, campus = pub.get("instituicao", "Universidade Federal de Viçosa — Campus Rio Paranaíba").partition(" — ")
    return {"titulo": f"Atlas Colaborativo de {mun['nome']}", "autoria": autoria, "coord": coord,
            "local": campus.removeprefix("Campus ").strip(), "editora": f"{orgao}, {autoria}" if coord else orgao,
            "site": f"https://{pub['dominio']}/" if pub.get("dominio") else pub.get("url", ""),
            "chave": f"atlas-{pub['slug']}", "doi": pub.get("doi", ""),
            "orcid": pub.get("coordenacao_orcid", "") if coord else ""}


SUBTITULO = "mapas abertos do município, a partir do OpenStreetMap"


def citacao(config: dict, ano: str) -> str:
    """Referência do atlas no formato da ABNT (NBR 6023:2018), para a página inicial. Com
    publicacao.doi (DOI conceito do Zenodo: todas as edições), "DOI: …" antes de "Disponível em"."""
    d = dados_citacao(config)
    entrada = f"{sobrenome_primeiro(d['coord'])} (coord.)" if d["coord"] else d["autoria"].upper()
    doi = f" DOI: {d['doi']}." if d["doi"] else ""
    disponivel = f" Disponível em: <{d['site']}>. Acesso em: *data do acesso*." if d["site"] else ""
    return (f"{entrada}. **{d['titulo']}**: {SUBTITULO}. {d['local'] or '[*S. l.*]'}: {d['editora']}, "
            f"{ano}.{doi}{disponivel}\n")


def bibtex(config: dict, ano: str) -> str:
    """A mesma referência em BibLaTeX: com o estilo abnt do biblatex-abnt sai igual à da ABNT
    (a coordenação como editor com editortype = coordinator, que imprime "(coord.)"). Tipo
    @dataset, como no CITATION.cff: o atlas são mapas e dados abertos; sem o campo organization,
    que o estilo abnt repetiria ao lado da editora."""
    d = dados_citacao(config)
    if d["coord"]:
        sobrenome, prenome = sobrenome_e_prenome(d["coord"])
        nomes = [("editor", f"{sobrenome}, {prenome}" if prenome else sobrenome), ("editortype", "coordinator")]
    else:
        nomes = [("author", "{" + d["autoria"] + "}")]
    campos = nomes + [("title", d["titulo"]), ("subtitle", SUBTITULO.replace("OpenStreetMap", "{OpenStreetMap}")),
                      ("location", d["local"]), ("publisher", d["editora"]), ("year", ano), ("doi", d["doi"]),
                      ("url", d["site"]), ("langid", "brazilian")]
    linhas = [f"  {k:<10} = {{{v}}}," for k, v in campos if v]
    acesso = "% Acrescente urldate = {AAAA-MM-DD}, a data do acesso.\n" if d["site"] else ""
    return acesso + f"@dataset{{{d['chave']},\n" + "\n".join(linhas) + "\n}\n"


def trecho_citacao(config: dict, ano: str) -> str:
    """_gerado/citacao.md: a referência ABNT (site e PDF) e, só no site, a entrada BibLaTeX
    para copiar ou baixar (_gerado/downloads/atlas-<slug>.bib)."""
    chave = dados_citacao(config)["chave"]
    return (citacao(config, ano) + "\n::: {.content-visible when-format=\"html\"}\n"
            f"Em BibLaTeX (estilo `abnt` do pacote biblatex-abnt; [baixar o arquivo .bib](_gerado/downloads/{chave}.bib)):\n\n"
            f"```bibtex\n{bibtex(config, ano)}```\n:::\n")


def cor_completude(c: float | None) -> str:
    if c is None:
        return "lightgrey"
    return "red" if c < 25 else "orange" if c < 50 else "yellow" if c < 75 else "green"


def badges(resumo: list, base_osm: str) -> dict[str, dict]:
    """Badges do README (formato endpoint do shields.io), publicados com o site em _gerado/badges/:
    leem o atlas publicado, não o repositório. Completude: C_t de cada tema com base oficial."""
    medidas = [(t.titulo, res["completude"]["C_t"]) for t, res in resumo if res.get("completude")]
    def fmt(c):
        return f"{c:.1f}".replace(".", ",").removesuffix(",0") + "%" if c is not None else "—"
    media = (sum(c for _, c in medidas if c is not None) / len([c for _, c in medidas if c is not None])
             if any(c is not None for _, c in medidas) else None)
    def badge(rotulo, mensagem, cor):
        return {"schemaVersion": 1, "label": rotulo, "message": mensagem, "color": cor}
    return {
        "completude": badge("completude", " · ".join(f"{titulo.lower()} {fmt(c)}" for titulo, c in medidas)
                            or "sem base oficial", cor_completude(media)),
        "dados": badge("dados do OSM", base_osm, "blue"),
        "motor": badge("motor", versao_motor(), "informational"),
    }


def escrever_quarto(livro: Path, config: dict, ativos: list, edicao: str = "") -> None:
    mun, pub = config["municipio"], config["publicacao"]
    capitulos = "\n".join(f"        - pranchas/{t.prancha}" for t in ativos) or "        - index.qmd"
    autoria, coord = pub.get("autoria", "Programa Youthmappers UFV"), pub.get("coordenacao", "")
    autores = [f"{coord} (coordenação)", autoria] if coord else [autoria]
    rodape = " · ".join(x for x in (f"Dados {pub['atribuicao']}", autoria, coord and f"Coordenação: {coord}",
                                    pub.get("registro", "")) if x)
    trocas = {
        "{{titulo}}": f"Atlas Colaborativo de {mun['nome']}",
        "{{autores}}": json.dumps(autores, ensure_ascii=False),          # lista YAML (forma JSON)
        "{{instituicao}}": pub.get("instituicao", "Universidade Federal de Viçosa — Campus Rio Paranaíba"),
        "{{site_url}}": f"https://{pub['dominio']}/" if pub.get("dominio") else pub.get("url", ""),
        "{{arquivo}}": f"atlas-{pub['slug']}",
        "{{rodape}}": rodape.replace('"', "'"),
        "{{capitulos}}": capitulos,
        "{{edicao}}": edicao.replace('"', "'"),
        "{{descricao}}": (f"Mapas temáticos de {mun['nome']} ({mun.get('uf', '')}) feitos a partir do OpenStreetMap, "
                          "com a completude do mapa em relação às bases oficiais e as lacunas a mapear."),
    }
    texto = (MOTOR / "livro" / "_quarto.modelo.yml").read_text(encoding="utf-8")
    if not trocas["{{site_url}}"]:              # hospedagem "artefato": sem endereço (o Quarto recusa vazio)
        texto = "".join(l for l in texto.splitlines(keepends=True) if "{{site_url}}" not in l)
    for marca, valor in trocas.items():
        texto = texto.replace(marca, str(valor))
    (livro / "_quarto.yml").write_text(texto, encoding="utf-8", newline="\n")


def aplicar_identidade(local: Path, livro: Path) -> None:
    """Põe a identidade visual do município (identidade/: _brand.yml e imagens) sobre a padrão do
    motor e gera o identidade.tex do PDF. Os .md de identidade/ (instruções) não entram no livro."""
    origem = local / "identidade"
    if origem.is_dir():
        for arq in origem.rglob("*"):
            if arq.is_file() and arq.suffix.lower() != ".md":
                destino = livro / arq.relative_to(origem)
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(arq, destino)
    faltam = gerar_identidade(livro)
    if faltam:
        sys.exit("O _brand.yml cita logos que não existem: " + ", ".join(faltam)
                 + " (caminhos relativos a identidade/, ex.: marca/logo.png)")


def limpar(livro: Path) -> None:
    """Esvazia o livro montado, mas mantém o que o Quarto usa entre execuções (.quarto, _site,
    _freeze): apagar a pasta inteira falha com o quarto preview aberto, que segura o cache."""
    if not livro.exists():
        return
    for item in livro.iterdir():
        if item.name in PRESERVAR:
            continue
        if item.is_dir():
            shutil.rmtree(item, onerror=tirar_somente_leitura)
        else:
            item.unlink()


def arquivos(pasta: Path) -> dict[Path, float]:
    return {p.relative_to(pasta): p.stat().st_mtime for p in pasta.rglob("*") if p.is_file()}


def previa(local: Path, livro: Path, porta: int, navegador: bool = True) -> int:
    """Roda o quarto preview no livro montado e, enquanto ele estiver aberto, copia para o
    livro os textos salvos em atlas/ (o navegador recarrega sozinho). Mudanças em dados,
    temas.toml ou atlas.toml pedem nova construção (feche com Ctrl+C e rode de novo)."""
    proc = subprocess.Popen(["quarto", "preview", str(livro), "--to", "html", "--port", str(porta)]
                            + ([] if navegador else ["--no-browser"]))
    print(f"Prévia em http://localhost:{porta}/ — edite atlas/ e salve; Ctrl+C para sair.")
    origem, vistos = local / "atlas", arquivos(local / "atlas")
    shutil.copytree(origem, livro, dirs_exist_ok=True)     # o que foi salvo durante a montagem
    try:
        while proc.poll() is None:
            time.sleep(1)
            agora = arquivos(origem)
            for rel, mtime in agora.items():
                if vistos.get(rel) != mtime:
                    (livro / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(origem / rel, livro / rel)
                    print(f"  atualizado: atlas/{rel.as_posix()}")
            for rel in vistos.keys() - agora.keys():
                (livro / rel).unlink(missing_ok=True)
                print(f"  removido: atlas/{rel.as_posix()}")
            vistos = agora
    except KeyboardInterrupt:
        proc.terminate()
    return 0


def main() -> int:
    usar_versao_declarada("construir.py")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumento_local(ap)
    ap.add_argument("--baixar", action="store_true", help="baixar um retrato novo do OSM antes")
    ap.add_argument("--sem-mapas", action="store_true", help="não gerar mapas (sem matplotlib)")
    ap.add_argument("--renderizar", choices=["html", "pdf", "todos"], help="chamar o Quarto no fim")
    ap.add_argument("--previa", action="store_true",
                    help="abrir o quarto preview e copiar para o livro as edições salvas em atlas/")
    ap.add_argument("--porta", type=int, default=4200, help="porta da prévia (padrão: 4200)")
    ap.add_argument("--sem-navegador", action="store_true", help="na prévia, não abrir o navegador")
    args = ap.parse_args()
    local = args.local.resolve()

    if args.baixar:
        if subprocess.run([sys.executable, str(MOTOR / "scripts" / "baixar_osm.py"), "--local", str(local)]).returncode:
            return 1
    r = verificar(local)
    if r.erros:
        print("A validação encontrou erros; corrija antes de construir:\n  " + "\n  ".join(r.erros), file=sys.stderr)
        return 1

    config, temas = ler_config(local), ler_temas(local)
    versao_declarada = config["motor"]["versao"]
    if versao_declarada != versao_motor():
        print(f"Aviso: o município declara o motor {versao_declarada}, mas este motor é {versao_motor()}.",
              file=sys.stderr)

    livro = local / "_construcao" / "livro"
    limpar(livro)
    shutil.copytree(MOTOR / "livro", livro, ignore=shutil.ignore_patterns("_quarto.modelo.yml"), dirs_exist_ok=True)
    shutil.copytree(local / "atlas", livro, dirs_exist_ok=True)
    aplicar_identidade(local, livro)
    gerado = livro / "_gerado"
    (gerado / "downloads").mkdir(parents=True, exist_ok=True)
    retrato_arq = local / "dados" / "osm" / "retrato.json"
    retrato = json.loads(retrato_arq.read_text(encoding="utf-8")) if retrato_arq.exists() else {}

    desenhar = desenhar_comparacao = None
    if not args.sem_mapas:
        from mapas import desenhar, desenhar_comparacao   # importa o matplotlib só aqui

    ativos, resumo, comparacoes = [t for t in temas if t.ativo], [], []
    for t in ativos:
        res = calcular(local, t, config)
        comp = res.get("comparacao")
        figuras = []
        if desenhar:
            recortes = ("municipio", "sede") if t.recorte == "ambos" else (t.recorte,)
            for rec in recortes:
                arq = f"{t.id}-{rec}.png"
                desenhar(local, t, rec, config, gerado / "figuras" / arq)
                figuras.append((arq, f"{t.titulo}: {'sede do município' if rec == 'sede' else 'município'}", rec))
            for rec in recortes if comp else ():
                arq = f"{t.id}-{rec}-comparacao.png"
                desenhar_comparacao(local, t, rec, config, comp, gerado / "figuras" / arq)
                onde = "sede do município" if rec == "sede" else "município"
                figuras.append((arq, f"{t.titulo}, OpenStreetMap e {comp['fonte']['orgao'] or 'base oficial'}: {onde}",
                                f"comparacao-{rec}"))
        if comp:                                  # as duas fontes num arquivo só: mapa do site e downloads
            (gerado / "downloads" / f"{t.id}-comparacao.geojson").write_text(geojson_comparacao(comp), encoding="utf-8")
            (gerado / "downloads" / f"{t.id}-comparacao.csv").write_text(csv_comparacao(comp), encoding="utf-8")
            comparacoes.append(t)
        (gerado / f"{t.id}.md").write_text(trecho_tema(t, res, figuras, retrato, config), encoding="utf-8")
        (gerado / t.id).mkdir(exist_ok=True)
        for parte, texto in trechos_tema(t, res, figuras, retrato, config).items():
            (gerado / t.id / f"{parte}.md").write_text(texto, encoding="utf-8")
        origem = local / "dados" / "osm" / f"{t.id}.geojson"
        if origem.exists():
            shutil.copy2(origem, gerado / "downloads" / origem.name)
        resumo.append((t, res))
        print(f"{t.numero:>2}. {t.titulo}: {res['total']} objetos")

    (gerado / "pranchas.md").write_text(sintese(resumo), encoding="utf-8")
    (gerado / "evolucao.md").write_text(evolucao(local, ativos), encoding="utf-8")
    shutil.copy2(local / "dados" / "osm" / "limite.geojson", gerado / "downloads" / "limite.geojson")
    arquivos_dados = [("Limite do município", "limite.geojson")] + [
        (t.titulo, f"{t.id}.geojson") for t, _ in resumo if (gerado / "downloads" / f"{t.id}.geojson").exists()]
    for t in comparacoes:
        arquivos_dados += [(f"{t.titulo}: comparação com a base oficial (mapa)", f"{t.id}-comparacao.geojson"),
                           (f"{t.titulo}: comparação com a base oficial (planilha)", f"{t.id}-comparacao.csv")]
    (gerado / "downloads.md").write_text(trecho_downloads(arquivos_dados, dados_citacao(config)["site"]),
                                         encoding="utf-8")
    # Data da edição: a do tema ativo com dados mais antigos (os servidores do Overpass nem sempre
    # estão na mesma data, e um tema pode ter sido baixado sozinho); cada prancha mostra a sua.
    datas = [retrato.get("temas", {}).get(t.id, {}).get("base_osm", "") for t, _ in resumo]
    base_iso = (min([d for d in datas if d], default="") or retrato.get("base_osm", ""))[:10]
    base_osm = data_br(base_iso) or "data desconhecida"
    versao = (f"Versão **{versao_local(local)}** (motor {versao_motor()}), com dados do OpenStreetMap de "
              f"**{base_osm}**.\n")
    pdf = botao_pdf(config["publicacao"]["slug"])
    (gerado / "notas.md").write_text(versao, encoding="utf-8")            # notas do release (publicar.yml)
    (gerado / "edicao.md").write_text(versao + "\n" + pdf, encoding="utf-8")  # página inicial
    (gerado / "pdf.md").write_text(pdf, encoding="utf-8")                  # Dados para download
    ano = base_iso[:4] if base_iso[:4].isdigit() else str(date.today().year)
    (gerado / "citacao.md").write_text(trecho_citacao(config, ano), encoding="utf-8")  # Como usar e citar
    (gerado / "downloads" / f"atlas-{config['publicacao']['slug']}.bib").write_text(bibtex(config, ano), encoding="utf-8")
    (gerado / "badges").mkdir(exist_ok=True)
    for nome, dados in badges(resumo, base_iso or "data desconhecida").items():
        (gerado / "badges" / f"{nome}.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    escrever_quarto(livro, config, ativos,
                    f"Versão {versao_local(local)} · motor {versao_motor()} · dados do OpenStreetMap de {base_osm}")
    print(f"Livro montado em {livro.relative_to(local)}.")

    if args.renderizar:
        cmd = ["quarto", "render", str(livro)] + ([] if args.renderizar == "todos" else ["--to", args.renderizar])
        if subprocess.run(cmd).returncode:
            return 1
        print(f"Resultado em {(livro / '_site').relative_to(local)}.")
    if args.previa:
        return previa(local, livro, args.porta, not args.sem_navegador)
    return 0


if __name__ == "__main__":
    sys.exit(main())
