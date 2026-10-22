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
import shutil
import subprocess
import sys
import time
from pathlib import Path

from comum import MOTOR, argumento_local, ler_config, ler_temas, versao_motor
from indicadores import calcular
from validar import verificar

PRESERVAR = {".quarto", "_site", "_freeze"}


def tabela(linhas: list[tuple[str, str]]) -> str:
    corpo = "\n".join(f"| {a} | {b} |" for a, b in linhas)
    return f"| Indicador | Valor |\n|:--|--:|\n{corpo}\n"


def trecho_tema(tema, res: dict, figuras: list[tuple[str, str]], retrato: dict, config: dict) -> str:
    partes = []
    for arq, legenda in figuras:
        partes.append(f"![{legenda}](../_gerado/figuras/{arq}){{fig-alt=\"{legenda}\" width=100%}}\n")
    if figuras:
        partes.append("Pontos cheios: objetos com nome no mapa; pontos vazados: sem nome.\n")
    partes.append(tabela(res["linhas"]))
    lacunas = res.get("lacunas") or []
    if lacunas:
        partes.append(f"\n**Itens da base oficial sem correspondente no mapa** ({len(lacunas)}):\n")
        partes.append("| Código | Nome |\n|:--|:--|\n" + "\n".join(f"| {o['id']} | {o['nome']} |" for o in lacunas[:60]) + "\n")
        if len(lacunas) > 60:
            partes.append(f"\n… e mais {len(lacunas) - 60}.\n")
    base = retrato.get("temas", {}).get(tema.id, {}).get("base_osm") or retrato.get("base_osm", "")
    partes.append(f"\n*Fonte: OpenStreetMap, dados de {base[:10] or 'data desconhecida'}. "
                  f"{config['publicacao']['atribuicao']}.*\n")
    return "\n".join(partes)


def versao_local(local: Path) -> str:
    if os.environ.get("ATLAS_VERSAO"):
        return os.environ["ATLAS_VERSAO"]
    try:
        return subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=local,
                              capture_output=True, text=True, check=True).stdout.strip() or "desenvolvimento"
    except (OSError, subprocess.CalledProcessError):
        return "desenvolvimento"


def escrever_quarto(livro: Path, config: dict, ativos: list) -> None:
    mun, pub = config["municipio"], config["publicacao"]
    capitulos = "\n".join(f"        - pranchas/{t.prancha}" for t in ativos) or "        - index.qmd"
    rodape = " · ".join(x for x in (f"Dados {pub['atribuicao']}", pub.get("autoria", "Programa Youthmappers UFV"),
                                    pub.get("registro", "")) if x)
    trocas = {
        "{{titulo}}": f"Atlas Colaborativo de {mun['nome']}",
        "{{autoria}}": pub.get("autoria", "Programa Youthmappers UFV"),
        "{{instituicao}}": pub.get("instituicao", "Universidade Federal de Viçosa — Campus Rio Paranaíba"),
        "{{site_url}}": f"https://{pub['dominio']}/" if pub.get("dominio") else pub.get("url", ""),
        "{{arquivo}}": f"atlas-{pub['slug']}",
        "{{rodape}}": rodape.replace('"', "'"),
        "{{capitulos}}": capitulos,
    }
    texto = (MOTOR / "livro" / "_quarto.modelo.yml").read_text(encoding="utf-8")
    for marca, valor in trocas.items():
        texto = texto.replace(marca, str(valor))
    (livro / "_quarto.yml").write_text(texto, encoding="utf-8", newline="\n")


def tirar_somente_leitura(funcao, caminho, _info) -> None:
    """No Windows (e em pastas do OneDrive), o Quarto deixa itens somente leitura que o
    rmtree não apaga: tira o atributo e tenta de novo."""
    os.chmod(caminho, 0o700)
    funcao(caminho)


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
    gerado = livro / "_gerado"
    (gerado / "downloads").mkdir(parents=True, exist_ok=True)
    retrato_arq = local / "dados" / "osm" / "retrato.json"
    retrato = json.loads(retrato_arq.read_text(encoding="utf-8")) if retrato_arq.exists() else {}

    desenhar = None
    if not args.sem_mapas:
        from mapas import desenhar                # importa o matplotlib só aqui

    ativos, resumo = [t for t in temas if t.ativo], []
    for t in ativos:
        res = calcular(local, t, config)
        figuras = []
        if desenhar:
            for rec in (("municipio", "sede") if t.recorte == "ambos" else (t.recorte,)):
                arq = f"{t.id}-{rec}.png"
                desenhar(local, t, rec, config, gerado / "figuras" / arq)
                figuras.append((arq, f"{t.titulo}: {'sede do município' if rec == 'sede' else 'município'}"))
        (gerado / f"{t.id}.md").write_text(trecho_tema(t, res, figuras, retrato, config), encoding="utf-8")
        origem = local / "dados" / "osm" / f"{t.id}.geojson"
        if origem.exists():
            shutil.copy2(origem, gerado / "downloads" / origem.name)
        resumo.append((t, res))
        print(f"{t.numero:>2}. {t.titulo}: {res['total']} objetos")

    linhas = "\n".join(f"| {t.numero} | [{t.titulo}](pranchas/{t.prancha}) | {res['total']} |" for t, res in resumo)
    (gerado / "pranchas.md").write_text("| Nº | Prancha | Objetos no mapa |\n|--:|:--|--:|\n" + linhas + "\n", encoding="utf-8")
    shutil.copy2(local / "dados" / "osm" / "limite.geojson", gerado / "downloads" / "limite.geojson")
    itens = ["- [Limite do município](_gerado/downloads/limite.geojson)"] + [
        f"- [{t.titulo}](_gerado/downloads/{t.id}.geojson)" for t, _ in resumo
        if (gerado / "downloads" / f"{t.id}.geojson").exists()]
    (gerado / "downloads.md").write_text("\n".join(itens) + "\n", encoding="utf-8")
    (gerado / "edicao.md").write_text(
        f"Versão **{versao_local(local)}** (motor {versao_motor()}), com dados do OpenStreetMap de "
        f"**{retrato.get('base_osm', '')[:10] or 'data desconhecida'}**.\n", encoding="utf-8")
    escrever_quarto(livro, config, ativos)
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
