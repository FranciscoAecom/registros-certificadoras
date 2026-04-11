# Fluxo Gold

## Fluxo 6: Construcao da Gold

Objetivo:

- consolidar todos os projetos `silver` em uma base unica
- deduplicar o projeto dentro do mesmo `reference_month`
- aplicar padronizacoes finais baseadas nas referencias

Passos esperados:

1. Descobrir todos os datasets `silver` disponiveis no repositorio.
2. Ler os projetos de todas as standards e snapshots elegiveis.
3. Enriquecer cada registro com metadados minimos de origem da `silver`.
4. Construir `project_history_id` como `standard_acronym + "_" + project_internal_id`.
5. Construir `record_id` como `standard_acronym + "_" + project_internal_id + "_" + reference_month`.
6. Agrupar registros pelo projeto dentro do mesmo `reference_month`.
7. Manter apenas o registro mais atualizado do mes.
8. Padronizar SDGs via referencia.
9. Padronizar pais via referencia.
10. Buscar `technical_area_id` a partir da metodologia.
11. Derivar `sectoral_scope_id` a partir de `technical_areas`.
12. Resolver `standard_reported_project_status` efetivo conforme `project_market` e regra da standard.
13. Mapear o status efetivo para o `standard_pipeline_status_id`.
14. Gerar o JSON final da `gold`.
15. Gerar `schema.json`.
16. Gerar `quality_report.json`.
17. Se existirem artefatos anteriores, criar uma pasta timestampada em `backup/` antes da sobrescrita.
18. Mover para essa pasta, mantendo os nomes originais:
   - `allprojects.json`
   - `quality_report.json`

## Regras Permanentes

- A `gold` deve ser sempre reconstruida integralmente.
- A `gold` nao deve operar por append incremental como estrategia oficial.
- O backup da versao anterior deve acontecer antes da sobrescrita dos arquivos finais.
- O backup deve ser organizado por pasta timestampada dentro de `data/project_standards/03_gold/projects/backup/`.
- A deduplicacao mensal deve manter somente o registro mais atualizado por projeto no mes.
- O processo deve ser deterministicamente reproduzivel a partir da `silver` e das referencias.
