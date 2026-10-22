"""Prepara uma base oficial, como baixada do órgão, para dados/oficiais/<base>/ do município.

Lê o arquivo original (CSV com vírgula ou ponto e vírgula; UTF-8, com ou sem BOM, ou
Latin-1; coordenadas com ponto ou vírgula decimal), fica só com as linhas do município
que interessam ao atlas, só com as colunas que o atlas usa (nunca telefone nem e-mail),
limpa as coordenadas e grava o CSV e o fonte.toml. Não muda nada se o formato do
órgão tiver mudado: lista as colunas que faltam.

Uso: python ../atlas-motor/scripts/preparar_base.py inep <arquivo baixado> [--data AAAA-MM-DD]
Formatos: inep (Catálogo de Escolas, "Tabela da lista das escolas - Detalhado").
Depois: validar.py e construir.py (a completude da prancha usa a base).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from comum import argumento_local, ler_config


def simples(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar nomes de município."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower().strip()


@dataclass
class Formato:
    nome: str                       # vai para o fonte.toml
    orgao: str
    url: str
    licenca: str
    arquivo: str                    # nome do CSV gravado em dados/oficiais/<base>/
    colunas: dict[str, str]         # coluna do original -> coluna gravada (só estas são gravadas)
    papeis: dict[str, str]          # id, nome, lat, lon -> coluna gravada
    do_municipio: Callable[[dict, dict], bool]   # (linha original, atlas.toml) -> é do município?
    manter: Callable[[dict], bool] = lambda linha: True   # linhas que entram na base
    sai: str = ""                   # o que `manter` tira, para o relatório e o fonte.toml
    unidade: str = "itens"


def _inep_municipio(linha: dict, config: dict) -> bool:
    m = config["municipio"]
    return (simples(linha["Município"]) == simples(m["nome"])
            and simples(linha["UF"]) == simples(m.get("uf", linha["UF"])))


FORMATOS = {
    "inep": Formato(
        nome="Catálogo de Escolas (lista detalhada)",
        orgao="INEP",
        url="https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/inep-data/catalogo-de-escolas",
        licenca="Dados abertos do INEP (Catálogo de Escolas, InepData)",
        arquivo="escolas.csv",
        colunas={"Código INEP": "codigo_inep", "Escola": "escola", "Localização": "localizacao",
                 "Dependência Administrativa": "dependencia", "Restrição de Atendimento": "situacao",
                 "Endereço": "endereco", "Latitude": "latitude", "Longitude": "longitude"},
        papeis={"id": "codigo_inep", "nome": "escola", "lat": "latitude", "lon": "longitude"},
        do_municipio=_inep_municipio,
        manter=lambda linha: "PARALISADA" not in linha["Restrição de Atendimento"].upper(),
        sai="escolas paralisadas",
        unidade="escolas",
    ),
}


def ler_original(arquivo: Path) -> list[dict]:
    bruto = arquivo.read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252")
    cabecalho = texto.split("\n", 1)[0]
    separador = ";" if cabecalho.count(";") > cabecalho.count(",") else ","
    return list(csv.DictReader(io.StringIO(texto, newline=""), delimiter=separador))


def coordenada(valor: str) -> str:
    """'-19,2807913 ' -> '-19.2807913'; vazio ou inválido -> ''."""
    v = (valor or "").strip().replace(",", ".")
    try:
        float(v)
    except ValueError:
        return ""
    return v


def toml_texto(valor: str) -> str:
    return json.dumps(valor, ensure_ascii=False)     # string JSON é string básica válida em TOML


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", choices=sorted(FORMATOS), help="formato do arquivo e pasta em dados/oficiais/")
    ap.add_argument("arquivo", type=Path, help="arquivo como baixado do órgão")
    ap.add_argument("--data", default=date.today().isoformat(), help="data do download (padrão: hoje)")
    ap.add_argument("--todas", action="store_true", help="não tirar nenhuma linha do município (ex.: paralisadas)")
    ap.add_argument("--substituir", action="store_true", help="substituir a base já carregada")
    argumento_local(ap)
    args = ap.parse_args()
    local = args.local.resolve()
    fmt = FORMATOS[args.base]
    try:
        date.fromisoformat(args.data)
    except ValueError:
        print(f"--data deve ser AAAA-MM-DD, não '{args.data}'.", file=sys.stderr)
        return 2
    if not (local / "atlas.toml").exists():
        print(f"{local} não é o repositório de um município (falta atlas.toml): rode de dentro dele "
              "ou use --local.", file=sys.stderr)
        return 2
    if not args.arquivo.is_file():
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 2
    config = ler_config(local)

    linhas = ler_original(args.arquivo)
    faltam = [c for c in fmt.colunas if c not in (linhas[0] if linhas else {})]
    if not linhas or faltam:
        print(f"{args.arquivo.name} não está no formato '{args.base}' esperado"
              + (f"; faltam as colunas: {', '.join(faltam)}" if faltam else " (arquivo vazio)")
              + ". O formato do órgão pode ter mudado: ajuste FORMATOS em preparar_base.py.", file=sys.stderr)
        return 2

    do_municipio = [l for l in linhas if fmt.do_municipio(l, config)]
    if not do_municipio:
        print(f"Nenhuma linha de {config['municipio']['nome']} em {args.arquivo.name}. "
              "Filtrou o município certo na fonte?", file=sys.stderr)
        return 2
    mantidas = do_municipio if args.todas else [l for l in do_municipio if fmt.manter(l)]

    pasta = local / "dados" / "oficiais" / args.base
    if (pasta / "fonte.toml").exists() and not args.substituir:
        print(f"Já existe dados/oficiais/{args.base}/. Para trocar pela base nova, use --substituir "
              "(a anterior fica no histórico do Git).", file=sys.stderr)
        return 2

    lat, lon = fmt.papeis["lat"], fmt.papeis["lon"]
    saida = []
    for l in mantidas:
        nova = {destino: (l.get(origem) or "").strip() for origem, destino in fmt.colunas.items()}
        nova[lat], nova[lon] = coordenada(nova[lat]), coordenada(nova[lon])
        if not (nova[lat] and nova[lon]):
            nova[lat] = nova[lon] = ""
        saida.append(nova)

    sul, oeste, norte, leste = config["municipio"]["bbox"]
    sem_coord = [s for s in saida if not s[lat]]
    fora = [s for s in saida if s[lat] and not (sul <= float(s[lat]) <= norte and oeste <= float(s[lon]) <= leste)]

    pasta.mkdir(parents=True, exist_ok=True)
    with (pasta / fmt.arquivo).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fmt.colunas.values()), lineterminator="\n")
        w.writeheader()
        w.writerows(saida)

    ibge = config["municipio"].get("ibge", "")
    retiradas = len(do_municipio) - len(mantidas)
    obs = (f"Gerado por preparar_base.py a partir de {args.arquivo.name}: {len(do_municipio)} {fmt.unidade} "
           f"do município {ibge}" + (f", {retiradas} {fmt.sai} retiradas" if retiradas else "")
           + f", {len(saida)} na base. Só as colunas usadas pelo atlas (sem telefone nem e-mail), "
           "renomeadas; coordenadas com ponto decimal.")
    papeis = "\n".join(f"{p} = {toml_texto(c)}" for p, c in fmt.papeis.items())
    (pasta / "fonte.toml").write_text(
        f"nome = {toml_texto(fmt.nome)}\norgao = {toml_texto(fmt.orgao)}\nurl = {toml_texto(fmt.url)}\n"
        f"data_acesso = {args.data}\nlicenca = {toml_texto(fmt.licenca)}\narquivo = {toml_texto(fmt.arquivo)}\n"
        f"observacao = {toml_texto(obs)}\n\n[colunas]\n{papeis}\n", encoding="utf-8", newline="\n")

    print(f"dados/oficiais/{args.base}/: {len(saida)} {fmt.unidade} de {len(do_municipio)} do município"
          + (f" ({retiradas} {fmt.sai} retiradas; --todas para manter)" if retiradas else "") + ".")
    if sem_coord:
        print(f"  Sem coordenada ({len(sem_coord)}; contam na base, mas não no mapa):")
        for s in sem_coord:
            print(f"    {s[fmt.papeis['id']]} {s[fmt.papeis['nome']]}")
    if fora:
        print(f"  Coordenada fora da área do município ({len(fora)}; confira na fonte):")
        for s in fora:
            print(f"    {s[fmt.papeis['id']]} {s[fmt.papeis['nome']]} ({s[lat]}, {s[lon]})")
    print("Confira a licença no fonte.toml com a página da fonte e rode validar.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
