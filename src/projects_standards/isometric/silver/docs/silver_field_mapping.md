# Mapeamento Inicial Silver da Isometric

- Snapshot analisado: `20260326`
- Arquivos de detalhe disponiveis no snapshot: `48`
- Arquivos de detalhe analisados na amostra: `10`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `5` maiores arquivos + `5` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260326`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 9 |
| Entidades Relacionadas | 5 | 1 |
| Localizacao | 6 | 1 |
| Datas | 8 | 6 |
| Quantidades e Indicadores | 7 | 2 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 10/10 | isometric |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 10/10 | ISM | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 10/10 | prj_1HHYZFVGW1S044ZY |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 10/10 | prj_1HHYZFVGW1S044ZY |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 10/10 | https://registry.isometric.com/project/prj_1HHYZFVGW1S044ZY |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 10/10 | data/project_standards/01_bronze/isometric/20260326/projects/prj_1HHYZFVGW1S044ZY.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 10/10 | prj_1HHYZFVGW1S044ZY.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `name` | direct | 10/10 | Great Plains Organic Waste Sequestration |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | detail_data | `status` | direct | 10/10 | VALIDATED |  |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | source | `carbon_standard` | rename | 10/10 | isometric |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `description` | direct | 10/10 | Vaulted deploys slurry injection technology to geologically sequester organic wastes for the purpose of permanent carbon removal. Vaulted... |  |
| `project_methodology` | Identificacao do Projeto | mapped | detail_data | `protocol.name` | direct | 10/10 | Biomass Geological Storage |  |
| `project_type` | Identificacao do Projeto | mapped | detail_data | `process.displayName` | direct | 10/10 | Biomass injection |  |
| `sector` | Identificacao do Projeto | mapped | detail_data | `process.pathway.name` | direct | 10/10 | Biomass Carbon Removal and Storage |  |
| `project_category` | Identificacao do Projeto | mapped | detail_data | `process.pathway.type` | direct | 10/10 | BIOMASS_CARBON_REMOVAL_AND_STORAGE |  |
| `project_subcategories` | Identificacao do Projeto | mapped | detail_data | `process.displayName` | direct | 10/10 | Biomass injection |  |
| `sdg_targets` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `supplier.organisation.name` | direct | 10/10 | Vaulted Deep |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | detail_data | `country.name` | direct | 10/10 | United States of America |  |
| `state_or_region` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 10/10 | 2026-03-26 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 10/10 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `validatedAt` | direct | 5/10 | 2023-12-22T12:00:00+00:00 |  |
| `status_date` | Datas | mapped | detail_data | `validatedAt` | direct | 5/10 | 2023-12-22T12:00:00+00:00 |  |
| `crediting_start_date` | Datas | mapped | detail_data | `creditingPeriodStart` | direct | 7/10 | 2023-08-21 |  |
| `crediting_end_date` | Datas | mapped | detail_data | `creditingPeriodEnd` | direct | 7/10 | 2028-08-20 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | detail_data | `creditBalance.total.credits` | direct | 10/10 | 44415.45 |  |
| `credits_retired_total` | Quantidades e Indicadores | mapped | detail_data | `creditBalance.retired.credits` | direct | 10/10 | 11335.616 |  |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Isometric.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da isometric, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Isometric.
