# Integration Notes

## Puro.earth

- Certificadora: `puro_earth`
- Status atual:
  - integracao validada
  - lista e detalhe por payloads embutidos no HTML do frontend

### URLs Publicas

- Lista: `https://registry.puro.earth/projects`
- Detalhe: `https://registry.puro.earth/projects/<projectId>`

### Estrategia Atual

- A lista extrai o array de projetos embutido no HTML do frontend.
- O detalhe baixa o HTML publico do projeto e extrai overview, transacoes e documentos.

### Vinculacao

- `projectId` como `project_public_id`
- `projectId` como `project_internal_id`

### Regras de Manutencao

- Manter retry para `429 Too Many Requests`.
- Manter log operacional em `logs/`.
- Se a Puro.earth voltar a expor endpoint JSON estavel, preferir esse caminho ao payload embutido.
