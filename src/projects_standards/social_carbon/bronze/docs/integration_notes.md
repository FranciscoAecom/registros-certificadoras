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
  - legado indisponivel: `https://wilder.earth/social_carbon`
  - atual: `https://registry.socialcarbon.org`
- Detalhe publico por projeto:
  - legado: `https://wilder.earth/project_details/<project_id_lower>-<project_internal_id>`
  - atual: `https://registry.socialcarbon.org/project/<project_internal_id>`
- Exemplo validado de detalhe:
  - `https://registry.socialcarbon.org/project/1688063105941x728008407457202200`

### Endpoints Confirmados

- Lista por Data API publica:
  - legado indisponivel: `GET https://wilder.earth/api/1.1/obj/project`
  - atual: `GET https://registry.socialcarbon.org/api/1.1/obj/project`
- Detalhe por Data API publica:
  - legado: `GET https://wilder.earth/api/1.1/obj/project/<project_internal_id>`
  - atual: `GET https://registry.socialcarbon.org/api/1.1/obj/project/<project_internal_id>`
- Meta publica da API:
  - legado indisponivel: `GET https://wilder.earth/api/1.1/meta`
  - atual: `GET https://registry.socialcarbon.org/api/1.1/meta`
  - portal auxiliar: `GET https://portal.socialcarbon.org/api/1.1/meta`

### Comportamento Observado do Frontend

- `wilder.earth` deixou de responder por DNS em `2026-04-22`.
- `registry.socialcarbon.org` e `portal.socialcarbon.org` continuam ativos e sao aplicacoes Bubble.
- A Data API publica continua exposta nos dominios novos.
- `registry.socialcarbon.org/api/1.1/meta` expoe o objeto `project` e responde sem autenticacao.
- `portal.socialcarbon.org/api/1.1/meta` tambem expoe `project`, mas o detalhe por `_id` validado respondeu corretamente apenas no `registry`.
- A Data API publica de `project` em `registry.socialcarbon.org` retorna projetos `SOCIALCARBON` com os mesmos campos centrais observados no legado.
- A URL publica de detalhe validada no dominio novo usa apenas o `_id` Bubble do projeto:
  - `/project/<project_internal_id>`
- O campo `Project ID` continua presente na lista e no detalhe, mas ha registros em que ele pode vir nulo; o `_id` segue sendo a chave tecnica confiavel para o detalhe.
- Auditoria exploratoria de `2026-04-22`:
  - `registry.socialcarbon.org/api/1.1/obj/project` retornou `18` projetos publicados, todos com `Project ID` preenchido (`SOCIALCARBON-1` a `SOCIALCARBON-18`)
  - `portal.socialcarbon.org/api/1.1/obj/project` retornou `24` registros
  - esses `24` do portal incluem uma mistura de publicados, pre-registro e registros incompletos/rascunhos
  - o portal nao deve ser tratado como substituto direto do registro oficial

### Decisao Atual

- A Social Carbon foi implementada sem navegador headless.
- A integracao passa a usar `https://registry.socialcarbon.org` como dominio principal.
- `extract_project_list.py` usa `GET /api/1.1/obj/project` com constraint `Standard = SOCIALCARBON`.
- `extract_project_details.py` usa `GET /api/1.1/obj/project/<_id>`.
- O vinculo entre lista e detalhe usa:
  - `Project ID` como `project_public_id`
  - `_id` como `project_internal_id`
- O bronze oficial deve continuar vindo do `registry`.
- O `portal` deve ser usado apenas em coleta exploratoria separada, sem misturar seus registros ao bronze oficial enquanto nao houver regra canônica de inclusao.

### Regras de Implementacao para esta Integracao

- Preservar o padrao `source`, `list_data` e `detail_data` na camada `bronze`.
- Manter o ritmo base do projeto:
  - `0.5s` entre solicitacoes
  - `2s` a cada `10` solicitacoes
  - retry limitado com espera quando houver `429 Too Many Requests`
- Nao voltar para scraping do DOM da pagina `social_carbon` enquanto a Data API publica continuar disponivel.
- Manter `portal.socialcarbon.org` apenas como referencia auxiliar enquanto `registry.socialcarbon.org` continuar respondendo lista e detalhe.
- Quando houver necessidade de mapear pre-registro, rascunhos ou registros incompletos do portal, usar coleta exploratoria separada e salvar a saida em `logs/`, nunca em `data/project_standards/01_bronze/social_carbon/`.

### Uso Futuro

- Atualizar este arquivo quando houver mudanca em:
  - dominio principal do registry
  - endpoint `api/1.1/obj/project`
  - disponibilidade da Data API publica
  - shape dos campos `Project ID` e `_id`
  - regra publica de montagem da URL do detalhe
