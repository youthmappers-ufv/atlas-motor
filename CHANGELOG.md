# Mudanças do atlas-motor

Versionamento semântico, `vMAIOR.MENOR.CORREÇÃO`:

- **CORREÇÃO** (v1.2.0 → v1.2.1): conserto sem mudança de comportamento esperado.
- **MENOR** (v1.2 → v1.3): compatível. Novos indicadores, temas no catálogo, scripts. O município atualiza só a versão (`scripts/atualizar_motor.py`).
- **MAIOR** (v1 → v2): exige mudança nos repositórios dos municípios (formato do `atlas.toml`, do `temas.toml`, dos dados ou dos textos). A entrada diz o que fazer.

**Pré-lançamento (`v0.y.z`).** Enquanto o motor não é lançado oficialmente, qualquer versão MENOR pode exigir mudança nos municípios; a entrada diz quando. **`v1.0.0` é o lançamento oficial**, e só a partir dele vale a garantia de compatibilidade dentro da mesma versão MAIOR. Critérios propostos para o lançamento, a confirmar pela coordenação:

- licença definida e repositórios públicos no GitHub;
- CI verde no GitHub (testes do motor e verificação, atualização e publicação de um município);
- primeiro atlas de Rio Paranaíba publicado pelo workflow no GitHub Pages do próprio repositório, com pelo menos uma base oficial carregada (INEP);
- `novo_local.py` usado para um segundo município, de ponta a ponta.

Cada versão é uma tag no `main`, criada só com o workflow *Testes do motor* verde. Os municípios escolhem quando atualizar; uma edição publicada continua reproduzível com a versão que a gerou.

As duas primeiras versões foram numeradas inicialmente como v1.0 e v1.1 e renumeradas para v0.1.0 e v0.2.0 antes de qualquer publicação.

## v0.10.0 — 2026-10-22

**Ao atualizar o município:** acrescente a fileira de badges logo abaixo do título do README. Para gerá-la, da pasta do município: `python -c "import sys, tomllib; sys.path.insert(0, '../atlas-motor/scripts'); from novo_local import linha_badges; print(linha_badges(tomllib.load(open('atlas.toml', 'rb')), 'youthmappers-ufv'))"`. Num município novo, o `novo_local.py` já a põe.

- Badges nos READMEs. Motor: versão (última tag), testes, licenças, Python, Quarto e documentação. Município público: site, *Publicar atlas*, *Verificar*, data dos dados do OSM, completude, versão do motor, edição (último release) e licenças; os de dados, completude e motor leem o atlas publicado (`_gerado/badges/*.json`, no formato *endpoint* do shields.io), não o repositório. Município privado: só os do GitHub Actions e fixos (o shields.io não lê repositório privado); o da versão do motor é trocado pelo `atualizar_motor.py`.
- Workflow *Release* do motor: release no GitHub com as notas do CHANGELOG (`scripts/notas_versao.py`). Sai sozinho só com a tag de versão maior (`vX.0.0`, a partir da `v1.0.0`); as demais, à mão (*Run workflow*). Preparado para o DOI do Zenodo (passos em `docs/configuracao-github.md`).

## v0.9.0 — 2026-10-22

**Ao atualizar o município:** acrescente o `CITATION.cff` e a seção "Como citar" do README (modelos em `modelo-local/`, com os marcadores preenchidos pelo `novo_local.py` num município novo); sem o `CITATION.cff`, o validador avisa.

- Citação também em BibLaTeX: no site, abaixo da referência ABNT, a entrada para copiar e o arquivo `atlas-<slug>.bib` para baixar. Com o estilo `abnt` do biblatex-abnt, a entrada dá a mesma referência (coordenação como editor com `editortype = coordinator`, que imprime "(coord.)"); conferido compilando o `.bib` gerado. O PDF continua só com a ABNT.
- Citação nos repositórios: `CITATION.cff` (botão *Cite this repository* do GitHub; tipo dataset, coordenação e programa como autores, licenças ODbL, CC BY 4.0 e MIT) e seção "Como citar" no README, com ABNT e BibLaTeX, geradas pelo `novo_local.py` com as mesmas funções da citação do site. O validador avisa se o `CITATION.cff` faltar ou não bater com o `atlas.toml` (título, coordenação).

## v0.8.0 — 2026-10-22

**Ao atualizar o município** (opcional): na página inicial (`atlas/index.qmd`), em "Como usar e citar", acrescente `Para citar o atlas (ABNT):` seguido de `{{< include _gerado/citacao.md >}}` (texto atual em `modelo-local/atlas/index.qmd`). Rio Paranaíba e São Gotardo têm a citação escrita à mão, para valer já na v0.7.0; troquem pelo include.

- Coordenação na autoria: `publicacao.coordenacao` (opcional) no `atlas.toml` põe o nome de quem coordena como primeiro autor, com "(coordenação)", na página inicial e na capa do PDF, e no rodapé ("Coordenação: …"). O validador recusa o campo vazio. Versões anteriores do motor ignoram o campo.
- Citação do atlas no formato da ABNT (NBR 6023:2018), gerada em `_gerado/citacao.md`: entrada pela coordenação ("SMARZARO, Rodrigo (coord.)") ou, sem ela, pela autoria; ano dos dados do OSM; endereço do site (sem ele, no município só com artefato).
- O PDF com a versão no nome (`atlas-<slug>-<versão>.pdf`) passa a ser feito só para as edições numeradas e o release; antes, ia também para a raiz do site como `atlas-<slug>-main.pdf`, uma cópia idêntica do `atlas-<slug>.pdf`. A cópia que já está no `gh-pages` não some sozinha (o workflow preserva os arquivos existentes).
- `scripts/preparar_base.py`: converte uma base oficial como baixada do órgão (formato `inep`: Catálogo de Escolas, lista detalhada) para `dados/oficiais/<base>/`, com o `fonte.toml`: filtra o município e as escolas paralisadas, tira telefone e colunas não usadas, aceita vírgula ou ponto e vírgula, UTF-8 ou Latin-1 e vírgula decimal, e lista itens sem coordenada ou fora da área. Roda direto do clone do motor, em qualquer versão declarada pelo município.
- Completude: a semelhança de nomes passa a considerar também as palavras distintivas (sem as genéricas, como "escola", "municipal", "colégio", e sem as do nome do município). Um nome contido no outro vale 0,95: "Alegria de Saber" (OSM) corresponde a "INSTITUTO EDUCACIONAL EQUIPE SG - ALEGRIA DE SABER" (INEP). A distância máxima não muda. Efeito: São Gotardo, educação, C_t de 13,3% para 16,7%; Rio Paranaíba sem mudança.
- Botão "Baixar o atlas completo em PDF" no site, na página inicial (dentro do trecho gerado `_gerado/edicao.md`, que os municípios já incluem) e na página "Dados para download"; o ícone que o Quarto põe na barra lateral passava despercebido. Não aparece no PDF. As notas do release passam a vir de `_gerado/notas.md` (só a versão e a data), porque o `edicao.md` agora tem o botão.
- Lacunas com motivo provável: cada item da base oficial sem correspondente no mapa ganha, na prancha (coluna nova na tabela de lacunas) e em `indicadores.py`, o motivo provável, para orientar a conferência: sem coordenada (e, se houver, o objeto do OSM de mesmo nome), coordenada fora do município, nome semelhante no OSM mas longe, objeto perto já pareado com outro item, objeto perto sem nome, objeto perto com nome diferente ou nada mapeado por perto. Conferido com os casos já levantados à mão nos dois municípios (Paulo Freire, Tancredo Neves, Joana Darc, José Luiz de Araújo, Colégio Dimensão). A completude não muda.
- `novo_local.py` falhava num clone novo do motor: a pasta vazia `modelo-local/atlas/pranchas/` não é guardada pelo Git; o script passa a criá-la. Afeta só a criação de município (os workflows não usam o script); a correção vale assim que o clone do motor for atualizado.
- Testes no CI: o teste do gancho de pre-push usa o validador do motor atual, sem depender das tags (o checkout do CI não as baixa).

## v0.7.0 — 2026-10-22

**Exige mudança nos municípios que têm a pasta `tema/`** (pré-lançamento):

1. `python ../atlas-motor/scripts/atualizar_motor.py --versao v0.7.0`;
2. `git mv tema identidade` (o validador acusa erro enquanto a pasta antiga existir);
3. no `README.md` e no `CONTRIBUTING.md` do município, troque `tema/` por `identidade/` (texto atual em `modelo-local/`).

Pranchas e textos existentes não mudam: o include `_gerado/<tema>.md` continua gerando a prancha inteira.

- **Pasta da identidade visual:** `tema/` passa a `identidade/` (o nome antigo se confundia com os temas das pranchas); `scripts/tema.py` passa a `scripts/identidade.py` e gera `identidade.tex`.
- **Pranchas em partes:** além de `_gerado/<tema>.md`, o motor gera `_gerado/<tema>/{mapa-municipio,mapa-sede,legenda,indicadores,lacunas,fonte}.md`, para a equipe montar a prancha com texto, seções e figuras próprias entre as partes.
- **Catálogo:** `cor`, `mapa` (`pontos` | `linhas`) e `indicadores` (`servico`, `vias`) de cada tema passam do código para `catalogo/temas.toml`; um tema novo deixa de exigir código. O município pode trocá-los no próprio `temas.toml` e nas pranchas próprias. O validador confere os valores.
- PDF: moldura dos quadros (callouts) nas cores da identidade.
- **Documentação** de uso e manutenção em `docs/` (guia do município, pranchas, novos temas, identidade visual, referência, manutenção, solução de problemas) e modelo de issue para propor tema novo.

## v0.6.0 — 2026-10-22

Compatível com v0.5.1: `atualizar_motor.py --versao v0.6.0`. Sem `tema/`, o atlas usa a identidade do programa.

- **Identidade visual por `_brand.yml`**, fonte única de cores, fontes e logos para o site e o PDF. Tema padrão do programa em `livro/_brand.yml` (com o logo em `livro/marca/`); o município troca a identidade com `tema/_brand.yml` e os logos ao lado (instruções em `modelo-local/tema/LEIAME.md`).
- PDF (LaTeX) no padrão visual dos documentos do programa: capa em faixas com os logos do tema, títulos sem serifa com filete, faixa de "Pranchas" sem página própria, cabeçalho, listas, tabelas e legendas nas cores do tema, texto sem serifa. `scripts/tema.py` gera o `tema.tex` do `_brand.yml`, com fontes de reserva se a do tema não estiver instalada.
- Site: tema `[cosmo, brand, estilo.scss]`; o `estilo.scss` deixa de fixar as cores do programa (elas anulavam o `_brand.yml`).
- Validador: `tema/` com cores inválidas, logos citados que não existem ou imagem com extensão trocada (ex.: JPEG chamado `.png`).
- `requirements.txt`: PyYAML (para ler o `_brand.yml` na construção). CI: Quarto 1.10.18 fixado e fonte Source Sans 3 instalada para o PDF.

## v0.5.1 — 2026-10-21

Correção: `atualizar_motor.py --versao v0.5.1`.

- `construir.py` omite o `site-url` do livro quando não há endereço (`hospedagem = "artefato"` com `url` vazio); com a v0.5.0, o Quarto recusava o projeto e o site não era gerado.

## v0.5.0 — 2026-10-21

**Exige mudança nos municípios** (pré-lançamento). O município passa a ser repositório **público** e publica o próprio site no GitHub Pages; o repositório de saída compartilhado (`youthmappers-ufv/atlas`) deixa de ser usado.

- `publicar.yml` publica no `gh-pages` do próprio município, com o token do workflow (sem chave de deploy nem segredo); edições numeradas em `edicoes/<tag>/`. Com `publicacao.hospedagem = "artefato"`, nada é publicado (repositório privado, ou hospedagem em outro lugar).
- `[publicacao]` do `atlas.toml`: saem `ativa`, `url_base` e `repositorio`; entram `hospedagem` (`"pages"` ou `"artefato"`), `url` (endereço do site) e `dominio` (opcional, domínio próprio). O validador acusa as chaves antigas.
- `construir.py`, `validar.py` e `baixar_osm.py` rodam na versão do motor declarada pelo município: se o motor ao lado estiver em outra versão, a declarada é extraída da tag para `~/.cache/atlas-motor/` e roda no lugar (`--motor-atual` usa o motor da pasta).
- `scripts/instalar_ganchos.py`: gancho de pre-push que roda o validador antes de cada envio.
- Validador: acusa telefone em dado curado e linha de CSV com mais valores que colunas (antes quebrava).
- Modelo de município para repositório público: regra de dados públicos no `CONTRIBUTING.md`, avisos nos modelos de issue e PR, `LICENCAS.md`. `novo_local.py` preenche `hospedagem` e `url` (`--organizacao`, `--privado`).
- Saem do motor o registro de pesquisa (`pesquisa/`), a estratégia das instâncias, `metricas_motor.py` e o esquema `atividades`, que não são necessários ao funcionamento; ficam no repositório de documentos do programa.
- Documentação: arquitetura e configuração do GitHub reescritas (Pages próprio, proteção da `main` e das tags do motor, domínio próprio, transferência para a prefeitura).

**Migração de um município** (num PR próprio, `[CONFIG] Motor v0.5.0`):

1. `python ../atlas-motor/scripts/atualizar_motor.py --versao v0.5.0`.
2. No `[publicacao]` do `atlas.toml`, apague `ativa`, `url_base` e `repositorio` e acrescente:
   `hospedagem = "pages"` (ou `"artefato"`, se o repositório for privado), `url = "https://youthmappers-ufv.github.io/atlas-<cidade>/"` (vazio com `"artefato"`) e `dominio = ""`.
3. No `.github/workflows/publicar.yml`, apague a linha `secrets: inherit`.
4. Se o repositório tiver `docs/decisoes.md` ou `dados/curados/atividades.csv`, mova-os para o repositório de documentos do programa.
5. Copie do modelo do motor os textos de repositório público (`README.md`, `CONTRIBUTING.md`, `LICENCAS.md`, modelos de issue e PR), ajustando o nome do município.
6. `python ../atlas-motor/scripts/validar.py` (0 erros) e `python ../atlas-motor/scripts/instalar_ganchos.py`.

## v0.4.0 — 2026-10-21

Compatível com v0.3.1: `atualizar_motor.py --versao v0.4.0`.

- `construir.py --previa`: monta o livro e abre o `quarto preview`; enquanto ele estiver aberto, os textos salvos em `atlas/` são copiados para o livro e o navegador recarrega (opções `--porta` e `--sem-navegador`).
- O livro em `_construcao/livro` é atualizado no lugar, preservando `.quarto`, `_site` e `_freeze`: rodar `construir.py` de novo com a prévia aberta (depois de mudar dados ou temas) não falha mais por arquivo em uso.

## v0.3.1 — 2026-10-21

Correção: `atualizar_motor.py --versao v0.3.1`.

- `construir.py` apaga a pasta `_construcao` mesmo quando o Quarto ou o OneDrive deixam itens somente leitura (Windows); antes, a segunda construção local falhava com "Acesso negado". Não afeta o CI.

## v0.3.0 — 2026-10-21

Compatível com v0.2.1: `atualizar_motor.py --versao v0.3.0`. Sem `publicacao.ativa` no `atlas.toml`, nada muda (vale `true`).

- `publicacao.ativa` no `atlas.toml`: com `false`, o workflow de publicação gera site e PDF só como artefato (e o release privado, em tags) e não envia nada ao site público; o segredo `ATLAS_CHAVE_PUBLICACAO` passa a ser opcional. Para municípios sem parceria, como o canário (decisão 0005).
- O validador exige `true` ou `false` (sem aspas); um teste confere que todo passo que publica no site depende da opção.

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
