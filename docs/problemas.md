# Solução de problemas

Erros comuns, do mais frequente ao mais raro. Se não resolver, abra uma issue com o comando, a mensagem completa e o sistema operacional.

## Validação

| Mensagem | O que fazer |
|---|---|
| `chama o motor em vX, mas atlas.toml diz vY` | rode `atualizar_motor.py --versao vY` (troca os dois juntos) em vez de editar à mão |
| `não está no catálogo do motor; prancha própria precisa de ...` | id com erro de digitação, ou prancha própria sem `numero`, `titulo` e `consulta` |
| `falta atlas/pranchas/<nn>-<id>.qmd` | rode `ativar_tema.py <id>` (cria a prancha) ou volte a situação para `planejado` |
| `... não corresponde a tema ativo` | prancha de um tema `planejado`, ou com número/nome errado no arquivo |
| `contém um e-mail` / `parece conter um CPF` / `parece conter um telefone` | tire o dado pessoal do CSV; telefone público de estabelecimento vai para o OSM |
| `mais valores que colunas` | texto com vírgula precisa de aspas no CSV: `"R$ 1.234,56"` |
| `fora da área do município` | coordenada trocada (lat/lon invertidas) ou com vírgula decimal; use ponto: `-19.1965` |
| `o conteúdo não é PNG (extensão trocada?)` | a imagem é de outro formato; salve de novo como PNG ou mude a extensão para a real |
| `a pasta tema/ passou a se chamar identidade/` | `git mv tema identidade` (mudança da v0.7.0 do motor) |

## Versão do motor

- **`O atlas.toml declara o motor vX, que não está no clone do motor`:** o clone do motor não tem a tag. Rode `git -C ../atlas-motor fetch --tags`. Para desenvolver o próprio motor, use `--motor-atual`.
- **Os scripts parecem usar outra versão:** é o esperado; localmente, `construir`, `validar` e `baixar_osm` usam a versão declarada pelo município (aparece um aviso). Use `--motor-atual` para o motor da pasta.

## Construção e prévia

- **`PermissionError` / `Acesso negado` ao construir (Windows, OneDrive):** a prévia (`--previa`) ainda está aberta e segura o cache do Quarto; feche-a (Ctrl+C) e rode de novo. Se persistir, pause a sincronização do OneDrive ou apague `_construcao/` à mão.
- **A prévia não mostra a mudança:** a prévia só acompanha textos de `atlas/`; mudanças em dados, `temas.toml`, `atlas.toml` ou `identidade/` pedem `construir.py` de novo.
- **`ModuleNotFoundError: yaml` ou `matplotlib`:** `pip install -r ../atlas-motor/requirements.txt`.
- **`quarto` não encontrado:** instale o [Quarto](https://quarto.org) e abra um terminal novo.
- **Imagem não aparece na prancha:** caminho relativo à pasta da prancha (`imagens/foto.jpg` para `atlas/pranchas/imagens/foto.jpg`; `../_gerado/figuras/...` para os mapas).

## PDF (LaTeX)

- **`latexmk`/Perl ausente (Windows com MiKTeX):** instale o Strawberry Perl e ponha só a pasta `perl\bin` no `PATH`.
- **Pacote LaTeX ausente:** o Quarto instala sozinho com o TinyTeX (`quarto install tinytex`); no MiKTeX, permita a instalação automática de pacotes.
- **`bad allocation` / falta de memória no XeTeX (Windows):** aumente a memória virtual (arquivo de paginação gerenciado pelo sistema) e feche programas pesados.
- **Fonte diferente da esperada:** a fonte da identidade não está instalada; o PDF usa a reserva. Instale a fonte no computador (no GitHub, a Source Sans 3 é instalada pelo workflow).

## Retrato do OSM

- **`502`, `504` ou tempo esgotado:** servidor Overpass sobrecarregado; o script já tenta os outros. Espere alguns minutos e rode de novo.
- **Retrato vazio num tema que tem objetos no mapa:** confira a consulta no [Overpass Turbo](https://overpass-turbo.eu/) com a caixa do município; etiqueta diferente da esperada é a causa mais comum.
- **Objetos de fora aparecem no mapa:** o recorte é pelo limite da relação do OSM (`osm_relacao`); um limite errado no OSM se corrige no OSM.

## Git e GitHub

- **Push recusado pelo gancho de pre-push:** a validação encontrou erro; corrija e envie de novo. `git push --no-verify` pula a validação (não recomendado).
- **`pre-push: não achei Python 3.11+`:** o Git não vê o Python no `PATH`; ajuste o `PATH` ou reinstale o gancho depois de instalar o Python.
- **Merge bloqueado:** a `main` exige *Verificar* verde e PR; corrija o que o *Verificar* acusou.
- **Workflow *Publicar atlas* sem site:** na primeira vez, é preciso ligar o Pages na branch `gh-pages` ([Configuração do GitHub](configuracao-github.md)); com `hospedagem = "artefato"`, o site só sai como artefato do workflow.

## Limitações conhecidas

- Os links da tabela "Pranchas desta edição" funcionam no site, mas no PDF apontam para arquivos `.qmd`.
- Tabelas de lacunas muito longas são cortadas em 60 itens na prancha; a lista completa fica nos dados.
