# Mapeamento Gold

## Objetivo

Este documento define o primeiro desenho operacional do mapeamento `silver -> gold`.

Ele responde a tres perguntas:

- quais campos da `silver` entram na `gold`
- quais campos mudam de nome
- quais campos da `gold` sao derivados ou enriquecidos por referencia

## Regras Gerais

- A `gold` parte da `silver` como fonte canonica base.
- A `gold` nao deve voltar ao `bronze` para enriquecer atributos.
- Campos de referencia padronizados devem ser resolvidos por relacionamento com `reference_dataset.xlsx`.
- Sempre que um campo da `gold` for derivado, a regra deve ser deterministica e documentada.

## Resultado Esperado

O primeiro desenho da `gold` usa tres tipos de campo:

- `direct`
  - copia direta da `silver`
- `renamed`
  - mesmo valor da `silver`, mas com nome ajustado na `gold`
- `derived`
  - valor calculado ou resolvido por relacao

## Campos da Gold

### 1. Proveniencia e Chaves

| gold_field | source_type | source | regra |
|---|---|---|---|
| `record_id` | `derived` | `standard_acronym`, `project_internal_id`, `reference_month` | `standard_acronym + "_" + project_internal_id + "_" + reference_month` |
| `project_history_id` | `derived` | `standard_acronym`, `project_internal_id` | `standard_acronym + "_" + project_internal_id` |
| `standard_name` | `direct` | `silver.standard_name` | copia direta |
| `standard_acronym` | `direct` | `silver.standard_acronym` | copia direta |
| `bronze_file_path` | `direct` | `silver.bronze_file_path` | copia direta |
| `source_file_name` | `direct` | `silver.source_file_name` | copia direta |
| `snapshot_date` | `direct` | `silver.snapshot_date` | copia direta |
| `reference_month` | `direct` | `silver.reference_month` | copia direta |
| `gold_selected_from_snapshot` | `derived` | `silver snapshot metadata` | snapshot que venceu a deduplicacao mensal |

### 2. Identificacao do Projeto

| gold_field | source_type | source | regra |
|---|---|---|---|
| `project_public_id` | `direct` | `silver.project_public_id` | copia direta |
| `project_internal_id` | `direct` | `silver.project_internal_id` | copia direta |
| `project_url` | `direct` | `silver.project_url` | copia direta |
| `project_name` | `direct` | `silver.project_name` | copia direta |
| `project_description` | `direct` | `silver.project_description` | copia direta |
| `standard_program` | `direct` | `silver.standard_program` | copia direta |
| `project_type` | `direct` | `silver.project_type` | copia direta |
| `project_category` | `direct` | `silver.project_category` | copia direta |
| `project_subcategories` | `direct` | `silver.project_subcategories` | copia direta |

### 3. Mercado e Status

| gold_field | source_type | source | regra |
|---|---|---|---|
| `project_market` | `derived` | `silver.project_voluntary_status`, `silver.project_regulatory_status` | inferir o mercado efetivo conforme a regra da standard. Se houver apenas status voluntario preenchido, mercado tende a ser `voluntary`; se houver apenas status regulatorio, mercado tende a ser `regulatory`; se ambos existirem, aplicar regra especifica documentada |
| `standard_reported_project_status` | `derived` | `project_market`, `silver.project_voluntary_status`, `silver.project_regulatory_status` | escolher o status informado pela standard correspondente ao mercado efetivo |
| `standard_pipeline_status_id` | `derived` | `project_market`, `standard_reported_project_status`, referencia `standards_status` | buscar o id do pipeline padrao pelo trio `standard_acronym + market + status_standard` |



### 4. Metodologia e Classificacao Padronizada

| gold_field | source_type | source | regra |
|---|---|---|---|
| `project_methodology` | `derived` | `silver.project_methodology`, referencia `methodologies`, referencia `technical_areas` | produzir uma lista de objetos com `project_methodology`, `technical_area_id` e `sectoral_scope_id` por metodologia |
| `standard_reported_sector` | `renamed` | `silver.sector` | manter lista original da `silver` deixando explicito que o valor foi informado pela standard |

Observacao:

- O relacionamento oficial acontece no nivel de cada item de `project_methodology`.
- `sectoral_scope_id` na `gold` deve ser sempre derivado por relacionamento, nunca arbitrado ad hoc.

### 5. SDGs Padronizados

| gold_field | source_type | source | regra |
|---|---|---|---|
| `sdg_targets_observed` | `direct` | `silver.sdg_targets` | opcional, para rastreabilidade |
| `sdg_goal_ids` | `derived` | referencia `sdg_observed_mapping` | mapear cada forma observada para o `goal_id` padrao |

Observacao:

- Como a `silver` hoje carrega formas observadas diversas no campo `sdg_targets`, a `gold` deve produzir uma lista padronizada de `goal_id`.
- Itens sem mapeamento devem ser descartados ou sinalizados conforme a politica final de qualidade.

### 6. Entidades Relacionadas

| gold_field | source_type | source | regra |
|---|---|---|---|
| `project_developer` | `direct` | `silver.project_developer` | copia direta |
| `project_owner` | `direct` | `silver.project_owner` | copia direta |
| `project_operator` | `direct` | `silver.project_operator` | copia direta |
| `validator_name` | `direct` | `silver.validator_name` | copia direta |
| `verifier_name` | `direct` | `silver.verifier_name` | copia direta |

### 7. Localizacao

| gold_field | source_type | source | regra |
|---|---|---|---|
| `country_observed` | `direct` | `silver.country` | opcional, para rastreabilidade |
| `country_standard` | `derived` | referencia `countries_observed_mapping` | resolver o pais padrao a partir do valor observado |
| `state_or_region` | `direct` | `silver.state_or_region` | copia direta |
| `city_or_locality` | `direct` | `silver.city_or_locality` | copia direta |
| `location_latitude` | `direct` | `silver.location_latitude` | copia direta |
| `location_longitude` | `direct` | `silver.location_longitude` | copia direta |
| `project_geometry` | `direct` | `silver.project_geometry` | copia direta em formato GeoJSON-like para preservar vertices/poligono quando houver |

### 8. Datas do Ciclo de Vida

| gold_field | source_type | source | regra |
|---|---|---|---|
| `registration_date` | `direct` | `silver.registration_date` | copia direta |
| `status_date` | `direct` | `silver.status_date` | copia direta |
| `crediting_start_date` | `direct` | `silver.crediting_start_date` | copia direta |
| `crediting_end_date` | `direct` | `silver.crediting_end_date` | copia direta |
| `first_issuance_date` | `direct` | `silver.first_issuance_date` | copia direta |
| `last_issuance_date` | `direct` | `silver.last_issuance_date` | copia direta |

### 9. Quantidades e Indicadores

| gold_field | source_type | source | regra |
|---|---|---|---|
| `credits_issued_total` | `direct` | `silver.credits_issued_total` | copia direta |
| `credits_retired_total` | `direct` | `silver.credits_retired_total` | copia direta |
| `credits_cancelled_total` | `direct` | `silver.credits_cancelled_total` | copia direta |
| `credits_buffer_total` | `direct` | `silver.credits_buffer_total` | copia direta |
| `estimated_annual_emission_reductions` | `direct` | `silver.estimated_annual_emission_reductions` | copia direta |
| `estimated_total_emission_reductions` | `direct` | `silver.estimated_total_emission_reductions` | copia direta |
| `area_hectares` | `direct` | `silver.area_hectares` | copia direta |

## Campos da Silver Que Nao Devem Entrar na Gold como Principais

Os campos abaixo nao devem entrar como atributos principais da `gold`:

- `country`
- `sdg_targets`

Motivo:

- a `gold` deve preferir a forma padronizada e consolidada

## Questao Aberta Ja Identificada

Hoje a `silver` nao possui `project_market` explicito.

Portanto, a implementacao da `gold` precisara definir uma regra oficial para derivar esse campo, usando ao menos:

- preenchimento relativo de `project_voluntary_status`
- preenchimento relativo de `project_regulatory_status`
- excecoes por standard, quando necessario

Essa regra deve ser formalizada no builder da `gold` e documentada no codigo.
