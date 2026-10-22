# Referência

Todos os arquivos de configuração e todos os comandos. Para o passo a passo, veja os guias ([município](guia-municipio.md), [pranchas](pranchas.md), [novos temas](novos-temas.md), [identidade visual](identidade-visual.md)).

## `atlas.toml` (município)

```toml
[municipio]
nome = "Rio Paranaíba"
uf = "MG"
ibge = "3155504"                 # código IBGE (7 dígitos)
osm_relacao = 314621             # relação do limite municipal no OSM (admin_level=8)
wikidata = "Q22065225"
bbox = [-19.45, -46.54, -19.04, -46.08]          # [sul, oeste, norte, leste], graus (WGS 84)
sede_bbox = [-19.2115, -46.26, -19.1815, -46.2265]  # recorte dos mapas da sede

[motor]
versao = "v0.7.0"                # versão do atlas-motor; troque com atualizar_motor.py

[hashtags]                       # sempre juntas nas edições do OSM
programa = "#youthmappersufv"
projeto = "#ymufv-atlas"

[overpass]
servidores = ["https://overpass-api.de/api/interpreter", "..."]   # tentados em ordem
tempo_limite = 240               # segundos por consulta

[completude]
distancia_max_m = 150            # distância máxima entre item oficial e objeto do OSM
similaridade_min = 0.6           # semelhança mínima de nome (0 a 1)

[publicacao]
hospedagem = "pages"             # "pages" (GitHub Pages deste repositório) | "artefato" (só artefato e release)
url = "https://youthmappers-ufv.github.io/atlas-rio-paranaiba/"   # com / no fim; vazio com "artefato"
dominio = ""                     # opcional: "atlas.prefeitura.mg.gov.br" (sem https:// nem /)
slug = "rio-paranaiba"           # nome do PDF: atlas-<slug>.pdf
atribuicao = "© colaboradores do OpenStreetMap (ODbL)"
autoria = "Programa Youthmappers UFV"
instituicao = "Universidade Federal de Viçosa — Campus Rio Paranaíba"
registro = "RAEX PRJ-211/2026"   # opcional, no rodapé
```

O validador exige `municipio` (nome, uf, ibge, osm_relacao, bbox, sede_bbox), `motor.versao` no formato `vX.Y.Z` e igual à dos workflows, as duas hashtags com `#`, `publicacao.slug` em minúsculas e hífen, `hospedagem` válida e `url` válida com `pages`.

## `temas.toml` (município)

Uma seção por tema que o município usa; temas não citados ficam `planejado`.

```toml
[tema.educacao]                  # tema do catálogo
situacao = "em-andamento"        # planejado | em-andamento | publicado
titulo = "Educação e creches"    # opcional: troca o título do catálogo
recorte = "sede"                 # opcional: municipio | sede | ambos
referencia = "inep"              # opcional: pasta em dados/oficiais/ ou "interno"
cor = "#304068"                  # opcional: cor no mapa
mapa = "pontos"                  # opcional: pontos | linhas
indicadores = ["servico"]        # opcional: "servico", "vias"

[tema.feiras]                    # prancha própria (id fora do catálogo)
numero = 20                      # obrigatório; 20 em diante
titulo = "Feiras livres"         # obrigatório
consulta = "feiras.overpassql"   # obrigatório; em consultas/ do município
situacao = "em-andamento"
recorte = "sede"
cor = "#BC9C38"
mapa = "pontos"
indicadores = ["servico"]
```

## `catalogo/temas.toml` (motor)

```toml
[[tema]]
id = "educacao"                  # nome dos arquivos; não muda
numero = 3                       # ordem; abaixo de 20; não muda
titulo = "Educação"
consulta = "educacao.overpassql" # em catalogo/consultas/
referencia = "inep"              # pasta padrão da base oficial no município, ou "interno"
recorte = "ambos"                # municipio | sede | ambos
cor = "#304068"                  # #RRGGBB
mapa = "pontos"                  # pontos | linhas
indicadores = ["servico"]        # [] | ["servico"] | ["vias"]
```

Consultas (`catalogo/consultas/<id>.overpassql` e `consultas/` do município) são Overpass QL com `{{bbox}}` em cada linha; o motor troca pela caixa do município, baixa com `out geom` e recorta pelo limite. Uma consulta de mesmo nome em `consultas/` do município substitui a do catálogo.

## Base oficial (`fonte.toml`)

Em `dados/oficiais/<base>/`, com o CSV (UTF-8, vírgula):

```toml
nome = "Catálogo de Escolas"
orgao = "INEP"
url = "https://www.gov.br/inep/..."   # de onde foi baixado
data_acesso = 2026-11-10
licenca = "..."                       # como consta na fonte
arquivo = "escolas.csv"
observacao = "Filtrado para o município 3155504; colunas renomeadas."   # opcional

[colunas]                             # quais colunas do CSV fazem cada papel
id = "codigo_inep"
nome = "escola"
lat = "latitude"
lon = "longitude"
```

## Esquemas de dados curados

Todo CSV em `dados/curados/` precisa de um esquema: do catálogo (`catalogo/esquemas/`) ou do município (`dados/esquemas/<nome>.toml`).

```toml
descricao = "Registros da conferência em campo"
arquivo = "levantamentos-campo.csv"
chave = "id"                          # coluna de valor único

[[coluna]]
nome = "id"
tipo = "texto"                        # texto | inteiro | decimal | data | lista | latitude | longitude | tema | url
obrigatoria = true
padrao = '^LC-\d{4}-\d{3}$'           # opcional: expressão regular

[[coluna]]
nome = "situacao"
tipo = "lista"
valores = ["confirmado", "corrigido", "inexistente"]

[[coluna]]
nome = "participantes"
tipo = "inteiro"
minimo = 0                            # opcional (inteiro e decimal)
```

Tipos: `data` é AAAA-MM-DD; `tema` é um id de tema do município; `lat`/`lon` (se existirem) precisam cair na caixa do município. Em qualquer coluna, o validador acusa e-mail, CPF formatado e telefone, e recusa colunas como `cpf`, `email`, `celular`, `matricula`.

Esquemas do catálogo: `levantamentos-campo` (conferência em campo) e `eventos-culturais` (calendário).

## `_brand.yml` (identidade visual)

Formato do Quarto. Campos usados pelo atlas: `meta.name`; `logo.images` (todos na capa do PDF) e `logo.medium` (site); `color.palette`, `primary`, `secondary`, `tertiary`, `light`, `foreground`, `background`; `typography.fonts`, `base`, `headings`, `monospace`. Exemplo e regras: [Identidade visual](identidade-visual.md).

## Partes geradas de cada prancha

Em `_construcao/livro/_gerado/` (fora do Git, refeito a cada construção):

| Arquivo | Conteúdo |
|---|---|
| `<tema>.md` | prancha gerada inteira (todas as partes) |
| `<tema>/mapa-municipio.md`, `<tema>/mapa-sede.md` | figuras dos mapas |
| `<tema>/legenda.md`, `indicadores.md`, `lacunas.md`, `fonte.md` | legenda, tabela de indicadores, lacunas da base oficial (com o motivo provável), fonte e atribuição |
| `figuras/<tema>-municipio.png`, `figuras/<tema>-sede.png` | mapas (PNG, 200 dpi) |
| `edicao.md`, `pranchas.md`, `downloads.md` | versão e data dos dados com o botão de baixar o PDF (só no site), lista de pranchas, links dos dados |
| `pdf.md`, `notas.md` | só o botão do PDF (página "Dados para download"); só a versão e a data (notas do release) |
| `downloads/<tema>.geojson` | dados de cada prancha para baixar |

## Comandos

Todos rodam de dentro do repositório do município (ou com `--local <pasta>`). `construir.py`, `validar.py` e `baixar_osm.py` usam a versão do motor declarada no `atlas.toml`, extraída da tag do clone do motor para `~/.cache/atlas-motor/`; `--motor-atual` usa o motor da pasta.

| Comando | O que faz | Opções |
|---|---|---|
| `validar.py` | confere o repositório (configuração, temas, retratos, bases, curados, pranchas, identidade, dados pessoais, arquivos) | `--local` |
| `baixar_osm.py` | baixa o retrato do OSM dos temas ativos | `--tema <id>` (repetível), `--local` |
| `construir.py` | monta o livro em `_construcao/livro/` e, se pedido, renderiza | `--renderizar html\|pdf\|todos`, `--previa` (`--porta`, `--sem-navegador`), `--baixar`, `--sem-mapas`, `--local` |
| `ativar_tema.py <id>` | muda a situação de um tema e cria a prancha | `--situacao planejado\|em-andamento\|publicado`, `--local` |
| `preparar_base.py <base> <arquivo>` | converte uma base oficial como baixada do órgão para `dados/oficiais/<base>/` (formatos: `inep`) | `--data`, `--todas`, `--substituir`, `--local` |
| `atualizar_motor.py` | troca a versão do motor no `atlas.toml` e nos workflows | `--versao vX.Y.Z`, `--local` |
| `instalar_ganchos.py` | instala o gancho de pre-push com o validador | `--local` |
| `indicadores.py` | mostra os indicadores e as lacunas, com o motivo provável, no terminal | `--tema`, `--local` |
| `mapas.py` | gera só os mapas | `--tema`, `--local` |
| `serie_historica.py` | refaz a série dos indicadores a partir dos retratos no Git | `--saida <csv>`, `--local` |
| `novo_local.py` | cria o repositório de um município novo | `--nome`, `--ibge`, `--uf`, `--slug`, `--destino`, `--baixar`, `--git`, `--organizacao`, `--privado`; sem rede: `--sem-rede --relacao --bbox= --sede-bbox= --wikidata` |

Variáveis de ambiente: `ATLAS_MOTOR_CACHE` (pasta do cache de versões), `ATLAS_MOTOR_ATUAL=1` (o mesmo que `--motor-atual`), `ATLAS_VERSAO` (texto da versão na capa; o CI usa a tag).

## Workflows do município

| Workflow | Quando | O que faz |
|---|---|---|
| *Verificar* | todo PR e push na `main` | valida e constrói o site |
| *Atualizar dados do OSM* | dia 1 de cada mês (horário próprio do município) ou manual | baixa o retrato, valida e abre um PR se algo mudou |
| *Publicar atlas* | dia 5 de cada mês, tags `v*` ou manual (versão, dados atuais, destino) | gera site e PDF; publica no Pages (ou só artefato); em tags, edição numerada e release |
