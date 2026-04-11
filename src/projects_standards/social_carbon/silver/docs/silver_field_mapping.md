# Mapeamento Inicial Silver da Social Carbon

- Snapshot analisado: `20260326`
- Arquivos de detalhe disponiveis no snapshot: `18`
- Arquivos de detalhe analisados na amostra: `10`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `5` maiores arquivos + `5` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260326`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 8 |
| Entidades Relacionadas | 5 | 3 |
| Localizacao | 6 | 4 |
| Datas | 8 | 5 |
| Quantidades e Indicadores | 7 | 2 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 10/10 | social_carbon |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 10/10 | SC | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 10/10 | SOCIALCARBON-1 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 10/10 | 1663921969278x388468748169510900 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 10/10 | https://wilder.earth/project_details/socialcarbon-1-1663921969278x388468748169510900 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 10/10 | data/project_standards/01_bronze/social_carbon/20260326/projects/SOCIALCARBON-1.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 10/10 | SOCIALCARBON-1.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `Project Name` | direct | 10/10 | Spekboom Regeneration and Carbon Sequestration |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | detail_data | `Project Status` | direct | 10/10 | Listed |  |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | detail_data | `Standard` | direct | 10/10 | SOCIALCARBON |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `Description` | direct | 10/10 | Spekboom Net Zero (SNZ) is a large-scale carbon capture project in South Africa based on planting Portulacaria Afra (Spekboom) on selecte... |  |
| `project_methodology` | Identificacao do Projeto | mapped | detail_data | `Methodology` | normalized | 10/10 | SCM0004 | Separa multiplas metodologias quando a Social Carbon as expuser em uma unica string delimitada por virgula ou ponto e virgula. |
| `project_type` | Identificacao do Projeto | mapped | detail_data | `Project Type` | direct | 10/10 | Agriculture Forestry and Other Land Use |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | mapped | detail_data | `Project Type` | direct | 10/10 | Agriculture Forestry and Other Land Use |  |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | mapped | detail_data | `SDGs` | direct | 6/10 | ["1 - No Poverty", "2 - Zero Hunger", "3 - Good Health and Well-Being", "4 - Quality Education", "5 - Gender Equality", "8 - Decent Work ... |  |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `Project Proponent(s)_TEXT` | direct | 10/10 | ["Spekboom Net Zero (Pty) Ltd"] |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | mapped | detail_data | `validator` | direct | 9/10 | KBS Certification Services |  |
| `verifier_name` | Entidades Relacionadas | mapped | detail_data | `verifier` | direct | 9/10 | KBS Certification Services |  |
| `country` | Localizacao | mapped | detail_data | `Country` | direct | 10/10 | South Africa |  |
| `state_or_region` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | mapped | detail_data | `Latitude` | direct | 10/10 | -33.045952 |  |
| `location_longitude` | Localizacao | mapped | detail_data | `Longitude` | direct | 10/10 | 24.53583 |  |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 10/10 | 2026-03-26 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 10/10 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `Created Date` | direct | 10/10 | 2022-09-23T08:32:52.128Z |  |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | detail_data | `Crediting period start` | direct | 10/10 | 2023-01-31T22:00:00.000Z |  |
| `crediting_end_date` | Datas | mapped | detail_data | `Crediting period end` | direct | 10/10 | 2033-01-31T22:00:00.000Z |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | mapped | detail_data | `Estimated Annual Emission Reductions` | direct | 9/10 | 7224 |  |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | mapped | detail_data | `Total Project Area` | direct | 10/10 | 7311 |  |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Social Carbon.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da social_carbon, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Social Carbon.
