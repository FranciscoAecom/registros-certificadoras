# Premissas do Projeto

## Escopo

Este projeto existe para armazenar scripts e dados brutos de extração de projetos de crédito de carbono por certificadora.

O foco atual é:

- American Carbon Registry
- BioCarbon
- Verra
- Gold Standard
- Cercarbono
- Equitable Earth
- TERO
- Social Carbon

## Modelo de Coleta

Cada certificadora deve seguir dois passos independentes:

1. Extração da lista completa de projetos.
2. Extração do detalhe de cada projeto a partir da lista já salva.

## Princípios de Arquitetura

- Separar código de dados.
- Separar lista de projetos de detalhe por projeto.
- Versionar o bruto por data de execução.
- Evitar acoplamento entre certificadoras.
- Permitir crescimento incremental por nova certificadora.
- Separar referências operacionais editáveis do dado bruto.
- Validar mapeamentos `bronze -> silver` com amostra representativa do snapshot, e não apenas por inspeção pontual.
- Separar descoberta exploratória de mapeamento e execução recorrente do mapeamento canônico.

## Estrutura de Código

```text
src/projects_standards/<certificadora>/bronze/extract_project_list.py
src/projects_standards/<certificadora>/bronze/extract_project_details.py
src/projects_standards/<certificadora>/bronze/docs/integration_notes.md
src/projects_standards/<certificadora>/bronze/logs/<arquivo_operacional>.json
src/projects_standards/<certificadora>/silver/build_silver_dataset.py
src/projects_standards/<certificadora>/silver/map_silver_fields.py
src/projects_standards/<certificadora>/silver/sync_status_reference.py
src/projects_standards/<certificadora>/silver/docs/<documento_transformacao>.md
src/projects_standards/<certificadora>/silver/logs/<arquivo_operacional>.json
src/projects_standards/shared/archive_data.py
src/projects_standards/shared/silver/framework.py
src/projects_standards/shared/silver/normalize.py
src/projects_standards/shared/silver/dates.py
src/projects_standards/shared/silver/text.py
src/projects_standards/shared/silver/numbers.py
src/projects_standards/shared/silver/missing.py
src/projects_standards/shared/silver/quality_checks.py
```

## Estrutura de Dados Brutos

```text
data/project_standards/01_bronze/<certificadora>/YYYYMMDD.zip
data/project_standards/01_bronze/<certificadora>/YYYYMMDD_core.zip
data/project_standards/01_bronze/<certificadora>/YYYYMMDD_core_001.zip
data/project_standards/01_bronze/<certificadora>/YYYYMMDD_spatial_001.zip
```

Em repouso, os snapshots ficam compactados como bundle. Durante a execução, o script descompacta para a estrutura interna:

```text
data/project_standards/01_bronze/<certificadora>/YYYYMMDD/
├── list/
│   └── projects.json
├── projects/
│   ├── <project_id>.json
│   └── ...
└── spatial/
    └── <project_id>/
        └── <arquivo_espacial>
```

Ao final, o script recompacta o snapshot e remove a pasta.

## Estrutura de Dados Silver

```text
data/project_standards/02_silver/<certificadora>/YYYYMMDD/allprojects.json
data/project_standards/02_silver/<certificadora>/YYYYMMDD/mapping_report.json
data/project_standards/02_silver/<certificadora>/YYYYMMDD/quality_report.json
```

## Estrutura de Dados Gold

```text
data/project_standards/03_gold/projects/allprojects.json
data/project_standards/03_gold/projects/schema.json
data/project_standards/03_gold/projects/quality_report.json
data/project_standards/03_gold/projects/backup/YYYYMMDDTHHMMSS/allprojects.json
data/project_standards/03_gold/projects/backup/YYYYMMDDTHHMMSS/quality_report.json
```

## Convenções da Gold

- A camada `gold` consolida todos os projetos `silver` em uma base unica.
- A unidade da `gold` e `1` projeto por `reference_month`.
- Quando houver mais de um registro do mesmo projeto no mesmo mes, deve prevalecer o registro mais atualizado do mes.
- A `gold` deve criar `project_history_id` e `record_id`.
- `project_history_id` deve concatenar `standard_acronym` e `project_internal_id` com `_`.
- `record_id` deve concatenar `standard_acronym`, `project_internal_id` e `reference_month` com `_`.
- SDGs da `gold` devem usar o mapeamento padronizado da referencia.
- O pais do projeto na `gold` deve usar o mapeamento padronizado da referencia.
- Metodologias devem ser relacionadas a `technical_area_id` e, por relacionamento, a `sectoral_scope_id`.
- A `gold` deve expor um unico `standard_reported_project_status` e um unico `standard_pipeline_status_id`.
- A `gold` deve ser sempre reconstruida integralmente.
- Antes de sobrescrever os arquivos finais da `gold`, os artefatos anteriores devem ser movidos para uma pasta timestampada em `backup/`.

## Estrutura de Referências

Referências editáveis por usuários devem ficar em planilhas:

```text
data/project_standards/00_reference/reference_dataset.xlsx
data/project_standards/00_reference/reference_dataset_maintenance.md
```

Esses arquivos são a base esperada para tabelas de apoio e `de_para` futuros.

## Decisões Importantes

- O snapshot temporal vem antes de `list/` e `projects/`.
- O snapshot é obrigatório porque a execução ocorre tipicamente no máximo uma vez por mês.
- `extract_project_details.py` deve receber a data da lista a ser consumida.
- O diretório de data não deve existir previamente por convenção manual. Ele nasce na execução.
- Em repouso, o formato preferencial do snapshot é o bundle:
  - `YYYYMMDD_core.zip` quando o core couber em um único arquivo
  - `YYYYMMDD_core_001.zip`, `YYYYMMDD_core_002.zip`, ... quando o core precisar ser particionado
  - `YYYYMMDD_spatial_001.zip`, `YYYYMMDD_spatial_002.zip`, ... para anexos espaciais quando existirem
- O arquivo simples `YYYYMMDD.zip` deve ser tratado como formato legado ainda aceito para leitura.
- A compactação e descompactação de snapshots são gerenciadas automaticamente pelos scripts de bronze e pelo framework da silver.
- As funções centralizadas de compactação e descompactação ficam em `src/projects_standards/shared/archive_data.py`.

## Regra para Dados Brutos

- A lista deve ser salva em um único arquivo `projects.json`.
- O detalhe deve ser salvo em vários arquivos, um por projeto.
- O bruto não deve ser normalizado nesta camada.
- O bruto não deve ser consolidado em um único arquivo de detalhes.
- O bruto de detalhe deve seguir a estrutura:
  - `source`
  - `list_data`
  - `detail_data`
- `source` deve conter, no mínimo, `carbon_standard`, `snapshot_date`, `reference_month`, `project_public_id`, `project_internal_id` e `project_url` quando ela existir.
- Em arquivos de detalhe, `carbon_standard` substitui o nome anterior `certificadora` dentro de `source`.
- `snapshot_date` deve ser salvo em formato ISO `YYYY-MM-DD`.
- `reference_month` deve registrar o primeiro dia do mes de `snapshot_date`, tambem em formato ISO `YYYY-MM-DD`.
- Quando a lista já trouxer `project_public_id` e `project_internal_id`, esses dois identificadores devem ser preservados no snapshot bruto e reutilizados pelo script de detalhe.
- `list_data` deve preservar o registro bruto vindo da lista.
- `detail_data` deve preservar o retorno bruto vindo do detalhe.
- Campos derivados como `combined_data`, `merged_data` ou equivalentes não devem existir na camada `bronze`.
- Logs operacionais da extra??o devem ficar em `src/projects_standards/<certificadora>/bronze/logs/`.
- Documentos auxiliares da extra??o por certificadora devem ficar em `src/projects_standards/<certificadora>/bronze/docs/`.
- `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md` deve concentrar descobertas estáveis e conhecimento curado da integração.
- Logs operacionais devem registrar contexto de execução, erro e evidências úteis para rerun ou diagnóstico.
- Em coletas por projeto, logs operacionais devem registrar falhas sem impedir a continuidade da lista quando isso for tecnicamente viável.
- Em integrações com navegador, sessão remota ou dependência externa instável, o script deve preferir retomar a execução automaticamente antes de abortar a coleta inteira.
- Em integrações sujeitas a rate limit, respostas como `429 Too Many Requests` devem acionar espera e retry limitado do mesmo item antes do registro da falha.
- O padrão base de ritmo do projeto deve buscar `0.5s` entre solicitações e `2s` a cada `10` solicitações, com possibilidade de endurecimento por certificadora quando necessário.
- Todo script que abrir recursos externos persistentes deve definir teardown explícito para encerrá-los ao final ou em interrupções.
- Navegador, subprocesso, sessão HTTP persistente, websocket, arquivo temporário e diretório temporário não podem ficar órfãos após a execução.

Motivos:

- facilita retomada
- facilita reprocessamento de um projeto específico
- reduz risco de perda total por falha
- melhora rastreabilidade

## Regra para Referências

- Referências editáveis por pessoas devem preferir `.xlsx`.
- JSON pode existir como apoio técnico ou etapa intermediária, mas o formato operacional preferencial é `.xlsx`.
- Cadastros como países, certificadoras e futuros `de_para` devem ser pensados para edição manual.
- Na referÃªncia `data/project_standards/00_reference/reference_dataset.xlsx`, a aba `standards_catalog` deve tratar `standard_acronym` como chave Ãºnica.
- Nenhuma certificadora nova pode ser adicionada com uma `sigla` já existente.

## Convenções de Scripts

- Todo script deve aceitar `--date`.
- Scripts de lista devem aceitar `--max-pages` para testes.
- Scripts de detalhe devem aceitar `--limit` para testes.
- Scripts devem expor parâmetros de ritmo de execução quando houver risco de bloqueio.
- Quando houver risco conhecido de `429 Too Many Requests`, os scripts devem expor parâmetros de retry e de espera entre tentativas.
- Sempre que houver paginação ou coleta por item, os defaults devem buscar o ritmo base do projeto, salvo exceção documentada para a certificadora.
- Scripts de detalhe devem exibir no terminal relatórios simples de progresso a cada `10` projetos concluídos, com percentual concluído e tempo restante estimado por média dos itens já processados.
- Todo script Python deve trazer no início do arquivo um comentário curto explicando o objetivo do script.
- Toda função deve trazer um comentário imediatamente acima da definição, explicando objetivamente sua responsabilidade no fluxo.
- Scripts devem trazer comentários curtos e objetivos nos trechos não triviais.
- Os comentários devem explicar a intenção do bloco, não repetir o código linha a linha.
- Comentários de arquivo e de função devem priorizar clareza operacional e intenção, evitando textos genéricos.
- Scripts com recursos externos persistentes devem mostrar no código, de forma legível, qual bloco é responsável pelo encerramento desses recursos.

## Convenções de Qualidade da Silver

- A camada `silver` pode aplicar padronização determinística e rastreável de valores vindos do `bronze`.
- Essa padronização não deve inventar valores nem alterar a semântica observada na fonte.
- Campos textuais devem passar por trim e redução de espaços excedentes quando isso não comprometer o significado original.
- Qualquer valor vazio, independentemente do tipo do campo, deve ser padronizado para `null` na `silver`.
- Isso inclui strings vazias, listas vazias, objetos vazios e marcadores usuais de ausência, como `N/A`, `NA`, `NONE`, `NULL` e equivalentes.
- Campos do tipo `date` devem usar `YYYY-MM-DD`.
- Campos do tipo `datetime`, quando existirem no schema ou nos metadados do dataset, devem usar `YYYY-MM-DDTHH:MM:SS`.
- Regras de parsing e padronização de datas devem ficar centralizadas em `src/projects_standards/shared/silver/dates.py`.
- Regras de tratamento textual devem ficar centralizadas em `src/projects_standards/shared/silver/text.py`.
- Regras de tratamento de ausências devem ficar centralizadas em `src/projects_standards/shared/silver/missing.py`.
- Regras numéricas compartilhadas devem ficar centralizadas em `src/projects_standards/shared/silver/numbers.py`.
- Validações leves de consistência da `silver` devem ficar centralizadas em `src/projects_standards/shared/silver/quality_checks.py`.

## Convenções de Mapeamento Bronze para Silver

- O mapeamento inicial de campos da camada `bronze` para a camada `silver` deve ser validado sobre uma amostra híbrida de pelo menos `10%` dos arquivos de detalhe disponíveis no snapshot.
- Quando `10%` do snapshot resultar em fração, o tamanho da amostra deve ser arredondado para cima.
- Quando o snapshot tiver poucos arquivos, a inspeção deve cobrir no mínimo `10` arquivos de detalhe, ou todos os arquivos quando o total for menor que `10`.
- A estratégia padrão dessa amostra híbrida deve combinar arquivos maiores do snapshot com uma parcela aleatória dos demais arquivos.
- O objetivo dessa amostra é reduzir falsos `unmapped`, isto é, casos em que um campo existe em outros projetos ou fases do programa, mas não apareceu nos poucos exemplos inspecionados inicialmente.
- A parte formada pelos maiores arquivos tende a aumentar a chance de capturar projetos com mais campos preenchidos.
- A parte aleatória tende a reduzir viés e preservar chance de capturar projetos menores, projetos mais simples ou registros de fases diferentes.
- Sempre que houver sinais de heterogeneidade no bruto, como status diferentes, tipos de projeto diferentes ou programas distintos, o agente deve preferir uma amostra híbrida com diversidade, em vez de depender apenas dos primeiros arquivos do diretório.
- Se o agente adotar uma estratégia melhor do que a regra híbrida padrão, como amostragem estratificada por status ou tipo, isso deve ser registrado explicitamente no documento de mapeamento gerado para a certificadora.
- O primeiro documento de mapeamento gerado para uma certificadora deve ser tratado como exploratório.
- Depois da revisão manual e do refinamento das regras, esse mapeamento deve ser promovido a mapeamento canônico da certificadora.
- O mapeamento canônico deve orientar as execuções recorrentes do processo `bronze -> silver`, de forma estável entre snapshots.
- O processo mensal não deve redescobrir o mapeamento do zero; ele deve reaplicar o mapeamento canônico vigente.
- Mudanças no mapeamento canônico devem ser conservadoras e motivadas por:
  - surgimento de novo campo relevante no bruto
  - mudança estrutural na certificadora
  - correção de regra anteriormente incorreta
- Quando houver manutenção do mapeamento canônico, a alteração deve ser documentada explicitamente no material da certificadora.
- A camada `silver` deve usar utilitários compartilhados centralizados em `src/projects_standards/shared/silver/` para regras transversais de qualidade e padronização.
- `src/projects_standards/shared/silver/framework.py` deve concentrar a orquestração compartilhada da geração do dataset e do mapeamento da `silver`.
- Parsing, normalização e validação da `silver` devem ficar separados em módulos próprios, evitando duplicação entre certificadoras.

## Convenções de Dependências

- Toda dependência Python externa precisa estar registrada em `requirements.txt`.
- Sempre que um agente adicionar uma nova biblioteca ao projeto, ele deve atualizar `requirements.txt` no mesmo trabalho.
- Se a dependência estiver ligada a uma decisão estrutural do projeto, essa decisão também deve ser refletida nos documentos de agentes.

## Convenções de Artefatos Temporários

- Arquivos temporários de pesquisa, inspeção, export local e depuração não devem permanecer no repositório ao final do trabalho.
- Se um agente precisar baixar HTML, CSV, JS, cookies ou outros artefatos auxiliares para investigação, ele deve removê-los depois do uso.
- Se houver recorrência desse tipo de arquivo, o agente deve ajustar o `.gitignore`.

## Convenções de Logging

Os scripts devem imprimir no terminal:

- início da execução
- parâmetros principais
- início de cada requisição relevante
- progresso acumulado
- percentual concluído e tempo estimado restante quando o fluxo percorrer itens ou páginas
- pausas intencionais
- resumo final
- quando houver retomada automática de sessão, registrar isso de forma explícita no terminal
- quando houver teardown relevante de sessão ou subprocesso, manter esse trecho claramente identificável no código

## Estratégia de Coleta

- Preferir endpoints oficiais ou usados pelo frontend.
- Evitar scraping de HTML quando a aplicação usa API.
- Quando não houver API pública utilizável, é aceitável renderizar a página em navegador headless e extrair o DOM final.
- Em SPAs públicas, o fallback preferencial deve ser automação conservadora do navegador, não parsing do HTML inicial sem renderização.
- Não paralelizar por padrão.
- Manter comportamento conservador para reduzir risco de bloqueio.

## Estado Atual das Certificadoras

### Verra

- Lista:
  - página: `https://registry.verra.org/app/search/VCS/All%20Projects`
  - endpoint: `POST https://registry.verra.org/uiapi/resource/resource/search`
- Detalhe:
  - página: `https://registry.verra.org/app/projectDetail/VCS/<id>`
  - endpoint: `GET https://registry.verra.org/uiapi/resource/resourceSummary/<id>`

### Gold Standard

- Lista:
  - página: `https://registry.goldstandard.org/projects?q=&page=1`
  - endpoint: `GET https://public-api.goldstandard.org/projects?page=<n>&size=<m>`
- Detalhe:
  - página: `https://registry.goldstandard.org/projects/details/<id>`
  - endpoint: `GET https://public-api.goldstandard.org/projects/<id>`

### Cercarbono

- Lista:
  - página: `https://www.ecoregistry.io/projects-list/cercarbono-co2`
  - endpoint: `GET https://api-front.ecoregistry.io/platform/project/public-by-standard/cercarbono-co2`
- Detalhe:
  - página: `https://www.ecoregistry.io/projects/<id>`
  - endpoint: `GET https://api-front.ecoregistry.io/platform/project/public/<id>`

### BioCarbon

- Lista:
  - página: `https://globalcarbontrace.io/registry/biocarbon/gei/projects`
  - endpoint: `GET https://api.globalcarbontrace.io/api/public/initiatives`
- Detalhe:
  - página: `https://globalcarbontrace.io/registry/biocarbon/gei/project/<id>`
  - endpoint: `GET https://api.globalcarbontrace.io/api/ghg/projects/<id>`
- Vinculação entre lista e detalhe:
  - a lista já expõe `project_id` como identificador público e `id` como identificador interno
  - o detalhe deve usar preferencialmente o `id` salvo no snapshot da lista, sem depender de navegação ou remapeamento em tempo de execução

### Equitable Earth

- Lista:
  - página: `https://registry.eq-earth.com/report/resource/PUBLIC/ERS_MEASUREMENT_STANDARD`
  - endpoint: `GET https://optimal-gateway.apx.com/reporting/api/resource/public`
- Detalhe:
  - página: `https://registry.eq-earth.com/dataroom/ERS/ERS_MEASUREMENT_STANDARD/byIdentifier/<project_internal_id>`
  - endpoint base: `GET https://optimal-gateway.apx.com/resource/resource/<id>/form/DATAROOM_ERS_MEASUREMENT_STANDARD`
- Observações:
  - a lista usa o header público `apx_s=ERS`
  - o detalhe usa o header público `apx_s=ERS`
  - o bundle de detalhe também consulta proponentes e arquivos públicos por endpoints separados do frontend

### American Carbon Registry

- Lista:
  - página: `https://acr2.apx.com/myModule/rpt/myrpt.asp?r=111`
  - endpoint: a própria página HTML, com paginação via `POST`
- Detalhe:
  - página: `https://acr2.apx.com/mymodule/reg/prjView.asp?id1=<id>`
  - documentos: `https://acr2.apx.com/mymodule/reg/TabDocuments.asp?...&id1=<id>`
- Observações:
  - a lista pública usa tabela HTML com paginação por formulário oculto
  - o detalhe público é HTML, não JSON
  - o vínculo correto é `Project ID` como identificador público e `id1` da URL como identificador interno

### TERO

- Lista:
  - página: `https://terocarbon.com/home/projetos/`
  - endpoint: `GET https://terocarbon.com/wp-json/wp/v2/project`
- Detalhe:
  - página: `https://terocarbon.com/project/<slug>/`
  - endpoint: `GET https://terocarbon.com/wp-json/wp/v2/project/<id>`
- Observações:
  - a integração usa o custom post type público `project` do WordPress REST
  - o detalhe reaproveita `id` salvo na lista como identificador interno
  - o HTML público do detalhe também é persistido porque `content.rendered` retorna shortcodes do Divi em vez do HTML final exibido

### Social Carbon

- Lista:
  - página: `https://wilder.earth/social_carbon`
  - endpoint: `GET https://wilder.earth/api/1.1/obj/project`
- Detalhe:
  - página: `https://wilder.earth/project_details/<project_id_lower>-<project_internal_id>`
  - endpoint: `GET https://wilder.earth/api/1.1/obj/project/<project_internal_id>`
- Observações:
  - a integração usa a Data API pública do Bubble exposta pelo próprio domínio `wilder.earth`
  - a lista filtra `Standard = SOCIALCARBON`
  - o detalhe reutiliza `_id` já salvo no snapshot da lista

## Dependências Atuais

- `pycountry`
  - geração da referência completa de países baseada em ISO 3166-1
- `openpyxl`
  - geração e manutenção de referências em `.xlsx`
- `websocket-client`
  - controle do navegador via DevTools Protocol em coletas de frontend dinâmico sem API pública utilizável

## Expectativa para Futuro

- Manter uma camada `bronze` confiável e reproduzível.
- Eventual consolidação ou tratamento deve ir para uma camada posterior.
- Toda nova certificadora deve entrar sem quebrar a simetria da estrutura existente.

## Regras para Dados Gold

- A camada `gold` deve consolidar uma base ?nica do projeto em `data/project_standards/03_gold/`.
- A temporalidade da `gold` deve ser registrada como campo do pr?prio dado, e n?o como parti??o obrigat?ria de pasta nesta fase.
- Regras de sele??o do registro mais atual do m?s por projeto e certificadora ser?o definidas e documentadas em etapa posterior.


- A referencia editavel de metodologias deve ficar na aba `methodologies` de `data/project_standards/00_reference/reference_dataset.xlsx`, com sincronizacao incremental a partir da camada `silver`.
- No schema canonico da `silver`, `project_methodology`, `sdg_targets` e `sector` devem ser sempre listas; quando nao houver valor confiavel, o campo deve ser `[]`.
- O `bronze` nao deve ser alterado para resolver ambiguidades numericas; esse tratamento deve acontecer apenas na camada `silver`.
- O parsing numerico da `silver` deve ser orientado por tipo canonico de campo, com distincao minima entre coordenadas, contagens/totais e medidas decimais.
- Quando uma certificadora usar convencao numerica diferente do padrao predominante, a regra deve ser implementada como override explicito no builder ou transformador daquele campo.
