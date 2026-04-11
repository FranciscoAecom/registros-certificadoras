# Mapeamento Inicial Silver da Gold Standard

- Snapshot analisado: `20260327`
- Arquivos de detalhe disponiveis no snapshot: `4055`
- Arquivos de detalhe analisados na amostra: `406`
- Regra de amostragem: `max(10, ceil(10% do snapshot))`, com limite no total disponivel
- Estrategia da amostra: `203` maiores arquivos + `203` arquivos aleatorios (proporcao alvo para maiores arquivos: 50%)
- Seed da amostra aleatoria: `20260327`
- Guia base: `docs/agentes/guia_silver.md`

## Resumo por Secao

| Secao | Campos | Campos com fonte inicial |
| --- | ---: | ---: |
| Metadados do Registro | 7 | 7 |
| Identificacao do Projeto | 11 | 9 |
| Entidades Relacionadas | 5 | 1 |
| Localizacao | 6 | 3 |
| Datas | 8 | 4 |
| Quantidades e Indicadores | 7 | 3 |

## Tabela de Mapeamento Inicial

| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `standard_name` | Metadados do Registro | mapped | source | `carbon_standard` | rename | 406/406 | gold_standard |  |
| `standard_acronym` | Metadados do Registro | mapped | reference | `data/project_standards/00_reference/reference_dataset.xlsx` (aba `standards_catalog`) | lookup | 406/406 | GS | Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro. |
| `project_public_id` | Metadados do Registro | mapped | source | `project_public_id` | direct | 406/406 | GS1001 |  |
| `project_internal_id` | Metadados do Registro | mapped | source | `project_internal_id` | direct | 406/406 | 2 |  |
| `project_url` | Metadados do Registro | mapped | source | `project_url` | direct | 406/406 | https://registry.goldstandard.org/projects/details/2 |  |
| `bronze_file_path` | Metadados do Registro | mapped | file_system | `bronze_file_path` | derived | 406/406 | data/project_standards/01_bronze/gold_standard/20260327/projects/2.json | Derivado do caminho do arquivo de detalhe no filesystem. |
| `source_file_name` | Metadados do Registro | mapped | file_system | `source_file_name` | derived | 406/406 | 2.json | Derivado do nome do arquivo de detalhe no filesystem. |
| `project_name` | Identificacao do Projeto | mapped | detail_data | `name` | direct | 406/406 | InfraVest Taiwan Wind Farms Bundled Project 2011 - Taiwan |  |
| `project_voluntary_status` | Identificacao do Projeto | mapped | list_data | `status` | direct | 406/406 | GOLD_STANDARD_CERTIFIED_PROJECT | Regra canonica atual: ate segunda ordem, todo status bruto da Gold Standard deve ser tratado como voluntario, com fal... |
| `project_regulatory_status` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0/406 |  | Regra canonica atual: project_regulatory_status deve permanecer nulo para a Gold Standard ate revisao futura. |
| `standard_program` | Identificacao do Projeto | mapped | list_data | `gsf_standards_version` | rename | 406/406 | Gold Standard for the Global Goals |  |
| `project_description` | Identificacao do Projeto | mapped | detail_data | `description` | rename | 406/406 | The InfraVest Taiwan Wind Farms Bundled Project 2011(hereinafter referred to as “the project”) is a bundled project o... |  |
| `project_methodology` | Identificacao do Projeto | mapped | detail_data | `methodology` | direct | 234/406 | ACM0002 Grid-connected electricity generation from renewable sources |  |
| `project_type` | Identificacao do Projeto | mapped | list_data | `type` | direct | 406/406 | Other |  |
| `sector` | Identificacao do Projeto | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `project_category` | Identificacao do Projeto | mapped | list_data | `size` | direct | 406/406 | Large Scale |  |
| `project_subcategories` | Identificacao do Projeto | mapped | list_data | `programme_of_activities + labels` | normalized | 403/406 | ["Standalone", "EMISSION_REDUCTION"] | Combina o enquadramento do projeto e labels expostos pela Gold Standard como subcategorias. |
| `sdg_targets` | Identificacao do Projeto | mapped | list_data | `sustainable_development_goals` | normalized | 406/406 | ["Goal 8: Decent Work and Economic Growth", "Goal 13: Climate Action", "Goal 7: Affordable and Clean Energy"] | Converte a lista de ODS da Gold Standard para uma lista canonica de nomes brutos. |
| `project_developer` | Entidades Relacionadas | mapped | list_data | `project_developer` | direct | 406/406 | South Pole Ltd |  |
| `project_owner` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `project_operator` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `validator_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `verifier_name` | Entidades Relacionadas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `country` | Localizacao | mapped | list_data | `country` | direct | 406/406 | Taiwan |  |
| `state_or_region` | Localizacao | unmapped | list_data | `state` | direct | 0/406 |  | Fonte candidata configurada, mas sem valores uteis no snapshot analisado. |
| `city_or_locality` | Localizacao | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `location_latitude` | Localizacao | mapped | detail_data | `latitude` | direct | 108/406 | 24.611389 |  |
| `location_longitude` | Localizacao | mapped | detail_data | `longitude` | direct | 108/406 | 120.736946 |  |
| `snapshot_date` | Datas | mapped | source | `snapshot_date` | direct | 406/406 | 2026-03-27 |  |
| `reference_month` | Datas | mapped | source | `reference_month` | direct | 406/406 | 2026-03-01 |  |
| `registration_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `status_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `crediting_start_date` | Datas | mapped | list_data | `crediting_period_start_date` | direct | 406/406 | 2014-02-01 |  |
| `crediting_end_date` | Datas | mapped | list_data | `crediting_period_end_date` | direct | 406/406 | 2021-01-31 |  |
| `first_issuance_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `last_issuance_date` | Datas | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_issued_total` | Quantidades e Indicadores | mapped | detail_data | `credits_summary` | aggregate | 172/406 | 976517 | Soma os totais com status ISSUED dentro de detail_data.credits_summary. |
| `credits_retired_total` | Quantidades e Indicadores | mapped | detail_data | `credits_summary` | aggregate | 131/406 | 921983 | Soma os totais com status RETIRED dentro de detail_data.credits_summary. |
| `credits_cancelled_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `credits_buffer_total` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `estimated_annual_emission_reductions` | Quantidades e Indicadores | mapped | list_data | `estimated_annual_credits` | direct | 406/406 | 264960 |  |
| `estimated_total_emission_reductions` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |
| `area_hectares` | Quantidades e Indicadores | unmapped |  | `` | unmapped | 0 |  | Nenhuma regra inicial configurada para este campo. |

## Observacoes

- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Gold Standard.
- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.
- Quando um campo permanecer sem origem confiavel no bruto da Gold Standard, ele deve seguir como `null` na `silver`.
- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.
- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.
- Campos derivados de filesystem e referencias operacionais continuam documentados porque fazem parte do registro final da `silver`.
- Este mapeamento foi validado sobre amostra hibrida deterministica, combinando maiores arquivos e selecao aleatoria, e nao por leitura apenas dos primeiros arquivos do snapshot.
