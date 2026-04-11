# Guia Gold

## Objetivo

A camada `gold` consolida, em uma base unica, todos os projetos canônicos produzidos na `silver` para todas as standards e todos os snapshots elegiveis do projeto.

Ela existe para:

- unificar os projetos em uma base analitica unica
- refletir os mapeamentos e referencias mais recentes do projeto
- garantir historico mensal consolidado por projeto
- expor atributos padronizados prontos para consumo analitico

## Escopo da Base

- A `gold` e unica.
- Todos os datasets `silver` das standards entram no processo de consolidacao.
- A `gold` deve ser regenerada integralmente a cada execucao.
- A regeneracao integral e obrigatoria para garantir que novos mapeamentos de referencia sejam refletidos na versao publicada.

## Unidade de Registro

A unidade de registro da `gold` e:

- `1` projeto por `reference_month`

Isso significa:

- um mesmo projeto pode aparecer em varios meses
- dentro de um mesmo `reference_month`, a `gold` deve manter apenas um registro final do projeto

## Regra de Deduplicacao Mensal

Podem existir varios registros do mesmo projeto dentro do mesmo mes, porque a `silver` pode conter mais de um snapshot no mesmo `reference_month`.

Nesses casos, o processo `silver -> gold` deve:

1. agrupar por projeto dentro do mesmo `reference_month`
2. comparar a data real de captura ou geracao do registro
3. manter apenas o registro mais atualizado daquele mes

O criterio de "mais atualizado" deve usar a melhor evidencia temporal disponivel no dataset `silver`, priorizando:

1. data e hora de geracao do dataset
2. data do snapshot
3. outra evidencia temporal explicita e rastreavel, se existir

## Chaves da Gold

A camada `gold` deve criar duas chaves novas.

### Chave do Projeto no Historico

Essa chave identifica o projeto ao longo do tempo.

Nome recomendado:

- `project_history_id`

Regra:

- concatenar `standard_acronym` + `_` + `project_internal_id`

Exemplo:

- `VCS_10`
- `GS_10`

### Chave do Registro da Base

Essa chave identifica um registro mensal unico na `gold`.

Nome recomendado:

- `record_id`

Regra:

- concatenar `standard_acronym` + `_` + `project_internal_id` + `_` + `reference_month`

Exemplo:

- `VCS_10_2026-03-01`

## Fonte de Verdade da Gold

A `gold` deve nascer da `silver`.

Regras:

- a `gold` nao deve voltar ao `bronze`
- a `gold` deve confiar na `silver` para o dado canonico base por standard
- referencias e mapeamentos complementares devem ser aplicados por join com `data/project_standards/00_reference/reference_dataset.xlsx`

## Padronizacoes Obrigatorias

### SDGs

Os SDGs da `gold` devem ser os SDGs padronizados conforme o mapeamento da referencia.

Fontes:

- `sdg_observed_mapping`
- `sdg_goals`

Resultado esperado:

- a `gold` nao deve carregar a forma observada bruta como valor principal quando houver forma padronizada disponivel
- o ideal e expor ao menos o `goal_id` padrao

### Metodologias, Atividades Tecnicas e Escopos Setoriais

Com base no mapeamento de metodologias:

- cada metodologia deve levar sua `technical_area_id` padronizada
- o `sectoral_scope_id` deve ser derivado por relacionamento com `technical_areas`

Fontes:

- `methodologies`
- `technical_areas`
- `sectoral_scopes`

Regra:

- a relacao primaria no nivel da metodologia e com `technical_area_id`
- o `sectoral_scope_id` e derivado, nao arbitrado diretamente no projeto quando ja existir relacao pela atividade tecnica
- na `gold`, esse relacionamento deve ser exposto dentro de `project_methodology`, em uma lista de objetos por metodologia

### Pais do Projeto

O pais do projeto na `gold` deve ser o pais padronizado conforme a referencia.

Fontes:

- `countries_observed_mapping`
- `countries_standard`

### Status Gold

A `gold` deve expor um unico atributo de status do projeto e, ao lado, o status padrao de pipeline.

Campos recomendados:

- `standard_reported_project_status`
- `standard_pipeline_status_id`

Regra de negocio:

1. ler `project_market`
2. identificar qual campo de status original da standard deve ser usado para aquele mercado
3. preencher `standard_reported_project_status` com esse status de negocio efetivo
4. buscar na referencia o mapeamento para o status padrao do pipeline
5. preencher o id do pipeline padrao correspondente

Fontes:

- `standards_status`
- `common_pipeline_status`

## Estrutura Esperada de Saida

O arquivo final da `gold` deve ser em JSON.

Estrutura base esperada:

```text
data/project_standards/03_gold/projects/allprojects.json
data/project_standards/03_gold/projects/schema.json
data/project_standards/03_gold/projects/quality_report.json
data/project_standards/03_gold/projects/backup/YYYYMMDDTHHMMSS/allprojects.json
data/project_standards/03_gold/projects/backup/YYYYMMDDTHHMMSS/quality_report.json
```

## Regra de Backup

Antes de sobrescrever a base `gold` atual:

1. verificar se existem artefatos atuais da `gold`
2. criar em `data/project_standards/03_gold/projects/backup/` uma pasta com timestamp do momento da movimentacao
3. mover para essa pasta ao menos:
   - `allprojects.json`
   - `quality_report.json`
4. manter os nomes originais dos arquivos dentro da pasta timestampada

Exemplo conceitual:

- `backup/20260331T154501/allprojects.json`
- `backup/20260331T154501/quality_report.json`

## Regra de Completude

A `gold` deve ser sempre reconstruida em sua completude.

Isso significa:

- nao fazer append incremental como estrategia oficial
- nao confiar em cache antigo de consolidacao como base de verdade
- toda execucao deve reavaliar a massa inteira de datasets `silver` disponiveis

## Campos Minimos Recomendados

Os nomes exatos podem ser refinados no desenho do schema, mas o contrato conceitual da `gold` deve incluir ao menos:

- `record_id`
- `project_history_id`
- `standard_acronym`
- `project_internal_id`
- `project_public_id`
- `reference_month`
- `snapshot_date`
- `project_name`
- `project_market`
- `standard_reported_project_status`
- `standard_pipeline_status_id`
- `country_standard`
- `project_geometry`
- `project_methodology`
- `sdg_goal_ids`

## Qualidade e Rastreabilidade

A `gold` deve:

- preservar rastreabilidade ate a `silver`
- registrar claramente a regra de deduplicacao mensal
- registrar a versao final gerada
- produzir `quality_report.json` com contagens, deduplicacao e ausencias relevantes

## Decisoes Ja Assumidas

As decisoes abaixo devem ser tratadas como contrato vigente para o desenho inicial da `gold`:

- base unica para todas as standards
- `1` registro por projeto por `reference_month`
- manter o registro mais atualizado do mes
- criar `project_history_id`
- criar `record_id`
- padronizar SDGs
- padronizar pais
- preservar geometria do projeto em formato GeoJSON-like quando disponivel
- padronizar atividade tecnica e escopo setorial
- consolidar um unico status do projeto e um unico status padrao de pipeline
- gerar a `gold` integralmente a cada execucao
- mover os artefatos anteriores para uma pasta timestampada em `backup` antes de sobrescrever os arquivos finais
