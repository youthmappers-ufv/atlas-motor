# Guia do município

Como trabalhar no repositório do atlas de um município (`atlas-<cidade>`). Para quem contribui com dados, textos ou edições no mapa: estudantes, servidores da prefeitura parceira, voluntários. Quem coordena vê também a [Manutenção](manutencao.md).

## O que fica onde

```
atlas.toml        município, versão do motor, hashtags, publicação
temas.toml        quais pranchas estão abertas (e ajustes delas); pranchas próprias
consultas/        consultas Overpass próprias (opcional)
dados/osm/        retratos do OpenStreetMap (gerados; não editar à mão)
dados/oficiais/   bases oficiais abertas, cada uma com fonte.toml
dados/curados/    dados levantados pela equipe (CSV com esquema)
dados/esquemas/   esquemas próprios (opcional)
atlas/            textos: index.qmd e pranchas/<nn>-<tema>.qmd; imagens próprias
identidade/       identidade visual própria (opcional): _brand.yml e logos
.github/          workflows que chamam o motor; modelos de issue e PR
```

Código não entra no repositório do município: scripts, consultas e esquemas comuns, mapas e o modelo do livro são do motor. Uma melhoria que serve a todos vira issue ou PR no `atlas-motor`.

## Antes de começar (uma vez)

1. **Contas:** GitHub (peça acesso à coordenação) e OpenStreetMap, para editar o mapa.
2. **Programas:** Git, Python 3.11 ou mais recente, [Quarto](https://quarto.org) e, para gerar o PDF, uma distribuição LaTeX (`quarto install tinytex` ou MiKTeX). No Windows com MiKTeX, instale também o Strawberry Perl (exigido pelo `latexmk`).
3. **Clones lado a lado** (a mesma pasta-mãe):

   ```bash
   git clone https://github.com/youthmappers-ufv/atlas-motor
   git clone https://github.com/youthmappers-ufv/atlas-<cidade>
   cd atlas-<cidade>
   pip install -r ../atlas-motor/requirements.txt
   python ../atlas-motor/scripts/instalar_ganchos.py
   ```

   O último comando instala o gancho que roda o validador antes de cada `git push`. Os scripts usam sozinhos a versão do motor declarada no `atlas.toml` (extraída do clone do motor); mantenha o clone atualizado com `git -C ../atlas-motor pull --tags`.

## O ciclo de cada contribuição

1. **Issue** descrevendo o que vai ser feito (modelos em *New issue*: lacuna no mapa, dado novo).
2. **Branch** a partir da `main`: `dados/...`, `texto/...`, `campo/...`, `config/...`.
3. **Commits pequenos**, um por passo, com mensagem que diga o que mudou (`[DADOS] Catálogo do INEP de nov/2026`).
4. **Conferir:** `python ../atlas-motor/scripts/validar.py` (0 erros) e ver o resultado com `python ../atlas-motor/scripts/construir.py --previa`.
5. **Pull request** com o modelo preenchido. O workflow *Verificar* precisa ficar verde; a coordenação revisa e mescla. Ninguém mescla o próprio PR.

## Dados públicos

O repositório do município é público: commits, branches, issues e PRs ficam visíveis assim que enviados e continuam no histórico. Só entram dados públicos. Nunca entram nomes de moradores ou informantes, telefones, e-mails, CPF, fotos de fichas ou anotações de campo brutas. O validador e o gancho de pre-push acusam e-mail, CPF e telefone; se algo pessoal escapar, avise a coordenação na hora (ver [Manutenção](manutencao.md#incidente-dado-pessoal-publicado)).

## Tarefas comuns

### Ver o atlas enquanto escreve

```bash
python ../atlas-motor/scripts/construir.py --previa
```

Abre o site no navegador e recarrega a cada texto salvo em `atlas/`. Mudou dados, `temas.toml`, `atlas.toml` ou a identidade visual? Rode `construir.py` de novo (pode ser com a prévia aberta, em outro terminal). Site e PDF em arquivo: `--renderizar html` ou `--renderizar todos` (resultado em `_construcao/livro/_site/`, fora do Git).

### Retrato novo do OSM

O workflow *Atualizar dados do OSM* faz isso todo mês e abre um PR. À mão: `python ../atlas-motor/scripts/baixar_osm.py` (todos os temas) ou `--tema educacao`. O Overpass às vezes falha (erro 502, tempo esgotado): espere alguns minutos e tente de novo; o script já tenta outros servidores.

### Abrir uma prancha

```bash
python ../atlas-motor/scripts/ativar_tema.py saude
python ../atlas-motor/scripts/baixar_osm.py --tema saude
```

Depois, escreva o texto em `atlas/pranchas/04-saude.qmd`. Tudo sobre pranchas, inclusive como montá-las do seu jeito: [Pranchas](pranchas.md).

### Carregar uma base oficial

**INEP (escolas):** no [Catálogo de Escolas](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/inep-data/catalogo-de-escolas), filtre o município e exporte a tabela "lista das escolas - Detalhado" em CSV. Depois, sem editar o arquivo:

```bash
python ../atlas-motor/scripts/preparar_base.py inep "<arquivo baixado>.csv"
python ../atlas-motor/scripts/validar.py
```

O script fica com as escolas do município em funcionamento (`--todas` mantém as paralisadas), tira telefone e as colunas que o atlas não usa, limpa as coordenadas, grava `dados/oficiais/inep/` com o `fonte.toml` e lista as escolas sem coordenada ou fora da área. Base nova por cima da antiga: `--substituir`; data do download diferente de hoje: `--data AAAA-MM-DD`. Confira a licença no `fonte.toml` com a página da fonte.

**Outras bases** (até o script conhecer o formato delas):

1. Baixe da fonte oficial, filtre para o município (código IBGE) e salve em CSV UTF-8, sem colunas de telefone ou e-mail.
2. Crie `dados/oficiais/<base>/` com o CSV e o `fonte.toml` (formato em [Referência](referencia.md#base-oficial-fontetoml)).
3. Se o nome da pasta for o que o catálogo espera (`inep`, `cnes`), a completude aparece sozinha; senão, aponte `referencia` no `temas.toml`.

As bases servem só para conferência: nada é copiado delas para o OSM.

### Corrigir as lacunas

A prancha lista os itens da base oficial sem correspondente no mapa, cada um com o **motivo provável** (também no terminal: `python ../atlas-motor/scripts/indicadores.py --tema educacao`). Um item tem correspondente quando há no OSM um objeto do tema a até `distancia_max_m` (150 m) com nome semelhante; o motivo diz qual das condições falhou e o que conferir:

| Motivo | O que costuma ser | O que fazer |
|---|---|---|
| sem coordenada na base oficial (às vezes com "no OSM há …") | a fonte não tem a posição | conferir em campo se o objeto citado é o mesmo item |
| coordenada oficial fora do município | posição errada na fonte | localizar pelo endereço; avisar o órgão (pela escola, secretaria) |
| nome semelhante no OSM a N m | posição errada na fonte ou no mapa | conferir em campo qual está certa; corrigir o mapa se for ele |
| "…" já corresponde a outro item da base | item repetido na base, ou dois lugares com um só objeto no mapa | conferir na fonte e em campo; mapear o que faltar |
| objeto sem nome no OSM a N m | o lugar está no mapa sem nome | conferir em campo e pôr o nome |
| "…" no OSM a N m, com nome diferente | nome antigo, apelido ou outro lugar vizinho | conferir em campo o nome correto |
| nada deste tema no OSM até 150 m | não mapeado | mapear (mapatona ou campo) |

O motivo é uma pista, não um diagnóstico: só a conferência em campo decide. Nunca se copia a posição ou o nome da base oficial para o OSM.

### Registrar a conferência em campo

Uma linha por item verificado em `dados/curados/levantamentos-campo.csv` (id `LC-AAAA-NNN`, data, tema, item, situação, objeto e *changeset* do OSM). As colunas e os valores aceitos estão no esquema do catálogo ([Referência](referencia.md#esquemas-de-dados-curados)).

### Editar o OpenStreetMap

Sempre à mão, com a sua conta, comentário descritivo e as hashtags `#youthmappersufv #ymufv-atlas`, sempre juntas. Nada de edição automática ou em lote. Telefone e horário públicos de um estabelecimento vão para o OSM, não para o repositório.

### Atualizar a versão do motor

Quando a coordenação avisar: num PR próprio, `python ../atlas-motor/scripts/atualizar_motor.py --versao vX.Y.Z` (troca no `atlas.toml` e nos workflows). Leia antes a entrada da versão no `CHANGELOG.md` do motor: versões que exigem mudança no município trazem as instruções.

### Publicar uma edição

A coordenação cria a tag quando uma etapa se fecha (`git tag v1.0 && git push origin v1.0`). O workflow *Publicar atlas* gera site e PDF daquela versão, publica em `edicoes/v1.0/` e como versão principal (se `publicacao.hospedagem = "pages"`) e anexa o PDF a um release. Relatórios citam números pela edição, para serem verificáveis.

## Quando algo dá errado

Veja [Solução de problemas](problemas.md). Se não resolver, abra uma issue no repositório do município com o comando, a mensagem de erro e o sistema operacional.
