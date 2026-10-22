# Configuração do GitHub

Feita pela coordenação, com o [GitHub CLI](https://cli.github.com/) (`gh`) autenticado numa conta dona da organização. A organização `youthmappers-ufv` está no plano **gratuito**; por isso os repositórios dos municípios são **públicos**: só assim têm GitHub Pages, minutos de Actions sem limite e regras de proteção de branch. Repositório privado é exceção (município sem parceria) e só gera o atlas como artefato.

Nos comandos, troque `<cidade>` pelo slug do município (ex.: `rio-paranaiba`).

## Uma vez: motor e organização

1. **`youthmappers-ufv/atlas-motor`** (público): com a licença já definida (MIT, `LICENSE`; textos em CC BY 4.0, veja o README), crie o repositório e envie a `main` e as tags:

   ```bash
   gh repo create youthmappers-ufv/atlas-motor --public --source atlas-motor --remote origin --push
   git -C atlas-motor push origin --tags
   ```

2. **Tags imutáveis:** os municípios chamam o motor pela tag; uma tag movida mudaria edições já publicadas. Regra que impede mover e apagar tags `v*` (ninguém tem dispensa):

   ```bash
   gh api -X POST repos/youthmappers-ufv/atlas-motor/rulesets --input - <<'JSON'
   {"name": "tags-imutaveis", "target": "tag", "enforcement": "active",
    "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
    "rules": [{"type": "update"}, {"type": "deletion"}]}
   JSON
   ```

   Confira em *Settings* > *Rules* > *Rulesets*.
3. **DOI (Zenodo), quando for usar:** em https://zenodo.org, entre com a conta do GitHub, autorize a organização `youthmappers-ufv` e ligue o `atlas-motor` em *GitHub* (lista de repositórios). Daí em diante, cada **release** do GitHub (não cada tag) é arquivado e ganha DOI; o workflow *Release* cria o release sozinho nas versões maiores e, nas outras, à mão. Com o primeiro DOI, acrescente ao README o badge do DOI conceito (aponta sempre para a versão mais recente; o Zenodo mostra o código do badge) e o campo `doi` no `CITATION.cff`. O mesmo vale para um município público, cujos releases são as edições numeradas.
4. **Permissão base da organização:** *Settings* > *Member privileges* > *Base permissions* = **No permission**: membros só escrevem nos repositórios a que forem adicionados. Donos (*owners*) podem tudo: mantenha como dono só a coordenação.

## Para cada município (público)

1. **Repositório local:** `python atlas-motor/scripts/novo_local.py --nome "<Nome>" --ibge <código> --baixar --git`. Confira o `atlas.toml` (`sede_bbox`, `registro`, `publicacao.url`) e o `LICENCAS.md`.
2. **Criar e enviar:**

   ```bash
   gh repo create youthmappers-ufv/atlas-<cidade> --public --source atlas-<cidade> --remote origin --push
   ```

3. **Actions:** permissão de escrita e criação de pull requests (PR mensal de dados):

   ```bash
   gh api -X PUT repos/youthmappers-ufv/atlas-<cidade>/actions/permissions/workflow -f default_workflow_permissions=write -F can_approve_pull_request_reviews=true
   ```

4. **Merge:** só *merge commit* (preserva os commits pequenos de cada PR) e apagar a branch depois:

   ```bash
   gh repo edit youthmappers-ufv/atlas-<cidade> --enable-merge-commit --enable-squash-merge=false --enable-rebase-merge=false --delete-branch-on-merge
   ```

5. **Primeira publicação:** rode *Publicar atlas* (cria a branch `gh-pages`) e, quando terminar, ligue o Pages nela:

   ```bash
   gh workflow run publicar.yml --repo youthmappers-ufv/atlas-<cidade> -f versao=main -f destino=principal
   gh api -X POST repos/youthmappers-ufv/atlas-<cidade>/pages -f "source[branch]=gh-pages" -f "source[path]=/"
   ```

   Endereço: `https://youthmappers-ufv.github.io/atlas-<cidade>/` (o `publicacao.url` do `atlas.toml`).
6. **Proteger a `main`:** a regra exige PR e os dois checks do *Verificar* antes do merge. Cada check se chama `<job do município> / <nome do job no motor>`: `verificar / Validação` e `verificar / Construção do site`. Confira os nomes no último commit da `main` (o push do passo 2 já rodou o *Verificar*); um nome que não existe faz a regra esperar por um check que nunca roda e trava todo PR:

   ```bash
   gh api repos/youthmappers-ufv/atlas-<cidade>/commits/main/check-runs --jq '.check_runs[].name'
   ```

   O `publicar / publicar` que aparece na lista não entra na regra: só roda na `main`, nunca em PR.

   ```bash
   gh api -X POST repos/youthmappers-ufv/atlas-<cidade>/rulesets --input - <<'JSON'
   {"name": "main-protegida", "target": "branch", "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"},
              {"type": "pull_request", "parameters": {"required_approving_review_count": 0,
               "dismiss_stale_reviews_on_push": false, "require_code_owner_review": false,
               "require_last_push_approval": false, "required_review_thread_resolution": false}},
              {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": false,
               "required_status_checks": [{"context": "verificar / Validação"},
                                          {"context": "verificar / Construção do site"}]}}]}
   JSON
   ```

   O PR mensal de dados (aberto pelo workflow) também passa por ela.
7. **Acesso:** *Settings* > *Collaborators and teams*:
   - estudantes do município: **Write** (abrem branches e PRs; quem mescla é a coordenação);
   - servidores da prefeitura parceira: **Triage** (abrem e comentam issues) ou **Write**, se forem contribuir com dados por PR, conforme o termo de parceria.

   Cada pessoa instala o gancho de pre-push no seu clone: `python ../atlas-motor/scripts/instalar_ganchos.py`.

## Município privado (sem parceria)

`novo_local.py ... --privado` grava `publicacao.hospedagem = "artefato"`. Crie o repositório com `--private`, faça os passos 3 e 4 e pule o 5 e o 6 (Pages e regras de branch não existem em repositório privado no plano gratuito). O *Publicar atlas* gera site e PDF como artefato do workflow. Repositórios privados dividem 2.000 minutos de Actions por mês na organização inteira; um município usa cerca de 30 a 60.

## Domínio próprio

Para publicar em `atlas.prefeitura.mg.gov.br`: `publicacao.dominio = "atlas.prefeitura.mg.gov.br"` no `atlas.toml` (o workflow grava o `CNAME` no `gh-pages`) e, no DNS do domínio, um registro `CNAME` para `youthmappers-ufv.github.io`. Depois, em *Settings* > *Pages*, marque *Enforce HTTPS*.

## Transferir para a prefeitura

Quando a prefeitura quiser manter o atlas na organização dela: *Settings* > *General* > *Transfer ownership* (o histórico, as issues e os PRs vão juntos e o GitHub redireciona o endereço antigo). Depois, ajuste `publicacao.url` (ou use domínio próprio), refaça os passos 3 a 6 na organização nova e mantenha os workflows chamando o `atlas-motor`, que continua público.

## Retirar um município

Arquive o repositório (*Settings* > *Archive*). O site continua no ar até o Pages ser desligado.
