# Manutenção

Rotinas da coordenação do atlas: quem revisa e mescla PRs, lança versões do motor, abre e encerra municípios. Configuração inicial dos repositórios no GitHub: [Configuração do GitHub](configuracao-github.md).

## Todo mês

| Quando | O quê | Como |
|---|---|---|
| dia 1 (automático) | retrato do OSM de cada município | o workflow *Atualizar dados do OSM* abre um PR; revise a diferença (objetos novos ou sumidos fazem sentido?) e mescle com *Verificar* verde. Sem PR = nada mudou no mapa. |
| dia 5 (automático) | publicação | o workflow *Publicar atlas* gera site e PDF a partir da `main`; confira se terminou verde e abra o site. |
| ao longo do mês | PRs da equipe | revise conteúdo e privacidade (só dados públicos), confira *Verificar* verde e mescle; ninguém mescla o próprio PR. |
| fim do mês | falhas | olhe a aba *Actions* de cada município: falha no Overpass costuma passar sozinha no mês seguinte; falha repetida, abra issue. |

## A cada versão do motor

Procedimento completo no [CONTRIBUTING.md](../CONTRIBUTING.md#publicar-uma-versão). Resumo:

1. Na `main` do motor, com *Testes do motor* verde: decida o tipo (correção, menor, maior; em pré-lançamento `v0.y.z`, uma versão menor pode exigir mudança nos municípios e o CHANGELOG diz qual).
2. Atualize `VERSAO`, `CITATION.cff` e `CHANGELOG.md`; commit `[VERSAO] vX.Y.Z`, tag `vX.Y.Z` e push da tag. As tags são protegidas: não podem ser movidas nem apagadas.
   Release no GitHub (e DOI, com o Zenodo): automático só em versão maior (`vX.0.0`); as demais, à mão em *Actions* > *Release* > *Run workflow*, quando a versão merecer um DOI próprio (por exemplo, citada num artigo).
3. **Canário primeiro:** no município canário, `atualizar_motor.py --versao vX.Y.Z` num PR e rode à mão os três workflows (*Verificar*, *Atualizar dados*, *Publicar atlas*). Com tudo verde, a versão está liberada.
4. **Demais municípios:** um PR de atualização em cada um (`[CONFIG] Motor vX.Y.Z`), seguindo as instruções de migração do CHANGELOG, se houver; até o ciclo mensal seguinte.
5. Registre as métricas da versão e as decisões de arquitetura no registro de pesquisa do projeto (fora deste repositório).

## Município novo

1. Conferir com a prefeitura: termo de parceria (inclui o uso de dados públicos, a publicação aberta e, se for o caso, o uso da marca), pessoas que terão acesso.
2. `python atlas-motor/scripts/novo_local.py --nome "<Nome>" --ibge <código> --baixar --git` (sem parceria: `--privado`).
3. Conferir `atlas.toml` (principalmente `sede_bbox`: o recorte dos mapas da sede) e o primeiro retrato.
4. Criar o repositório e configurar Pages, proteções e acesso: [Configuração do GitHub](configuracao-github.md#para-cada-município-público).
5. Primeira publicação e conferência do site; anotar o município no registro de pesquisa do projeto.

## Revisar um PR de município

- **Privacidade:** nada de nomes de pessoas, telefones, e-mails, CPF, fotos de pessoas identificáveis, anotações brutas de campo. O validador acusa os padrões mais comuns, não tudo.
- **Bases oficiais:** `fonte.toml` completo (órgão, URL, data de acesso, licença); filtrada para o município; nenhuma cópia para o OSM.
- **Textos:** dizem o que o mapa mostra e o que falta, sem afirmar o que os dados não sustentam; mantêm a atribuição ao OSM.
- **Imagens próprias:** autorização e licença; tamanho razoável.
- **Configuração:** mudança em `atlas.toml` ou na versão do motor só em PR próprio.

## Incidente: dado pessoal publicado

Se um dado pessoal entrou num repositório público (commit, issue, PR):

1. **Na hora:** apague ou edite a issue ou o comentário; num PR ainda aberto, peça um commit que remova o dado e, antes de mesclar, reescreva a branch para tirá-lo do histórico.
2. **Já na `main`:** o dado continua no histórico. Reescreva o histórico do repositório (`git filter-repo` ou `git filter-branch`, removendo o arquivo ou trocando o texto), force o push e peça a todos que clonem de novo. Peça ao suporte do GitHub a limpeza do cache de commits antigos.
3. Avise a pessoa cujo dado foi exposto e registre o incidente (data, o que, como foi resolvido) no registro do projeto.
4. Veja se uma regra nova no validador evitaria a repetição.

## Problemas de infraestrutura

- **Overpass fora do ar ou lento:** o motor tenta os servidores de `[overpass]` em ordem. Se um servidor sair do ar de vez, atualize a lista no `modelo-local/atlas.toml` (municípios novos) e avise os municípios.
- **Minutos de Actions:** repositórios públicos não têm limite; os privados (canário) dividem 2.000 minutos por mês na organização. Acompanhe em *Settings* > *Billing* da organização.
- **Quarto ou TinyTeX quebrou no CI:** a versão do Quarto é fixada nos workflows do motor; atualizar é uma versão de correção do motor, testada no canário.
- **Pages fora do ar:** veja *Settings* > *Pages* do município e a aba *Actions*; republique com o botão *Run workflow* do *Publicar atlas*.

## Encerrar ou transferir

- **Transferir para a prefeitura:** [Configuração do GitHub](configuracao-github.md#transferir-para-a-prefeitura).
- **Encerrar um município:** arquive o repositório (*Settings* > *Archive*); o site fica no ar até o Pages ser desligado. Anote no registro do projeto.
- **Canário que vira parceiro:** passa a produção (repositório público, `hospedagem = "pages"`); defina outro canário ou use o município de exemplo dos testes.

## Checklist semestral

- [ ] Versões do motor em uso por município (todas recentes?).
- [ ] Bases oficiais com `data_acesso` de mais de um ano: atualizar.
- [ ] Acessos: quem saiu da equipe ou da prefeitura sai dos repositórios.
- [ ] Links dos sites e PDFs publicados funcionando.
- [ ] Issues paradas há mais de três meses: fechar ou retomar.
- [ ] Documentação ainda condiz com o motor (este diretório `docs/`).
