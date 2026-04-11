# Mapeamento Inicial Silver da Equitable Earth

- Snapshot analisado: `20260326`
- Arquivos de detalhe disponiveis no snapshot: `16`
- Arquivos de detalhe analisados na amostra: `10`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `5` maiores arquivos + `5` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260326`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 6 |
| Entidades Relacionadas | 5 | 1 |
| Localizacao | 6 | 2 |
| Datas | 8 | 4 |
| Quantidades e Indicadores | 7 | 0 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 10/10 | equitable_earth |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 10/10 | EQE | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 10/10 | ERS1001 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 10/10 | A52C05BC-F8A2-11EE-8547-22CB1A1D4914 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 10/10 | https://registry.eq-earth.com/dataroom/ERS/ERS_MEASUREMENT_STANDARD/byIdentifier/A52C05BC-F8A2-11EE-8547-22CB1A1D4914 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 10/10 | data/project_standards/01_bronze/equitable_earth/20260326/projects/ERS1001.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 10/10 | ERS1001.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | list_data | `resourceProgramName` | direct | 10/10 | Manjarisoa |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | list_data | `resourceProgramStatusName` | direct | 10/10 | Active (MRV) |  |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | detail_data | `resource.programs[0].name` | fallback | 10/10 | Manjarisoa | Prioriza o nome do programa no detalhe, com fallback para o codigo tecnico do programa na origem. |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `resource.programs[0].description` | direct | 10/10 | The Manjarisoa project is a reforestation project located in North Eastern Madagascar, in the region of Toamasina (18°27'47.1"S 49°06'43.... | Descricao institucional exposta no bloco de programas do detalhe. |
| `project_methodology` | Identificacao do Projeto | mapped | list_data | `programProtocol` | direct | 10/10 | M000 : 1.0.0 |  |
| `project_type` | Identificacao do Projeto | mapped | list_data | `resourceTypeName` | direct | 10/10 | Reforestation |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `proponents.legalEntities[0].name` | fallback | 10/10 | FORESTCALLING | Prioriza o nome estruturado do proponente no detalhe, com fallback para a string da lista. |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | detail_data | `resource.naturalGeography.address.countryIso2Code` | fallback | 10/10 | MG | Usa o codigo do pais no detalhe, com fallback para o codigo iso3 da lista. |
| `state_or_region` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `city_or_locality` | Localizacao | mapped | detail_data | `resource.naturalGeography.address.municipality` | direct | 1/10 | Canto do Buriti |  |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 10/10 | 2026-03-26 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 10/10 | 2026-03-01 |  |
| `registration_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | detail_data | `crediting_periods.currentCreditingPeriod.startDateInclusive` | direct | 10/10 | 2022-08-01 |  |
| `crediting_end_date` | Datas | mapped | detail_data | `crediting_periods.currentCreditingPeriod.endDateExclusive` | direct | 10/10 | 2062-08-01 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/10 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Equitable Earth.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da equitable_earth, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Equitable Earth.
