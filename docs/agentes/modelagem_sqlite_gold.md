# Modelagem SQLite Gold

## Resumo de Tabelas e Relacionamentos

### 📊 **Tabelas Principais**

#### **1. projects** (Tabela Central)
- **Chaves:** `record_id` (PK), `project_history_id` (AK)
- **Descrição:** Tabela principal com dados consolidados dos projetos (grão: 1 projeto por reference_month)
- **Relacionamentos:**
  - `standard_acronym` → **standards_catalog.standard_acronym** (N:1)
  - `country_standard` → **countries_standard.country_standard** (N:1)  
  - `standard_pipeline_status_id` → **common_pipeline_status.pipeline_status_id** (N:1)

#### **2. standards_catalog** (Certificadoras)
- **Chave:** `standard_acronym` (PK)
- **Descrição:** Catálogo de certificadoras de crédito de carbono
- **Relacionamentos:**
  - **projects** (1:N) - Uma certificadora tem muitos projetos
  - **standards_status** (1:N) - Uma certificadora tem múltiplos status

#### **3. methodologies** (Metodologias)
- **Chave:** `methodology_id` (PK)  
- **Descrição:** Metodologias de projetos de carbono
- **Relacionamentos:**
  - **project_methodologies** (1:N) - Uma metodologia pode estar em vários projetos
  - `technical_area_id` → **technical_areas.technical_area_id** (N:1)
  - `sectoral_scope_id` → **sectoral_scopes.sectoral_scope_id** (N:1)

#### **4. countries_standard** (Países Padronizados)
- **Chave:** `country_standard` (PK)
- **Descrição:** Lista padronizada de países
- **Relacionamentos:**
  - **projects** (1:N) - Um país pode ter muitos projetos
  - **countries_observed_mapping** (1:N) - Um país padrão mapeia várias formas observadas

#### **5. common_pipeline_status** (Status de Pipeline)
- **Chave:** `pipeline_status_id` (PK)
- **Descrição:** Status padronizados de pipeline de projetos
- **Relacionamentos:**
  - **projects** (1:N) - Um status pode estar em muitos projetos

### 📊 **Tabelas de Referência Secundárias**

#### **6. countries_observed_mapping** 
- **Chaves:** `country_raw` (PK), `country_standard` (FK)
- **Relacionamento:** N:1 com **countries_standard**
- **Descrição:** Mapeamento de formas brutas observadas para países padronizados

#### **7. standards_status**
- **Chaves:** `standard_acronym` (FK), `status_standard` (PK composta)
- **Relacionamento:** N:1 com **standards_catalog**
- **Descrição:** Status específicos por certificadora

#### **8. sdg_goals** (Objetivos de Desenvolvimento Sustentável)
- **Chave:** `sdg_goal_id` (PK)
- **Relacionamentos:**
  - **project_sdgs** (1:N) - Um objetivo SDG pode estar em vários projetos
  - **sdg_targets** (1:N) - Um objetivo tem múltiplos targets

#### **9. sdg_targets** 
- **Chaves:** `sdg_target_id` (PK), `sdg_goal_id` (FK)
- **Relacionamento:** N:1 com **sdg_goals**

#### **10. technical_areas**
- **Chave:** `technical_area_id` (PK)
- **Relacionamentos:**
  - **methodologies** (1:N) - Uma área técnica agrupa várias metodologias
  - `sectoral_scope_id` → **sectoral_scopes.sectoral_scope_id** (N:1)

#### **11. sectoral_scopes**
- **Chave:** `sectoral_scope_id` (PK)
- **Relacionamentos:**
  - **technical_areas** (1:N) - Um escopo setorial tem várias áreas técnicas
  - **methodologies** (1:N) - Um escopo setorial tem várias metodologias

### 📊 **Tabelas de Relacionamento (Many-to-Many)**

#### **12. project_methodologies**
- **Chaves:** `record_id` (FK), `methodology_name` (FK) - PK composta
- **Relacionamentos:** 
  - N:1 com **projects**
  - N:1 com **methodologies** (por nome da metodologia)
- **Descrição:** Relacionamento N:N entre projetos e metodologias

#### **13. project_subcategories** 
- **Chaves:** `record_id` (FK), `subcategory` (FK) - PK composta  
- **Relacionamento:** N:1 com **projects**
- **Descrição:** Subcategorias de cada projeto

#### **14. project_sectors**
- **Chaves:** `record_id` (FK), `sector` (FK) - PK composta
- **Relacionamento:** N:1 com **projects** 
- **Descrição:** Setores reportados pela certificadora para cada projeto

#### **15. project_sdgs**
- **Chaves:** `record_id` (FK), `sdg_goal_id` (FK) - PK composta
- **Relacionamentos:**
  - N:1 com **projects**
  - N:1 com **sdg_goals**
- **Descrição:** Relacionamento N:N entre projetos e objetivos SDG

### 🔗 **Resumo de Cardinalidades**

```
standards_catalog (1) ←→ (N) projects
countries_standard (1) ←→ (N) projects  
common_pipeline_status (1) ←→ (N) projects

standards_catalog (1) ←→ (N) countries_observed_mapping
standards_catalog (1) ←→ (N) standards_status

sectoral_scopes (1) ←→ (N) technical_areas
technical_areas (1) ←→ (N) methodologies
sectoral_scopes (1) ←→ (N) methodologies

sdg_goals (1) ←→ (N) sdg_targets
sdg_goals (1) ←→ (N) project_sdgs (N) ←→ (1) projects

projects (1) ←→ (N) project_methodologies (N) ←→ (1) methodologies
projects (1) ←→ (N) project_subcategories
projects (1) ←→ (N) project_sectors
```

---

*Esta modelagem normaliza os dados JSON da camada Gold em estrutura relacional SQLite, preservando integridade referencial e permitindo consultas eficientes.*

## Objetivo

Este documento define a modelagem relacional inicial do banco SQLite que armazenara a camada `gold` de projetos.

Ele existe para:

- documentar a normalizacao adotada
- evitar redundancia desnecessaria
- deixar claro o grao de cada entidade
- servir como base para o futuro `schema.sql` e para o builder `gold -> sqlite`

## Principios de Modelagem

- O SQLite deve nascer da `gold`, e nao diretamente da `silver` ou do `bronze`.
- A modelagem deve preservar o grao oficial da `gold`: `1` registro por projeto por `reference_month`.
- A identidade historica do projeto deve ficar separada do estado mensal do projeto.
- Campos multivalorados nao devem ser achatados como texto JSON quando houver relacao tabular clara.
- Tabelas de referencia devem ser armazenadas como entidades proprias, com chaves e relacionamentos.
- O banco deve minimizar duplicacao de texto e de chaves de negocio.

## Estrategia Geral

A modelagem inicial sera organizada em quatro grupos:

1. referencias
2. entidades centrais do projeto
3. tabelas relacionais do historico
4. metadados operacionais de carga

## Tabelas de Referencia

As referencias devem ser armazenadas de forma separada, para evitar repeticao e garantir consistencia relacional no SQLite.

Regra desta fase:

- nesta fase, a modelagem de referencia deve preservar integralmente os campos hoje existentes nas estruturas de referencia do projeto
- as tabelas abaixo devem espelhar integralmente os campos atuais definidos para as referencias do projeto, apenas com adaptacao semantica de nomenclatura para o banco
- simplificacoes so podem acontecer depois de uma decisao explicita de governanca

### Table: `ref_countries`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_standard_project_country_mapping` | `country_alpha_3` | `country_alpha_3` | `1:N` | um pais padronizado pode aparecer em varias formas observadas |
| `ref_standards` | `country_alpha_3` | `country_alpha_3` | `1:N` | um pais pode ser sede de varias standards |
| `project_history` | `country_alpha_3` | `country_alpha_3` | `1:N` | um pais pode estar associado a varios registros mensais de projeto |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `country_alpha_3` | `TEXT` | `PK` |  | codigo ISO alpha-3 do pais | chave principal da tabela de paises |
| `country_name_pt` | `TEXT` |  |  | nome padronizado do pais em portugues |  |
| `country_name_es` | `TEXT` |  |  | nome padronizado do pais em espanhol |  |
| `country_name_en` | `TEXT` |  |  | nome padronizado do pais em ingles | valor textual padrao esperado para exibicao |
| `country_alpha_2` | `TEXT` |  |  | codigo ISO alpha-2 do pais |  |
| `country_numeric_code` | `INTEGER` |  |  | codigo ISO numerico do pais |  |

### Table: `ref_standard_project_country_mapping`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_countries` | `country_alpha_3` | `country_alpha_3` | `N:1` | cada forma observada deve apontar para um pais padronizado |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `observed_project_country_name` | `TEXT` | `PK` |  | forma observada do pais nos projetos das standards |  |
| `standard_country_name` | `TEXT` |  |  | nome padronizado do pais associado ao valor observado | preservado para leitura humana |
| `country_alpha_3` | `TEXT` | `FK` | `ref_countries.country_alpha_3` | codigo ISO alpha-3 correspondente ao pais padronizado | coluna relacional recomendada para integridade referencial |

### Table: `ref_standards`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_countries` | `country_alpha_3` | `country_alpha_3` | `N:1` | cada standard aponta para um pais sede |
| `projects` | `standard_acronym` | `standard_acronym` | `1:N` | uma standard pode ter varios projetos |
| `ref_standard_project_status_mapping` | `standard_acronym` | `standard_acronym` | `1:N` | uma standard pode ter varios status mapeados |
| `ref_methodologies` | `standard_acronym` | `standard_acronym` | `1:N` | uma standard pode ter varias metodologias |
| `silver_datasets_scanned` | `standard_acronym` | `standard_acronym` | `1:N` | uma standard pode aparecer em varias leituras de dataset |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `standard_acronym` | `TEXT` | `PK` |  | sigla unica da standard |  |
| `standard_name` | `TEXT` |  |  | nome oficial ou preferencial da standard |  |
| `country_alpha_3` | `TEXT` | `FK` | `ref_countries.country_alpha_3` | pais da standard representado por codigo ISO alpha-3 |  |
| `standard_homepage_url` | `TEXT` |  |  | URL principal institucional da standard |  |
| `standard_projects_search_url` | `TEXT` |  |  | URL da pagina de busca ou lista de projetos |  |
| `project_details_url_template` | `TEXT` |  |  | template de URL para compor o detalhe publico do projeto |  |

### Table: `ref_common_pipeline_status`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_standard_project_status_mapping` | `pipeline_status_id` | `pipeline_status_id` | `1:N` | um status comum pode mapear varios status de standard |
| `project_history` | `pipeline_status_id` | `standard_pipeline_status_id` | `1:N` | um status comum pode aparecer em varios registros mensais |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `pipeline_status_id` | `TEXT` | `PK` |  | identificador canonico do status no pipeline comum |  |
| `pipeline_flow_order` | `INTEGER` |  |  | ordem sugerida de exibicao ou progressao do status |  |
| `pipeline_flow_type` | `TEXT` |  |  | categoria funcional do status no pipeline |  |
| `pipeline_status_name_pt` | `TEXT` |  |  | nome do status em portugues |  |
| `pipeline_status_name_en` | `TEXT` |  |  | nome do status em ingles |  |
| `pipeline_status_name_es` | `TEXT` |  |  | nome do status em espanhol |  |
| `pipeline_status_description_pt` | `TEXT` |  |  | descricao do status em portugues |  |
| `pipeline_status_description_en` | `TEXT` |  |  | descricao do status em ingles |  |
| `pipeline_status_description_es` | `TEXT` |  |  | descricao do status em espanhol |  |

### Table: `ref_standard_project_status_mapping`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_standards` | `standard_acronym` | `standard_acronym` | `N:1` | cada status pertence a uma standard |
| `ref_common_pipeline_status` | `pipeline_status_id` | `pipeline_status_id` | `N:1` | cada status mapeia para um pipeline comum |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `standard_acronym` | `TEXT` | `PK` | `ref_standards.standard_acronym` | sigla da standard dona do status | parte da PK composta |
| `project_market` | `TEXT` | `PK` |  | mercado ao qual o status se aplica | parte da PK composta; valores esperados: `voluntary`, `regulatory` |
| `standard_reported_project_status` | `TEXT` | `PK` |  | status original informado pela standard | parte da PK composta |
| `pipeline_status_id` | `TEXT` | `FK` | `ref_common_pipeline_status.pipeline_status_id` | status correspondente no pipeline comum |  |
| `standard_reported_project_status_description` | `TEXT` |  |  | descricao resumida do status informado pela standard |  |
| `official_status_definition` | `TEXT` |  |  | definicao oficial do status, quando houver |  |
| `status_source_url` | `TEXT` |  |  | URL da fonte utilizada para documentar o status |  |

### Table: `ref_sdg_goals`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_sdg_targets` | `sdg_goal_id` | `sdg_goal_id` | `1:N` | uma SDG pode ter varias metas |
| `ref_sdg_observed_mapping` | `sdg_goal_id` | `sdg_goal_id` | `1:N` | varias formas observadas podem apontar para a mesma SDG |
| `project_history_sdgs` | `sdg_goal_id` | `sdg_goal_id` | `1:N` | uma SDG pode estar ligada a varios registros de projeto |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `sdg_goal_id` | `INTEGER` | `PK` |  | identificador numerico da SDG |  |
| `sdg_goal_short_name` | `TEXT` |  |  | nome curto da SDG |  |
| `sdg_goal_name` | `TEXT` |  |  | nome completo da SDG |  |

### Table: `ref_sdg_targets`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_sdg_goals` | `sdg_goal_id` | `sdg_goal_id` | `N:1` | cada meta pertence a uma SDG |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `sdg_target_code` | `TEXT` | `PK` |  | codigo identificador da meta |  |
| `sdg_goal_id` | `INTEGER` | `FK` | `ref_sdg_goals.sdg_goal_id` | identificador da SDG dona da meta |  |
| `sdg_target_name` | `TEXT` |  |  | nome completo da meta |  |

### Table: `ref_sdg_observed_mapping`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_sdg_goals` | `sdg_goal_id` | `sdg_goal_id` | `N:1` | cada forma observada aponta para uma SDG padronizada |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `observed_project_sdg_value` | `TEXT` | `PK` |  | forma observada da SDG nos dados de origem |  |
| `observed_project_sdg_count` | `INTEGER` |  |  | quantidade de ocorrencias observadas para aquela forma |  |
| `sdg_goal_id` | `INTEGER` | `FK` | `ref_sdg_goals.sdg_goal_id` | identificador da SDG padronizada correspondente |  |

### Table: `ref_sectoral_scopes`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_technical_areas` | `sectoral_scope_id` | `sectoral_scope_id` | `1:N` | um escopo setorial pode conter varias areas tecnicas |
| `project_history_methodologies` | `sectoral_scope_id` | `sectoral_scope_id` | `1:N` | um escopo setorial pode aparecer em varias metodologias historicas |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `sectoral_scope_id` | `TEXT` | `PK` |  | identificador do escopo setorial |  |
| `sectoral_scope_name_en` | `TEXT` |  |  | nome completo do escopo em ingles |  |
| `sectoral_scope_name_pt` | `TEXT` |  |  | nome completo do escopo em portugues |  |
| `sectoral_scope_name_es` | `TEXT` |  |  | nome completo do escopo em espanhol |  |
| `sectoral_scope_short_name_en` | `TEXT` |  |  | nome curto do escopo em ingles |  |
| `sectoral_scope_short_name_pt` | `TEXT` |  |  | nome curto do escopo em portugues |  |
| `sectoral_scope_short_name_es` | `TEXT` |  |  | nome curto do escopo em espanhol |  |
| `source_document` | `TEXT` |  |  | nome do documento de origem da referencia |  |
| `source_table_name` | `TEXT` |  |  | nome da tabela de origem dentro do documento |  |
| `source_page_start` | `INTEGER` |  |  | pagina inicial da referencia no documento |  |
| `source_page_end` | `INTEGER` |  |  | pagina final da referencia no documento |  |
| `source_url` | `TEXT` |  |  | URL do documento ou fonte |  |

### Table: `ref_technical_areas`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_sectoral_scopes` | `sectoral_scope_id` | `sectoral_scope_id` | `N:1` | cada area tecnica pertence a um escopo setorial |
| `ref_methodologies` | `technical_area_id` | `technical_area_id` | `1:N` | uma area tecnica pode ser usada por varias metodologias |
| `project_history_methodologies` | `technical_area_id` | `technical_area_id` | `1:N` | uma area tecnica pode aparecer em varias metodologias historicas |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `technical_area_id` | `TEXT` | `PK` |  | identificador da area tecnica |  |
| `sectoral_scope_id` | `TEXT` | `FK` | `ref_sectoral_scopes.sectoral_scope_id` | escopo setorial ao qual a area tecnica pertence |  |
| `technical_area_name_en` | `TEXT` |  |  | nome completo da area tecnica em ingles |  |
| `technical_area_name_pt` | `TEXT` |  |  | nome completo da area tecnica em portugues |  |
| `technical_area_name_es` | `TEXT` |  |  | nome completo da area tecnica em espanhol |  |
| `technical_area_short_name_en` | `TEXT` |  |  | nome curto da area tecnica em ingles |  |
| `technical_area_short_name_pt` | `TEXT` |  |  | nome curto da area tecnica em portugues |  |
| `technical_area_short_name_es` | `TEXT` |  |  | nome curto da area tecnica em espanhol |  |
| `typical_activities_and_ghg_en` | `TEXT` |  |  | descricao das atividades tipicas e GEE em ingles |  |
| `typical_activities_and_ghg_pt` | `TEXT` |  |  | descricao das atividades tipicas e GEE em portugues |  |
| `typical_activities_and_ghg_es` | `TEXT` |  |  | descricao das atividades tipicas e GEE em espanhol |  |
| `technical_knowledge_en` | `TEXT` |  |  | descricao do conhecimento tecnico exigido em ingles |  |
| `technical_knowledge_pt` | `TEXT` |  |  | descricao do conhecimento tecnico exigido em portugues |  |
| `technical_knowledge_es` | `TEXT` |  |  | descricao do conhecimento tecnico exigido em espanhol |  |
| `source_document` | `TEXT` |  |  | nome do documento de origem da referencia |  |
| `source_table_name` | `TEXT` |  |  | nome da tabela de origem dentro do documento |  |
| `source_page_start` | `INTEGER` |  |  | pagina inicial da referencia no documento |  |
| `source_page_end` | `INTEGER` |  |  | pagina final da referencia no documento |  |
| `source_url` | `TEXT` |  |  | URL do documento ou fonte |  |

### Table: `ref_methodologies`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_standards` | `standard_acronym` | `standard_acronym` | `N:1` | cada metodologia pertence a uma standard |
| `ref_technical_areas` | `technical_area_id` | `technical_area_id` | `N:1` | cada metodologia aponta para uma area tecnica padronizada |
| `project_history_methodologies` | `methodology_name` | `methodology_name` | `1:N` | relacionamento potencial; depende de coluna adicional de standard para FK composta completa |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `standard_acronym` | `TEXT` | `PK` | `ref_standards.standard_acronym` | sigla da standard dona da metodologia | parte da PK composta |
| `methodology_name` | `TEXT` | `PK` |  | nome da metodologia na referencia consolidada | parte da PK composta |
| `methodology_description` | `TEXT` |  |  | descricao resumida da metodologia |  |
| `methodology_source_url` | `TEXT` |  |  | URL da fonte da metodologia ou da descricao |  |
| `technical_area_id` | `TEXT` | `FK` | `ref_technical_areas.technical_area_id` | area tecnica padronizada associada a metodologia |  |

Justificativa:

- a metodologia e especifica da standard
- o mapeamento para `technical_area_id` deve ficar centralizado na referencia

## Entidades Centrais

### Table: `projects`

Representa a identidade historica do projeto ao longo do tempo.

Grao:

- `1` linha por `project_history_id`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `ref_standards` | `standard_acronym` | `standard_acronym` | `N:1` | cada projeto pertence a uma standard |
| `project_history` | `project_history_id` | `project_history_id` | `1:N` | um projeto pode ter varios registros historicos mensais |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `project_history_id` | `TEXT` | `PK` |  | identificador historico do projeto ao longo do tempo | formado por `standard_acronym + "_" + project_internal_id` |
| `standard_acronym` | `TEXT` | `FK` | `ref_standards.standard_acronym` | sigla da standard dona do projeto |  |
| `project_internal_id` | `TEXT` |  |  | identificador interno do projeto na standard | faz parte da composicao da chave historica |
| `project_public_id` | `TEXT` |  |  | identificador publico do projeto, quando existir | pode ser nulo |
| `project_url` | `TEXT` |  |  | URL publica principal do projeto | pode ser nula ou variar no tempo no futuro |

Justificativa:

- esses campos identificam o projeto ao longo da historia
- nao representam um estado mensal
- evitam repeticao em todos os snapshots

### Table: `project_history`

Representa o estado do projeto em um `reference_month`.

Grao:

- `1` linha por `project_history_record_id`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `projects` | `project_history_id` | `project_history_id` | `N:1` | cada registro historico pertence a um projeto |
| `ref_common_pipeline_status` | `standard_pipeline_status_id` | `pipeline_status_id` | `N:1` | cada registro pode apontar para um status do pipeline comum |
| `ref_countries` | `country_alpha_3` | `country_alpha_3` | `N:1` | cada registro pode apontar para um pais padronizado |
| `project_history_methodologies` | `project_history_record_id` | `project_history_record_id` | `1:N` | um registro historico pode ter varias metodologias |
| `project_history_sdgs` | `project_history_record_id` | `project_history_record_id` | `1:N` | um registro historico pode ter varias SDGs |
| `project_history_sectors` | `project_history_record_id` | `project_history_record_id` | `1:N` | um registro historico pode ter varios setores reportados |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `project_history_record_id` | `TEXT` | `PK` |  | identificador unico do registro mensal do projeto | corresponde ao `record_id` da gold JSON |
| `project_history_id` | `TEXT` | `FK` | `projects.project_history_id` | identificador historico do projeto | liga o estado mensal ao projeto |
| `reference_month` | `DATE` |  |  | primeiro dia do mes de referencia do registro | grao temporal oficial da gold |
| `snapshot_date` | `DATE` |  |  | data do snapshot vencedor dentro do mes |  |
| `gold_selected_from_snapshot` | `TEXT` |  |  | token do snapshot silver escolhido na deduplicacao mensal | valor atual no formato `YYYYMMDD`; pode ser renomeado depois |
| `bronze_file_path` | `TEXT` |  |  | caminho do arquivo de origem no bronze | lineage operacional |
| `source_file_name` | `TEXT` |  |  | nome do arquivo de origem | lineage operacional |
| `standard_name` | `TEXT` |  |  | nome da standard no momento do snapshot | redundancia controlada para leitura analitica |
| `project_name` | `TEXT` |  |  | nome do projeto no snapshot | pode mudar ao longo do tempo |
| `project_description` | `TEXT` |  |  | descricao do projeto no snapshot | pode mudar ao longo do tempo |
| `standard_program` | `TEXT` |  |  | programa ou iniciativa da standard associada ao projeto | pode ser nulo |
| `project_market` | `TEXT` |  |  | mercado efetivo do projeto no snapshot | valores esperados: `voluntary`, `regulatory` |
| `standard_reported_project_status` | `TEXT` |  |  | status informado pela standard para o mercado efetivo | valor de negocio observado ou derivado da gold |
| `standard_pipeline_status_id` | `TEXT` | `FK` | `ref_common_pipeline_status.pipeline_status_id` | identificador do pipeline comum correspondente ao status | pode ser nulo se a referencia ainda nao mapear |
| `project_type` | `TEXT` |  |  | tipo do projeto no snapshot |  |
| `project_category` | `TEXT` |  |  | categoria principal do projeto no snapshot |  |
| `project_developer` | `TEXT` |  |  | entidade desenvolvedora do projeto | pode mudar ao longo do tempo |
| `project_owner` | `TEXT` |  |  | entidade proprietaria do projeto | pode mudar ao longo do tempo |
| `project_operator` | `TEXT` |  |  | entidade operadora do projeto | pode mudar ao longo do tempo |
| `validator_name` | `TEXT` |  |  | entidade validadora do projeto |  |
| `verifier_name` | `TEXT` |  |  | entidade verificadora do projeto |  |
| `country_standard` | `TEXT` |  |  | nome padronizado do pais do projeto para leitura humana | complementar a `country_alpha_3` |
| `country_alpha_3` | `TEXT` | `FK` | `ref_countries.country_alpha_3` | codigo ISO alpha-3 do pais padronizado do projeto | coluna recomendada para integridade referencial |
| `state_or_region` | `TEXT` |  |  | estado, provincia ou regiao do projeto |  |
| `city_or_locality` | `TEXT` |  |  | cidade ou localidade do projeto |  |
| `location_latitude` | `REAL` |  |  | latitude do projeto | pode ser nula |
| `location_longitude` | `REAL` |  |  | longitude do projeto | pode ser nula |
| `project_geometry` | `TEXT` |  |  | geometria do projeto em formato GeoJSON serializado (Point/Polygon/MultiPolygon) | pode ser nula quando a fonte nao expuser geometria |
| `registration_date` | `DATE` |  |  | data de registro do projeto |  |
| `status_date` | `DATE` |  |  | data associada ao status do projeto |  |
| `crediting_start_date` | `DATE` |  |  | inicio do periodo de creditacao |  |
| `crediting_end_date` | `DATE` |  |  | fim do periodo de creditacao |  |
| `first_issuance_date` | `DATE` |  |  | primeira data de emissao conhecida |  |
| `last_issuance_date` | `DATE` |  |  | ultima data de emissao conhecida |  |
| `credits_issued_total` | `REAL` |  |  | total de creditos emitidos no snapshot | pode ser inteiro na pratica, mas `REAL` preserva consistencia numerica |
| `credits_retired_total` | `REAL` |  |  | total de creditos aposentados no snapshot |  |
| `credits_cancelled_total` | `REAL` |  |  | total de creditos cancelados no snapshot |  |
| `credits_buffer_total` | `REAL` |  |  | total de creditos em buffer no snapshot |  |
| `estimated_annual_emission_reductions` | `REAL` |  |  | reducoes anuais estimadas de emissoes |  |
| `estimated_total_emission_reductions` | `REAL` |  |  | reducoes totais estimadas de emissoes |  |
| `area_hectares` | `REAL` |  |  | area do projeto em hectares |  |

Justificativa:

- esses campos representam o estado do projeto naquele mes
- status, descricao, localizacao, datas e metricas podem mudar no tempo
- o historico mensal e a entidade correta para armazenar essa variacao temporal

## Tabelas Relacionais do Historico

### Table: `project_history_methodologies`

Representa as metodologias do registro historico do projeto.

Grao:

- `N` linhas por `project_history_record_id`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `project_history` | `project_history_record_id` | `project_history_record_id` | `N:1` | cada metodologia historica pertence a um registro mensal |
| `ref_technical_areas` | `technical_area_id` | `technical_area_id` | `N:1` | cada metodologia pode apontar para uma area tecnica |
| `ref_sectoral_scopes` | `sectoral_scope_id` | `sectoral_scope_id` | `N:1` | cada metodologia pode apontar para um escopo setorial derivado |
| `ref_methodologies` | `methodology_name` | `methodology_name` | `N:1` | relacionamento potencial; idealmente deve usar tambem `standard_acronym` para FK composta completa |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `project_history_record_id` | `TEXT` | `PK, FK` | `project_history.project_history_record_id` | identificador do registro mensal do projeto | parte da PK composta |
| `methodology_sequence` | `INTEGER` | `PK` |  | ordem da metodologia dentro da lista do snapshot | parte da PK composta; preserva ordenacao da fonte |
| `standard_acronym` | `TEXT` |  | `ref_standards.standard_acronym` | sigla da standard dona da metodologia observada | ajuda a viabilizar FK composta futura com `ref_methodologies` |
| `methodology_name` | `TEXT` |  |  | metodologia associada ao projeto naquele snapshot | corresponde ao nome observado ou padronizado na gold |
| `technical_area_id` | `TEXT` | `FK` | `ref_technical_areas.technical_area_id` | area tecnica associada a metodologia | hoje pode ser nula em placeholders |
| `sectoral_scope_id` | `TEXT` | `FK` | `ref_sectoral_scopes.sectoral_scope_id` | escopo setorial derivado da atividade tecnica | redundancia controlada para consumo analitico |

Justificativa:

- um registro historico pode ter varias metodologias
- cada metodologia pode apontar para uma atividade tecnica
- o escopo setorial e derivado no nivel da metodologia

Observacao:

- `sectoral_scope_id` pode ficar aqui por conveniencia analitica, embora seja derivavel por `technical_area_id`
- se quisermos um modelo mais estrito, podemos guardar apenas `technical_area_id`

### Table: `project_history_sdgs`

Representa as SDGs padronizadas do registro historico.

Grao:

- `N` linhas por `project_history_record_id`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `project_history` | `project_history_record_id` | `project_history_record_id` | `N:1` | cada SDG historica pertence a um registro mensal |
| `ref_sdg_goals` | `sdg_goal_id` | `sdg_goal_id` | `N:1` | cada relacao aponta para uma SDG padronizada |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `project_history_record_id` | `TEXT` | `PK, FK` | `project_history.project_history_record_id` | identificador do registro mensal do projeto | parte da PK composta |
| `sdg_goal_id` | `INTEGER` | `PK, FK` | `ref_sdg_goals.sdg_goal_id` | SDG padronizada associada ao registro historico do projeto | parte da PK composta |

Justificativa:

- SDG e multivalorado
- nao faz sentido armazenar lista serializada no banco relacional

### Table: `project_history_sectors`

Representa os setores informados pela standard no registro historico.

Grao:

- `N` linhas por `project_history_record_id`

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `project_history` | `project_history_record_id` | `project_history_record_id` | `N:1` | cada setor historico pertence a um registro mensal |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `project_history_record_id` | `TEXT` | `PK, FK` | `project_history.project_history_record_id` | identificador do registro mensal do projeto | parte da PK composta |
| `standard_reported_sector` | `TEXT` | `PK` |  | setor informado pela standard para aquele registro historico | parte da PK composta |

Justificativa:

- `standard_reported_sector` e lista observada
- o valor e reportado pela standard e pode ter mais de um item

## Metadados Operacionais

### Table: `gold_build_runs`

Opcional na primeira versao, mas recomendado.

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `silver_datasets_scanned` | `build_id` | `build_id` | `1:N` | uma execucao pode consumir varios datasets silver |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `build_id` | `TEXT` | `PK` |  | identificador unico da execucao de build da gold | pode ser timestamp ou UUID |
| `generated_at` | `DATETIME` |  |  | data e hora da geracao da build |  |
| `source_datasets_scanned` | `INTEGER` |  |  | quantidade de datasets silver lidos na execucao |  |
| `source_projects_scanned` | `INTEGER` |  |  | quantidade total de projetos lidos antes da deduplicacao |  |
| `gold_projects_generated` | `INTEGER` |  |  | quantidade final de registros gerados na gold |  |
| `backup_created` | `TEXT` |  |  | caminho do backup criado para a execucao | pode ser nulo quando nao houver artefato anterior |

### Table: `silver_datasets_scanned`

Opcional na primeira versao, mas recomendado.

Relacionamentos:

| related_table | local_field | related_field | cardinality | notes |
|---|---|---|---|---|
| `gold_build_runs` | `build_id` | `build_id` | `N:1` | cada dataset lido pertence a uma execucao de build |
| `ref_standards` | `standard_acronym` | `standard_acronym` | `N:1` | cada dataset lido pertence a uma standard |

| field_name | logical_type | key_role | references | description | observations |
|---|---|---|---|---|---|
| `build_id` | `TEXT` | `FK` | `gold_build_runs.build_id` | identificador da execucao que consumiu o dataset silver |  |
| `dataset_path` | `TEXT` | `PK` |  | caminho do dataset silver lido na execucao | pode compor PK com `build_id` se a mesma fonte puder aparecer em builds diferentes |
| `standard_acronym` | `TEXT` | `FK` | `ref_standards.standard_acronym` | sigla da standard dona do dataset silver |  |
| `snapshot_date` | `DATE` |  |  | data do snapshot silver |  |
| `generated_at` | `DATETIME` |  |  | data e hora de geracao do dataset silver |  |
| `project_count` | `INTEGER` |  |  | quantidade de projetos presentes no dataset silver |  |

## Decisoes Ja Assumidas

- `project_history_record_id` substitui `record_id` como chave da tabela `project_history`.
- `project_history_id` continua sendo a chave historica do projeto.
- `standard_reported_project_status` fica em `project_history`, nao na entidade historica `projects`.
- `standard_reported_sector` nao deve ficar serializado na tabela principal; deve virar tabela filha do historico.
- metodologias devem ficar em tabela filha do historico.
- SDGs devem ficar em tabela filha do historico.
- paises devem se relacionar por `country_alpha_3`.
- tabelas e campos de referencia devem usar nomes semanticos e autoexplicativos no SQLite.

## Questao em Aberto para Fechamento

Ainda precisamos decidir se:

1. `gold_selected_from_snapshot` sera mantido com esse nome
2. ou se renomearemos para algo mais explicito sobre o snapshot silver vencedor da deduplicacao mensal

Minha recomendacao atual:

- o campo pode continuar nesta primeira versao porque ja esta bem compreendido na regra da gold
- se quisermos maior clareza semantica depois, podemos migrar para algo como `selected_silver_snapshot_token`

## Proximo Passo Recomendado

Depois de validar esta modelagem conceitual, o proximo passo natural e criar:

1. o modelo logico final com PKs e FKs fechadas
2. o `schema.sql`
3. o builder `gold -> sqlite`
