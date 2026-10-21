# Mudanças do atlas-motor

Versões no formato `vMAIOR.MENOR`:

- **MENOR** (v1.0 → v1.1): compatível. Novos indicadores, temas no catálogo, correções. O município atualiza só a versão (`scripts/atualizar_motor.py`).
- **MAIOR** (v1.x → v2.0): exige mudança nos repositórios dos municípios (formato do `atlas.toml`, do `temas.toml`, dos dados ou dos textos). A entrada diz o que fazer.

Cada versão é uma tag no `main`, criada só com o workflow *Testes do motor* verde. Os municípios escolhem quando atualizar; uma edição publicada continua reproduzível com a versão que a gerou.

## v1.1 — 2026-10-21

Compatível com v1.0: basta `atualizar_motor.py --versao v1.1`.

- Registro para pesquisa e publicações (`pesquisa/`): decisões de arquitetura, diário, ideias de publicação, municípios atendidos e métricas do motor por versão.
- `scripts/serie_historica.py`: série histórica dos indicadores de um município, refeita a partir dos retratos versionados no Git.
- `scripts/metricas_motor.py`: métricas do software, registradas a cada versão (o teste cobra).
- Esquema `atividades` no catálogo (mapatonas, oficinas, campo, reuniões com parceiros; só números agregados) e `atividades.csv` no modelo municipal. Municípios existentes podem criar o arquivo com o cabeçalho do esquema.
- `ler_temas` aceita o formato antigo do `temas.toml` (lista `[[tema]]`), para a série histórica atravessar a migração para o motor.
- `CITATION.cff` para citar o software.

## v1.0 — 2026-10-21

Primeira versão, separada do repositório de Rio Paranaíba.

- Catálogo de 9 pranchas (`catalogo/temas.toml`), consultas Overpass e esquemas de dados levantados em campo e de eventos culturais.
- Scripts: `baixar_osm.py` (retrato do OSM), `validar.py` (integridade), `indicadores.py` (completude C_t e Q_t, indicadores internos), `mapas.py`, `construir.py` (monta o livro e renderiza site e PDF).
- Manutenção: `novo_local.py` (repositório de município novo pelo código IBGE), `ativar_tema.py`, `atualizar_motor.py`.
- Modelo do livro Quarto (`livro/`) e modelo de repositório municipal (`modelo-local/`).
- Workflows reutilizáveis: verificar, atualizar dados (PR mensal) e publicar (site e PDF em `youthmappers-ufv/atlas/<slug>/`).
