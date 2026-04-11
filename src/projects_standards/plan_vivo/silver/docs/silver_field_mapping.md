# Mapeamento Inicial Silver da Plan Vivo

- Snapshot analisado: `20260326`
- Arquivos de detalhe disponiveis no snapshot: `9`
- Arquivos de detalhe analisados na amostra: `9`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `9` maiores arquivos + `0` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260326`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 6 |
| Entidades Relacionadas | 5 | 1 |
| Localizacao | 6 | 1 |
| Datas | 8 | 4 |
| Quantidades e Indicadores | 7 | 1 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 9/9 | plan_vivo |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 9/9 | PV | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 9/9 | fes-enying-cameroon |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 9/9 | fes-enying-cameroon |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 9/9 | https://www.planvivo.org/projects/fes-enying-cameroon |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 9/9 | data/project_standards/01_bronze/plan_vivo/20260326/projects/fes-enying-cameroon.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 9/9 | fes-enying-cameroon.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `page_title` | direct | 9/9 | Fes Enying – Cameroon |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | list_data | `tags.0` | direct | 9/9 | Certified Carbon |  |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | detail_data | `project_summary.certified_beneath` | direct | 9/9 | PV Climate Version 5 |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `about_the_project` | direct | 9/9 | In the Adamawa region of Cameroon, where the rainforests of the Congo Basin meet the savannah of the Sahel, an innovative agroforestry pr... |  |
| `project_methodology` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `project_type` | Identificacao do Projeto | mapped | detail_data | `project_summary.activities` | direct | 9/9 | Afforestation/reforestation &amp; agroforestry |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | mapped | detail_data | `project_summary.activities` | direct | 9/9 | Afforestation/reforestation &amp; agroforestry |  |
| `project_subcategories` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `sdg_targets` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `project_developer` | Entidades Relacionadas | mapped | detail_data | `project_summary.coordinators` | direct | 9/9 | ["Graine de Vie"] |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | detail_data | `project_summary.country` | direct | 9/9 | Cameroon |  |
| `state_or_region` | Localizacao | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 9/9 | 2026-03-26 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 9/9 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `project_summary.start_date` | direct | 9/9 | 2023 |  |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | detail_data | `project_summary.start_date` | direct | 9/9 | 2023 |  |
| `crediting_end_date` | Datas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | detail_data | `project_summary.pvcs_issued_to_date` | direct | 6/9 | 28,504 | Usa o total de PVCs emitidos ate a data exibido na capa do projeto. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/9 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Plan Vivo.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da plan_vivo, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Plan Vivo.
