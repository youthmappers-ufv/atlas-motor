# Arquitetura

O atlas fica em repositórios separados por papel: um **motor** público com o código e um **repositório por município** com os dados e os textos, que publica o próprio site no GitHub Pages. A parte institucional e de pesquisa do programa fica no repositório de documentos do Programa Youthmappers UFV, sem ligação de código.

![Arquitetura dos repositórios do atlas](figuras/arquitetura-repositorios.svg)

| Repositório | Visibilidade | Conteúdo |
|---|---|---|
| `atlas-motor` | público | Catálogo de temas e consultas, esquemas, scripts (retrato do OSM, validação, indicadores, mapas, construção), modelo do livro Quarto, modelo de município (`novo_local.py`), workflows reutilizáveis. Versões `vX.Y.Z`, com tags protegidas contra alteração. |
| `atlas-<cidade>` | **público** (padrão) | `atlas.toml` (identificação, **versão do motor**, publicação), `temas.toml` (pranchas abertas), retratos do OSM, bases oficiais abertas, levantamentos de campo, textos das pranchas e três workflows que só chamam os do motor. Publica o próprio site (branch `gh-pages`). Só dados públicos. |
| `atlas-<cidade>` | privado (exceção) | Mesmo conteúdo, para município sem parceria (por exemplo, um município de teste). Sem GitHub Pages: o atlas sai só como artefato do workflow (`publicacao.hospedagem = "artefato"`). |
| `youthmappers-ufv-docs` | privado | Parte institucional e registro de pesquisa do projeto. |

**Por que assim.** Em repositório público, o plano gratuito do GitHub oferece GitHub Pages, minutos de Actions sem limite e regras de proteção de branch e de tag; cada município fica com um repositório só, sem chave de deploy nem repositório de saída compartilhado. A prefeitura parceira pode assumir o repositório (transferência para a organização dela, com todo o histórico) e publicar onde quiser: GitHub Pages com domínio próprio (`publicacao.dominio`) ou o site gerado, baixado do artefato ou do release. O motor público é chamado pelos workflows dos municípios e evita forks divergentes: uma correção chega a todos pela atualização de versão.

**Versão fixada.** Cada município declara no `atlas.toml` a versão do motor que usa, e os workflows chamam o motor nessa tag (o validador confere que batem; `scripts/atualizar_motor.py` troca as duas juntas). Uma versão nova do motor não muda nada num município até ele atualizar, e uma edição antiga refeita hoje usa o mesmo motor de quando foi feita. As tags `v*` do motor são protegidas por uma regra do repositório: não podem ser movidas nem apagadas.

## Identidade visual

Um arquivo só, o `_brand.yml` (formato do Quarto), define cores, fontes e logos do site e do PDF. O motor traz o tema padrão do programa (`livro/_brand.yml`); um município troca a identidade com `tema/_brand.yml` e os logos ao lado, no próprio repositório. Na construção, o tema do município é posto sobre o padrão; o Quarto aplica o `_brand.yml` no site, e `scripts/tema.py` o traduz para o `tema.tex` do PDF (LaTeX), que o estilo do atlas (`livro/atlas-estilo.tex`) e a capa usam. Nem o estilo do site nem o do PDF definem cores ou fontes próprias: tudo vem do tema. As cores dos mapas são fixas por tema do atlas (leitura cartográfica e comparação entre municípios) e não mudam com a identidade.

## Ciclo mensal de um município

![Ciclo mensal de um município](figuras/ciclo-mensal.svg)

1. **Dia 1 — Atualizar dados:** baixa o retrato do OSM e abre um PR com a diferença.
2. **Verificar:** roda em todo PR (validação de integridade e construção do site). A branch `main` é protegida e só aceita merge com ele verde.
3. **Revisão e merge:** pela coordenação.
4. **Dia 5 — Publicar:** gera site e PDF e publica no `gh-pages` do próprio repositório (ou só como artefato). Tags `v*` no município criam edições numeradas em `edicoes/<tag>/` e um release com o PDF.

Cada workflow roda **no repositório do município** (nos minutos e com as permissões dele), fazendo o checkout do município e do motor (na versão do `atlas.toml`) lado a lado. Hora e minuto dos agendamentos são próprios de cada município, para não sobrecarregar o Overpass.

## Na máquina local

As pastas ficam lado a lado (`atlas-motor/`, `atlas-<cidade>/`). De dentro de um município, `python ../atlas-motor/scripts/construir.py --previa` monta o livro em `_construcao/livro/` (fora do Git) e abre a prévia. `construir.py`, `validar.py` e `baixar_osm.py` rodam na versão do motor declarada pelo município: se o motor ao lado estiver em outra versão, a declarada é extraída da tag (cache em `~/.cache/atlas-motor/`) e roda no lugar. `--motor-atual` força o motor da pasta, para desenvolver o próprio motor.

Antes de cada push, o gancho instalado por `scripts/instalar_ganchos.py` roda o validador (inclusive as regras de dados pessoais): num repositório público, o que é enviado fica visível na hora.

## Figuras

Os diagramas estão em `figuras/`. O `.svg` é a fonte; `python docs/figuras/exportar.py` gera o `.pdf` (vetorial, para LaTeX) e o `.png` com o Chrome ou o Edge.
