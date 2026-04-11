# Mapeamento Inicial Silver da BioCarbon

- Snapshot analisado: `20260326`
- Arquivos de detalhe disponiveis no snapshot: `102`
- Arquivos de detalhe analisados na amostra: `11`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `6` maiores arquivos + `5` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260326`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 10 |
| Entidades Relacionadas | 5 | 5 |
| Localizacao | 6 | 2 |
| Datas | 8 | 5 |
| Quantidades e Indicadores | 7 | 3 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 11/11 | biocarbon |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 11/11 | BCR | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 11/11 | BCR-AR-763-13-001 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 11/11 | 58 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 11/11 | https://globalcarbontrace.io/registry/biocarbon/gei/project/58 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 11/11 | data/project_standards/01_bronze/biocarbon/20260326/projects/BCR-AR-763-13-001.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 11/11 | BCR-AR-763-13-001.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `project.initiative.name` | direct | 11/11 | Treatment of non-hazardous industrial waste to obtain Biocompost |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | detail_data | `project.initiative.status` | direct | 11/11 | Registered |  |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | detail_data | `project.initiative.applicable_standard` | direct | 11/11 | BCR |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `project.initiative.description` | direct | 11/11 | The large amount of non-hazardous, dangerous and pathogenic organic waste in Argentina is estimated at 11,000,000 Tons, only 10% is adequ... |  |
| `project_methodology` | Identificacao do Projeto | mapped | detail_data | `project.initiative.methodologies` | normalized | 11/11 | CDM - AMS-III.F._Avoidance of methane emissions through composting | Extrai os nomes de metodologia da lista estruturada de metodologias da BioCarbon. |
| `project_type` | Identificacao do Projeto | mapped | detail_data | `project.initiative.type_project_name` | direct | 11/11 | Compost |  |
| `sector` | Identificacao do Projeto | mapped | detail_data | `project.initiative.sector_name` | direct | 11/11 | Waste handling and disposal |  |
| `project_category` | Identificacao do Projeto | mapped | detail_data | `project.initiative.type_project.short_name` | direct | 11/11 | OTH |  |
| `project_subcategories` | Identificacao do Projeto | mapped | detail_data | `project.initiative.type_project.name` | direct | 11/11 | Compost |  |
| `sdg_targets` | Identificacao do Projeto | mapped | detail_data | `project.initiative.objetives` | normalized | 11/11 | ["SDG 9 - Industry, innovation, and infrastructure", "SDG 11 - Sustainable cities and communities", "SDG 12 - Responsible consumption and... | Usa os ODS estruturados da BioCarbon, priorizando text_cadt e text_thallo. |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `project.initiative.holder_name` | direct | 11/11 | WORMS ARGENTINA SA |  |
| `project_owner` | Entidades Relacionadas | mapped | detail_data | `project.initiative.holder.holder` | direct | 11/11 | Polaris Network España SL |  |
| `project_operator` | Entidades Relacionadas | mapped | detail_data | `project.initiative.participants` | direct | 11/11 | WORMS ARGENTINA SA. (Titular) |  |
| `validator_name` | Entidades Relacionadas | mapped | detail_data | `project.initiative.validation_body.name` | direct | 9/11 | Asociacion de Normalizacion y Certificacion, S.A. de C.V. |  |
| `verifier_name` | Entidades Relacionadas | mapped | detail_data | `project.initiative.ovv` | direct | 8/11 | Asociacion de Normalizacion y Certificacion, S.A. de C.V. |  |
| `country` | Localizacao | mapped | detail_data | `project.initiative.country` | direct | 11/11 | Argentina |  |
| `state_or_region` | Localizacao | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |

-33.1419089... |  |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 11/11 | 2026-03-26 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 11/11 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `project.initiative.acceptance_date` | direct | 8/11 | 2025-01-17 09:25:34 |  |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | detail_data | `project.initiative.quantification_period_start` | direct | 11/11 | 2018-04-01 |  |
| `crediting_end_date` | Datas | mapped | detail_data | `project.initiative.quantification_period_end` | direct | 11/11 | 2028-03-31 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | detail_data | `project.initiative.verified_reductions` | normalized | 11/11 | 59,574 | Usa o total de reducoes verificadas exposto pela propria iniciativa como total emitido do snapshot. |
| `credits_retired_total` | Quantidades e Indicadores | mapped | detail_data | `retreats.data` | conditional_aggregate | 1/11 | 2 | Soma os retiros apenas quando o payload bruto contem todas as paginas em uma unica resposta (last_page=1). |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | mapped | detail_data | `project.initiative.total_reductions_general` | direct | 8/11 | 123314 |  |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/11 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da BioCarbon.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da biocarbon, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da BioCarbon.
