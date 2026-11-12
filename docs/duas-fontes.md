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

| Modo | Quando se aplica | Situação |
|---|---|---|
| `itens` | a base lista objetos com coordenada (INEP, CNES, Censo SUAS, Conab) | **implementado**: é o descrito acima |
| `contagem` | a base dá totais por unidade territorial (CNEFE: endereços por setor) | previsto: razão OSM ÷ oficial por unidade, em mapa coroplético |
| `extensao` | a base é uma malha de linhas ou áreas (faces de logradouro, distritos) | previsto: comprimento ou área no OSM ÷ oficial por unidade |

Os modos `contagem` e `extensao` dependem de carregar as bases correspondentes e a malha de unidades (setores ou distritos); até lá, as pranchas de Edificações, Logradouros e Bairros usam só indicadores internos.

## Como a correspondência é feita

Um item oficial corresponde a um objeto do OpenStreetMap quando está a até `completude.distancia_max_m` dele e os nomes são semelhantes (`completude.similaridade_min`), cada objeto valendo para um item só. A distância é medida **até o objeto**: zero se a coordenada oficial cai dentro do polígono; senão, até a borda. Detalhes e motivos das lacunas: `scripts/indicadores.py`.
