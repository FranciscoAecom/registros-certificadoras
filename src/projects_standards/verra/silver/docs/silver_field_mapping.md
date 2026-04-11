# Mapeamento Inicial Silver da Verra

- Snapshot analisado: `20260325`
- Arquivos de detalhe disponiveis no snapshot: `4921`
- Arquivos de detalhe analisados na amostra: `493`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `247` maiores arquivos + `246` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260325`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 6 |
| Identificacao do Projeto | 11 | 5 |
| Entidades Relacionadas | 5 | 1 |
| Localizacao | 6 | 4 |
| Datas | 8 | 5 |
| Quantidades e Indicadores | 7 | 2 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_acronym` | Metadados do Registro | mapped | constant | `VCS` | constant | 493/493 | VCS | Nao vem explicitamente no bruto; sigla tecnica do programa VCS para a Verra. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 493/493 | 5 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 493/493 | 5 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 493/493 | https://registry.verra.org/app/projectDetail/VCS/5 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 493/493 | data/project_standards/01_bronze/verra/20260325/projects/5.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 493/493 | 5.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `resourceName` | direct | 493/493 | Greater Lebanon Refuse Authority Landfill Gas Collection and Combustion Project |  |
| `project_voluntary_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `project_description` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `project_methodology` | Identificacao do Projeto | mapped | detail_data | `participationSummaries[].attributes[PROTOCOL_NAME]` | normalized | 493/493 | ACM0001 | Usa os nomes de protocolo da Verra e separa multiplas metodologias quando vierem em texto unico delimitado por virgul... |
| `project_type` | Identificacao do Projeto | mapped | list_data | `version` | direct | 493/493 | VCS Version 3 |  |
| `sector` | Identificacao do Projeto | mapped | detail_data | `participationSummaries[].attributes[PRIMARY_PROJECT_CATEGORY_NAME]` | direct | 493/493 | Waste handling and disposal |  |
| `project_category` | Identificacao do Projeto | mapped | list_data | `protocolSubCategories` | direct | 216/493 | ARR |  |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | unmapped | list_data | `programObjectives` | normalized | 0/493 |  | Campo existe na lista, mas aparece nulo nos exemplos atuais analisados. |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `participationSummaries[].attributes[PROPONENT_NAME]` | direct | 493/493 | Greater Lebanon Refuse Authority |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped | list_data | `operator` | direct | 0/493 |  | Fonte candidata configurada, mas sem valores uteis no snapshot analisado. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | list_data | `country` | direct | 493/493 | United States |  |
| `state_or_region` | Localizacao | mapped | detail_data | `attributes[STATE_PROVINCE]` | direct | 446/493 | PA |  |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | mapped | detail_data | `location.latitude` | direct | 493/493 | 40.3662 |  |
| `location_longitude` | Localizacao | mapped | detail_data | `location.longitude` | direct | 493/493 | -76.49293 |  |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 493/493 | 2026-03-25 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 493/493 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | list_data | `projectRegistrationDate` | direct | 375/493 | 2020-04-06 |  |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | list_data | `creditingPeriodStartDate` | direct | 395/493 | 2018-04-01 |  |
| `crediting_end_date` | Datas | mapped | list_data | `creditingPeriodEndDate` | direct | 395/493 | 2028-03-31 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | mapped | list_data | `estAnnualEmissionReductions` | direct | 493/493 | 25600 |  |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | mapped | detail_data | `participationSummaries[].attributes[PROJECT_ACREAGE]` | normalized | 224/493 | 5625 Hectares |  |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Verra.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Campos derivados de filesystem ou constantes tecnicas continuam documentados porque fazem parte do registro final da `silver`.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Verra.
