# Mudanças do atlas-motor

Versionamento semântico, `vMAIOR.MENOR.CORREÇÃO`:

- **CORREÇÃO** (v1.2.0 → v1.2.1): conserto sem mudança de comportamento esperado.
- **MENOR** (v1.2 → v1.3): compatível. Novos indicadores, temas no catálogo, scripts. O município atualiza só a versão (`scripts/atualizar_motor.py`).
- **MAIOR** (v1 → v2): exige mudança nos repositórios dos municípios (formato do `atlas.toml`, do `temas.toml`, dos dados ou dos textos). A entrada diz o que fazer.

**Pré-lançamento (`v0.y.z`).** Enquanto o motor não é lançado oficialmente, qualquer versão MENOR pode exigir mudança nos municípios; a entrada diz quando. **`v1.0.0` é o lançamento oficial**, e só a partir dele vale a garantia de compatibilidade dentro da mesma versão MAIOR. Critérios propostos para o lançamento, a confirmar pela coordenação:

- licença definida e repositórios públicos no GitHub;
- CI verde no GitHub (testes do motor e verificação, atualização e publicação de um município);
- primeiro atlas de Rio Paranaíba publicado pelo workflow, com pelo menos uma base oficial carregada (INEP);
- `novo_local.py` usado para um segundo município, de ponta a ponta.

Cada versão é uma tag no `main`, criada só com o workflow *Testes do motor* verde. Os municípios escolhem quando atualizar; uma edição publicada continua reproduzível com a versão que a gerou.

As duas primeiras versões foram numeradas inicialmente como v1.0 e v1.1 e renumeradas para v0.1.0 e v0.2.0 antes de qualquer publicação.

## v0.2.1 — 2026-10-21

Correção, a partir do teste com um segundo município (São Gotardo). Compatível: `atualizar_motor.py --versao v0.2.1`; nos municípios já criados, trocar à mão o horário dos agendamentos (ver abaixo).

- `novo_local.py` dá a cada município hora (8h a 11h UTC) e minuto próprios nos agendamentos de `atualizar-dados.yml` e `publicar.yml`, tirados do slug; antes, todos baixavam do Overpass e publicavam no mesmo minuto. Rio Paranaíba: `25 8`; São Gotardo: `7 11`.
- `publicar.yml`: segunda tentativa, depois de uma espera aleatória, se o push no `gh-pages` for recusado porque outro município publicou ao mesmo tempo (a `concurrency` não vale entre repositórios).
- `baixar_osm.py`: User-Agent `atlas-motor`, não mais o nome do município-piloto.

## v0.2.0 — 2026-10-21

Compatível com v0.1.0: basta `atualizar_motor.py --versao v0.2.0`.

- Registro para pesquisa e publicações (`pesquisa/`): decisões de arquitetura, diário, ideias de publicação, municípios atendidos e métricas do motor por versão.
- `scripts/serie_historica.py`: série histórica dos indicadores de um município, refeita a partir dos retratos versionados no Git.
- `scripts/metricas_motor.py`: métricas do software, registradas a cada versão (o teste cobra).
- Esquema `atividades` no catálogo (mapatonas, oficinas, campo, reuniões com parceiros; só números agregados) e `atividades.csv` no modelo municipal. Municípios existentes podem criar o arquivo com o cabeçalho do esquema.
- `ler_temas` aceita o formato antigo do `temas.toml` (lista `[[tema]]`), para a série histórica atravessar a migração para o motor.
- `CITATION.cff` para citar o software.

## v0.1.0 — 2026-10-21

Primeira versão, separada do repositório de Rio Paranaíba.

- Catálogo de 9 pranchas (`catalogo/temas.toml`), consultas Overpass e esquemas de dados levantados em campo e de eventos culturais.
- Scripts: `baixar_osm.py` (retrato do OSM), `validar.py` (integridade), `indicadores.py` (completude C_t e Q_t, indicadores internos), `mapas.py`, `construir.py` (monta o livro e renderiza site e PDF).
- Manutenção: `novo_local.py` (repositório de município novo pelo código IBGE), `ativar_tema.py`, `atualizar_motor.py`.
- Modelo do livro Quarto (`livro/`) e modelo de repositório municipal (`modelo-local/`).
- Workflows reutilizáveis: verificar, atualizar dados (PR mensal) e publicar (site e PDF em `youthmappers-ufv/atlas/<slug>/`).
