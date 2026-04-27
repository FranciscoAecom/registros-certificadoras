# Integration Notes

## Cercarbono

### Visao Geral

- Certificadora: `cercarbono`
- Lista publica: `https://www.ecoregistry.io/projects-list/cercarbono-co2`
- Detalhe publico: `https://www.ecoregistry.io/projects/<id>`
- Backend do frontend: `https://api-front.ecoregistry.io/platform`

### Endpoints Confirmados

- Lista:
  - `GET /project/public-by-standard/cercarbono-co2`
- Detalhe:
  - `GET /project/public/<id>`
- Documentos por verificacao publica:
  - `GET /projectDocument/get-by-project-id/<id>/<verification_number>`
- Download de cartografia publica:
  - `GET /projectLocationsDocuments/download/<document_id>`
- Metadados do padrao:
  - `GET /standard/cercarbono-co2`

### Identificadores

- `project_public_id`: campo `code` da lista, por exemplo `CDC-265`
- `project_internal_id`: campo `id` da lista, por exemplo `266`
- `project_url`: `https://www.ecoregistry.io/projects/<project_internal_id>`

### Observacoes

- A lista publica ja retorna todos os projetos em um unico payload JSON.
- O detalhe tambem retorna JSON diretamente, sem necessidade de navegador headless.
- O frontend expoe anexos de cartografia em `Technical data > Formulation > Cartography`.
- Esses anexos aparecem no payload de documentos como itens `type=documentLocation`.
- Quando presentes, os anexos cartograficos devem ser baixados e preservados no bronze em `detail_data.spatial_documents`.
- Os binarios espaciais nao ficam embutidos no JSON bronze.
- Cada item de `detail_data.spatial_documents` referencia o arquivo bruto salvo no snapshot por:
  - `storageMode: snapshot_file`
  - `snapshotRelativePath`
  - `byteSize`
- Os endpoints exigem os headers usados pelo frontend, em especial:
  - `Platform: ecoregistry`
  - `Lng: en`
- Como esta integracao nao precisa de navegador nem sessao persistente, o teardown esperado e leve.
- Mesmo assim, os scripts usam um contexto gerenciado de encerramento para padronizar limpeza explicita e permitir evolucao futura sem deixar recursos orfaos.

### Formato Atual do Snapshot Bronze

- O snapshot de detalhe da Cercarbono passou a usar bundle `core + spatial`.
- Estrutura esperada em repouso:
  - `YYYYMMDD_core.zip` quando o core couber em um unico arquivo
  - `YYYYMMDD_core_001.zip`, `YYYYMMDD_core_002.zip`, ... quando o core precisar ser particionado
  - `YYYYMMDD_spatial_001.zip`, `YYYYMMDD_spatial_002.zip`, ... para anexos espaciais
- Dentro do snapshot descompactado:
  - `list/projects.json`
  - `projects/<project_public_id>.json`
  - `spatial/<project_public_id>/...`
- A criacao das partes `spatial_<n>` e automatica e usa o teto configuravel de `--spatial-part-max-bytes`.

### Logging Operacional

- Falhas do `extract_project_list.py` devem ser persistidas em `logs/extract_project_list_failures_<YYYYMMDD>.json`.
- Falhas do `extract_project_details.py` devem ser persistidas em `logs/extract_project_details_failures_<YYYYMMDD>.json`.
- Em detalhe, falhas pontuais por projeto devem ser registradas sem interromper a execucao dos proximos itens.
