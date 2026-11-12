# Duas fontes: OpenStreetMap e base oficial

Toda prancha do atlas mostra os dados do **OpenStreetMap**. Quando existe uma base oficial para o tema, ela entra como **comparação**, nunca no lugar deles: o atlas mede o mapa aberto, e a base oficial é a régua. As bases oficiais servem só para conferência; nada é copiado delas para o OpenStreetMap.

## O que aparece na prancha

Na mesma ordem no site e no PDF:

1. **O tema no OpenStreetMap**: mapa (interativo no site, estático no PDF) e indicadores internos (total, nome, endereço, extensão, área).
2. **Mapa de comparação**, com três símbolos:
   - círculo cheio: item **nas duas fontes**;
   - círculo vazado: objeto **só no OpenStreetMap**;
   - losango vermelho numerado: item **só na base oficial** (lacuna do mapa). O número é o mesmo da tabela.
3. **Quadro-resumo**, igual em todas as pranchas: itens na base oficial, objetos no OpenStreetMap, nas duas, só na oficial, só no OpenStreetMap e a **cobertura do mapa** (nas duas ÷ base oficial).
4. **Só na base oficial**: tabela numerada, com o motivo provável de cada lacuna, para orientar a conferência em campo.
5. **Só no OpenStreetMap**: objetos sem item na base. Podem ser novos, estar fora do cadastro ou ser erro no mapa; a tabela leva ao objeto no OpenStreetMap.
6. **Fontes**: as duas, cada uma com a sua data (retrato do OpenStreetMap e data de acesso à base).

A página inicial traz a **síntese**: uma linha por prancha, com os objetos no OpenStreetMap e, onde há base oficial, quantos itens dela foram encontrados no mapa.

## Um dado só para o site e para o PDF

Na construção, o motor junta as duas fontes num arquivo por tema, publicado em *Dados para download*:

| Arquivo | Conteúdo |
|---|---|
| `<tema>-comparacao.geojson` | pontos com `situacao` (`ambas`, `so_oficial`, `so_osm`), número da lacuna, código e nome oficiais, objeto do OSM e motivo provável |
| `<tema>-comparacao.csv` | o mesmo em planilha, inclusive os itens oficiais sem coordenada |

Dele saem o mapa estático do PDF, o mapa interativo do site e as tabelas; por isso os dois produtos nunca divergem. Da base oficial são publicados só código, nome e situação de cada item.

## O que a base cobre (`filtro_osm`)

O tema costuma ser mais largo que a base. A prancha de Educação traz escolas, creches e ensino superior; o Catálogo de Escolas do INEP só lista a educação básica. Para que a universidade não apareça como "só no OpenStreetMap", o `fonte.toml` da base diz o que ela cobre:

```toml
filtro_osm = ["amenity=school|kindergarten|childcare"]
```

Cada regra é `chave=valor`, com alternativas separadas por `|`; só a chave (`"healthcare"`) aceita qualquer valor; basta uma regra casar. Os objetos fora do filtro continuam no mapa do tema e nos indicadores, mas não entram na comparação, e o quadro-resumo diz quantos são. Sem `filtro_osm`, todos os objetos do tema entram.

## Modos de comparação

O `fonte.toml` da base diz o modo (`comparacao`); sem ele, vale `itens`.

| Modo | Quando se aplica | O que a prancha mostra |
|---|---|---|
| `itens` | a base lista objetos com coordenada (INEP, CNES) | o descrito acima: cada item nas duas fontes, só na oficial ou só no OpenStreetMap |
| `contagem` | a base dá totais por unidade territorial (CNEFE: endereços por setor censitário) | mapa dos setores na cor da razão OpenStreetMap ÷ oficial (cinco classes), quadro com os totais e a razão, e a tabela dos setores da maior falta para a menor |
| `nomes` | a base é uma lista de nomes (logradouros da Base de Faces do IBGE) | mapa das faces na cor da situação do nome (nas duas, só na oficial, sem nome na base), quadro, a tabela dos nomes oficiais que faltam no mapa (com a grafia parecida, quando há) e a lista dos nomes só no OpenStreetMap |

No modo `contagem`, o `fonte.toml` aponta a pasta das unidades (`unidades = "setores"`), as colunas (`[colunas] unidade`, `total`) e os rótulos do quadro (`rotulo_oficial`, `rotulo_osm`). Cada objeto do OpenStreetMap é contado no setor em que o seu ponto representativo cai. Endereço não é edificação (um prédio tem vários), e por isso a razão é uma aproximação: serve para ordenar os setores por falta, não como medida exata.

No modo `nomes`, os nomes são comparados sem acento, sem maiúsculas e com as abreviações usuais por extenso (R., Av., Dr., Prof., Cel.); um nome oficial sem igual no mapa, mas com um parecido, ganha a pista "conferir a grafia". O `fonte.toml` pode apontar as geometrias de apoio (`geometrias = "faces.geojson"`), usadas só para desenhar o mapa.

## Baixar as bases

`scripts/baixar_bases.py` baixa e prepara as bases federais que o motor conhece, a partir do código IBGE e da UF do `atlas.toml`:

```
python ../atlas-motor/scripts/baixar_bases.py                # todas
python ../atlas-motor/scripts/baixar_bases.py --base cnes    # só uma (pode repetir)
```

| Base | Fonte | O que grava em `dados/oficiais/` | Prancha |
|---|---|---|---|
| `cnes` | API de dados abertos do Ministério da Saúde | `cnes/estabelecimentos.csv`: estabelecimentos ativos, com código, nome fantasia, tipo, esfera, endereço e coordenada | Saúde (`itens`) |
| `setores` | Malha de setores do Censo 2022 (IBGE), arquivo da UF | `setores/setores.geojson`: os setores do município | unidades da contagem |
| `cnefe` | CNEFE do Censo 2022 (IBGE), arquivo do município | `cnefe/enderecos-por-setor.csv`: endereços por setor e por espécie | Edificações (`contagem`) |
| `faces` | Base de Faces de Logradouros 2022 (IBGE), arquivo da UF | `faces/logradouros.csv` e `faces/faces.geojson` | Logradouros (`nomes`) |

Só o recorte do município entra no repositório, e só o que a comparação usa: do CNES não saem razão social, CNPJ ou CPF, telefone nem e-mail; do CNEFE saem só as contagens, nenhum endereço. Os arquivos originais ficam em `~/.cache/atlas-motor/bases` (os da UF servem a todos os municípios do estado; setores e faces de Minas Gerais somam cerca de 300 MB). `setores` deve vir antes de `cnefe`: cada endereço é contado no setor da malha publicada em que a sua coordenada cai, porque o código de setor do CNEFE é o da coleta e nem sempre existe na malha.

O Catálogo de Escolas do INEP continua a ser baixado à mão do painel do órgão e preparado com `preparar_base.py`.

## Como a correspondência é feita

Um item oficial corresponde a um objeto do OpenStreetMap quando está a até `completude.distancia_max_m` dele e os nomes são semelhantes (`completude.similaridade_min`), cada objeto valendo para um item só. A distância é medida **até o objeto**: zero se a coordenada oficial cai dentro do polígono; senão, até a borda. Detalhes e motivos das lacunas: `scripts/indicadores.py`.
