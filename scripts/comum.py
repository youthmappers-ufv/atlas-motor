"""Funções comuns aos scripts do motor do atlas: configuração, geometria e nomes.

Dois lugares:
  MOTOR  este repositório (atlas-motor): catálogo, livro, scripts, modelo de município;
  local  o repositório de um município (atlas-<cidade>): atlas.toml, temas.toml, dados/, atlas/.
Os scripts recebem o local em --local (padrão: a pasta atual).

Só biblioteca padrão (Python 3.11+), para que a verificação do CI rode sem
instalar nada. O que precisa de bibliotecas externas (mapas) fica em mapas.py.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
CATALOGO = MOTOR / "catalogo"
SITUACOES = ("planejado", "em-andamento", "publicado")


# ---------------------------------------------------------------- Configuração
@dataclass
class Tema:
    id: str
    numero: int
    titulo: str
    situacao: str
    consulta: str
    referencia: str
    recorte: str
    proprio: bool = False          # prancha só deste município (fora do catálogo)
    cor: str = "#304068"           # cor dos objetos do tema no mapa
    mapa: str = "pontos"           # pontos (objetos em destaque sobre as vias) | linhas (rede: vias, estradas)
    indicadores: tuple = ()        # além de total e nome: "servico" (endereço, horário), "vias" (km, pavimento)

    @property
    def prancha(self) -> str:
        return f"{self.numero:02d}-{self.id}.qmd"

    @property
    def ativo(self) -> bool:
        return self.situacao != "planejado"


MAPAS = ("pontos", "linhas")
INDICADORES = ("servico", "vias")


def _visual(base: dict, escolha: dict) -> dict:
    """cor, mapa e indicadores de um tema: do catálogo, trocáveis pelo município."""
    return {"cor": escolha.get("cor", base.get("cor", "#304068")),
            "mapa": escolha.get("mapa", base.get("mapa", "pontos")),
            "indicadores": tuple(escolha.get("indicadores", base.get("indicadores", ())))}


def ler_toml(arquivo: Path) -> dict:
    with arquivo.open("rb") as f:
        return tomllib.load(f)


def versao_motor() -> str:
    return (MOTOR / "VERSAO").read_text(encoding="utf-8").strip()


def argumento_local(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--local", type=Path, default=Path.cwd(),
                    help="repositório do município (padrão: a pasta atual)")


def ler_config(local: Path) -> dict:
    return ler_toml(local / "atlas.toml")


# ---------------------------------------------------------------- Versão declarada
CACHE_VERSOES = Path(os.environ.get("ATLAS_MOTOR_CACHE", Path.home() / ".cache" / "atlas-motor"))


def tirar_somente_leitura(funcao, caminho, _info) -> None:
    """No Windows (e em pastas do OneDrive), o Quarto deixa itens somente leitura que o
    rmtree não apaga: tira o atributo e tenta de novo."""
    os.chmod(caminho, 0o700)
    funcao(caminho)


def _local_dos_argumentos(argv: list[str]) -> Path:
    for i, a in enumerate(argv):
        if a == "--local" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if a.startswith("--local="):
            return Path(a.split("=", 1)[1])
    return Path.cwd()


def _extrair_versao(versao: str, destino: Path) -> None:
    """Extrai a tag do clone local do motor para o cache (as tags do motor nunca mudam)."""
    r = subprocess.run(["git", "-C", str(MOTOR), "archive", "--format=tar", f"refs/tags/{versao}"],
                       capture_output=True)
    if r.returncode:
        sys.exit(f"O atlas.toml declara o motor {versao}, que não está no clone do motor em {MOTOR}.\n"
                 f"Rode: git -C \"{MOTOR}\" fetch --tags   (ou use --motor-atual para usar o motor desta pasta)")
    temporario = destino.with_name(destino.name + ".parcial")
    shutil.rmtree(temporario, ignore_errors=True)
    temporario.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        if hasattr(tarfile, "data_filter"):               # Python 3.11.4+
            tar.extractall(temporario, filter="data")
        else:
            tar.extractall(temporario)
    temporario.replace(destino)


def usar_versao_declarada(script: str) -> None:
    """Roda o script na versão do motor declarada no atlas.toml do município.

    Localmente, o motor ao lado pode estar em outra versão; neste caso, a versão declarada é
    extraída da tag (cache em ~/.cache/atlas-motor/) e o script dela roda no lugar deste.
    No CI o motor já vem na versão declarada e nada muda. --motor-atual (ou ATLAS_MOTOR_ATUAL=1)
    força o motor desta pasta, para desenvolver o próprio motor."""
    if "--motor-atual" in sys.argv:
        sys.argv.remove("--motor-atual")
        return
    if os.environ.get("ATLAS_MOTOR_ATUAL"):
        return
    argv = sys.argv[1:]
    local = _local_dos_argumentos(argv).resolve()
    if local == MOTOR or MOTOR in local.parents:          # município de exemplo dos testes
        return
    try:
        declarada = ler_config(local)["motor"]["versao"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return                                             # o próprio script reporta o problema
    if declarada == versao_motor():
        return
    pasta = CACHE_VERSOES / declarada
    if not (pasta / "scripts" / script).exists():
        _extrair_versao(declarada, pasta)
    if script == "construir.py" and (local / "_construcao").exists():
        # versões antigas apagam _construcao sem tratar itens somente leitura
        shutil.rmtree(local / "_construcao", onerror=tirar_somente_leitura)
    print(f"O atlas.toml declara o motor {declarada}; usando essa versão (este motor é {versao_motor()}; "
          "--motor-atual usa este).", file=sys.stderr, flush=True)
    env = dict(os.environ, ATLAS_MOTOR_ATUAL="1")
    sys.exit(subprocess.run([sys.executable, str(pasta / "scripts" / script), *argv], env=env).returncode)


def ler_temas(local: Path) -> list[Tema]:
    """Catálogo do motor combinado com o temas.toml do município.

    No município: [tema.<id>] com situacao (e, opcionalmente, referencia, recorte, titulo).
    Um id fora do catálogo é prancha própria do município e precisa de numero, titulo e
    consulta (em consultas/ do município).
    """
    catalogo = {t["id"]: t for t in ler_toml(CATALOGO / "temas.toml")["tema"]}
    escolhas = ler_toml(local / "temas.toml").get("tema", {}) if (local / "temas.toml").exists() else {}
    if isinstance(escolhas, list):               # formato anterior ao motor ([[tema]] com id), em commits antigos
        escolhas = {t["id"]: t for t in escolhas if "id" in t}
    temas = []
    for tid, base in catalogo.items():
        e = escolhas.get(tid, {})
        temas.append(Tema(id=tid, numero=base["numero"], titulo=e.get("titulo", base["titulo"]),
                          situacao=e.get("situacao", "planejado"), consulta=base["consulta"],
                          referencia=e.get("referencia", base["referencia"]),
                          recorte=e.get("recorte", base["recorte"]), **_visual(base, e)))
    for tid, e in escolhas.items():
        if tid not in catalogo:
            temas.append(Tema(id=tid, numero=e.get("numero", 0), titulo=e.get("titulo", tid),
                              situacao=e.get("situacao", "planejado"), consulta=e.get("consulta", ""),
                              referencia=e.get("referencia", "interno"), recorte=e.get("recorte", "municipio"),
                              proprio=True, **_visual({}, e)))
    return sorted(temas, key=lambda t: t.numero)


def caminho_consulta(local: Path, tema: Tema) -> Path:
    """Consulta do município (consultas/) se existir; senão, a do catálogo."""
    propria = local / "consultas" / tema.consulta
    return propria if propria.exists() or tema.proprio else CATALOGO / "consultas" / tema.consulta


def ler_esquemas(local: Path) -> dict[str, tuple[Path, dict]]:
    """Esquemas dos CSV de dados/curados/: os do catálogo e os próprios do município
    (dados/esquemas/), que prevalecem quando descrevem o mesmo arquivo."""
    esquemas = {}
    for pasta in (CATALOGO / "esquemas", local / "dados" / "esquemas"):
        for arq in sorted(pasta.glob("*.toml")):
            try:
                e = ler_toml(arq)
            except tomllib.TOMLDecodeError as erro:
                esquemas[f"!{arq}"] = (arq, {"_erro": str(erro)})
                continue
            esquemas[e.get("arquivo", arq.stem + ".csv")] = (arq, e)
    return esquemas


def ler_csv(arquivo: Path) -> tuple[list[str], list[dict]]:
    with arquivo.open(encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        linhas = list(leitor)
        return list(leitor.fieldnames or []), linhas


def escrever_json(arquivo: Path, dados) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    # Fim de linha LF também no Windows: o mesmo retrato gera o mesmo arquivo em qualquer sistema.
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- Geometria
def aneis_externos(relacao: dict) -> list[list[tuple[float, float]]]:
    """Junta os caminhos 'outer' de uma relação do Overpass (out geom) em anéis (lon, lat)."""
    pedacos = [[(p["lon"], p["lat"]) for p in m["geometry"]]
               for m in relacao.get("members", []) if m.get("type") == "way" and m.get("role") == "outer"]
    aneis = []
    while pedacos:
        anel = pedacos.pop(0)
        while anel[0] != anel[-1]:
            for i, p in enumerate(pedacos):
                if p[0] == anel[-1]:
                    anel += p[1:]
                elif p[-1] == anel[-1]:
                    anel += p[-2::-1]
                else:
                    continue
                pedacos.pop(i)
                break
            else:
                break                     # anel aberto: dados incompletos
        aneis.append(anel)
    return aneis


def dentro(lon: float, lat: float, aneis: list) -> bool:
    """Ponto no polígono (par-ímpar), para um ou mais anéis."""
    res = False
    for anel in aneis:
        for (x1, y1), (x2, y2) in zip(anel, anel[1:]):
            if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                res = not res
    return res


def distancia_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distância em metros (haversine)."""
    r = 6371008.8
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df, dl = f2 - f1, math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def coordenadas(geometria: dict) -> list[tuple[float, float]]:
    """Todos os vértices de uma geometria GeoJSON (Point, LineString, Polygon)."""
    t, c = geometria["type"], geometria["coordinates"]
    if t == "Point":
        return [tuple(c)]
    if t == "LineString":
        return [tuple(p) for p in c]
    if t == "Polygon":
        return [tuple(p) for anel in c for p in anel]
    raise ValueError(f"geometria não suportada: {t}")


def ponto_representativo(geometria: dict) -> tuple[float, float]:
    pts = coordenadas(geometria)
    if geometria["type"] == "LineString":
        return pts[len(pts) // 2]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def ler_limite(local: Path) -> list[list[tuple[float, float]]]:
    dados = json.loads((local / "dados" / "osm" / "limite.geojson").read_text(encoding="utf-8"))
    geometria = dados["features"][0]["geometry"]
    return [[tuple(p) for p in anel] for anel in geometria["coordinates"]]


# ---------------------------------------------------------------- Nomes
SUFIXOS = {"filho", "filha", "neto", "neta", "junior", "júnior", "sobrinho", "sobrinha"}


def sobrenome_e_prenome(nome: str) -> tuple[str, str]:
    """"Rodrigo Smarzaro" -> ("Smarzaro", "Rodrigo"); "João Souza Filho" -> ("Souza Filho", "João");
    partículas ficam com o prenome ("João da Silva" -> ("Silva", "João da")), como na NBR 6023."""
    p = nome.split()
    n = 2 if len(p) > 2 and p[-1].lower() in SUFIXOS else 1
    return " ".join(p[-n:]), " ".join(p[:-n])


ABREVIACOES = {
    r"\be\.?\s*e\.?\b": "escola estadual",
    r"\be\.?\s*m\.?\b": "escola municipal",
    r"\bemef\b": "escola municipal de ensino fundamental",
    r"\bcmei\b": "centro municipal de educacao infantil",
    r"\bprof\.?\b": "professor",
    r"\bprofa\.?\b": "professora",
    r"\bdr\.?\b": "doutor",
    r"\bubs\b": "unidade basica de saude",
    r"\besf\b": "estrategia saude da familia",
    r"\bsta\.?\b": "santa",
    r"\bsto\.?\b": "santo",
    r"\bn\.?\s*s(ra)?\.?\b": "nossa senhora",
}


def normalizar_nome(nome: str) -> str:
    """Minúsculas, sem acentos e com as abreviações usuais expandidas."""
    t = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    for padrao, troca in ABREVIACOES.items():
        t = re.sub(padrao, troca, t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()
