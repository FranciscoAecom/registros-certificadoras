# Integration Notes

## Gold Standard

- Certificadora: `gold_standard`
- Status atual:
  - integracao validada
  - lista e detalhe por API publica da registry

### URLs Publicas

- Lista: `https://registry.goldstandard.org/projects?q=&page=1`
- Detalhe: `https://registry.goldstandard.org/projects/details/<id>`

### Endpoints

- Lista: `GET https://public-api.goldstandard.org/projects?page=<n>&size=<m>`
- Detalhe: `GET https://public-api.goldstandard.org/projects/<id>`
- Resumo de creditos do projeto: `GET https://public-api.goldstandard.org/projects/<id>/credits/summary`

### Vinculacao

- `id` como `project_internal_id`
- `GS + sustaincert_id` como `project_public_id`
- Exemplo validado em `id=309`: `sustaincert_id=2290` resulta em `project_public_id=GS2290`

### Regras de Manutencao

- Manter retry para `429 Too Many Requests`.
- Manter log operacional em `logs/`.
- Priorizar a API publica da Gold Standard em vez de scraping do frontend.
- O endpoint principal de detalhe nao traz os totais exibidos como `ISSUED` e `RETIRED`; esses valores devem ser coletados em `credits/summary`.
- O script operacional de detalhe usa somente `projects/<id>` e `projects/<id>/credits/summary`, reduzindo volume de chamadas e risco de `429`.
- Em caso de `429`, o script deve respeitar `Retry-After` quando presente e aplicar espera crescente por tentativa.
- O fluxo de detalhe deve manter pequena pausa entre as chamadas internas do mesmo projeto, evitando disparos consecutivos no mesmo identificador.
