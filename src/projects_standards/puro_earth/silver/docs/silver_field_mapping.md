# Mapeamento Inicial Silver da Puro.earth

- Snapshot analisado: `20260330`
- Arquivos de detalhe disponiveis no snapshot: `109`
- Arquivos de detalhe analisados na amostra: `11`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `6` maiores arquivos + `5` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260330`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 5 |
| Entidades Relacionadas | 5 | 1 |
| Localizacao | 6 | 3 |
| Datas | 8 | 6 |
| Quantidades e Indicadores | 7 | 2 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 11/11 | puro_earth |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 11/11 | PE | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 11/11 | 133206 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 11/11 | 133206 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 11/11 | https://registry.puro.earth/projects/133206 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 11/11 | data/project_standards/01_bronze/puro_earth/20260330/projects/133206.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 11/11 | 133206.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `project_name` | direct | 11/11 | Freres Lumber Co., Inc. |  |
| `project_voluntary_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | detail_data | `project_overview.general_rules.version` | direct | 11/11 | Puro Standard General Rules Version 3.1 |  |
| `project_description` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `project_methodology` | Identificacao do Projeto | mapped | detail_data | `project_overview.methodology.name` | direct | 11/11 | Biochar, 2022 |  |
| `project_type` | Identificacao do Projeto | mapped | detail_data | `project_overview.methodology.name` | direct | 11/11 | Biochar, 2022 |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | mapped | list_data | `sdgs` | normalized | 11/11 | Climate action | Usa a lista estruturada de ODS exposta pela listagem do projeto. |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `project_overview.supplier` | direct | 11/11 | ACT Commodities Inc. |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | detail_data | `project_overview.host_country` | direct | 11/11 | United States |  |
| `state_or_region` | Localizacao | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | mapped | list_data | `latitude` | direct | 1/11 | 45.3500000 |  |
| `location_longitude` | Localizacao | mapped | list_data | `longitude` | direct | 1/11 | -107.2700000 |  |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 11/11 | 2026-03-30 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 11/11 | 2026-03-01 |  |
| `registration_date` | Datas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | list_data | `creditingPeriodStart` | direct | 11/11 | 2019-12-01 |  |
| `crediting_end_date` | Datas | mapped | list_data | `creditingPeriodEnd` | direct | 11/11 | 2025-11-30 |  |
| `first_issuance_date` | Datas | mapped | detail_data | `transactions[].bundles[].issuanceDate` | aggregate | 11/11 | 2021-08-24 | Usa a menor issuanceDate encontrada nos bundles transacionais. |
| `last_issuance_date` | Datas | mapped | detail_data | `transactions[].bundles[].issuanceDate` | aggregate | 11/11 | 2025-12-10 | Usa a maior issuanceDate encontrada nos bundles transacionais. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | detail_data | `credits_summary.issued_corcs` | direct | 11/11 | 29 545 |  |
| `credits_retired_total` | Quantidades e Indicadores | mapped | detail_data | `credits_summary.retired_corcs` | direct | 11/11 | 28 698 |  |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Puro.earth.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da puro_earth, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Puro.earth.
