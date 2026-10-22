# Pranchas

Uma prancha é o capítulo do atlas sobre um tema. Tem duas partes:

- **o texto da equipe**, em `atlas/pranchas/<nn>-<tema>.qmd` do município: o que o mapa mostra, o que chama atenção, o que falta, o contexto local;
- **as partes geradas pelo motor** a cada construção, a partir do retrato do OSM e das bases oficiais: mapas, legenda, indicadores, lacunas e fonte.

O arquivo `.qmd` é Markdown do [Quarto](https://quarto.org/docs/authoring/markdown-basics.html); o mesmo texto vira a página do site e o capítulo do PDF.

## Abrir, fechar e marcar como publicada

```bash
python ../atlas-motor/scripts/ativar_tema.py educacao                        # abre (em-andamento) e cria o .qmd
python ../atlas-motor/scripts/baixar_osm.py --tema educacao                  # dados do tema
python ../atlas-motor/scripts/ativar_tema.py educacao --situacao publicado   # revisada
python ../atlas-motor/scripts/ativar_tema.py educacao --situacao planejado   # tira do atlas
```

A situação fica no `temas.toml`: `planejado` (fora do atlas), `em-andamento` e `publicado` (as duas aparecem; `publicado` indica que o texto foi revisado). Ao fechar uma prancha, apague também o `.qmd` (o validador acusa erro em prancha que não corresponde a tema ativo).

## A prancha padrão

O `.qmd` criado pelo `ativar_tema.py` tem o título, um parágrafo para a equipe escrever e um include com **tudo** o que o motor gera para o tema:

```markdown
# 3. Educação {.unnumbered}

Texto da equipe.

{{< include ../_gerado/educacao.md >}}
```

O título deve manter o formato `# <número>. <título> {.unnumbered}`: o número é o da prancha no catálogo, e o `{.unnumbered}` evita a numeração automática do Quarto.

## Montar a prancha do seu jeito

O motor gera também cada parte em separado, em `_gerado/<tema>/`:

| Parte | Include | Conteúdo |
|---|---|---|
| mapa do município | `{{< include ../_gerado/educacao/mapa-municipio.md >}}` | figura do município inteiro (largura total) |
| mapa da sede | `{{< include ../_gerado/educacao/mapa-sede.md >}}` | figura da área urbana da sede (largura total) |
| legenda | `{{< include ../_gerado/educacao/legenda.md >}}` | "Pontos cheios: com nome; vazados: sem nome." |
| indicadores | `{{< include ../_gerado/educacao/indicadores.md >}}` | tabela de indicadores (total, nome, endereço, horário, completude) |
| lacunas | `{{< include ../_gerado/educacao/lacunas.md >}}` | itens da base oficial sem correspondente no mapa, com o motivo provável |
| fonte | `{{< include ../_gerado/educacao/fonte.md >}}` | data do retrato e atribuição ao OSM (obrigatória pela licença) |

Uma parte que não se aplica fica vazia (ex.: o mapa da sede de um tema só com recorte do município, as lacunas de um tema sem base oficial); incluí-la não dá erro. Troque o include único pelas partes, na ordem que quiser, com o seu texto entre elas.

> **Atribuição:** mantenha sempre a parte `fonte` (ou outra menção a "© colaboradores do OpenStreetMap") na prancha; a licença do OSM (ODbL) exige.

### Texto entre as partes e seções próprias

```markdown
# 3. Educação {.unnumbered}

As escolas se concentram na sede...

{{< include ../_gerado/educacao/mapa-municipio.md >}}

## Na sede

O que o mapa da sede mostra...

{{< include ../_gerado/educacao/mapa-sede.md >}}
{{< include ../_gerado/educacao/legenda.md >}}

## Indicadores

{{< include ../_gerado/educacao/indicadores.md >}}

{{< include ../_gerado/educacao/fonte.md >}}
```

Seções com `##` aparecem no sumário do site e no do PDF. Use `###` para subdivisões que não precisam ir ao sumário.

### Outro tamanho ou alinhamento de mapa

Os includes de mapa usam largura total. Para outro tamanho, use a figura diretamente, em vez do include:

```markdown
![Educação: sede do município](../_gerado/figuras/educacao-sede.png){width=60% fig-align="center"}
```

As figuras geradas ficam em `_gerado/figuras/<tema>-municipio.png` e `<tema>-sede.png`. A legenda entre colchetes é a do seu texto; mantenha uma descrição do que o mapa mostra.

### Mapas lado a lado

```markdown
::: {#fig-educacao-mapas layout-ncol=2}
![Município](../_gerado/figuras/educacao-municipio.png)

![Sede](../_gerado/figuras/educacao-sede.png)

Escolas no município e na sede
:::
```

O rótulo (`#fig-...`) e a última linha (legenda do conjunto) fazem as subfiguras saírem como (a) e (b); sem eles, as duas ficam como (a).

### Imagens próprias (fotos, croquis, mapas antigos)

Ponha os arquivos em `atlas/pranchas/imagens/` e cite pelo caminho relativo:

```markdown
![Escola conferida em campo, 2027](imagens/escola-campo.jpg){width=50% fig-align="center"}
```

- Formatos: PNG, JPG (com a extensão certa) ou SVG; até alguns MB por imagem (o validador recusa arquivos acima de 25 MB).
- O repositório é público: só imagens que a equipe pode publicar, **sem pessoas identificáveis** sem autorização por escrito, sem placas de veículos, sem interior de casas.
- Imagem de terceiros (mapa antigo do arquivo municipal, foto de jornal): só com licença ou autorização, citada na legenda.

### Deixar uma parte de fora

Basta não incluí-la. Exemplo comum: tirar a tabela de lacunas de uma prancha que ficaria longa demais e citar a lista no texto ou nos dados para download.

### Quadros de destaque

```markdown
::: {.callout-note}
## Em campo
Texto do quadro.
:::
```

Tipos: `callout-note`, `callout-tip`, `callout-warning`, `callout-important`, `callout-caution`. As cores seguem a identidade visual do atlas.

### Tabelas próprias

Tabelas em Markdown simples, com uma linha de legenda opcional:

```markdown
| Distrito | Escolas | Com nome no mapa |
|:--|--:|--:|
| Sede | 7 | 7 |
| Chave Olhos d'Água | 2 | 1 |

: Escolas por distrito, conferência de 2027 {#tbl-distritos}
```

Números de uma tabela própria são da equipe: diga a fonte e a data no texto.

### Referências cruzadas

Dê um rótulo a uma figura ou tabela (`{#fig-sede}`, `{#tbl-distritos}`) e cite com `@fig-sede` ou `@tbl-distritos` no texto. Os rótulos precisam ser únicos no atlas inteiro.

## Ajustes da prancha sem mexer no texto (`temas.toml`)

No `temas.toml` do município, cada tema aberto pode trocar o que vem do catálogo:

```toml
[tema.educacao]
situacao = "em-andamento"
titulo = "Educação e creches"      # título no sumário e na prancha gerada
recorte = "sede"                   # municipio | sede | ambos: quais mapas gerar
referencia = "inep-2027"           # outra pasta em dados/oficiais/ para a completude
cor = "#1B6E3A"                    # cor dos objetos no mapa
```

Os campos e os valores aceitos estão na [Referência](referencia.md#temastoml-município). Mude a cor de um tema do catálogo só com motivo: cores iguais entre municípios facilitam comparar atlas.

## Prancha própria do município

Um assunto que só interessa a um município (ex.: feiras livres, nascentes de uma serra) vira uma prancha própria, sem esperar o catálogo:

1. Escreva a consulta Overpass em `consultas/<id>.overpassql`, restrita ao município com `{{bbox}}`:

   ```
   // Feiras livres
   (
     nwr({{bbox}})[amenity=marketplace];
   );
   ```

2. Declare o tema no `temas.toml`, com número de 20 em diante (os números abaixo de 20 são do catálogo):

   ```toml
   [tema.feiras]
   numero = 20
   titulo = "Feiras livres"
   consulta = "feiras.overpassql"
   situacao = "em-andamento"
   recorte = "sede"
   cor = "#BC9C38"
   mapa = "pontos"
   indicadores = ["servico"]
   ```

3. `python ../atlas-motor/scripts/ativar_tema.py feiras`, `python ../atlas-motor/scripts/baixar_osm.py --tema feiras`, escreva o texto, valide.

Se outros municípios quiserem a mesma prancha, proponha a entrada dela no catálogo: [Novos temas](novos-temas.md).

## Apresentação do atlas (`atlas/index.qmd`)

A primeira página do atlas é do município: apresentação, parcerias, créditos da equipe. Os trechos `{{< include _gerado/edicao.md >}}` (versão e data dos dados e, no site, o botão de baixar o PDF) `{{< include _gerado/pranchas.md >}}` (lista das pranchas) e `{{< include _gerado/citacao.md >}}` (como citar o atlas, no formato da ABNT, com o ano dos dados e o endereço do site) são gerados; mantenha-os. As páginas "Como o atlas é feito" e "Dados para download" vêm do motor e são iguais em todos os atlas.

## Conferir antes do PR

- `python ../atlas-motor/scripts/construir.py --previa` para ver o site enquanto escreve;
- `python ../atlas-motor/scripts/construir.py --renderizar todos` para ver também o PDF (em `_construcao/livro/_site/`), principalmente se mudou tamanho de figuras ou incluiu imagens;
- `python ../atlas-motor/scripts/validar.py` com 0 erros.
