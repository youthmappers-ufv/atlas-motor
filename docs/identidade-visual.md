# Identidade visual

Cores, fontes e logos do site e do PDF de um atlas vêm de **um arquivo só**, o `_brand.yml` ([formato do Quarto](https://posit-dev.github.io/brand-yml/)). Sem nada no município, o atlas usa a identidade do Programa Youthmappers UFV (`livro/_brand.yml` do motor). Com a pasta `identidade/` no repositório do município, a prefeitura parceira usa a sua.

O que muda com a identidade: capa do PDF (faixas, logos), títulos, filetes, cabeçalho, links, listas, tabelas, legendas, quadros, fonte do texto, cores e logo do site. O que **não** muda: as cores dos mapas (são do catálogo de temas, iguais em todos os atlas, para que possam ser comparados) e o conteúdo.

## Usar a identidade da prefeitura

1. **Autorização:** o uso da marca da prefeitura depende de autorização dela, registrada no termo de parceria. O repositório é público.
2. **Logos:** peça os arquivos oficiais, de preferência PNG com fundo transparente (ou SVG), e ponha em `identidade/marca/`.
3. **`identidade/_brand.yml`:**

   ```yaml
   meta:
     name: Prefeitura Municipal de Exemplo      # aparece no cabeçalho do PDF
   logo:
     images:                                    # todos aparecem na capa do PDF, na ordem
       prefeitura: marca/prefeitura.png
       programa: marca/ymufv_logo.png           # logo do programa, já incluído no motor
     medium: prefeitura                         # logo do site (barra lateral)
   color:
     palette:
       verde: "#1B6E3A"
       amarelo: "#D9A400"
       terra: "#8A4B1F"
     primary: verde          # títulos, faixas, links
     secondary: terra        # segunda faixa da capa, números das listas
     tertiary: amarelo       # filetes e marcadores
     light: "#F3F6EF"        # fundos claros
     foreground: "#222222"   # texto
     background: "#FFFFFF"
   typography:
     fonts:
       - family: Source Sans 3
         source: google      # o site baixa a fonte do Google Fonts
     base: Source Sans 3     # texto
     headings:
       family: Source Sans 3 # títulos
       weight: bold
       color: primary
     monospace: Source Code Pro
   ```

4. **Conferir:** `python ../atlas-motor/scripts/validar.py` e `python ../atlas-motor/scripts/construir.py --renderizar todos`. Veja a capa e algumas páginas do PDF em `_construcao/livro/_site/`, e o site. A prévia (`--previa`) não acompanha mudanças na identidade: rode `construir.py` de novo.
5. **PR** `[IDENTIDADE] Identidade visual da Prefeitura`, com uma captura da capa na descrição.

## Regras e cuidados

- **Cores** em hexadecimal (`#RRGGBB`), diretamente ou pelo nome definido na `palette`. Cor ausente ou inválida cai na do programa; o validador acusa as inválidas.
- **Contraste:** `primary` aparece como fundo de faixas com texto branco e como cor de títulos sobre branco; precisa funcionar nos dois. Evite cores claras demais em `primary` e `secondary`.
- **Imagens** em PNG, JPG, SVG ou PDF, **com a extensão certa**: o validador confere o formato real (um JPEG chamado `.png` é recusado, porque alguns programas não o abrem).
- **Logos citados** precisam existir em `identidade/` (ou ser o do programa, `marca/ymufv_logo.png`, que já vem no motor).
- **Fontes:** o PDF usa a fonte do tema se ela estiver instalada no computador (ou no GitHub, que instala a Source Sans 3); senão, cai numa reserva (Source Sans Pro, TeX Gyre Heros) sem erro. Para uma fonte institucional específica, combine com a coordenação a instalação no workflow de publicação.
- **Créditos:** mesmo com a identidade da prefeitura, a autoria do programa (`publicacao.autoria` no `atlas.toml`) e a atribuição ao OpenStreetMap continuam no atlas.

## Como funciona por dentro

Na construção, o motor copia `livro/` (com a identidade padrão) para `_construcao/livro/`, põe por cima o conteúdo de `identidade/` do município (menos os `.md`) e gera o `identidade.tex` a partir do `_brand.yml` (`scripts/identidade.py`): nomes de cor (`atlasprimaria`, `atlassecundaria`, `atlasdestaque`, `atlasclaro`, `atlastexto`), fontes com reservas, logos (`\atlaslogos`) e nome da marca (`\atlasmarca`). O estilo do PDF (`livro/atlas-estilo.tex`) e a capa (`livro/before-body.tex`) usam só esses nomes; o site usa o `_brand.yml` pelo tema `[cosmo, brand, estilo.scss]`. Nenhum dos dois estilos define cor ou fonte própria (um teste do motor confere).

## Voltar à identidade do programa

Apague `identidade/_brand.yml` (ou a pasta `identidade/` inteira, menos o `LEIAME.md`).
