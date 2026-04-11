# Integration Notes

## Plan Vivo

- Certificadora: `plan_vivo`
- Status atual:
  - integracao validada
  - lista e detalhe por HTML publico

### URLs Publicas

- Lista: `https://www.planvivo.org/projects/carbon?q=`
- Detalhe: `https://www.planvivo.org/projects/<project_slug>`

### Estrategia Atual

- A lista percorre a paginacao HTML e extrai os cards de projeto.
- O detalhe baixa o HTML publico do projeto e extrai blocos principais e documentos.

### Vinculacao

- `project_slug` como `project_public_id`
- `project_slug` como `project_internal_id`

### Regras de Manutencao

- Manter retry para `429 Too Many Requests`.
- Manter log operacional em `logs/`.
- Se a Plan Vivo expuser API publica estavel no futuro, preferir esse caminho ao parser HTML.
