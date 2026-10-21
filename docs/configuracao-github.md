# Configuração do GitHub

Feita pelo coordenador. A organização `youthmappers-ufv` está no plano **gratuito**, o que explica três pontos do desenho:

- repositório privado **não publica GitHub Pages**: o site sai num repositório público só de saída (`atlas`), que recebe o resultado gerado;
- repositório privado **não tem proteção de branch**: o CI roda em todo PR, mas não dá para bloquear o merge sem ele. A regra combinada é só mesclar com *Verificar* verde e revisão da coordenação;
- workflows reutilizáveis ficam num repositório **público** (`atlas-motor`), para que os repositórios privados dos municípios possam chamá-los.

Se a organização obtiver o plano Team (há benefício para professores pelo GitHub Education), dá para exigir o *Verificar* antes do merge; o restante não muda.

## Uma vez: motor e publicação

1. **`youthmappers-ufv/atlas-motor`** (público): crie vazio, escolha a licença (veja o README) e faça o push da `main` e das tags (versões `v0.x.y` de pré-lançamento; `v1.0.0` é o lançamento oficial). Em *Settings* > *Actions* > *General* > *Access*, nada a mudar (repositório público).
2. **`youthmappers-ufv/atlas`** (público, só saída):
   - README dizendo que o conteúdo é gerado automaticamente a partir dos repositórios dos municípios e que correções vão para o mapa (OSM) ou para o programa;
   - branch `gh-pages` com um `index.html` simples listando os municípios (`/rio-paranaiba/`, `/sao-gotardo/`, …);
   - *Settings* > *Pages*: publicar a partir de **gh-pages**, `/ (root)`. Endereço: `https://youthmappers-ufv.github.io/atlas/<slug>/`.
   - Ninguém edita à mão; só os workflows *Publicar atlas* dos municípios escrevem nele, cada um na sua pasta.
3. **Permissão base da organização:** *Settings* > *Member privileges* > *Base permissions* = **No permission**, para que membros só vejam os repositórios municipais a que forem adicionados. Confira se isso não afeta outros repositórios da organização. Donos (*owners*) veem tudo: mantenha como dono só a coordenação.

## Para cada município

1. Gere o repositório local: `python atlas-motor/scripts/novo_local.py --nome "<Nome>" --ibge <código> --baixar --git`. Confira o `atlas.toml` (`sede_bbox`, `registro`).
2. Crie `youthmappers-ufv/atlas-<slug>`, **privado** e vazio, e faça o push.
3. **Acesso:** *Settings* > *Collaborators and teams*:
   - estudantes do município: **Write** (abrem branches e PRs; quem mescla é a coordenação);
   - servidores da prefeitura parceira: **Triage** (leem tudo, abrem e comentam issues, sem alterar arquivos) ou **Write**, se forem contribuir com dados por PR, conforme o termo de parceria;
   - pessoas de um município não precisam ver os outros.
4. *Settings* > *Actions* > *General*:
   - *Workflow permissions*: **Read and write permissions**;
   - marque **Allow GitHub Actions to create and approve pull requests** (PR mensal de dados).
5. *Settings* > *General*: deixe só **Allow merge commits** (preserva os commits pequenos de cada PR) e marque *Automatically delete head branches*.
6. **Chave de publicação** (uma por município, com acesso só ao repositório `atlas`):

   ```bash
   ssh-keygen -t ed25519 -C "publicar atlas-<slug>" -N "" -f atlas-<slug>
   ```

   - `atlas-<slug>.pub` → `youthmappers-ufv/atlas` > *Settings* > *Deploy keys* > *Add deploy key* (título `atlas-<slug>`), com **Allow write access**;
   - `atlas-<slug>` (privada) → `youthmappers-ufv/atlas-<slug>` > *Settings* > *Secrets and variables* > *Actions*, segredo **`ATLAS_CHAVE_PUBLICACAO`**;
   - apague os dois arquivos do computador.
7. **Primeira publicação:** rode *Verificar* e depois *Publicar atlas* pelo botão (versão `main`, destino `principal`). Acrescente o município ao `index.html` do repositório `atlas`.

## Retirar um município

Remova a deploy key dele no repositório `atlas` (a publicação para) e arquive o repositório municipal. A pasta publicada continua no ar até ser apagada da branch `gh-pages`.

## Custos

Repositórios privados do plano gratuito somam 2.000 minutos de Actions por mês para a organização inteira. Por município, o uso previsto é de cerca de 30 a 60 minutos por mês (verificação por PR, um retrato e uma ou duas publicações; a com PDF é a mais demorada, por instalar o TinyTeX). Com muitos municípios, acompanhe em *Settings* > *Billing*; os testes do próprio motor não contam (repositório público).
