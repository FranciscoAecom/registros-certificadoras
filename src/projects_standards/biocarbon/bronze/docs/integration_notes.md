# Integration Notes

## BioCarbon Registry

### Visão Geral

- Certificadora: `biocarbon`
- Lista pública: `https://globalcarbontrace.io/registry/biocarbon/gei/projects`
- Detalhe público: `https://globalcarbontrace.io/registry/biocarbon/gei/project/<detail_id>`
- Estratégia atual:
  - lista por API pública consumida pelo frontend
  - detalhe por API pública consumida pelo frontend

### Motivo da Estratégia

- A coleta atual de lista e detalhe usa os endpoints públicos identificados no bundle JS do frontend.
- O parâmetro `language` da API substitui a necessidade de clique na interface pública para fixar idioma.
- A lista já retorna o `id` interno do projeto junto com o `project_id` público, então o detalhe deve consumir esse `id` diretamente do snapshot salvo.

### Endpoints Confirmados

- Lista pública auxiliar da API:
  - `GET https://api.globalcarbontrace.io/api/public/initiatives?language=<lang>&per_page=<n>`
- Detalhe:
  - `GET https://api.globalcarbontrace.io/api/ghg/projects/<id>?language=<lang>`
- Créditos emitidos por projeto:
  - `GET https://api.globalcarbontrace.io/api/ghg/carbon-credits/project/<id>?sortField=created_at&sortDirection=desc&per_page=100`
- Retreats por projeto:
  - `GET https://api.globalcarbontrace.io/api/ghg/retreats/project/<id>?sortField=created_at&sortDirection=desc`
- A API pública usada pelo frontend exige header `x-api-key` exposto no bundle da aplicação.

### Riscos e Comportamentos Observados

- A API pública exige header `x-api-key` exposto no bundle do frontend atual.
- Lista e detalhe deixaram de depender de navegador, clique de idioma e renderização do DOM.
- Após a migração da lista para o bruto da API, o acoplamento correto entre lista e detalhe passa a ser `project_id` como identificador público e `id` como identificador interno.
- Regressões podem ocorrer se o script de detalhe voltar a assumir o shape antigo de cards renderizados (`card_title`, `card_id`, `card_holder`) em vez do shape bruto da API.
- A coleta de detalhe da BioCarbon usa cadência mais conservadora que o mínimo geral do projeto: `1s` entre projetos e `2s` a cada `10` projetos.
- Quando a API retornar `429 Too Many Requests`, o script deve aguardar `5s` e tentar novamente o mesmo projeto, com até `3` tentativas adicionais antes de registrar falha e seguir.
- Mudanças futuras no bundle podem trocar a chave pública ou os endpoints e exigirão nova validação.

### Logging Operacional

- Falhas de execução do `extract_project_list.py` são persistidas em `src/projects_standards/biocarbon/bronze/logs/`.
- O arquivo atual segue o padrão `extract_project_list_failures_<YYYYMMDD>.json`.
- Falhas de execução do `extract_project_details.py` são persistidas em `src/projects_standards/biocarbon/bronze/logs/`.
- O arquivo atual segue o padrão `extract_project_details_failures_<YYYYMMDD>.json`.
- O `source` dos detalhes usa `project_public_id` para o código público do card, `project_internal_id` para o identificador numérico da URL e `project_url` para a URL pública do projeto.
- O `list_data` salvo pela lista deve permanecer no shape bruto da API pública, incluindo `id`, `project_id`, `project_name` e `holder_name`.
- Cada falha deve registrar:
  - projeto
  - estágio da falha
  - tipo e mensagem do erro
  - traceback
- Quando houver coleta de detalhe por API, registrar também o endpoint usado na metadata de `source` quando isso ajudar manutenção.

### Uso Futuro

- Atualizar este arquivo quando houver descoberta estável sobre DOM, paginação, idioma ou fluxo de navegação.
- Não registrar aqui logs extensos de execução; esses devem ficar no diretório `logs/`.
