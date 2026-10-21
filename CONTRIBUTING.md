# Como mudar o motor

O motor serve a vários municípios ao mesmo tempo; uma mudança aqui chega a todos quando eles atualizarem a versão. Por isso:

1. **Issue** descrevendo a mudança e para que serve (vale para todos os municípios?). Uma necessidade de um município só costuma caber no repositório dele (consulta ou esquema próprio, prancha própria).
2. **Branch** a partir da `main` e **commits pequenos**, um por passo (`[CODIGO] …`, `[CATALOGO] …`, `[LIVRO] …`, `[CI] …`, `[DOC] …`).
3. **Testes:** toda regra nova do validador ganha um teste em `testes/test_validar.py` com o defeito plantado numa cópia do município de exemplo; todo script novo, um teste em `testes/test_scripts.py`. Se a mudança precisar de dados novos no exemplo, ajuste `testes/exemplo/` no mesmo PR.
4. Antes do PR: `python -m unittest discover -s testes` e `python scripts/construir.py --local testes/exemplo --renderizar html`.
5. **Pull request** com o workflow *Testes do motor* verde; a coordenação revisa e mescla.

## Publicar uma versão

1. Na `main`, com tudo verde, decida se a versão é **menor** (compatível) ou **maior** (exige mudança nos municípios); veja a política no [CHANGELOG.md](CHANGELOG.md).
2. Atualize `VERSAO`, a `version` e a `date-released` do `CITATION.cff`, e acrescente a entrada no `CHANGELOG.md` (para versão maior, com as instruções de migração).
3. Registre as métricas da versão: `python scripts/metricas_motor.py --registrar` (grava em `pesquisa/dados/metricas-versoes.csv`). Se a versão traz uma decisão de arquitetura, acrescente-a em `pesquisa/decisoes/`; anote no `pesquisa/diario.md` o que vale lembrar.
   Os testes `test_versao_registrada_no_changelog`, `test_versao_com_metricas` e `test_citation_na_versao` falham se algo faltar.
4. Commit `[VERSAO] vX.Y`, tag `vX.Y` e push da tag.
5. Em cada município, num PR próprio: `python ../atlas-motor/scripts/atualizar_motor.py --versao vX.Y`.

## Registro para pesquisa

O desenvolvimento do motor é também objeto de pesquisa: decisões, diário, métricas e ideias de publicação ficam em [pesquisa/](pesquisa/README.md). Mudança de arquitetura entra com a sua decisão (`pesquisa/decisoes/NNNN-*.md`, a partir de `0000-modelo.md`) no mesmo PR.

Nunca mova nem apague uma tag publicada: edições antigas dos municípios dependem dela para serem regeradas.

## Regras de código

- Scripts com `pathlib`, Python 3.11+, só biblioteca padrão, exceto `mapas.py` (matplotlib).
- Todo script recebe o município em `--local` (padrão: a pasta atual) e nunca grava fora dele.
- Nada específico de um município no motor: nomes, coordenadas e textos ficam nos repositórios municipais; o que for comum vai para `catalogo/`, `livro/` ou `modelo-local/`.
- Mudou o formato do `atlas.toml`, do `temas.toml` ou dos dados? É versão maior; atualize `modelo-local/` e o município de exemplo juntos.
