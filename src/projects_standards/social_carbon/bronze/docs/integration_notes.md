# Integration Notes

## Social Carbon Registry

### Visao Geral

- Certificadora: `social_carbon`
- Sigla de referencia sugerida: `SC`
- Status atual:
  - integracao validada
  - lista e detalhe implementados por Data API publica do Bubble

### URLs Publicas Confirmadas

- Lista publica:
  - `https://wilder.earth/social_carbon`
- Detalhe publico por projeto:
  - `https://wilder.earth/project_details/<project_id_lower>-<project_internal_id>`
- Exemplo validado de detalhe:
  - `https://wilder.earth/project_details/socialcarbon-18-1773423654292x760048670748834600`

### Endpoints Confirmados

- Lista por Data API publica:
  - `GET https://wilder.earth/api/1.1/obj/project`
- Detalhe por Data API publica:
  - `GET https://wilder.earth/api/1.1/obj/project/<project_internal_id>`
- Meta publica da API:
  - `GET https://wilder.earth/api/1.1/meta`

### Comportamento Observado do Frontend

- O site `wilder.earth` e uma aplicacao Bubble.
- A pagina de detalhe carrega shell HTML inicial e depois resolve dados da pagina.
- O endpoint `init/data` do Bubble funciona para a URL publica de detalhe, mas nao foi necessario para a coleta final.
- A lista publica `social_carbon` nao devolve itens por `init/data`; a fonte estavel da lista foi a Data API publica.
- A Data API publica de `project` ja retorna somente projetos com `Standard = SOCIALCARBON`.
- A pagina publica de detalhe segue o padrao:
  - `project_id` em minusculas
  - seguido de `-`
  - seguido do `_id` Bubble do projeto

### Decisao Atual

- A Social Carbon foi implementada sem navegador headless.
- `extract_project_list.py` usa `GET /api/1.1/obj/project` com constraint `Standard = SOCIALCARBON`.
- `extract_project_details.py` usa `GET /api/1.1/obj/project/<_id>`.
- O vinculo entre lista e detalhe usa:
  - `Project ID` como `project_public_id`
  - `_id` como `project_internal_id`

### Regras de Implementacao para esta Integracao

- Preservar o padrao `source`, `list_data` e `detail_data` na camada `bronze`.
- Manter o ritmo base do projeto:
  - `0.5s` entre solicitacoes
  - `2s` a cada `10` solicitacoes
  - retry limitado com espera quando houver `429 Too Many Requests`
- Nao voltar para scraping do DOM da pagina `social_carbon` enquanto a Data API publica continuar disponivel.

### Uso Futuro

- Atualizar este arquivo quando houver mudanca em:
  - endpoint `api/1.1/obj/project`
  - disponibilidade da Data API publica
  - shape dos campos `Project ID` e `_id`
  - regra publica de montagem da URL do detalhe
