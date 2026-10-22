# Novos temas

Como um tema novo (ex.: esportes e lazer, segurança, abastecimento de água) entra no **catálogo comum** e chega aos atlas dos municípios. Um assunto que interessa a um município só não precisa passar por aqui: vira uma [prancha própria](pranchas.md#prancha-própria-do-município).

## Visão geral

```
issue "Novo tema" no motor → definição (etiquetas, consulta, mapa, indicadores, base oficial)
  → teste num município (prancha própria ou branch do motor) → PR no motor (catálogo + consulta)
  → versão MENOR do motor → canário → municípios atualizam e abrem a prancha
```

Um tema novo **não exige código**: o catálogo (`catalogo/temas.toml`) e uma consulta (`catalogo/consultas/`) bastam. Só um tipo novo de indicador ou de mapa exige mudar o motor (ver o fim deste guia).

## 1. Quando um tema entra no catálogo

Critérios, conferidos pela coordenação na issue:

- **Interesse comum:** útil a mais de um município ou ao programa (relatórios, comparação regional).
- **Mapeável no OSM:** os objetos do tema existem no OpenStreetMap com etiquetas estáveis e documentadas na [wiki do OSM](https://wiki.openstreetmap.org/wiki/Map_features), e a equipe consegue conferi-los em campo.
- **Dados públicos:** o tema não expõe pessoas (nada de residências identificadas, dados de saúde individuais).
- **Base oficial (desejável):** se existir uma lista oficial nacional e aberta (como o INEP para escolas e o CNES para saúde), o tema ganha o indicador de completude.
- **Não duplica** um tema existente; se sobrepõe, prefira ampliar a consulta do tema existente.

Um bom caminho é começar como prancha própria num município, ver se funciona e então propor o tema ao catálogo com a experiência em mãos.

## 2. Proposta

Abra uma issue no `atlas-motor` com o modelo **Novo tema** e preencha: assunto, para que serve, etiquetas do OSM, base oficial (se houver) e municípios interessados. A discussão define os campos abaixo.

## 3. Definição

### Identificação

| Campo | Regra | Exemplo |
|---|---|---|
| `id` | minúsculas, sem acento, palavras separadas por hífen; vira nome de arquivo e não muda depois | `esporte-lazer` |
| `numero` | o próximo livre abaixo de 20 (de 20 em diante são as pranchas próprias); não reaproveite números | `10` |
| `titulo` | curto, como aparece no sumário | `Esporte e lazer` |

### Etiquetas e consulta

1. Levante as etiquetas na wiki do OSM e confira o uso real no Brasil no [taginfo](https://taginfo.openstreetmap.org/).
2. Teste no [Overpass Turbo](https://overpass-turbo.eu/) sobre um município conhecido: os objetos que aparecem são os esperados? Falta algo comum? Vem lixo?
3. Escreva `catalogo/consultas/<id>.overpassql`, com um comentário de cabeçalho e `{{bbox}}` em cada linha (o motor troca pela caixa do município e depois recorta pelo limite):

   ```
   // Prancha 10 — Esporte e lazer: quadras, campos, ginásios, academias ao ar livre, praças.
   (
     nwr({{bbox}})[leisure~"^(pitch|sports_centre|stadium|fitness_station|playground|park)$"];
     nwr({{bbox}})[sport];
   );
   ```

   Prefira `nwr` (nós, linhas e relações) e filtros por valor exato ou expressão ancorada (`^...$`). Evite consultas muito amplas (ex.: todo `building`): o retrato fica pesado e o Overpass recusa.

### Mapa

| Campo | Valores | Como escolher |
|---|---|---|
| `recorte` | `municipio`, `sede`, `ambos` | onde o tema acontece: no território todo, na área urbana ou nos dois |
| `mapa` | `pontos`, `linhas` | `pontos` para objetos (escolas, praças), desenhados sobre as vias de fundo; `linhas` quando o próprio tema é uma rede (vias, estradas rurais) |
| `cor` | `#RRGGBB` | contraste com o fundo bege claro do mapa (`#F4F1E8`) e diferente dos temas próximos; cores do catálogo: azul `#304068`, bordô `#7A1C1C`, dourado `#BC9C38`, verde `#2E7D32`, marrom `#6D4C41`, grafite `#303030` |

As cores dos mapas são do catálogo, não da identidade visual da prefeitura: o mesmo tema tem a mesma cor em todos os atlas, o que facilita comparar.

### Indicadores

Todo tema tem o total de objetos e a proporção com nome. Acrescente em `indicadores`:

| Valor | O que mede | Para temas de |
|---|---|---|
| `"servico"` | proporção com endereço (rua) e com horário de funcionamento | serviços e equipamentos que o público procura |
| `"vias"` | comprimento total e proporção com tipo de pavimento | redes viárias |

### Base oficial e completude (opcional)

Se houver base oficial, defina em `referencia` o nome padrão da pasta que cada município cria em `dados/oficiais/` (ex.: `"inep"`). O motor mede a completude C_t (itens oficiais com correspondente no mapa, a até 150 m e com nome semelhante) e a qualidade Q_t (correspondidos com nome e endereço), e lista as lacunas. A base precisa ter, por item, um código, um nome e coordenadas; o formato do `fonte.toml` está na [Referência](referencia.md#base-oficial-fontetoml). Documente no PR de onde baixar a base e como filtrá-la para um município. Sem base oficial: `referencia = "interno"`.

### Dados levantados pela equipe (opcional)

Se o tema pede um levantamento próprio (ex.: estado de conservação de quadras), crie um esquema em `catalogo/esquemas/` (formato na [Referência](referencia.md#esquemas-de-dados-curados)) e um CSV vazio com o cabeçalho em `modelo-local/dados/curados/` e em `testes/exemplo/dados/curados/`. Só dados públicos.

## 4. Teste

Antes do PR, prove o tema num município real:

- **Como prancha própria** (sem mexer no motor): consulta em `consultas/` do município e `[tema.<id>]` com número 20+ no `temas.toml` ([Pranchas](pranchas.md#prancha-própria-do-município)); ou
- **Numa branch do motor**: com o tema no catálogo, rode no município (os dois últimos comandos com `--motor-atual`, para usar o motor da branch em vez da versão declarada pelo município):

  ```bash
  python ../atlas-motor/scripts/ativar_tema.py esporte-lazer
  python ../atlas-motor/scripts/baixar_osm.py --tema esporte-lazer --motor-atual
  python ../atlas-motor/scripts/construir.py --renderizar todos --motor-atual
  ```

  Não commite essa mudança no município: ela só vale depois da versão do motor que traz o tema.

Confira no site e no PDF: o mapa é legível (cor, quantidade de objetos)? Os indicadores fazem sentido? O retrato tem tamanho razoável (`dados/osm/<id>.geojson`)?

## 5. PR no motor

Na mesma branch, um commit por passo:

1. `catalogo/temas.toml`: o tema com todos os campos (`id`, `numero`, `titulo`, `consulta`, `referencia`, `recorte`, `cor`, `mapa`, `indicadores`);
2. `catalogo/consultas/<id>.overpassql`;
3. esquema e CSVs de modelo, se houver;
4. entrada no `CHANGELOG.md` (versão MENOR).

O teste `CatalogoDeTemas` confere que todo tema tem os campos, valores válidos, consulta existente, id e número únicos e número abaixo de 20. Rode `python -m unittest discover -s testes` e `python scripts/construir.py --local testes/exemplo --renderizar html`.

## 6. Versão e adoção

1. A coordenação lança a versão MENOR (`CONTRIBUTING.md`, seção "Publicar uma versão").
2. O canário atualiza primeiro e abre o tema.
3. Cada município, quando quiser: `atualizar_motor.py --versao vX.Y.Z` num PR, depois `ativar_tema.py <id>`, `baixar_osm.py --tema <id>` e o texto da prancha.

Um tema novo no catálogo não aparece em atlas nenhum até o município abri-lo.

## Promover uma prancha própria ao catálogo

Quando a prancha própria de um município vira tema do catálogo:

1. No motor: o tema entra no catálogo com o **mesmo `id`** e um número abaixo de 20; a consulta vai para `catalogo/consultas/`.
2. No município que já tinha a prancha, depois de atualizar o motor: no `temas.toml`, deixe em `[tema.<id>]` só a `situacao` (e ajustes, se houver), apague `consultas/<id>.overpassql` e renomeie o arquivo da prancha para o número novo (`git mv atlas/pranchas/20-<id>.qmd atlas/pranchas/10-<id>.qmd`), ajustando o número no título. O validador acusa a prancha com o número antigo; já uma consulta própria que ficar em `consultas/` continua valendo no lugar da do catálogo, sem aviso, por isso apague-a.

## Mudar um tema existente

- **Consulta:** muda o que entra nos retratos dali em diante; os retratos antigos continuam como foram baixados. Registre no CHANGELOG, porque afeta a série histórica do tema.
- **Indicadores ou referência:** a série histórica é recalculada com o motor atual (`serie_historica.py`), então a mudança vale para o passado também. Registre no CHANGELOG.
- **Cor, recorte, título:** só aparência.
- **`id` e `numero`:** não mudam (são nomes de arquivos em todos os municípios). Um tema que deixa de fazer sentido sai do catálogo numa versão MAIOR, com instrução de migração.

## Quando o tema exige código

Um tipo novo de indicador (ex.: área total de parques) ou de mapa é mudança no motor: em `scripts/indicadores.py` (ou `mapas.py`), um nome novo em `INDICADORES` (ou `MAPAS`) de `scripts/comum.py`, testes em `testes/` e este guia atualizado. Siga o `CONTRIBUTING.md`.
