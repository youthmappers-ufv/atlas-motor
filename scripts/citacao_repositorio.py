"""Citação no repositório do município, gerada do atlas.toml: CITATION.cff (botão "Cite this
repository" do GitHub), .zenodo.json (metadados do DOI no Zenodo, só em município público), a
fileira de badges e a seção "Como citar" do README. Usa as mesmas funções da citação do site
(construir.citacao e construir.bibtex): as três citações nunca divergem.

Rode de novo depois de mudar coordenação, ORCID, DOI, site ou nome no atlas.toml:
  python ../atlas-motor/scripts/citacao_repositorio.py [--local <município>] [--organizacao youthmappers-ufv]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path
from urllib.parse import quote

from comum import argumento_local, sobrenome_e_prenome

DOI_MOTOR = "10.5281/zenodo.23573341"          # DOI conceito do atlas-motor (todas as versões)
LICENCAS_CFF = ["ODbL-1.0", "CC-BY-4.0", "MIT"]
LICENCA_ZENODO = "odbl-1.0"                    # o Zenodo aceita uma licença só: a dos dados
NOTA_LICENCAS = ("Licenças: dados derivados do OpenStreetMap e levantados pela equipe sob ODbL 1.0; textos, mapas, "
                 "site e PDF sob CC BY 4.0; configuração e workflows sob MIT (LICENCAS.md do repositório). "
                 "Dados © colaboradores do OpenStreetMap.")


def estatico(rotulo: str, mensagem: str, cor: str) -> str:
    """Badge fixo do shields.io (hífen e sublinhado se escrevem dobrados no caminho)."""
    def esc(s: str) -> str:
        return quote(s.replace("-", "--").replace("_", "__"), safe="")
    return f"https://img.shields.io/badge/{esc(rotulo)}-{esc(mensagem)}-{cor}"


def linha_badges(config: dict, organizacao: str) -> str:
    """Fileira de badges do README. Público, com site: os dinâmicos leem o atlas publicado
    (_gerado/badges/*.json, gerados pelo construir.py). Privado: o shields.io não lê o repositório,
    então só os do GitHub Actions (visíveis a quem tem acesso) e fixos; o da versão do motor é
    trocado pelo atualizar_motor.py. Com publicacao.doi, o badge do DOI vem primeiro."""
    from construir import dados_citacao
    d = dados_citacao(config)
    repo = f"https://github.com/{organizacao}/atlas-{config['publicacao']['slug']}"
    site = d["site"]
    def acoes(wf: str, nome: str, ramo: str = "") -> str:
        return f"[![{nome}]({repo}/actions/workflows/{wf}/badge.svg{ramo})]({repo}/actions/workflows/{wf})"
    def endpoint(nome: str) -> str:
        return "https://img.shields.io/endpoint?url=" + quote(f"{site}_gerado/badges/{nome}.json", safe="")
    doi = [f"[![DOI](https://zenodo.org/badge/DOI/{d['doi']}.svg)](https://doi.org/{d['doi']})"] if d["doi"] else []
    licencas = [f"[![dados: ODbL 1.0]({estatico('dados', 'ODbL 1.0', 'brightgreen')})](LICENCAS.md)",
                f"[![textos: CC BY 4.0]({estatico('textos', 'CC BY 4.0', 'lightgrey')})](LICENCAS.md)"]
    publicacao = [acoes("publicar.yml", "Publicar atlas"), acoes("verificar.yml", "Verificar", "?branch=main")]
    if not site:
        motor = config["motor"]["versao"]
        return " ".join(doi + publicacao + [
            f"[![motor {motor}]({estatico('motor', motor, 'informational')})](https://github.com/youthmappers-ufv/atlas-motor)",
            f"![atlas: só artefato (privado)]({estatico('atlas', 'só artefato (privado)', 'lightgrey')})"] + licencas)
    return " ".join(doi + [f"[![site do atlas]({estatico('atlas', 'site', 'blue')})]({site})"] + publicacao + [
        f"[![dados do OSM]({endpoint('dados')})]({site}dados.html)",
        f"[![completude]({endpoint('completude')})]({site})",
        f"[![motor]({endpoint('motor')})](https://github.com/youthmappers-ufv/atlas-motor)",
        f"[![edição](https://img.shields.io/github/v/release/{organizacao}/atlas-{config['publicacao']['slug']}"
        f"?label=edi%C3%A7%C3%A3o)]({repo}/releases)"] + licencas)


def afiliacao(config: dict) -> str:
    return config["publicacao"].get("instituicao", "Universidade Federal de Viçosa — Campus Rio Paranaíba").replace(" — ", ", ")


def resumo(config: dict) -> str:
    mun = config["municipio"]
    return (f"Mapas temáticos abertos de {mun['nome']} ({mun['uf']}), feitos a partir do OpenStreetMap, com a "
            "completude medida em relação às bases oficiais e as lacunas apontadas para conferência em campo. "
            f"{config['publicacao'].get('autoria', 'Programa Youthmappers UFV')}.")


def cff(config: dict, organizacao: str) -> str:
    """CITATION.cff do município (tipo dataset; ORCID e DOI quando o atlas.toml os tiver)."""
    from construir import dados_citacao
    d = dados_citacao(config)
    linhas = ["cff-version: 1.2.0",
              'message: "Para citar este atlas, use a referência abaixo. A página inicial do atlas traz a referência '
              'no formato da ABNT e em BibLaTeX."',
              "type: dataset", f'title: "{d["titulo"]}"', f'abstract: "{resumo(config)}"', "authors:"]
    if d["coord"]:
        sobrenome, prenome = sobrenome_e_prenome(d["coord"])
        linhas += [f'  - family-names: "{sobrenome}"', f'    given-names: "{prenome}"',
                   f'    affiliation: "{afiliacao(config)}"']
        if d["orcid"]:
            linhas.append(f'    orcid: "https://orcid.org/{d["orcid"]}"')
    linhas.append(f'  - name: "{d["autoria"]}"')
    if d["doi"]:
        linhas.append(f'doi: "{d["doi"]}"')
    linhas.append(f'repository: "https://github.com/{organizacao}/atlas-{config["publicacao"]["slug"]}"')
    if d["site"]:
        linhas.append(f'url: "{d["site"]}"')
    linhas += ["license:"] + [f"  - {lic}" for lic in LICENCAS_CFF]
    linhas += ["keywords:", "  - OpenStreetMap", "  - atlas municipal", "  - completude",
               f'  - "{config["municipio"]["nome"]}"']
    return "\n".join(linhas) + "\n"


def zenodo(config: dict) -> dict:
    """.zenodo.json: no Zenodo, tem precedência sobre o CITATION.cff. Necessário porque o registro
    aceita uma licença só (a lista do CFF faz a importação falhar) e para o tipo dataset."""
    from construir import dados_citacao
    d = dados_citacao(config)
    criadores = []
    if d["coord"]:
        sobrenome, prenome = sobrenome_e_prenome(d["coord"])
        criador = {"name": f"{sobrenome}, {prenome}" if prenome else sobrenome, "affiliation": afiliacao(config)}
        if d["orcid"]:
            criador["orcid"] = d["orcid"]
        criadores.append(criador)
    criadores.append({"name": d["autoria"]})
    descricao = resumo(config) + (f" Site: {d['site']}" if d["site"] else "")
    return {"upload_type": "dataset", "title": d["titulo"], "description": descricao, "creators": criadores,
            "license": LICENCA_ZENODO, "keywords": ["OpenStreetMap", "atlas municipal", "completude",
                                                    config["municipio"]["nome"]],
            "language": "por", "notes": NOTA_LICENCAS,
            "related_identifiers": [{"identifier": DOI_MOTOR, "relation": "isCompiledBy",
                                     "resource_type": "software", "scheme": "doi"}]}


def secao_como_citar(config: dict, ano: str) -> str:
    """A seção "Como citar" do README (do título até antes da seção seguinte)."""
    from construir import bibtex, citacao
    return ("## Como citar\n\n" + citacao(config, ano) + "\nEm BibLaTeX (estilo `abnt` do pacote biblatex-abnt):\n\n"
            "```bibtex\n" + bibtex(config, ano) + "```\n\n"
            "O GitHub também oferece a citação pelo botão *Cite this repository* (arquivo `CITATION.cff`). A página "
            "inicial do atlas traz a referência com o ano da edição e o arquivo `.bib` para baixar. Os dados do "
            "OpenStreetMap pedem, além disso, a atribuição *© colaboradores do OpenStreetMap (ODbL)*.\n\n")


RE_BADGES = re.compile(r"^(?:\[!\[|!\[).*$", re.MULTILINE)


def atualizar(local: Path, organizacao: str, ano: str | None = None) -> list[str]:
    """Regrava CITATION.cff, .zenodo.json (só com site público) e, no README, a fileira de badges
    (a linha logo abaixo do título) e a seção "Como citar". Devolve os arquivos alterados."""
    config = tomllib.loads((local / "atlas.toml").read_text(encoding="utf-8"))
    ano = ano or str(date.today().year)
    novos = {"CITATION.cff": cff(config, organizacao)}
    from construir import dados_citacao
    if dados_citacao(config)["site"]:
        novos[".zenodo.json"] = json.dumps(zenodo(config), ensure_ascii=False, indent=2) + "\n"
    readme = (local / "README.md").read_text(encoding="utf-8")
    titulo, _, resto = readme.partition("\n\n")
    linha = linha_badges(config, organizacao)
    if resto.startswith("@@BADGES@@") or RE_BADGES.match(resto.split("\n", 1)[0]):
        resto = linha + "\n" + resto.split("\n", 1)[1]
    else:
        resto = linha + "\n\n" + resto
    readme = titulo + "\n\n" + resto
    secao = secao_como_citar(config, ano)
    if "## Como citar\n" in readme:
        ini = readme.index("## Como citar\n")
        fim = readme.find("\n## ", ini + 1)
        readme = readme[:ini] + secao + (readme[fim + 1:] if fim >= 0 else "")
    else:
        fim = readme.find("\n## ", len(titulo) + 2)
        readme = readme[:fim + 1] + secao + readme[fim + 1:] if fim >= 0 else readme + "\n" + secao
    novos["README.md"] = readme
    alterados = []
    for nome, texto in novos.items():
        arq = local / nome
        if not arq.exists() or arq.read_text(encoding="utf-8") != texto:
            arq.write_text(texto, encoding="utf-8", newline="\n")
            alterados.append(nome)
    return alterados


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumento_local(ap)
    ap.add_argument("--organizacao", default="youthmappers-ufv", help="dona do repositório no GitHub")
    args = ap.parse_args()
    alterados = atualizar(args.local.resolve(), args.organizacao)
    print("Atualizados: " + ", ".join(alterados) if alterados else "Nada a mudar: a citação já está em dia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
