# Integration Notes

## TERO Carbon

### Visao Geral

- Certificadora: `tero`
- Sigla de referencia sugerida: `TER`
- Status atual:
  - integracao validada
  - lista e detalhe implementados por WordPress REST API publica

### URLs Publicas Confirmadas

- Lista publica:
  - `https://terocarbon.com/home/projetos/`
- Detalhe publico por projeto:
  - `https://terocarbon.com/project/<slug>/`
- Exemplo validado de detalhe:
  - `https://terocarbon.com/project/cm-serras-da-mantiqueira/`

### Endpoints Confirmados

- Lista por WordPress REST:
  - `GET https://terocarbon.com/wp-json/wp/v2/project`
- Detalhe por WordPress REST:
  - `GET https://terocarbon.com/wp-json/wp/v2/project/<id>`
- Root da API:
  - `GET https://terocarbon.com/wp-json/`

### Comportamento Observado do Frontend

- O site da TERO e um WordPress com tema Divi.
- Em alguns ambientes Python, `terocarbon.com` pode falhar com `CERTIFICATE_VERIFY_FAILED`; os scripts aceitam `--insecure-ssl` para contornar esse problema operacional quando a cadeia CA local nao estiver completa.
- A pagina publica de projetos mostra atualmente os mesmos `3` projetos retornados pelo endpoint REST do custom post type `project`.
- O endpoint REST exposto para `project` e publico e paginado por `page` e `per_page`.
- O detalhe REST retorna o conteudo do WordPress, mas o campo `content.rendered` preserva shortcodes do Divi em vez do HTML final da pagina.
- Para nao perder o bruto efetivamente exibido ao usuario, `extract_project_details.py` salva:
  - a resposta JSON do WordPress REST
  - o HTML publico da pagina do projeto
- A pagina publica tambem pode expor anexos e referencias espaciais diretamente no HTML.
- No projeto `Aruana I`, foi observado:
  - iframe e link publico de Google My Maps em `https://www.google.com/maps/d/...`
  - exportacao direta de KML via `https://www.google.com/maps/d/kml?mid=<MID>&forcekml=1`
  - documento `Relatorio de Geoprocessamento (PT)` em PDF na tabela publica de links.

### Decisao Atual

- A TERO foi implementada sem navegador headless.
- `extract_project_list.py` usa `GET /wp-json/wp/v2/project?_embed=1`.
- `extract_project_details.py` usa:
  - `GET /wp-json/wp/v2/project/<id>?_embed=1`
  - `GET https://terocarbon.com/project/<slug>/`
- O script tambem extrai links da pagina publica em `detail_data.page_links`.
- Quando houver Google My Maps ou anexos espaciais diretos, o script baixa e preserva esses artefatos em `detail_data.spatial_documents`.
- Os binarios espaciais nao ficam embutidos no JSON bronze.
- Cada item de `detail_data.spatial_documents` referencia o arquivo bruto salvo no snapshot por:
  - `storageMode: snapshot_file`
  - `snapshotRelativePath`
  - `byteSize`
- O vinculo entre lista e detalhe usa:
  - `slug` como `project_public_id`
  - `id` como `project_internal_id`

### Formato Atual do Snapshot Bronze

- O snapshot de detalhe da TERO passou a usar bundle `core + spatial`.
- Estrutura esperada em repouso:
  - `YYYYMMDD_core.zip` quando o core couber em um unico arquivo
  - `YYYYMMDD_core_001.zip`, `YYYYMMDD_core_002.zip`, ... quando o core precisar ser particionado
  - `YYYYMMDD_spatial_001.zip`, `YYYYMMDD_spatial_002.zip`, ... para anexos espaciais
- Dentro do snapshot descompactado:
  - `list/projects.json`
  - `projects/<project_public_id>.json`
  - `spatial/<project_public_id>/...`
- A criacao das partes `spatial_<n>` e automatica e usa o teto configuravel de `--spatial-part-max-bytes`.

### Regras de Implementacao para esta Integracao

- Preservar o padrao `source`, `list_data` e `detail_data` na camada `bronze`.
- Manter o ritmo base do projeto:
  - `0.5s` entre solicitacoes
  - `2s` a cada `10` solicitacoes
  - retry limitado com espera quando houver `429 Too Many Requests`
- Nao voltar para scraping puro da lista enquanto o custom post type `project` continuar exposto em `wp-json`.

### Uso Futuro

- Atualizar este arquivo quando houver mudanca em:
  - rota REST `wp/v2/project`
  - quantidade publica de projetos
  - shape do campo `content.rendered`
  - regra de montagem da URL publica por `slug`
  - estrutura da tabela publica de links e padrao dos links espaciais
