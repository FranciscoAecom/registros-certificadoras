# Mapeamento Inicial Silver da TERO

- Snapshot analisado: `20260326`
- Arquivos de detalhe disponiveis no snapshot: `3`
- Arquivos de detalhe analisados na amostra: `3`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `3` maiores arquivos + `0` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260326`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 4 |
| Entidades Relacionadas | 5 | 0 |
| Localizacao | 6 | 4 |
| Datas | 8 | 4 |
| Quantidades e Indicadores | 7 | 0 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 3/3 | tero |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 3/3 | TER | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 3/3 | aruana-i |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 3/3 | 2870 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 3/3 | https://terocarbon.com/project/aruana-i/ |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 3/3 | data/project_standards/01_bronze/tero/20260326/projects/aruana-i.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 3/3 | aruana-i.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `api_response.title.rendered` | direct | 3/3 | Aruanã I |  |
| `project_voluntary_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `standard_program` | Identificacao do Projeto | mapped | source | `carbon_standard` | rename | 3/3 | tero |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `api_response.yoast_head_json.description` | direct | 3/3 | A Aruanã I é um projeto AFOLU, REDD+, localizado em Itacoatiara, Amazonas, Brasil, certificado e verificado pela Tero Carbon. |  |
| `project_methodology` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_type` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_subcategories` | Identificacao do Projeto | mapped | detail_data | `api_response.class_list` | normalized | 3/3 | ["afolu", "redd"] | Deriva subcategorias taxonomicas a partir das classes CSS project_category-* do payload da API. |
| `sdg_targets` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_developer` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | detail_data | `api_response.yoast_head_json.description` | reference_lookup | 3/3 | Brazil | Identifica o pais usando a localizacao textual e a tabela tb_paisPadrao, retornando o nome_en padrao. |
| `state_or_region` | Localizacao | mapped | detail_data | `api_response.content.rendered` | parsed_html | 2/3 | Amazonas | Infere a unidade federativa a partir da localizacao textual exibida na pagina. |
| `city_or_locality` | Localizacao | mapped | detail_data | `api_response.content.rendered` | parsed_html | 2/3 | Itacoatiara | Infere a cidade a partir da localizacao textual exibida na pagina. |
| `location_latitude` | Localizacao | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `location_longitude` | Localizacao | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 3/3 | 2026-03-26 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 3/3 | 2026-03-01 |  |
| `registration_date` | Datas | mapped | detail_data | `api_response.date_gmt` | direct | 3/3 | 2023-11-21T14:16:40 |  |
| `status_date` | Datas | mapped | detail_data | `api_response.modified_gmt` | direct | 3/3 | 2024-07-22T14:00:12 |  |
| `crediting_start_date` | Datas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_end_date` | Datas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_retired_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0/3 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da TERO.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da tero, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da TERO.
