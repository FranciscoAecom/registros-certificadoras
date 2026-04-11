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
- Sempre que houver `KML/KMZ` em `documentGroups`, baixar e preservar o conteudo bruto em `detail_data.spatial_documents`.
