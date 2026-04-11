# Reference Dataset

Este diretorio contem as referencias editaveis do projeto e agora tambem o arquivo consolidado [reference_dataset.xlsx](/c:/Users/pedro.almeida/registrosCertificadoras/data/project_standards/00_reference/reference_dataset.xlsx).

## Objetivo

O arquivo `reference_dataset.xlsx` centraliza, em um unico workbook, as tabelas estruturadas atualmente distribuidas pelos arquivos de referencia do projeto.

Ele serve para:

- facilitar navegacao e consulta humana
- centralizar revisao operacional de referencias
- reduzir troca de arquivo ao trabalhar com paises, metodologias, standards e ODS

## Regra atual

- `reference_dataset.xlsx` e o workbook canÃ´nico operacional do projeto
- o workbook pode ser reparado e validado diretamente sem depender dos arquivos historicos de origem
- cada tabela estruturada de cada workbook de origem foi copiada para uma aba propria
- o consolidado deve ser gerado pelo script [build_reference_dataset.py](/C:/Users/pedro.almeida/registrosCertificadoras/src/projects_standards/shared/reference/build_reference_dataset.py)
- o gerador remove `AutoFilter` no nivel do worksheet e preserva o `AutoFilter` apenas dentro das tabelas, para manter compatibilidade com o Excel e evitar reparos ao abrir o arquivo
- a manutencao estrutural do workbook esta documentada em [reference_dataset_maintenance.md](/C:/Users/pedro.almeida/registrosCertificadoras/data/project_standards/00_reference/reference_dataset_maintenance.md)

## Mapeamento das Abas

- `standards_catalog`: tabela `tb_certificadora` de `reference_dataset.xlsx` (aba `standards_catalog`)
- `standards_status`: tabela de status da aba `certificadora_status` de `reference_dataset.xlsx` (aba `standards_catalog`)
- `common_pipeline_status`: tabela `tb_pipelineStatus` de `reference_dataset.xlsx` (aba `standards_catalog`)
- `methodologies`: tabela da aba `standard_methodologies` de `reference_dataset.xlsx` (aba `methodologies`)
- `countries_standard`: tabela `tb_paisPadrao` de `reference_dataset.xlsx` (abas `countries_standard` e `countries_observed_mapping`)
- `countries_observed_mapping`: tabela `tb_mapPaisCertificadora` de `reference_dataset.xlsx` (abas `countries_standard` e `countries_observed_mapping`)
- `sdg_goals`: tabela da aba `goals` de `reference_dataset.xlsx` (abas `sdg_goals` e `sdg_targets`)
- `sdg_targets`: tabela da aba `targets` de `reference_dataset.xlsx` (abas `sdg_goals` e `sdg_targets`)
- `sdg_observed_mapping`: formas observadas de SDGs na camada `silver` com mapeamento para `goal_id`
- `sectoral_scopes`: escopos setoriais da UNFCCC a partir do documento `A6.4-STAN-ACCR-001`
- `technical_areas`: areas tecnicas da UNFCCC com textos em EN/PT/ES para atividades tipicas e conhecimento tecnico

## Padronizacao de nomenclatura no consolidado

- no `reference_dataset.xlsx`, o conceito consolidado passa a usar `standard` ou `standards`
- os arquivos de origem podem continuar usando a nomenclatura historica `certificadora` enquanto nao houver migracao completa
- exemplos de rename aplicados apenas no consolidado:
  - `sigla` -> `standard_acronym` nas abas de standards e metodologias
  - `nome` -> `standard_name` na aba de catalogo
  - `status_certificadora` -> `status_standard` na aba de status

## Observacoes

- a aba `aecom_status` nao entrou no consolidado porque nao possui tabela estruturada ativa
- quando novas abas ou tabelas de referencia forem adicionadas ao workbook canonico, o processo de reparo e validacao deve ser executado
