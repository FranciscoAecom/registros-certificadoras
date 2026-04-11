# Mapeamento Inicial Silver da Climate Action Reserve

- Snapshot analisado: `20260325`
- Arquivos de detalhe disponiveis no snapshot: `1234`
- Arquivos de detalhe analisados na amostra: `124`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `62` maiores arquivos + `62` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260325`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 7 |
| Entidades Relacionadas | 5 | 5 |
| Localizacao | 6 | 3 |
| Datas | 8 | 5 |
| Quantidades e Indicadores | 7 | 1 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 124/124 | climate_action_reserve |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 124/124 | CAR | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 124/124 | CAR402 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 124/124 | 402 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 124/124 | https://thereserve2.apx.com/mymodule/reg/prjView.asp?id1=402 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 124/124 | data/project_standards/01_bronze/climate_action_reserve/20260325/projects/CAR402.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 124/124 | CAR402.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `Project Name` | direct | 124/124 | The Dry Creek Dairy BioFactory� Project |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | detail_data | `Project Status` | direct | 124/124 | Completed |  |
| `project_regulatory_status` | Identificacao do Projeto | mapped | list_data | `Compliance Program Status` | direct | 123/124 | Not ARB or WA ECO Eligible |  |
| `standard_program` | Identificacao do Projeto | mapped | source | `carbon_standard` | rename | 124/124 | climate_action_reserve |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `Project Description` | direct | 124/124 | This project entails the installation of an anaerobic digester at the Dry Creek dairy farm in Hansen, Idaho. The digester will capture me... |  |
| `project_methodology` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `project_type` | Identificacao do Projeto | mapped | detail_data | `Project Type` | direct | 124/124 | Livestock Gas Capture/Combustion |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | mapped | list_data | `SDG Impact` | normalized | 35/124 | ["3. Good Health and Well-Being", "6. Clean Water and Sanitation", "9. Industry, Innovation and Infrastructure", "13. Climate Action"] | Mantem o texto bruto de SDG Impact, dividido por ponto e virgula quando necessario. |
| `project_developer` | Entidades Relacionadas | mapped | list_data | `Project Developer` | direct | 124/124 | Camco International Group, Inc. |  |
| `project_owner` | Entidades Relacionadas | mapped | list_data | `Project Owner` | direct | 124/124 | Camco International Group, Inc. |  |
| `project_operator` | Entidades Relacionadas | mapped | list_data | `Offset Project Operator` | direct | 42/124 | Camco International Group, Inc. |  |
| `validator_name` | Entidades Relacionadas | mapped | list_data | `Verification Body` | direct | 41/124 | First Environment, Inc. |  |
| `verifier_name` | Entidades Relacionadas | mapped | list_data | `Verification Body` | direct | 41/124 | First Environment, Inc. |  |
| `country` | Localizacao | mapped | detail_data | `Country` | direct | 124/124 | US |  |
| `state_or_region` | Localizacao | mapped | list_data | `Project Site State` | direct | 124/124 | IDAHO |  |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 124/124 | 2026-03-25 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 124/124 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `Project Registered Date` | direct | 89/124 | 07/13/2010 |  |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | detail_data | `Project Reporting Start Date` | direct | 123/124 | 7/11/2008 |  |
| `crediting_end_date` | Datas | mapped | detail_data | `Crediting Period Expires` | direct | 74/124 | 6/12/2018 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | list_data | `Total Number of Offset Credits Registered ` | direct | 87/124 | 151565 |  |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/124 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Climate Action Reserve.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da climate_action_reserve, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Climate Action Reserve.
