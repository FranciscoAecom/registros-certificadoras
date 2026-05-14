# Registros Certificadoras

Repositorio para coleta, preservacao, padronizacao e consolidacao de dados
publicos de projetos de credito de carbono por certificadora.

O projeto trabalha com snapshots por data, separando dados brutos, dados
normalizados e produtos analiticos finais em camadas `bronze`, `silver` e
`gold`.

## Objetivo

- Extrair listas publicas de projetos por certificadora.
- Extrair detalhes individuais de cada projeto.
- Preservar o dado bruto sem transformacao analitica na camada `bronze`.
- Padronizar campos em uma camada `silver` rastreavel.
- Consolidar uma base unica `gold` para consumo analitico.
- Manter referencias operacionais editaveis em planilhas.

## Certificadoras

O repositorio possui estrutura para:

- American Carbon Registry
- BioCarbon
- Cercarbono
- Climate Action Reserve
- Equitable Earth
- Gold Standard
- Isometric
- Plan Vivo
- Puro.earth
- Social Carbon
- TERO
- Verra

Nem todas as certificadoras precisam estar no mesmo nivel de maturidade. A
documentacao de cada integracao fica junto aos scripts da propria
certificadora.

## Estrutura

```text
src/
|-- projects_standards/
|   |-- shared/
|   |-- <certificadora>/
|   |   |-- bronze/
|   |   `-- silver/
|   `-- ...
`-- issued_credits_standards/
    |-- shared/
    `-- <certificadora>/

data/
|-- project_standards/
|   |-- 00_reference/
|   |-- 01_bronze/
|   |-- 02_silver/
|   `-- 03_gold/
`-- issued_credits_standards/
    |-- 00_reference/
    |-- 01_bronze/
    |-- 02_silver/
    `-- 03_gold/

docs/agentes/
resultados/
```

Camadas principais:

- `00_reference`: planilhas e arquivos de referencia editaveis.
- `01_bronze`: snapshots brutos por certificadora e data.
- `02_silver`: datasets normalizados por certificadora e data.
- `03_gold`: base analitica consolidada.

## Requisitos

- Python 3.11 ou superior.
- Dependencias listadas em `requirements.txt`.

Ambiente local no PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Fluxo de Projetos

Todos os snapshots de projetos usam `--date` no formato `YYYYMMDD`.

### 1. Bronze: lista de projetos

Exemplo com Verra:

```powershell
python -m src.projects_standards.verra.bronze.extract_project_list --date YYYYMMDD --max-pages 1
```

Para carga completa, remover `--max-pages`:

```powershell
python -m src.projects_standards.verra.bronze.extract_project_list --date YYYYMMDD
```

### 2. Bronze: detalhe por projeto

```powershell
python -m src.projects_standards.verra.bronze.extract_project_details --date YYYYMMDD --limit 10
```

Para carga completa, remover `--limit`:

```powershell
python -m src.projects_standards.verra.bronze.extract_project_details --date YYYYMMDD
```

### 3. Silver: normalizacao por certificadora

```powershell
python -m src.projects_standards.verra.silver.build_silver_dataset --date YYYYMMDD
```

A camada `silver` aplica mapeamentos e normalizacoes deterministicas, preserva
rastreabilidade ate o `bronze` e gera relatorios de qualidade.

### 4. Gold: consolidacao analitica

```powershell
python -m src.projects_standards.shared.gold.build_gold_dataset
```

Para gerar um recorte mensal:

```powershell
python -m src.projects_standards.shared.gold.build_gold_dataset --reference-month YYYY-MM
```

Para gerar Excel a partir de um recorte mensal:

```powershell
python -m src.projects_standards.shared.gold.build_gold_excel --reference-month YYYY-MM
```

Saida principal:

```text
data/project_standards/03_gold/projects/
|-- allprojects.json
|-- schema.json
|-- quality_report.json
`-- backup/
```

## Creditos Emitidos

A frente `issued_credits_standards` foi criada para dados de creditos emitidos
por standard.

Exemplo de coleta bronze de VCUs emitidos pela Verra:

```powershell
python -m src.issued_credits_standards.verra.bronze.extract_issued_credits --start-month YYYY-MM --end-month YYYY-MM
```

Para teste curto:

```powershell
python -m src.issued_credits_standards.verra.bronze.extract_issued_credits --start-month YYYY-MM --end-month YYYY-MM --limit 1
```

## Regras de Dados

### Bronze

- Deve preservar a resposta bruta da fonte.
- A lista de projetos fica em `list/projects.json`.
- O detalhe fica em um JSON por projeto dentro de `projects/`.
- A estrutura de detalhe deve preservar `source`, `list_data` e `detail_data`.
- Snapshots em repouso devem ficar compactados como ZIP ou bundle.
- Pastas descompactadas de execucao nao devem ser versionadas.

### Silver

- Deve aplicar padronizacao deterministica e rastreavel.
- Valores ausentes devem ser padronizados como `null`.
- Datas devem usar `YYYY-MM-DD`.
- Regras compartilhadas ficam em `src/projects_standards/shared/silver/`.
- Cada certificadora possui seu proprio mapeamento `bronze -> silver`.

### Gold

- Deve consolidar todos os datasets `silver` elegiveis.
- A unidade da base e um projeto por `reference_month`.
- O processo deve reconstruir a base inteira, sem append incremental.
- Antes de sobrescrever artefatos finais, a versao anterior deve ir para
  `backup/`.
- A base final deve gerar `allprojects.json`, `schema.json` e
  `quality_report.json`.

## Referencias

O workbook principal de referencias fica em:

```text
data/project_standards/00_reference/reference_dataset.xlsx
```

Ele concentra catalogos e mapeamentos operacionais, incluindo certificadoras,
paises, status, metodologias, areas tecnicas, escopos setoriais e ODS.

## Boas Praticas Operacionais

- Fazer testes curtos antes de cargas completas.
- Usar `--max-pages` em scripts de lista.
- Usar `--limit` em scripts de detalhe.
- Evitar paralelismo em coletas sem decisao explicita.
- Respeitar pausas, retries e limites das fontes publicas.
- Nao salvar credenciais, cookies ou arquivos temporarios no repositorio.
- Manter logs operacionais junto aos scripts da certificadora, nao dentro do
  `bronze`.

## Documentacao

Documentos detalhados ficam em `docs/agentes/`:

- `docs/agentes/premissas_projeto.md`
- `docs/agentes/fluxos_operacionais.md`
- `docs/agentes/guia_bronze.md`
- `docs/agentes/guia_silver.md`
- `docs/agentes/guia_gold.md`
- `docs/agentes/fluxo_gold.md`
- `docs/agentes/mapeamento_gold.md`
- `docs/agentes/modelagem_sqlite_gold.md`

