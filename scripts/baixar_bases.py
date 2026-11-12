"""Baixa as bases oficiais abertas usadas na comparação com o OpenStreetMap e as prepara
para dados/oficiais/<base>/ do município (CSV ou GeoJSON e o fonte.toml).

Bases (todas públicas, de órgãos federais; nada é copiado delas para o OpenStreetMap):
  cnes     Cadastro Nacional de Estabelecimentos de Saúde (API de dados abertos do Ministério
           da Saúde): estabelecimentos ativos do município. Comparação por itens (Saúde).
  setores  Malha de setores censitários do Censo 2022 (IBGE): os setores do município, que
           são as unidades das comparações por contagem.
  cnefe    Cadastro Nacional de Endereços para Fins Estatísticos, Censo 2022 (IBGE): número
           de endereços por setor censitário. Comparação por contagem (Edificações).
  faces    Base de Faces de Logradouros do Censo 2022 (IBGE): os logradouros com nome do
           município. Comparação por nomes (Logradouros e endereços).

O que entra no repositório é só o recorte do município e só o que a comparação usa:
do CNES saem código, nome fantasia, tipo e coordenada (nunca razão social, CNPJ ou CPF,
telefone e e-mail); do CNEFE, só as contagens por setor (nenhum endereço).

Os arquivos originais ficam num cache fora do repositório (~/.cache/atlas-motor/bases ou
ATLAS_MOTOR_CACHE), para não serem baixados de novo; os do estado inteiro (setores, faces)
servem a todos os municípios da mesma UF.

Uso (de dentro do repositório do município):
  python ../atlas-motor/scripts/baixar_bases.py                    # todas
  python ../atlas-motor/scripts/baixar_bases.py --base cnes        # só uma (pode repetir)
  python ../atlas-motor/scripts/baixar_bases.py --de-novo          # ignora o cache
Depois: validar.py e construir.py. Só biblioteca padrão.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
import struct
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from comum import CACHE_VERSOES, argumento_local, dentro, distancia_m, ler_config, poligonos_de

USER_AGENT = "atlas-motor (Programa Youthmappers UFV)"
CACHE = CACHE_VERSOES.parent / "bases" if CACHE_VERSOES.name != "atlas-motor" else CACHE_VERSOES / "bases"
IBGE_LICENCA = ("Uso livre com citação da fonte (IBGE: https://www.ibge.gov.br/acesso-informacao/"
                "institucional/politica-de-dados-abertos.html)")
URL_CNES = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
URL_CNEFE = ("https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
             "Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/")
URL_SETORES = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"
               "malha_com_atributos/setores/gpkg/UF/{uf}/{uf}_setores_CD2022.gpkg")
URL_FACES = ("https://geoftp.ibge.gov.br/recortes_para_fins_estatisticos/malha_de_setores_censitarios/censo_2022/"
             "base_de_faces_de_logradouros_versao_2022_censo_demografico/shp/{uf}_faces_de_logradouros_2022_shp.zip")
# Espécies de endereço do CNEFE (COD_ESPECIE)
ESPECIES = {"1": "domicilios", "2": "domicilios", "3": "agropecuarios", "4": "ensino", "5": "saude",
            "6": "outras_finalidades", "7": "em_construcao", "8": "religiosos"}


# ---------------------------------------------------------------- Rede e cache
def abrir(url: str, tempo: int = 120):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=tempo)


def baixar(url: str, destino: Path, de_novo: bool = False) -> Path:
    """Baixa para o cache (se ainda não estiver lá) e devolve o caminho."""
    if destino.exists() and destino.stat().st_size and not de_novo:
        print(f"  no cache: {destino.name}")
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".parcial")
    print(f"  baixando {url}")
    with abrir(url, 600) as r, parcial.open("wb") as f:
        total = 0
        while bloco := r.read(1 << 20):
            f.write(bloco)
            total += len(bloco)
    parcial.replace(destino)
    print(f"  {total / 1e6:.1f} MB em {destino}")
    return destino


def gravar_fonte(pasta: Path, campos: dict, colunas: dict | None = None) -> None:
    """fonte.toml da base (texto simples: os valores são cadeias, datas ou listas de cadeias)."""
    def valor(v):
        if isinstance(v, list):
            return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in v) + "]"
        return v.isoformat() if isinstance(v, date) else json.dumps(v, ensure_ascii=False)
    linhas = [f"{k} = {valor(v)}" for k, v in campos.items()]
    if colunas:
        linhas += ["", "[colunas]"] + [f"{k} = {json.dumps(v)}" for k, v in colunas.items()]
    (pasta / "fonte.toml").write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")


def gravar_csv(arquivo: Path, cabecalho: list[str], linhas: list[list]) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cabecalho)
        w.writerows(linhas)


def gravar_geojson(arquivo: Path, feicoes: list[dict]) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    linhas = ",\n".join(json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in feicoes)
    arquivo.write_text('{"type":"FeatureCollection","features":[\n' + linhas + "\n]}\n", encoding="utf-8", newline="\n")


def r7(v: float) -> float:
    return round(v, 7)


# ---------------------------------------------------------------- CNES
def base_cnes(local: Path, config: dict, de_novo: bool) -> str:
    ibge6 = str(config["municipio"]["ibge"])[:6]
    itens, inicio = [], 0
    while True:
        url = f"{URL_CNES}?{urllib.parse.urlencode({'codigo_municipio': ibge6, 'limit': 20, 'offset': inicio})}"
        with abrir(url) as r:
            pagina = json.load(r).get("estabelecimentos", [])
        itens += pagina
        if len(pagina) < 20:
            break
        inicio += 20
    ativos = [e for e in itens if not e.get("codigo_motivo_desabilitacao_estabelecimento")]
    linhas = []
    for e in sorted(ativos, key=lambda e: int(e["codigo_cnes"])):
        lat, lon = e.get("latitude_estabelecimento_decimo_grau"), e.get("longitude_estabelecimento_decimo_grau")
        endereco = " ".join(str(x).strip() for x in (e.get("endereco_estabelecimento"), e.get("numero_estabelecimento")) if x)
        linhas.append([e["codigo_cnes"], (e.get("nome_fantasia") or "").strip(), e.get("codigo_tipo_unidade") or "",
                       e.get("descricao_esfera_administrativa") or "", endereco, (e.get("bairro_estabelecimento") or "").strip(),
                       "" if lat is None else r7(float(lat)), "" if lon is None else r7(float(lon))])
    pasta = local / "dados" / "oficiais" / "cnes"
    gravar_csv(pasta / "estabelecimentos.csv",
               ["codigo_cnes", "estabelecimento", "tipo_unidade", "esfera", "endereco", "bairro", "latitude", "longitude"], linhas)
    gravar_fonte(pasta, {
        "nome": "Cadastro Nacional de Estabelecimentos de Saúde", "orgao": "CNES",
        "url": "https://apidadosabertos.saude.gov.br/v1/#/CNES", "data_acesso": date.today(),
        "licenca": ("Livre utilização: dados abertos do Poder Executivo federal (Decreto nº 8.777/2016, art. 4º); "
                    "a API do Ministério da Saúde não declara uma licença específica"),
        "arquivo": "estabelecimentos.csv",
        "observacao": (f"Baixado pela API para o município {ibge6} por baixar_bases.py: {len(itens)} estabelecimentos, "
                       f"mantidos os {len(ativos)} sem motivo de desabilitação. Ficam só código, nome fantasia, tipo, esfera, "
                       "endereço e coordenada (saem razão social, CNPJ/CPF, telefone e e-mail)."),
    }, {"id": "codigo_cnes", "nome": "estabelecimento", "lat": "latitude", "lon": "longitude"})
    return f"cnes: {len(ativos)} estabelecimentos ativos (de {len(itens)})"


# ---------------------------------------------------------------- Setores censitários (GeoPackage)
def _aneis_wkb(dados: bytes, pos: int) -> tuple[list, int]:
    """Lê uma geometria WKB (Polygon ou MultiPolygon, 2D) e devolve a lista de polígonos."""
    ordem = "<" if dados[pos] == 1 else ">"
    tipo = struct.unpack_from(ordem + "I", dados, pos + 1)[0] % 1000
    pos += 5
    if tipo == 3:
        n_aneis = struct.unpack_from(ordem + "I", dados, pos)[0]
        pos += 4
        aneis = []
        for _ in range(n_aneis):
            n = struct.unpack_from(ordem + "I", dados, pos)[0]
            pos += 4
            pts = struct.unpack_from(f"{ordem}{2 * n}d", dados, pos)
            pos += 16 * n
            aneis.append([[r7(pts[i]), r7(pts[i + 1])] for i in range(0, 2 * n, 2)])
        return [aneis], pos
    if tipo == 6:
        n_pol = struct.unpack_from(ordem + "I", dados, pos)[0]
        pos += 4
        poligonos = []
        for _ in range(n_pol):
            parte, pos = _aneis_wkb(dados, pos)
            poligonos += parte
        return poligonos, pos
    raise ValueError(f"geometria WKB não suportada: tipo {tipo}")


def geometria_gpkg(blob: bytes) -> dict:
    """Geometria de um GeoPackage (cabeçalho GP + WKB) como GeoJSON (Polygon ou MultiPolygon)."""
    if blob[:2] != b"GP":
        raise ValueError("não é uma geometria de GeoPackage")
    envelope = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 7]
    poligonos, _ = _aneis_wkb(blob, 8 + envelope)
    if len(poligonos) == 1:
        return {"type": "Polygon", "coordinates": poligonos[0]}
    return {"type": "MultiPolygon", "coordinates": poligonos}


def _coluna(colunas: list[str], *candidatas: str) -> str | None:
    por_nome = {c.upper(): c for c in colunas}
    return next((por_nome[c] for c in candidatas if c in por_nome), None)


def base_setores(local: Path, config: dict, de_novo: bool) -> str:
    mun, uf = str(config["municipio"]["ibge"]), config["municipio"]["uf"]
    arq = baixar(URL_SETORES.format(uf=uf), CACHE / f"{uf}_setores_CD2022.gpkg", de_novo)
    con = sqlite3.connect(arq)
    try:
        tabela, geom = con.execute("SELECT table_name, column_name FROM gpkg_geometry_columns").fetchone()
        colunas = [l[1] for l in con.execute(f'PRAGMA table_info("{tabela}")')]
        c_setor, c_mun = _coluna(colunas, "CD_SETOR"), _coluna(colunas, "CD_MUN")
        c_sit, c_bairro = _coluna(colunas, "SITUACAO", "CD_SIT"), _coluna(colunas, "NM_BAIRRO", "NM_DIST")
        if not c_setor or not c_mun:
            raise SystemExit(f"O formato da malha de setores mudou: colunas {colunas}")
        extras = [c for c in (c_sit, c_bairro) if c]
        consulta = f'SELECT "{c_setor}", "{geom}"' + "".join(f', "{c}"' for c in extras) + f' FROM "{tabela}" WHERE "{c_mun}" = ?'
        feicoes = []
        for linha in con.execute(consulta, (mun,)):
            props = {"setor": str(linha[0])}
            for nome, v in zip(("situacao", "local")[:len(extras)] if c_sit else ("local",), linha[2:]):
                props[nome] = "" if v is None else str(v)
            feicoes.append({"type": "Feature", "properties": props, "geometry": geometria_gpkg(linha[1])})
    finally:
        con.close()
    if not feicoes:
        raise SystemExit(f"Nenhum setor do município {mun} na malha de {uf}.")
    feicoes.sort(key=lambda f: f["properties"]["setor"])
    pasta = local / "dados" / "oficiais" / "setores"
    gravar_geojson(pasta / "setores.geojson", feicoes)
    gravar_fonte(pasta, {
        "nome": "Malha de setores censitários do Censo Demográfico 2022", "orgao": "IBGE",
        "url": URL_SETORES.format(uf=uf), "data_acesso": date.today(), "licenca": IBGE_LICENCA,
        "arquivo": "setores.geojson", "papel": "unidades",
        "observacao": f"Setores do município {mun}, extraídos da malha de {uf} por baixar_bases.py. Unidades das comparações por contagem.",
    })
    return f"setores: {len(feicoes)} setores censitários"


# ---------------------------------------------------------------- CNEFE
def base_cnefe(local: Path, config: dict, de_novo: bool) -> str:
    mun = str(config["municipio"]["ibge"])
    arq = CACHE / f"cnefe_{mun}.zip"
    if not arq.exists() or de_novo:
        with abrir(URL_CNEFE) as r:
            pasta_uf = re.search(rf'href="({mun[:2]}_[A-Z]{{2}}/)"', r.read().decode("latin-1"))
        if not pasta_uf:
            raise SystemExit("Não achei a pasta do estado na página do CNEFE (o endereço mudou?).")
        with abrir(URL_CNEFE + pasta_uf[1]) as r:
            nome = re.search(rf'href="({mun}_[^"]+\.zip)"', r.read().decode("latin-1"))
        if not nome:
            raise SystemExit(f"Não achei o arquivo do município {mun} no CNEFE.")
        url = URL_CNEFE + pasta_uf[1] + nome[1]
    else:
        url = URL_CNEFE
    baixar(url, arq, de_novo)
    # Cada endereço é contado no setor da malha publicada em que a sua coordenada cai. O código de
    # setor do próprio CNEFE é o da coleta, e a malha publicada às vezes divide ou junta setores:
    # pela coordenada, as contagens casam com os polígonos. Sem a malha (base "setores"), ou para
    # o endereço sem coordenada ou fora de todos os setores, vale o código do CNEFE.
    formas = []
    arq_setores = local / "dados" / "oficiais" / "setores" / "setores.geojson"
    if arq_setores.is_file():
        for f in json.loads(arq_setores.read_text(encoding="utf-8"))["features"]:
            pols = poligonos_de(f["geometry"])
            xs = [p[0] for pol in pols for p in pol[0]]
            ys = [p[1] for pol in pols for p in pol[0]]
            formas.append((f["properties"]["setor"], pols, (min(xs), min(ys), max(xs), max(ys))))

    def setor_da_coordenada(x: float, y: float) -> str | None:
        for setor, pols, (x0, y0, x1, y1) in formas:
            if x0 <= x <= x1 and y0 <= y <= y1 and any(
                    dentro(x, y, pol[:1]) and not any(dentro(x, y, [furo]) for furo in pol[1:]) for pol in pols):
                return setor
        return None

    por_setor: dict[str, Counter] = defaultdict(Counter)
    pelo_codigo = 0
    with zipfile.ZipFile(arq) as z:
        interno = next(i for i in z.infolist() if i.filename.lower().endswith(".csv"))
        leitor = csv.DictReader(io.TextIOWrapper(z.open(interno), encoding="utf-8"), delimiter=";")
        for linha in leitor:
            setor = None
            try:
                setor = setor_da_coordenada(float(linha["LONGITUDE"]), float(linha["LATITUDE"]))
            except (KeyError, ValueError):
                pass
            if setor is None:
                pelo_codigo += 1
                setor = "".join(c for c in linha["COD_SETOR"] if c.isdigit())[:15]
            por_setor[setor]["enderecos"] += 1
            por_setor[setor][ESPECIES.get(linha["COD_ESPECIE"], "outras_finalidades")] += 1
    especies = sorted(set(ESPECIES.values()))
    linhas = [[s, c["enderecos"], c["enderecos"] - c["em_construcao"]] + [c[e] for e in especies]
              for s, c in sorted(por_setor.items())]
    pasta = local / "dados" / "oficiais" / "cnefe"
    gravar_csv(pasta / "enderecos-por-setor.csv", ["setor", "enderecos", "enderecos_existentes"] + especies, linhas)
    total = sum(c["enderecos"] for c in por_setor.values())
    gravar_fonte(pasta, {
        "nome": "Cadastro Nacional de Endereços para Fins Estatísticos (Censo 2022)", "orgao": "IBGE",
        "url": URL_CNEFE, "data_acesso": date.today(), "licenca": IBGE_LICENCA,
        "arquivo": "enderecos-por-setor.csv", "comparacao": "contagem", "unidades": "setores",
        "rotulo_oficial": "Endereços (Censo 2022)", "rotulo_osm": "Edificações no OpenStreetMap",
        "observacao": (f"Contagem dos {total} endereços do município {mun} por setor censitário, feita por baixar_bases.py; "
                       "nenhum endereço é guardado. Cada endereço é contado no setor da malha publicada em que a sua coordenada cai. A comparação usa os endereços existentes (sem os de edificação em "
                       "construção). Endereço não é edificação: um prédio tem vários endereços, e a razão é uma aproximação."),
    }, {"unidade": "setor", "total": "enderecos_existentes"})
    return f"cnefe: {total} endereços em {len(por_setor)} setores"


# ---------------------------------------------------------------- Faces de logradouro (shapefile)
def ler_dbf(f) -> tuple[list[tuple[str, int]], int, int, int]:
    """Cabeçalho de um .dbf: campos (nome, tamanho), nº de registros, tamanho do cabeçalho e do registro."""
    cab = f.read(32)
    n, tam_cab, tam_reg = struct.unpack("<IHH", cab[4:12])
    campos = []
    while (d := f.read(32))[0] != 0x0D:
        campos.append((d[:11].split(b"\0")[0].decode("ascii"), d[16]))
        if len(campos) > 255:
            raise ValueError("cabeçalho de .dbf inválido")
    return campos, n, tam_cab, tam_reg


def linhas_shp(registro: bytes) -> list[list[list[float]]]:
    """Partes de um registro PolyLine (tipos 3, 13, 23) de um .shp, como listas de [lon, lat]."""
    tipo = struct.unpack_from("<i", registro, 0)[0]
    if tipo not in (3, 13, 23):
        return []
    n_partes, n_pontos = struct.unpack_from("<ii", registro, 36)
    inicios = list(struct.unpack_from(f"<{n_partes}i", registro, 44)) + [n_pontos]
    base = 44 + 4 * n_partes
    pts = struct.unpack_from(f"<{2 * n_pontos}d", registro, base)
    return [[[r7(pts[2 * i]), r7(pts[2 * i + 1])] for i in range(a, b)] for a, b in zip(inicios, inicios[1:])]


def base_faces(local: Path, config: dict, de_novo: bool) -> str:
    mun, uf = str(config["municipio"]["ibge"]), config["municipio"]["uf"]
    arq = baixar(URL_FACES.format(uf=uf), CACHE / f"{uf}_faces_de_logradouros_2022_shp.zip", de_novo)
    # O arquivo do estado traz um shapefile por município: só os três arquivos deste saem do zip.
    pasta_cache = CACHE / f"faces_{mun}"
    if not any(pasta_cache.glob("*.shp")) or de_novo:
        pasta_cache.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(arq) as z:
            for i in z.infolist():
                nome = Path(i.filename).name
                if nome.startswith(mun) and Path(nome).suffix.lower() in (".shp", ".shx", ".dbf") and not i.is_dir():
                    (pasta_cache / nome).write_bytes(z.read(i))
    if not any(pasta_cache.glob("*.shp")):
        raise SystemExit(f"Nenhum arquivo do município {mun} na base de faces de {uf}.")
    shp = next(pasta_cache.glob("*.shp"))
    feicoes, nomes = [], defaultdict(float)
    with shp.with_suffix(".dbf").open("rb") as dbf, shp.with_suffix(".shx").open("rb") as shx, shp.open("rb") as f:
        campos, n, tam_cab, tam_reg = ler_dbf(dbf)
        posicoes, p = {}, 1
        for nome, tam in campos:
            posicoes[nome.upper()] = (p, tam)
            p += tam
        c_setor = next((c for c in ("CD_SETOR", "CD_GEO", "CD_FACE") if c in posicoes), None)
        c_nome = [c for c in ("NM_TIP_LOG", "NM_TIT_LOG", "NM_LOG") if c in posicoes]
        if not c_setor or "NM_LOG" not in posicoes:
            raise SystemExit(f"O formato da base de faces mudou: campos {[c for c, _ in campos]}")
        a, tam = posicoes[c_setor]
        for i in range(n):
            dbf.seek(tam_cab + i * tam_reg)
            reg = dbf.read(tam_reg)
            if not reg[a:a + tam].startswith(mun.encode()):
                continue
            def campo(c):
                ini, t = posicoes[c]
                return reg[ini:ini + t].decode("latin-1").strip()
            nome = " ".join(x for x in (campo(c) for c in c_nome) if x)
            shx.seek(100 + 8 * i)
            desloc, tamanho = struct.unpack(">ii", shx.read(8))
            f.seek(desloc * 2 + 8)
            partes = linhas_shp(f.read(tamanho * 2))
            if not partes:
                continue
            km = sum(distancia_m(*p1, *p2) for parte in partes for p1, p2 in zip(parte, parte[1:])) / 1000
            if nome:
                nomes[nome] += km
            geometria = ({"type": "LineString", "coordinates": partes[0]} if len(partes) == 1
                         else {"type": "MultiLineString", "coordinates": partes})
            feicoes.append({"type": "Feature", "properties": {"nome": nome, "setor": campo(c_setor)[:15]}, "geometry": geometria})
    if not feicoes:
        raise SystemExit(f"Nenhuma face de logradouro do município {mun} na base de {uf}.")
    pasta = local / "dados" / "oficiais" / "faces"
    gravar_geojson(pasta / "faces.geojson", feicoes)
    gravar_csv(pasta / "logradouros.csv", ["logradouro", "faces_km"],
               [[nome, round(km, 2)] for nome, km in sorted(nomes.items())])
    gravar_fonte(pasta, {
        "nome": "Base de Faces de Logradouros do Censo Demográfico 2022", "orgao": "IBGE",
        "url": URL_FACES.format(uf=uf), "data_acesso": date.today(), "licenca": IBGE_LICENCA,
        "arquivo": "logradouros.csv", "comparacao": "nomes", "geometrias": "faces.geojson",
        "filtro_osm": ["highway"],
        "observacao": (f"Faces de logradouro do município {mun}, extraídas da base de {uf} por baixar_bases.py: "
                       f"{len(feicoes)} faces, {len(nomes)} logradouros com nome. logradouros.csv lista cada nome e a soma "
                       "do comprimento das suas faces (cada lado de quadra é uma face: uma rua costuma ter duas)."),
    }, {"nome": "logradouro"})
    return f"faces: {len(feicoes)} faces, {len(nomes)} logradouros com nome"


BASES = {"cnes": base_cnes, "setores": base_setores, "cnefe": base_cnefe, "faces": base_faces}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", action="append", choices=list(BASES), help="só esta base (pode repetir; padrão: todas)")
    ap.add_argument("--de-novo", action="store_true", help="baixar de novo, mesmo com o arquivo no cache")
    argumento_local(ap)
    args = ap.parse_args()
    local = args.local.resolve()
    config = ler_config(local)
    falhas = 0
    for nome in args.base or list(BASES):
        print(f"{nome}...")
        try:
            print("  " + BASES[nome](local, config, args.de_novo))
        except (OSError, ValueError, KeyError, sqlite3.Error, zipfile.BadZipFile) as erro:
            falhas += 1
            print(f"  FALHOU: {erro}", file=sys.stderr)
    print("Bases gravadas em dados/oficiais/. Próximo: validar.py e construir.py." if not falhas
          else f"{falhas} base(s) falharam; as demais foram gravadas.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
