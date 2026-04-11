# Integration Notes

## Cercarbono

### Visão Geral

- Certificadora: `cercarbono`
- Lista pública: `https://www.ecoregistry.io/projects-list/cercarbono-co2`
- Detalhe público: `https://www.ecoregistry.io/projects/<id>`
- Backend do frontend: `https://api-front.ecoregistry.io/platform`

### Endpoints Confirmados

- Lista:
  - `GET /project/public-by-standard/cercarbono-co2`
- Detalhe:
  - `GET /project/public/<id>`
- Metadados do padrão:
  - `GET /standard/cercarbono-co2`

### Identificadores

- `project_public_id`: campo `code` da lista, por exemplo `CDC-265`
- `project_internal_id`: campo `id` da lista, por exemplo `266`
- `project_url`: `https://www.ecoregistry.io/projects/<project_internal_id>`

### Observações

- A lista pública já retorna todos os projetos em um único payload JSON.
- O detalhe também retorna JSON diretamente, sem necessidade de navegador headless.
- Os endpoints exigem os headers usados pelo frontend, em especial:
  - `Platform: ecoregistry`
  - `Lng: en`
- Como esta integração não precisa de navegador nem sessão persistente, o teardown esperado é leve.
- Mesmo assim, os scripts usam um contexto gerenciado de encerramento para padronizar limpeza explícita e permitir evolução futura sem deixar recursos órfãos.

### Logging Operacional

- Falhas do `extract_project_list.py` devem ser persistidas em `logs/extract_project_list_failures_<YYYYMMDD>.json`.
- Falhas do `extract_project_details.py` devem ser persistidas em `logs/extract_project_details_failures_<YYYYMMDD>.json`.
- Em detalhe, falhas pontuais por projeto devem ser registradas sem interromper a execução dos próximos itens.
