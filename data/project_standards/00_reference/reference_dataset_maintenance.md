# Reference Dataset Maintenance

Este documento registra as regras de criacao, edicao, validacao e manutencao do arquivo [reference_dataset.xlsx](/C:/Users/pedro.almeida/registrosCertificadoras/data/project_standards/00_reference/reference_dataset.xlsx).

## Objetivo

O workbook `reference_dataset.xlsx` centraliza as tabelas de referencia usadas pelo projeto em um unico arquivo Excel. Ele deve continuar:

- abrindo no Excel sem dialogo de reparo
- preservando tabelas estruturadas em todas as abas
- mantendo cabecalhos, filtros e hyperlinks consistentes
- servindo como ponto unico de governanca dos dados de referencia

## Causa do erro que ocorreu

O erro recente nao foi mais causado por `AutoFilter` duplicado no worksheet. Desta vez, a causa foi outra:

- os cabecalhos visiveis da primeira linha foram renomeados
- os metadados internos das tabelas em `xl/tables/table*.xml` continuaram com os nomes antigos
- o Excel detectou a divergencia entre cabecalho da aba e colunas da tabela
- ao abrir o arquivo, o Excel reparou as tabelas automaticamente

Exemplo pratico do problema:

- cabecalho visivel: `standard_country`
- metadado interno da tabela: `pais_origem`

Quando isso acontece, o arquivo pode abrir com a mensagem de reparo e o Excel pode reescrever ou remover partes da tabela.

## Regra estrutural obrigatoria

Em toda aba que tiver tabela estruturada:

- a linha 1 deve conter o cabecalho oficial
- os nomes das colunas internas da tabela devem ser exatamente iguais aos valores da linha 1
- o `AutoFilter` deve existir apenas dentro da tabela
- o worksheet nao deve ter `AutoFilter` proprio fora da tabela
- o workbook nao deve manter `_xlnm._FilterDatabase`

## Processo recomendado de manutencao

Sempre que o workbook for alterado por script:

1. editar valores, abas, cabecalhos e larguras normalmente
2. sincronizar os nomes internos das tabelas com a linha 1
3. remover `AutoFilter` no nivel do worksheet
4. remover `_xlnm._FilterDatabase`
5. validar se os cabecalhos da aba continuam iguais aos nomes internos da tabela
6. abrir no Excel para uma validacao final quando a mudanca for estrutural

## Scripts oficiais

### Geracao completa

Use o gerador consolidado quando os workbooks de origem estiverem disponiveis:

```powershell
python src/projects_standards/shared/reference/build_reference_dataset.py
```

### Reparo estrutural

Use este script quando o `reference_dataset.xlsx` ja existir e tiver sido editado:

```powershell
python src/projects_standards/shared/reference/repair_reference_dataset.py
```

O reparador:

- sincroniza os nomes internos das colunas das tabelas
- remove `AutoFilter` indevido do worksheet
- remove `_xlnm._FilterDatabase`
- valida a coerencia do workbook antes de finalizar

## Boas praticas de edicao

- Preferir editar o workbook consolidado com uma rotina dedicada, nao com scripts ad hoc soltos.
- Quando renomear um cabecalho, sempre sincronizar a tabela correspondente no mesmo fluxo.
- Evitar salvar uma versao intermediaria como final sem rodar o reparador.
- Nao manter copias temporarias do workbook no diretorio final.
- Se o arquivo estiver aberto no Excel, fechar antes de qualquer escrita automatica.

## Validacoes minimas apos cada alteracao

- O arquivo abre no Excel sem mensagem de reparo.
- Todas as abas continuam com tabela estruturada.
- Os filtros da tabela continuam funcionando.
- Hyperlinks permanecem clicaveis quando aplicavel.
- Os nomes das colunas permanecem em ingles e coerentes com o contrato atual do dataset.

## Contrato atual de nomenclatura

O workbook consolidado usa o termo `standard` ou `standards` como padrao semantico, mesmo quando arquivos historicos ainda usam `certificadora`.

Exemplos:

- `standards_catalog`
- `standards_status`
- `common_pipeline_status`
- `countries_observed_mapping`

## Quando revisar este documento

Revisar estas orientacoes quando houver:

- criacao de novas abas de referencia
- mudanca do processo de consolidacao
- substituicao da biblioteca usada para editar XLSX
- qualquer novo erro de reparo exibido pelo Excel
