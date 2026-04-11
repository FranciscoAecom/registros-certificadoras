# Mapeamento Inicial Silver da American Carbon Registry

- Snapshot analisado: `20260327`
- Arquivos de detalhe disponiveis no snapshot: `959`
- Arquivos de detalhe analisados na amostra: `96`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `48` maiores arquivos + `48` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260327`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 7 |
| Entidades Relacionadas | 5 | 5 |
| Localizacao | 6 | 3 |
| Datas | 8 | 6 |
| Quantidades e Indicadores | 7 | 1 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 96/96 | american_carbon_registry |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 96/96 | ACR | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 96/96 | ACR114 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 96/96 | 114 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 96/96 | https://acr2.apx.com/mymodule/reg/prjView.asp?id1=114 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 96/96 | data/project_standards/01_bronze/american_carbon_registry/20260327/projects/ACR114.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 96/96 | ACR114.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `project_fields.Project Name` | direct | 96/96 | GreenTrees ACRE (Advanced Carbon Restored Ecosystem) |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | list_data | `Voluntary Status` | direct | 33/96 | Registered |  |
| `project_regulatory_status` | Identificacao do Projeto | mapped | list_data | `Compliance Program Status (ARB or Ecology)` | direct | 96/96 | Not ARB or Ecology Eligible |  |
| `standard_program` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `project_fields.Project Description` | rename | 96/96 | The project uses tree planting to establish trees on lands that have been in continuous agricultural use and have not been in a forested ... |  |
| `project_methodology` | Identificacao do Projeto | mapped | list_data | `Project Methodology/Protocol` | direct | 96/96 | Afforestation and Reforestation of Degraded Lands |  |
| `project_type` | Identificacao do Projeto | mapped | list_data | `Project Type` | direct | 96/96 | Forest Carbon |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | mapped | list_data | `Sustainable Development Goal(s)` | normalized | 95/96 | ["03: Good Health and Well-Being", "06: Clean Water and Sanitation", "13: Climate Action", "15: Life on Land"] | Preserva a lista textual de ODS como exposta pela ACR, separada por ponto e virgula. |
| `project_developer` | Entidades Relacionadas | mapped | list_data | `Project Developer` | direct | 96/96 | GreenTrees, LLC |  |
| `project_owner` | Entidades Relacionadas | mapped | detail_data | `project_fields.Authorized Project Designee` | direct | 19/96 | Blue Source LLC |  |
| `project_operator` | Entidades Relacionadas | mapped | detail_data | `project_fields.Offset Project Operator` | direct | 63/96 | Round Valley Indian Tribes |  |
| `validator_name` | Entidades Relacionadas | mapped | list_data | `ACR Project Validation` | direct | 20/96 | Environmental Services, Inc. |  |
| `verifier_name` | Entidades Relacionadas | mapped | list_data | `Current VVB` | direct | 83/96 | Aster Global Environmental Solutions, Inc. |  |
| `country` | Localizacao | mapped | detail_data | `project_fields.Project Site Country` | direct | 96/96 | US |  |
| `state_or_region` | Localizacao | mapped | detail_data | `project_fields.Project Site State (Primary)` | direct | 96/96 | ARKANSAS |  |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 96/96 | 2026-03-27 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 96/96 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `project_fields.Project Registration/Listing Date` | direct | 85/96 | 6/29/2010 |  |
| `status_date` | Datas | mapped | list_data | `Project Status Date` | direct | 96/96 | 05/01/2012 |  |
| `crediting_start_date` | Datas | mapped | list_data | `Current Crediting Period Start Date` | direct | 96/96 | 01/01/2008 |  |
| `crediting_end_date` | Datas | mapped | list_data | `Current Crediting Period End Date` | direct | 96/96 | 12/31/2047 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | list_data | `Total Number of Credits Registered` | normalized | 96/96 | 7,792,791 | Usa o total de creditos registrados da ACR como melhor aproximacao operacional para o total emitido no snapshot. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/96 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da American Carbon Registry.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da american_carbon_registry, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da American Carbon Registry.
