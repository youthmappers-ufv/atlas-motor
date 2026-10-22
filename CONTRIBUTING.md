# Como mudar o motor

O motor serve a vários municípios ao mesmo tempo; uma mudança aqui chega a todos quando eles atualizarem a versão. Um tema novo no catálogo segue o processo próprio de [docs/novos-temas.md](docs/novos-temas.md); as rotinas da coordenação (versões, canário, municípios novos) estão em [docs/manutencao.md](docs/manutencao.md). Para mudanças de código:

1. **Issue** descrevendo a mudança e para que serve (vale para todos os municípios?). Uma necessidade de um município só costuma caber no repositório dele (consulta ou esquema próprio, prancha própria).
2. **Branch** a partir da `main` e **commits pequenos**, um por passo (`[CODIGO] …`, `[CATALOGO] …`, `[LIVRO] …`, `[CI] …`, `[DOC] …`).
3. **Testes:** toda regra nova do validador ganha um teste em `testes/test_validar.py` com o defeito plantado numa cópia do município de exemplo; todo script novo, um teste em `testes/test_scripts.py`. Se a mudança precisar de dados novos no exemplo, ajuste `testes/exemplo/` no mesmo PR.
4. Antes do PR: `python -m unittest discover -s testes` e `python scripts/construir.py --local testes/exemplo --renderizar html`. Para testar a mudança num município real, que declara outra versão do motor, use `--motor-atual` (sem ele, os scripts rodam na versão declarada pelo município).
5. **Pull request** com o workflow *Testes do motor* verde; a coordenação revisa e mescla.

## Publicar uma versão

1. Na `main`, com tudo verde, decida se a versão é de **correção**, **menor** (compatível) ou **maior** (exige mudança nos municípios); veja a política no [CHANGELOG.md](CHANGELOG.md). Até o lançamento oficial (`v1.0.0`), as versões são `v0.y.z`.
2. Atualize `VERSAO`, a `version` e a `date-released` do `CITATION.cff`, e acrescente a entrada no `CHANGELOG.md` (para versão maior, com as instruções de migração).
3. Os testes `test_versao_registrada_no_changelog` e `test_citation_na_versao` falham se algo faltar. A coordenação registra as métricas da versão e as decisões de arquitetura no registro de pesquisa do projeto, que fica fora deste repositório.
4. Commit `[VERSAO] vX.Y.Z`, tag anotada `vX.Y.Z` e push da tag.
5. **Release no GitHub** (workflow *Release*, notas tiradas do CHANGELOG; com o Zenodo ligado, cada release ganha DOI): sai sozinho com a tag de uma **versão maior** (`vX.0.0`, a partir da `v1.0.0`); as versões menores e as correções só ganham release quando alguém pedir, em *Actions* > *Release* > *Run workflow*, informando a tag.
6. Em cada município, num PR próprio: `python ../atlas-motor/scripts/atualizar_motor.py --versao vX.Y.Z`.

## Tags

Nunca mova nem apague uma tag publicada: edições antigas dos municípios dependem dela para serem regeradas.

## Regras de código

- Scripts com `pathlib`, Python 3.11+, só biblioteca padrão, exceto `mapas.py` (matplotlib).
- Todo script recebe o município em `--local` (padrão: a pasta atual) e nunca grava fora dele.
- Nada específico de um município no motor: nomes, coordenadas e textos ficam nos repositórios municipais; o que for comum vai para `catalogo/`, `livro/` ou `modelo-local/`.
- Mudou o formato do `atlas.toml`, do `temas.toml` ou dos dados? É versão maior; atualize `modelo-local/` e o município de exemplo juntos.
