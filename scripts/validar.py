"""Verifica a integridade do repositório de um município (roda no CI em todo pull request).

Confere:
  - atlas.toml: município, hashtags, versão do motor (vX.Y), publicação (slug);
  - temas.toml: ids do catálogo ou pranchas próprias completas, situação e recorte válidos,
    consultas existentes e restritas ao município ({{bbox}});
  - workflows do município chamam o motor na mesma versão declarada no atlas.toml;
  - dados/osm: GeoJSON bem formado, ids únicos, coordenadas no município, contagens
    iguais às do retrato.json;
  - dados/oficiais/<base>/fonte.toml: órgão, URL, data de acesso, licença, arquivo e
    colunas declaradas presentes no CSV;
  - dados/curados/*.csv: cada arquivo tem esquema (catálogo do motor ou dados/esquemas/)
    e o respeita (colunas, obrigatórias, tipos, valores, padrões, chave única, coordenadas);
  - nenhum CSV com dado pessoal aparente (e-mail, CPF formatado) nem coluna proibida;
  - atlas/: index.qmd e uma prancha atlas/pranchas/<nn>-<id>.qmd para cada tema ativo
    (fora de "planejado"), e nenhuma prancha sobrando;
  - arquivos de texto em UTF-8, sem marcas de conflito, nenhum arquivo acima de 25 MB.

Uso: python <motor>/scripts/validar.py [--local CAMINHO]
Saída: lista de ERRO/AVISO; código 1 se houver erro.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

from comum import (CATALOGO, SITUACOES, Tema, argumento_local, caminho_consulta, coordenadas, ler_csv,
                   ler_esquemas, ler_temas, ler_toml)

RECORTES = {"municipio", "sede", "ambos"}
COLUNAS_PROIBIDAS = {"cpf", "rg", "email", "e-mail", "telefone_pessoal", "celular", "matricula", "endereco_residencial"}
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# Só o CPF formatado: 11 dígitos seguidos não servem, pois identificadores de nós do OSM já têm 11 dígitos.
RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
RE_URL = re.compile(r"^https?://\S+$")
RE_VERSAO = re.compile(r"^v\d+\.\d+(\.\d+)?$")
RE_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RE_CHAMADA = re.compile(r"uses:\s*youthmappers-ufv/atlas-motor/\.github/workflows/[\w.-]+@(\S+)")
TIPOS = {"texto", "inteiro", "decimal", "data", "lista", "latitude", "longitude", "tema", "url"}
IGNORAR = {".git", "_site", "_gerado", "_construcao", ".quarto", "__pycache__", "_freeze", ".venv"}
LIMITE_BYTES = 25 * 1024 * 1024
MARGEM = 0.02            # graus de tolerância em torno da caixa do município


class Relatorio:
    def __init__(self) -> None:
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def erro(self, msg: str) -> None:
        self.erros.append(msg)

    def aviso(self, msg: str) -> None:
        self.avisos.append(msg)


def dentro_caixa(lon: float, lat: float, bbox: list[float]) -> bool:
    s, o, n, l = bbox
    return s - MARGEM <= lat <= n + MARGEM and o - MARGEM <= lon <= l + MARGEM


# ---------------------------------------------------------------- Configuração
def verificar_config(local: Path, r: Relatorio) -> tuple[dict, list[Tema]]:
    try:
        config = ler_toml(local / "atlas.toml")
    except (OSError, tomllib.TOMLDecodeError) as e:
        r.erro(f"[config] atlas.toml ilegível ou ausente: {e}")
        return {}, []
    mun = config.get("municipio", {})
    for chave in ("nome", "uf", "ibge", "osm_relacao", "bbox", "sede_bbox"):
        if chave not in mun:
            r.erro(f"[config] atlas.toml: falta municipio.{chave}")
    if "ibge" in mun and not re.fullmatch(r"\d{7}", str(mun["ibge"])):
        r.erro("[config] atlas.toml: municipio.ibge deve ter 7 dígitos")
    for chave in ("bbox", "sede_bbox"):
        caixa = mun.get(chave, [])
        if chave in mun and (len(caixa) != 4 or not (caixa[0] < caixa[2] and caixa[1] < caixa[3])):
            r.erro(f"[config] atlas.toml: municipio.{chave} deve ser [sul, oeste, norte, leste]")
    for chave in ("programa", "projeto"):
        if not str(config.get("hashtags", {}).get(chave, "")).startswith("#"):
            r.erro(f"[config] atlas.toml: hashtags.{chave} ausente ou sem '#'")
    if not RE_VERSAO.match(str(config.get("motor", {}).get("versao", ""))):
        r.erro("[config] atlas.toml: motor.versao ausente ou fora do formato vX.Y")
    if not RE_SLUG.match(str(config.get("publicacao", {}).get("slug", ""))):
        r.erro("[config] atlas.toml: publicacao.slug ausente ou inválido (minúsculas, números e hífen)")

    catalogo = {t["id"] for t in ler_toml(CATALOGO / "temas.toml")["tema"]}
    escolhas = {}
    if (local / "temas.toml").exists():
        try:
            escolhas = ler_toml(local / "temas.toml").get("tema", {})
        except tomllib.TOMLDecodeError as e:
            r.erro(f"[temas] temas.toml ilegível: {e}")
            return config, []
    else:
        r.erro("[temas] falta temas.toml")
    for tid, e in escolhas.items():
        if e.get("situacao", "planejado") not in SITUACOES:
            r.erro(f"[temas] {tid}: situação '{e.get('situacao')}' (use {list(SITUACOES)})")
        if "recorte" in e and e["recorte"] not in RECORTES:
            r.erro(f"[temas] {tid}: recorte '{e['recorte']}' (use {sorted(RECORTES)})")
        if tid not in catalogo:
            faltam = {"numero", "titulo", "consulta"} - set(e)
            if faltam:
                r.erro(f"[temas] {tid}: não está no catálogo do motor; prancha própria precisa de {sorted(faltam)}")
    temas = ler_temas(local)
    numeros = {}
    for t in temas:
        if t.numero in numeros:
            r.erro(f"[temas] número de prancha repetido: {t.numero} ({numeros[t.numero]} e {t.id})")
        numeros[t.numero] = t.id
        consulta = caminho_consulta(local, t)
        if not consulta.is_file():
            r.erro(f"[temas] {t.id}: consulta inexistente: {consulta.name or '(vazia)'}")
        elif "{{bbox}}" not in consulta.read_text(encoding="utf-8"):
            r.erro(f"[temas] {t.id}: a consulta {consulta.name} não usa {{{{bbox}}}} (precisa ser restrita ao município)")
        if t.ativo and t.referencia != "interno" and not (local / "dados" / "oficiais" / t.referencia).is_dir():
            r.aviso(f"[temas] {t.id}: base oficial '{t.referencia}' ainda não carregada em dados/oficiais/")
    return config, temas


def verificar_workflows(local: Path, config: dict, r: Relatorio) -> None:
    versao = str(config.get("motor", {}).get("versao", ""))
    pasta = local / ".github" / "workflows"
    chamadas = 0
    for arq in sorted(pasta.glob("*.yml")) if pasta.exists() else []:
        for ref in RE_CHAMADA.findall(arq.read_text(encoding="utf-8")):
            chamadas += 1
            if ref != versao:
                r.erro(f"[motor] .github/workflows/{arq.name} chama o motor em {ref}, mas atlas.toml diz {versao}")
    if chamadas == 0:
        r.aviso("[motor] nenhum workflow chama o atlas-motor (o CI não vai verificar nem publicar)")


# ---------------------------------------------------------------- Dados do OSM
def verificar_osm(local: Path, config: dict, temas: list[Tema], r: Relatorio) -> None:
    pasta = local / "dados" / "osm"
    if not (pasta / "limite.geojson").exists():
        r.aviso("[osm] dados/osm/limite.geojson ausente: rode baixar_osm.py")
        return
    bbox = config.get("municipio", {}).get("bbox", [-90, -180, 90, 180])
    retrato = {}
    if (pasta / "retrato.json").exists():
        try:
            retrato = json.loads((pasta / "retrato.json").read_text(encoding="utf-8")).get("temas", {})
        except json.JSONDecodeError as e:
            r.erro(f"[osm] retrato.json ilegível: {e}")
    else:
        r.erro("[osm] falta dados/osm/retrato.json (gerado por baixar_osm.py)")
    conhecidos = {t.id for t in temas} | {"limite"}
    for arq in sorted(pasta.glob("*.geojson")):
        nome = arq.stem
        if nome not in conhecidos:
            r.erro(f"[osm] {arq.name}: não corresponde a nenhum tema")
            continue
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            r.erro(f"[osm] {arq.name}: JSON inválido ({e})")
            continue
        if dados.get("type") != "FeatureCollection":
            r.erro(f"[osm] {arq.name}: não é FeatureCollection")
            continue
        vistos = set()
        for i, f in enumerate(dados.get("features", []), 1):
            osm = f.get("properties", {}).get("osm", "")
            if not re.fullmatch(r"(node|way|relation)/\d+", osm):
                r.erro(f"[osm] {arq.name}: feição {i} sem identificador OSM válido")
            elif osm in vistos:
                r.erro(f"[osm] {arq.name}: {osm} repetido")
            vistos.add(osm)
            try:
                pts = coordenadas(f["geometry"])
            except (KeyError, ValueError, TypeError) as e:
                r.erro(f"[osm] {arq.name}: {osm or i}: geometria inválida ({e})")
                continue
            if nome != "limite" and f["geometry"]["type"] != "LineString" and not all(dentro_caixa(x, y, bbox) for x, y in pts):
                r.erro(f"[osm] {arq.name}: {osm} fora da área do município")
        if nome != "limite":
            esperado = retrato.get(nome, {}).get("feicoes")
            if esperado is None:
                r.erro(f"[osm] {arq.name}: tema ausente do retrato.json")
            elif esperado != len(dados.get("features", [])):
                r.erro(f"[osm] {arq.name}: {len(dados['features'])} feições, mas retrato.json diz {esperado}")
    for t in temas:
        if t.ativo and not (pasta / f"{t.id}.geojson").exists():
            r.erro(f"[osm] {t.id} está ativo, mas falta dados/osm/{t.id}.geojson (rode baixar_osm.py --tema {t.id})")


# ---------------------------------------------------------------- Bases oficiais
def verificar_oficiais(local: Path, config: dict, r: Relatorio) -> None:
    bbox = config.get("municipio", {}).get("bbox", [-90, -180, 90, 180])
    for pasta in sorted(p for p in (local / "dados" / "oficiais").glob("*") if p.is_dir()):
        fonte_arq = pasta / "fonte.toml"
        if not fonte_arq.exists():
            r.erro(f"[oficiais] {pasta.name}: falta fonte.toml")
            continue
        try:
            fonte = ler_toml(fonte_arq)
        except tomllib.TOMLDecodeError as e:
            r.erro(f"[oficiais] {pasta.name}/fonte.toml ilegível: {e}")
            continue
        for chave in ("nome", "orgao", "url", "data_acesso", "licenca", "arquivo"):
            if not str(fonte.get(chave, "")).strip():
                r.erro(f"[oficiais] {pasta.name}/fonte.toml: falta '{chave}'")
        try:
            date.fromisoformat(str(fonte.get("data_acesso", "")))
        except ValueError:
            r.erro(f"[oficiais] {pasta.name}/fonte.toml: data_acesso deve ser AAAA-MM-DD")
        arq = pasta / str(fonte.get("arquivo", ""))
        if not arq.is_file():
            r.erro(f"[oficiais] {pasta.name}: arquivo declarado não existe: {fonte.get('arquivo')}")
            continue
        try:
            cab, linhas = ler_csv(arq)
        except UnicodeDecodeError:
            r.erro(f"[oficiais] {pasta.name}/{arq.name}: não está em UTF-8")
            continue
        colunas = fonte.get("colunas", {})
        for papel in ("id", "nome", "lat", "lon"):
            if colunas.get(papel) not in cab:
                r.erro(f"[oficiais] {pasta.name}: coluna para '{papel}' ({colunas.get(papel)}) não está no CSV")
        if colunas.get("lat") in cab and colunas.get("lon") in cab:
            for n, linha in enumerate(linhas, 2):
                try:
                    lat, lon = float(linha[colunas["lat"]]), float(linha[colunas["lon"]])
                except (TypeError, ValueError):
                    continue                      # item sem coordenada: tratado na completude
                if not dentro_caixa(lon, lat, bbox):
                    r.aviso(f"[oficiais] {pasta.name}/{arq.name}:{n}: coordenada fora da área do município")
        verificar_dados_pessoais(f"oficiais/{pasta.name}/{arq.name}", cab, linhas, r)


# ---------------------------------------------------------------- Dados curados
def verificar_curados(local: Path, config: dict, temas: list[Tema], r: Relatorio) -> None:
    bbox = config.get("municipio", {}).get("bbox", [-90, -180, 90, 180])
    ids_temas = {t.id for t in temas}
    esquemas = ler_esquemas(local)
    for chave, (arq_esq, e) in esquemas.items():
        if "_erro" in e:
            r.erro(f"[esquemas] {arq_esq.name} ilegível: {e['_erro']}")
            continue
        for c in e.get("coluna", []):
            if c.get("tipo") not in TIPOS:
                r.erro(f"[esquemas] {arq_esq.name}: coluna {c.get('nome')} com tipo '{c.get('tipo')}' desconhecido")
    for arq in sorted((local / "dados" / "curados").glob("*.csv")):
        rot = f"curados/{arq.name}"
        if arq.name not in esquemas:
            r.erro(f"[curados] {arq.name}: sem esquema (catálogo do motor ou dados/esquemas/, campo arquivo = \"{arq.name}\")")
            continue
        _, esq = esquemas[arq.name]
        try:
            cab, linhas = ler_csv(arq)
        except UnicodeDecodeError:
            r.erro(f"[curados] {arq.name}: não está em UTF-8")
            continue
        definidas = [c["nome"] for c in esq.get("coluna", [])]
        if cab != definidas:
            r.erro(f"[curados] {arq.name}: colunas {cab} diferem do esquema {definidas}")
            continue
        chaves = set()
        for n, linha in enumerate(linhas, 2):
            for c in esq["coluna"]:
                valor = (linha.get(c["nome"]) or "").strip()
                if not valor:
                    if c.get("obrigatoria"):
                        r.erro(f"[curados] {arq.name}:{n}: '{c['nome']}' é obrigatória")
                    continue
                problema = checar_tipo(valor, c, ids_temas)
                if problema:
                    r.erro(f"[curados] {arq.name}:{n}: '{c['nome']}' {problema}")
            chave = (linha.get(esq.get("chave", "")) or "").strip()
            if chave:
                if chave in chaves:
                    r.erro(f"[curados] {arq.name}:{n}: chave '{chave}' repetida")
                chaves.add(chave)
            lat, lon = (linha.get("lat") or "").strip(), (linha.get("lon") or "").strip()
            if bool(lat) != bool(lon):
                r.erro(f"[curados] {arq.name}:{n}: informe lat e lon juntas")
            elif lat and lon:
                try:
                    if not dentro_caixa(float(lon), float(lat), bbox):
                        r.erro(f"[curados] {arq.name}:{n}: coordenada fora da área do município")
                except ValueError:
                    pass                          # já apontado pela checagem de tipo
        verificar_dados_pessoais(rot, cab, linhas, r)


def checar_tipo(valor: str, c: dict, ids_temas: set[str]) -> str | None:
    tipo = c.get("tipo")
    try:
        if tipo == "inteiro":
            v = int(valor)
            if "minimo" in c and v < c["minimo"] or "maximo" in c and v > c["maximo"]:
                return f"fora do intervalo {c.get('minimo')}–{c.get('maximo')}"
        elif tipo in ("decimal", "latitude", "longitude"):
            v = float(valor)
            if tipo == "latitude" and not -90 <= v <= 90 or tipo == "longitude" and not -180 <= v <= 180:
                return "fora do intervalo válido"
        elif tipo == "data":
            date.fromisoformat(valor)
        elif tipo == "lista" and valor not in c.get("valores", []):
            return f"= '{valor}' não está entre {c.get('valores')}"
        elif tipo == "tema" and valor not in ids_temas:
            return f"= '{valor}' não é tema do atlas"
        elif tipo == "url" and not RE_URL.match(valor):
            return "não é uma URL http(s)"
    except ValueError:
        return f"= '{valor}' não é {tipo} válido"
    if c.get("padrao") and not re.fullmatch(c["padrao"], valor):
        return f"= '{valor}' não segue o padrão {c['padrao']}"
    return None


def verificar_dados_pessoais(rot: str, cab: list[str], linhas: list[dict], r: Relatorio) -> None:
    for col in cab:
        if col.strip().lower() in COLUNAS_PROIBIDAS:
            r.erro(f"[lgpd] {rot}: coluna '{col}' não é permitida (dado pessoal)")
    for n, linha in enumerate(linhas, 2):
        for col, valor in linha.items():
            valor = valor or ""
            if RE_EMAIL.search(valor):
                r.erro(f"[lgpd] {rot}:{n}: '{col}' contém um e-mail")
            if RE_CPF.search(valor):
                r.erro(f"[lgpd] {rot}:{n}: '{col}' parece conter um CPF")


# ---------------------------------------------------------------- Pranchas
def verificar_pranchas(local: Path, temas: list[Tema], r: Relatorio) -> None:
    if not (local / "atlas" / "index.qmd").exists():
        r.erro("[atlas] falta atlas/index.qmd (apresentação do atlas do município)")
    existentes = {p.name for p in (local / "atlas" / "pranchas").glob("*.qmd")}
    esperadas = {t.prancha for t in temas if t.ativo}
    for t in temas:
        if t.ativo and t.prancha not in existentes:
            r.erro(f"[atlas] {t.id} está '{t.situacao}', mas falta atlas/pranchas/{t.prancha}")
    for p in sorted(existentes - esperadas):
        r.erro(f"[atlas] atlas/pranchas/{p} não corresponde a tema ativo (situação 'planejado' ou nome errado)")
    for p in sorted(existentes & esperadas):
        if "_gerado/" not in (local / "atlas" / "pranchas" / p).read_text(encoding="utf-8"):
            r.aviso(f"[atlas] pranchas/{p} não inclui o trecho gerado ({{{{< include ../_gerado/<tema>.md >}}}})")


# ---------------------------------------------------------------- Arquivos
def verificar_arquivos(local: Path, r: Relatorio) -> None:
    textos = {".md", ".qmd", ".toml", ".csv", ".py", ".yml", ".yaml", ".json", ".geojson", ".overpassql", ".scss", ".txt"}
    for arq in local.rglob("*"):
        if not arq.is_file() or IGNORAR & set(arq.relative_to(local).parts):
            continue
        rel = arq.relative_to(local).as_posix()
        if arq.stat().st_size > LIMITE_BYTES:
            r.erro(f"[arquivos] {rel}: maior que 25 MB (use outra forma de armazenamento)")
        if arq.suffix.lower() in textos:
            try:
                texto = arq.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                r.erro(f"[arquivos] {rel}: não está em UTF-8")
                continue
            if re.search(r"^(<{7}|>{7})( |$)", texto, re.MULTILINE):
                r.erro(f"[arquivos] {rel}: marcas de conflito de merge")
        if arq.suffix == ".py":
            r.aviso(f"[arquivos] {rel}: script no repositório do município; código comum vai para o atlas-motor")


def verificar(local: Path) -> Relatorio:
    r = Relatorio()
    config, temas = verificar_config(local, r)
    verificar_workflows(local, config, r)
    verificar_osm(local, config, temas, r)
    verificar_oficiais(local, config, r)
    verificar_curados(local, config, temas, r)
    verificar_pranchas(local, temas, r)
    verificar_arquivos(local, r)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumento_local(ap)
    args = ap.parse_args()
    r = verificar(args.local.resolve())
    for m in r.erros:
        print(f"ERRO   {m}")
    for m in r.avisos:
        print(f"AVISO  {m}")
    print(f"\n{len(r.erros)} erro(s), {len(r.avisos)} aviso(s).")
    return 1 if r.erros else 0


if __name__ == "__main__":
    sys.exit(main())
