# Mapeamento Inicial Silver da Cercarbono

- Snapshot analisado: `20260330`
- Arquivos de detalhe disponiveis no snapshot: `227`
- Arquivos de detalhe analisados na amostra: `23`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `12` maiores arquivos + `11` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260330`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 10 |
| Entidades Relacionadas | 5 | 3 |
| Localizacao | 6 | 6 |
| Datas | 8 | 5 |
| Quantidades e Indicadores | 7 | 1 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 23/23 | cercarbono |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 23/23 | CCR | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 23/23 | CDC-29 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 23/23 | 29 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 23/23 | https://www.ecoregistry.io/projects/29 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 23/23 | data/project_standards/01_bronze/cercarbono/20260330/projects/CDC-29.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 23/23 | CDC-29.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `project.name` | direct | 23/23 | PROYECTO ASOCIATIVO PROGRAMÁTICO ZONA ANDINA Y COSTA ATLÁNTICA - FCG |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | list_data | `projectStage` | direct | 23/23 | Certified |  |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | list_data | `standard` | direct | 23/23 | Cercarbono |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `project.descriptionProjectIng` | fallback | 23/23 | An Associative project combines multiple instances or phases (project areas) of project activity into a single combined initiative over a... | Prioriza a descricao em ingles do detalhe, com fallback para a descricao principal em espanhol. |
| `project_methodology` | Identificacao do Projeto | mapped | list_data | `methodology` | normalized | 23/23 | CCB - M/UT/F-A01: Methodology To Implement GHG Removal Projects Through Reforestation, Forest Restoration and the Establishment of Woody ... | Usa a lista estruturada de metodologias da Cercarbono. |
| `project_type` | Identificacao do Projeto | mapped | list_data | `methodology` | normalized | 14/23 | ARR | Usa o tipo de mecanismo da metodologia quando a Cercarbono o expuser. |
| `sector` | Identificacao do Projeto | mapped | list_data | `sectorsText` | direct | 23/23 | Land use (AFOLU) |  |
| `project_category` | Identificacao do Projeto | mapped | list_data | `methodology` | normalized | 23/23 | Removal | Usa a classificacao Avoidance ou Removal associada a metodologia. |
| `project_subcategories` | Identificacao do Projeto | mapped | list_data | `protocols` | normalized | 23/23 | PROTOCOL CVCC V2.1 | Usa os protocolos associados ao projeto como classificacao complementar. |
| `sdg_targets` | Identificacao do Projeto | mapped | list_data | `projectsGlobalGoal` | normalized | 21/23 | ["No poverty", "Education", "Gender equality", "Economic growth", "Climate action", "Life on land"] | Mantem a representacao textual bruta dos ODS expostos pela Cercarbono, pois o snapshot nao traz codigo estruturado de target. |
| `project_developer` | Entidades Relacionadas | mapped | list_data | `developer` | direct | 23/23 | Forestry Consulting Group S.A.S. |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | mapped | detail_data | `project.validator` | direct | 23/23 | Verifit |  |
| `verifier_name` | Entidades Relacionadas | mapped | detail_data | `project.verifier` | direct | 23/23 | ICONTEC |  |
| `country` | Localizacao | mapped | detail_data | `locations[*].countryDescription` | selection | 23/23 | Colombia | Seleciona o pais da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe. |
| `state_or_region` | Localizacao | mapped | detail_data | `locations[*].regionDescription` | selection | 23/23 | Antioquia | Seleciona a regiao da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe. |
| `city_or_locality` | Localizacao | mapped | detail_data | `locations[*].cityDescription` | selection | 23/23 | Santa Rosa de Osos | Seleciona a cidade ou localidade da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe. |
| `location_latitude` | Localizacao | mapped | detail_data | `locations[*].dataMap.latitude` | selection | 20/23 | 6.645850555246716 | Seleciona a coordenada da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe. |
| `location_longitude` | Localizacao | mapped | detail_data | `locations[*].dataMap.longitude` | selection | 20/23 | -75.4667427348153 | Seleciona a coordenada da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 23/23 | 2026-03-30 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 23/23 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `project.date` | direct | 23/23 | 2020-07-23 |  |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | detail_data | `project.periodInit` | direct | 23/23 | 2011-03-13 |  |
| `crediting_end_date` | Datas | mapped | detail_data | `project.periodEnd` | direct | 23/23 | 2060-03-12 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | detail_data | `certificatedVerification` | aggregate | 17/23 | 1942142 | Soma os totais de certificatedVerification para representar os creditos emitidos no snapshot. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/23 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Cercarbono.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da cercarbono, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Cercarbono.
