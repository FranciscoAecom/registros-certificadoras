# Integration Notes

## Isometric

- Certificadora: `isometric`
- Status atual:
  - integracao validada
  - lista e detalhe por endpoint GraphQL publico usado pelo frontend

### URLs Publicas

- Lista: `https://registry.isometric.com/?tab=projects`
- Detalhe: `https://registry.isometric.com/project/<id>`

### Endpoints

- Lista e detalhe: `POST https://edge.isometric.com`

### Queries

- Lista: `RegistryHomePage_ProjectsQuery`
- Detalhe: `ProjectDetails`

### Vinculacao

- `id` como `project_public_id`
- `id` como `project_internal_id`

### Regras de Manutencao

- Manter retry para `429 Too Many Requests`.
- Manter log operacional em `logs/`.
- Preservar os filtros de status usados na query da lista.
