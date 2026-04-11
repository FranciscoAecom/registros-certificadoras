# Integration Notes

## Equitable Earth Registry

### Visão Geral

- Certificadora: `equitable_earth`
- Sigla de referência sugerida: `EQE`
- Status atual:
  - integração validada
  - lista e detalhe implementados por API pública usada pelo frontend

### URLs Públicas Confirmadas

- Lista pública:
  - `https://registry.eq-earth.com/report/resource/PUBLIC/ERS_MEASUREMENT_STANDARD`
- Detalhe público por identificador:
  - `https://registry.eq-earth.com/dataroom/ERS/ERS_MEASUREMENT_STANDARD/byIdentifier/<project_internal_id>`
- Exemplo validado de detalhe:
  - `https://registry.eq-earth.com/dataroom/ERS/ERS_MEASUREMENT_STANDARD/byIdentifier/7CE3FC58-F51C-11EF-BFE3-36293FBAD3EA`

### Comportamento Observado do Frontend

- A página pública da lista abre um shell de `report`.
- A página pública do detalhe abre um shell de `dataroom`.
- O HTML inicial do detalhe é majoritariamente estrutural e delega o conteúdo a componentes `apx-dataroom-*`.
- O frontend resolve o tenant público da EQE via `GET https://optimal-gateway.apx.com/api/tenantByHost/registry.eq-earth.com`.
- A lista usa `GET https://optimal-gateway.apx.com/reporting/api/resource/public` com:
  - header `apx_s: ERS`
  - query params `$skip`, `$top`, `$count=true` e `programCode=ERS_MEASUREMENT_STANDARD`
- O detalhe usa `GET https://optimal-gateway.apx.com/resource/resource/<resourceIdentifier>/form/DATAROOM_ERS_MEASUREMENT_STANDARD` com header `apx_s: ERS`.
- O bundle do detalhe também consulta:
  - `POST https://optimal-gateway.apx.com/legalentity/api/legalEntity/byIdentifier?sourceSystemCode=ERS`
  - `GET https://optimal-gateway.apx.com/resource/program/ERS_MEASUREMENT_STANDARD/<version>/protocolVersion`
  - `GET https://optimal-gateway.apx.com/resource/protocol/<code>/<version>/creditingPeriods/<start>/<today>`
  - `GET https://optimal-gateway.apx.com/fileRegistry/api/file/report/file/public`

### Decisão Atual

- A Equitable Earth foi implementada sem navegador headless.
- `extract_project_list.py` usa a API pública de reporting consumida pelo frontend.
- `extract_project_details.py` usa o bundle de chamadas públicas do dataroom para compor o detalhe bruto.
- O vínculo entre lista e detalhe usa:
  - `programAssignedIdentifier` como `project_public_id`
  - `resourceIdentifier` como `project_internal_id`

### Regras de Implementação para esta Integração

- Preservar o padrão `source`, `list_data` e `detail_data` na camada `bronze`.
- Buscar primeiro endpoint público ou usado pelo frontend antes de recorrer a scraping do DOM.
- Manter o padrão base de ritmo do projeto:
  - `0.5s` entre solicitações
  - `2s` a cada `10` solicitações
  - retry limitado com espera quando houver `429 Too Many Requests`

### Uso Futuro

- Atualizar este arquivo quando houver mudança em:
  - header público `apx_s`
  - endpoints do `reporting`, `resource`, `legalentity` ou `fileRegistry`
  - shape da lista pública
  - identificadores público e interno
