# atlas-motor

[![versão](https://img.shields.io/github/v/tag/youthmappers-ufv/atlas-motor?sort=semver&label=vers%C3%A3o)](CHANGELOG.md) [![Testes do motor](https://github.com/youthmappers-ufv/atlas-motor/actions/workflows/testes.yml/badge.svg?branch=main)](https://github.com/youthmappers-ufv/atlas-motor/actions/workflows/testes.yml) [![código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-blue)](LICENSE) [![textos: CC BY 4.0](https://img.shields.io/badge/textos-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/deed.pt-br) ![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB) ![Quarto 1.10](https://img.shields.io/badge/Quarto-1.10-75AADB) [![documentação](https://img.shields.io/badge/documenta%C3%A7%C3%A3o-docs-informational)](docs/README.md)
<!-- DOI: com a integração do Zenodo ligada, acrescente aqui o badge do DOI conceito (docs/configuracao-github.md). -->

Código e estrutura comuns do **Atlas Colaborativo** do Programa Youthmappers UFV: atlas municipais abertos, feitos a partir do OpenStreetMap, com medição de completude em relação às bases oficiais, publicados como site e PDF.

Cada município tem o seu repositório (`atlas-<cidade>`), que guarda **só** configuração, dados e textos, usa este motor numa versão fixada e publica o próprio site no GitHub Pages. O código vive num lugar só: uma correção ou um indicador novo chega a todos os municípios, e nenhum repositório municipal diverge da estrutura.

```
youthmappers-ufv/atlas-motor        público    este repositório: código, catálogo, modelos, workflows
youthmappers-ufv/atlas-<cidade>     público    um por município: atlas.toml, temas.toml, dados/, atlas/;
                                               publica o site no próprio GitHub Pages (só dados públicos)
```

![Arquitetura dos repositórios do atlas](docs/figuras/arquitetura-repositorios.svg)

Detalhes e o ciclo mensal de um município em [docs/arquitetura.md](docs/arquitetura.md). **Toda a documentação de uso e manutenção** (guia do município, pranchas, novos temas, identidade visual, referência, manutenção, solução de problemas) está em [docs/](docs/README.md).

## O que tem aqui

```
VERSAO, CHANGELOG.md    versão atual (vX.Y.Z) e o que mudou em cada uma
catalogo/
  temas.toml            as pranchas (número, título, consulta, base de referência, recorte, cor, mapa, indicadores)
  consultas/            uma consulta Overpass por prancha ({{bbox}} = caixa do município)
  esquemas/             esquemas dos CSV levantados pelas equipes
livro/                  modelo do livro Quarto: método, dados, _quarto.modelo.yml, tema padrão (_brand.yml,
                        marca/), estilo do site (estilo.scss) e do PDF (atlas-estilo.tex, capa)
modelos/prancha.qmd     modelo de prancha (usado por ativar_tema.py)
modelo-local/           modelo de repositório municipal (usado por novo_local.py)
scripts/
  baixar_osm.py         retrato do OSM do município
  validar.py            integridade do repositório do município (CI em todo PR)
  indicadores.py        completude C_t e Q_t e indicadores internos
  mapas.py              mapas das pranchas (matplotlib)
  construir.py          monta o livro e renderiza site e PDF
  identidade.py         traduz o _brand.yml (identidade visual) para o PDF
  novo_local.py         cria o repositório de um município novo pelo código IBGE
  instalar_ganchos.py   instala no município o gancho de pre-push com o validador
  ativar_tema.py        abre uma prancha num município
  preparar_base.py      converte uma base oficial baixada (INEP) para dados/oficiais/ do município
  atualizar_motor.py    muda a versão do motor usada por um município
  serie_historica.py    série histórica dos indicadores de um município, a partir do Git
  notas_versao.py       notas de uma versão (do CHANGELOG) e a regra do release automático
.github/workflows/      reutilizáveis (verificar, atualizar-dados, publicar), os testes e o release do motor
testes/                 testes, com o município sintético testes/exemplo/
docs/                   documentação de uso e manutenção (índice em docs/README.md; diagramas em figuras/)
CITATION.cff            como citar o software
```

## Município novo

Com o motor clonado numa pasta e os repositórios municipais ao lado dele:

```bash
python atlas-motor/scripts/novo_local.py --nome "São Gotardo" --ibge 3162104 --baixar --git
```

O script busca no OSM o limite (pelo `IBGE:GEOCODIGO`), a caixa envolvente, o Wikidata e a sede; preenche o modelo; baixa o primeiro retrato; e faz o primeiro commit em `../atlas-sao-gotardo`. Depois, siga [docs/configuracao-github.md](docs/configuracao-github.md) para criar o repositório (público), ligar o GitHub Pages, proteger a `main` e dar acesso à equipe e à prefeitura parceira. Município sem parceria: `--privado` (o atlas sai só como artefato).

## Uso num município

```bash
cd atlas-rio-paranaiba
python ../atlas-motor/scripts/instalar_ganchos.py    # uma vez por clone
python ../atlas-motor/scripts/validar.py
python ../atlas-motor/scripts/baixar_osm.py
python ../atlas-motor/scripts/ativar_tema.py saude
python ../atlas-motor/scripts/construir.py --renderizar todos      # site e PDF em _construcao/livro/_site/
python ../atlas-motor/scripts/construir.py --previa                # prévia ao vivo (quarto preview)
```

Requisitos: Python 3.11+ (validação e testes só com a biblioteca padrão), `pip install -r requirements.txt` (matplotlib, para os mapas; PyYAML, para o tema) e [Quarto](https://quarto.org); para o PDF, TinyTeX (`quarto install tinytex`) ou MiKTeX.

## Versões

O município declara a versão em `atlas.toml` (`[motor] versao = "vX.Y.Z"`) e chama os workflows na mesma versão (`...@vX.Y.Z`); o validador confere que batem. Os workflows baixam o motor na versão declarada pelo município **na versão do município que está sendo publicada**: uma edição antiga é sempre regerada como foi. Localmente, `construir.py`, `validar.py` e `baixar_osm.py` também rodam na versão declarada, extraída da tag do clone ao lado (`--motor-atual` usa o motor da pasta). As tags publicadas são protegidas e nunca mudam. Política de versões e o que mudou: [CHANGELOG.md](CHANGELOG.md). Como mudar o motor: [CONTRIBUTING.md](CONTRIBUTING.md).

## Como citar

Em trabalho acadêmico, cite a versão usada (a do `atlas.toml` do município):

SMARZARO, Rodrigo; PROGRAMA YOUTHMAPPERS UFV. **atlas-motor**: motor aberto para atlas municipais colaborativos a partir do OpenStreetMap. Versão v0.10.0. Rio Paranaíba: Universidade Federal de Viçosa, 2026. Disponível em: <https://github.com/youthmappers-ufv/atlas-motor>. Acesso em: *data do acesso*.

Em BibLaTeX (estilo `abnt` do pacote biblatex-abnt, que imprime a versão a partir de `edition`; acrescente `urldate = {AAAA-MM-DD}`):

```bibtex
@software{atlas-motor,
  author    = {Smarzaro, Rodrigo and {Programa Youthmappers UFV}},
  title     = {atlas-motor},
  subtitle  = {motor aberto para atlas municipais colaborativos a partir do {OpenStreetMap}},
  edition   = {Versão v0.10.0},
  location  = {Rio Paranaíba},
  publisher = {Universidade Federal de Viçosa},
  year      = {2026},
  url       = {https://github.com/youthmappers-ufv/atlas-motor},
  langid    = {brazilian},
}
```

O GitHub também oferece a citação pelo botão *Cite this repository* (`CITATION.cff`). Para citar um atlas (os mapas e dados de um município), use a referência da página inicial dele.

## Licença

| Conteúdo | Licença |
|---|---|
| Código (`scripts/`, `testes/`, workflows), catálogo (`catalogo/`), modelos de configuração e o município sintético de testes (`testes/exemplo/`) | [MIT](LICENSE) |
| Textos: documentação (`docs/`, READMEs), páginas do livro (`livro/*.qmd`) e textos do modelo de município | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt-br) |

O motor não guarda dados do OpenStreetMap; os retratos de cada município, sob a [ODbL 1.0](https://opendatacommons.org/licenses/odbl/), ficam nos repositórios municipais.

O logo do programa (`livro/marca/`) é marca do Programa Youthmappers UFV e não entra em nenhuma dessas licenças. Cada município declara as licenças dos próprios dados e textos no `LICENCAS.md` do seu repositório (modelo em `modelo-local/LICENCAS.md`).
