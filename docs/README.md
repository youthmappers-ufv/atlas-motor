# Documentação do atlas

O atlas tem dois tipos de repositório: o **motor** (este, comum a todos) e um **repositório por município** (`atlas-<cidade>`), que guarda só configuração, dados e textos. Comece pelo guia do seu papel.

## Por papel

| Você... | Comece por |
|---|---|
| contribui com o atlas de um município (estudante, servidor da prefeitura, voluntário) | [Guia do município](guia-municipio.md) e [Pranchas](pranchas.md) |
| quer a identidade visual da prefeitura no site e no PDF | [Identidade visual](identidade-visual.md) |
| quer propor um tema novo para todos os atlas (ex.: esportes, segurança) | [Novos temas](novos-temas.md) |
| coordena o atlas (revisa PRs, lança versões, abre municípios) | [Manutenção](manutencao.md) e [Configuração do GitHub](configuracao-github.md) |
| mexe no código do motor | [CONTRIBUTING.md](../CONTRIBUTING.md) e [Arquitetura](arquitetura.md) |

## Todos os documentos

- [Arquitetura](arquitetura.md): repositórios, versão fixada, ciclo mensal, máquina local, identidade visual (com diagramas).
- [Guia do município](guia-municipio.md): o trabalho do dia a dia no repositório de um município.
- [Pranchas](pranchas.md): abrir, escrever e personalizar uma prancha (texto, seções, mapas, imagens, tamanhos); prancha própria do município.
- [Novos temas](novos-temas.md): como um tema entra no catálogo comum, da proposta à adoção pelos municípios.
- [Identidade visual](identidade-visual.md): cores, fontes e logos do site e do PDF com um `_brand.yml`.
- [Referência](referencia.md): todos os arquivos de configuração (`atlas.toml`, `temas.toml`, catálogo, bases oficiais, esquemas, `_brand.yml`) e todos os comandos.
- [Manutenção](manutencao.md): rotinas da coordenação (mensal, por versão, por município), incidentes e encerramento.
- [Configuração do GitHub](configuracao-github.md): criar repositórios, Pages, proteções, acesso, domínio próprio, transferência.
- [Solução de problemas](problemas.md): erros comuns e o que fazer.

## Vocabulário

- **Tema**: assunto de uma prancha (educação, saúde, sistema viário...). O catálogo de temas é comum a todos os municípios (`catalogo/temas.toml`); um município pode ter temas próprios.
- **Prancha**: o capítulo do atlas sobre um tema: texto da equipe e partes geradas pelo motor (mapas, indicadores, lacunas).
- **Retrato do OSM**: os dados de um tema baixados do OpenStreetMap numa data, guardados em `dados/osm/` do município.
- **Base oficial**: lista de um órgão público (INEP, CNES, Prefeitura) usada para medir a completude do mapa; nunca é copiada para o OSM.
- **Identidade visual**: cores, fontes e logos do site e do PDF (`_brand.yml`), do programa ou da prefeitura.
- **Edição**: versão numerada do atlas de um município (tag `vX.Y` no repositório dele), publicada e citável.
- **Versão do motor**: tag `vX.Y.Z` deste repositório, declarada por cada município no `atlas.toml`.
- **Canário**: município sem parceria que recebe cada versão nova do motor antes dos outros.
