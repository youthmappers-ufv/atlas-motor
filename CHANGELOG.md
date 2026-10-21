# Mudanças do atlas-motor

Versões no formato `vMAIOR.MENOR`:

- **MENOR** (v1.0 → v1.1): compatível. Novos indicadores, temas no catálogo, correções. O município atualiza só a versão (`scripts/atualizar_motor.py`).
- **MAIOR** (v1.x → v2.0): exige mudança nos repositórios dos municípios (formato do `atlas.toml`, do `temas.toml`, dos dados ou dos textos). A entrada diz o que fazer.

Cada versão é uma tag no `main`, criada só com o workflow *Testes do motor* verde. Os municípios escolhem quando atualizar; uma edição publicada continua reproduzível com a versão que a gerou.

## v1.0 — 2026-10-21

Primeira versão, separada do repositório de Rio Paranaíba.

- Catálogo de 9 pranchas (`catalogo/temas.toml`), consultas Overpass e esquemas de dados levantados em campo e de eventos culturais.
- Scripts: `baixar_osm.py` (retrato do OSM), `validar.py` (integridade), `indicadores.py` (completude C_t e Q_t, indicadores internos), `mapas.py`, `construir.py` (monta o livro e renderiza site e PDF).
- Manutenção: `novo_local.py` (repositório de município novo pelo código IBGE), `ativar_tema.py`, `atualizar_motor.py`.
- Modelo do livro Quarto (`livro/`) e modelo de repositório municipal (`modelo-local/`).
- Workflows reutilizáveis: verificar, atualizar dados (PR mensal) e publicar (site e PDF em `youthmappers-ufv/atlas/<slug>/`).
