# Integration Notes

## Verra

- Certificadora: `verra`
- Status atual:
  - integracao validada
  - lista e detalhe por endpoints oficiais do frontend

### URLs Publicas

- Lista: `https://registry.verra.org/app/search/VCS/All%20Projects`
- Detalhe: `https://registry.verra.org/app/projectDetail/VCS/<resourceIdentifier>`

### Endpoints

- Lista: `POST https://registry.verra.org/uiapi/resource/resource/search`
- Detalhe: `GET https://registry.verra.org/uiapi/resource/resourceSummary/<resourceIdentifier>`
- Geometria complementar:
  - o detalhe pode expor documentos espaciais em `detail_data.documentGroups[].documents[]`
  - documentos `KML/KMZ` trazem `uri` publica em `documents[].uri`
  - exemplo de download: `GET https://registry.verra.org/mymodule/ProjectDoc/Project_ViewFile.asp?...`

### Vinculacao

- `resourceIdentifier` como `project_public_id`
- `resourceIdentifier` como `project_internal_id`

### Regras de Manutencao

- Manter retry para `429 Too Many Requests`.
- Manter log operacional em `logs/`.
- Nao trocar o endpoint oficial por scraping do HTML enquanto a API continuar estavel.
- Sempre que houver `KML/KMZ` em `documentGroups`, baixar e preservar o conteudo bruto como arquivos do snapshot em `spatial/<project_id>/...`.
- Em `detail_data.spatial_documents`, preservar os metadados do anexo e o apontamento para `snapshotRelativePath`, evitando embutir o binario no JSON do detalhe.
- O snapshot datado da Verra passa a ser empacotado como bundle:
  - `YYYYMMDD_core.zip` quando o core couber em uma unica parte
  - `YYYYMMDD_core_001.zip`, `002`, ... quando o core precisar ser particionado
  - `YYYYMMDD_spatial_001.zip`, `002`, ... com os anexos espaciais
- O script controla automaticamente a criacao de `core_<n>.zip` e `spatial_<n>.zip` conforme o teto configurado por `--spatial-part-max-bytes`.
- Para coletas completas com milhares de projetos, preferir `--safe-mode` para endurecer pausas, timeout e retry.
- O script aceita `--spatial-document-sleep-seconds` para reduzir rajadas ao baixar varios anexos espaciais do mesmo projeto.
- Em cenarios de risco operacional elevado, `--skip-spatial-documents` pode ser usado para concluir primeiro a coleta completa do detalhe principal e deixar o backfill de `KML/KMZ` para uma etapa separada.
