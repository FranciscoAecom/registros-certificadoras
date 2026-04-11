# Guia da Camada Silver

## Objetivo

Este documento define como os dados da camada `bronze` devem ser lidos, interpretados e transformados para uma futura camada `silver`.

O objetivo da camada `silver` e:

- padronizar a estrutura entre certificadoras
- preservar rastreabilidade ate o dado bruto de origem
- permitir comparacao e analise entre programas diferentes
- orientar o Codex a fazer o mapeamento entre campos brutos e campos canonicos

## Papel da Camada Silver

A camada `silver` nao deve reproduzir cada payload bruto como veio da certificadora. Ela deve:

- escolher uma estrutura canonica unica para todas as certificadoras
- manter nomes de colunas e tipos o mais estaveis possivel
- registrar de onde cada valor veio no `bronze`
- explicitar ausencia, ambiguidade ou conflito de origem

A camada `silver` nao deve:

- apagar a referencia ao `bronze`
- misturar valores inferidos com valores observados sem sinalizacao
- sobrescrever silenciosamente conflitos entre campos de lista e detalhe

## Principios de Transformacao

- O `bronze` continua sendo a fonte de verdade original.
- A `silver` e a camada canonica para consumo analitico e consolidacao.
- Cada campo canonico da `silver` deve ter uma regra de origem clara.
- Sempre que possivel, o valor da `silver` deve apontar para um caminho de origem no `bronze`.
- Quando o mesmo conceito existir em varias certificadoras com nomes diferentes, a `silver` deve convergir para um unico nome canonico.
- Quando um campo nao existir em uma certificadora, o valor deve ficar nulo, sem inventar preenchimento.
- Quando houver necessidade de derivacao, isso deve ficar explicitado como regra de transformacao.
- Regras compartilhadas de padronizacao, parsing e validacao devem ficar centralizadas em `src/projects_standards/shared/silver/`.
- `src/projects_standards/shared/silver/framework.py` deve atuar como orquestrador compartilhado da geracao de mapeamentos e datasets da `silver`.
- A ordem dos campos em mapeamentos, planilhas e scripts de transformacao deve seguir o agrupamento e a sequencia definidos na `Estrutura Canonica Recomendada`.
- Se um nome de campo em ingles se mostrar impreciso, ambiguo ou pouco natural, o schema canonico pode evoluir para um nome melhor, desde que a alteracao fique documentada no guia e nos mapeamentos afetados.
- O mapeamento inicial nao deve ser validado apenas por inspeção de poucos arquivos escolhidos manualmente.
- Para reduzir falsos `unmapped`, o agente deve inspecionar uma amostra hibrida de pelo menos `10%` dos arquivos de detalhe disponiveis no snapshot analisado.
- Quando `10%` resultar em fracao, a amostra deve ser arredondada para cima.
- Em snapshots com poucos arquivos, a inspecao deve cobrir no minimo `10` arquivos, ou todos os arquivos quando houver menos de `10`.
- A estrategia padrao dessa amostra hibrida deve combinar parte dos maiores arquivos do snapshot com uma parte aleatoria dos demais arquivos.
- Sempre que possivel, a amostra deve buscar diversidade de status, tipo de projeto, programa ou outras variacoes relevantes do bruto.
- O primeiro resultado dessa etapa deve ser tratado como mapeamento exploratorio.
- Depois de refinado e validado, ele deve ser promovido a mapeamento canonico da certificadora.
- O mapeamento canonico deve ser mantido estavel entre snapshots recorrentes, para preservar consistencia historica.
- A execucao mensal do processo `bronze -> silver` deve reaplicar o mapeamento canonico vigente, e nao reconstruir o mapeamento do zero a cada rodada.

## Regra de Amostragem para Mapeamento

Ao construir um mapeamento inicial `bronze -> silver`, o agente deve seguir pelo menos esta regra minima:

- calcular o total de arquivos de detalhe do snapshot
- selecionar uma amostra hibrida de pelo menos `10%` desse total
- arredondar para cima quando houver fracao
- respeitar um piso de `10` arquivos, salvo snapshots menores
- reservar parte da amostra para os maiores arquivos do snapshot
- reservar parte da amostra para selecao aleatoria
- usar essa amostra para avaliar cobertura e plausibilidade das fontes candidatas

Quando houver heterogeneidade relevante entre os projetos, uma abordagem melhor do que a estrategia hibrida simples e:

- amostragem hibrida estratificada por status
- amostragem hibrida estratificada por tipo de projeto
- amostragem hibrida estratificada por programa ou fase do ciclo de vida
- amostragem aleatoria estratificada por status
- amostragem aleatoria estratificada por tipo de projeto
- amostragem aleatoria estratificada por programa ou fase do ciclo de vida

Se essa abordagem melhor for usada, ela deve ficar explicitada no documento de mapeamento da certificadora.

## Padronizacao de Valores na Silver

Antes de gravar o dataset final da `silver`, o processo deve aplicar uma normalizacao compartilhada e deterministica por tipo de campo.

Essa normalizacao deve seguir estas regras base:

- campos textuais:
  - aplicar trim
  - reduzir espacos excedentes internos
  - converter strings vazias e marcadores usuais de ausencia para `null`
- qualquer valor vazio, independentemente do tipo:
  - converter para `null`
  - isso inclui listas vazias, objetos vazios e estruturas equivalentes sem conteudo util
- campos `date`:
  - usar sempre `YYYY-MM-DD`
- campos `datetime`:
  - usar sempre `YYYY-MM-DDTHH:MM:SS`
- campos numericos:
  - manter tipo numerico quando houver origem confiavel
- listas:
  - remover itens vazios
  - remover duplicados preservando a ordem original quando tecnicamente viavel
  - para `project_methodology`, `sdg_targets` e `sector`, o valor canonico deve ser sempre uma lista
  - quando nao houver nenhum valor confiavel nesses tres campos, gravar lista vazia `[]`

Essa padronizacao nao deve:

- inventar valor ausente
- sobrescrever conflito sem regra documentada
- alterar a semantica do valor bruto observado

Organizacao recomendada dos utilitarios compartilhados:

```text
src/
`-- projects_standards/
    `-- shared/
        `-- silver/
            |-- framework.py
            |-- normalize.py
            |-- dates.py
            |-- text.py
            |-- numbers.py
            |-- missing.py
            `-- quality_checks.py
```

Responsabilidades esperadas:

- `framework.py`
  - orquestracao de mapeamento e geracao de dataset
  - descompacta automaticamente o snapshot `bronze` (`.zip`) antes de ler os dados
  - recompacta o snapshot `bronze` em `.zip` ao final do processamento
  - usa `pack_directory` e `unpack_archive` de `archive_data.py`
- `normalize.py`
  - normalizacao por campo canonico
- `dates.py`
  - parsing e formatacao de datas e datetimes
- `text.py`
  - trim e reducao de espacos excedentes
- `numbers.py`
  - parsing numerico compartilhado
- `missing.py`
  - tratamento de vazios e marcadores de ausencia
- `quality_checks.py`
  - validacoes leves e nao destrutivas de consistencia

## Mapeamento Exploratorio e Mapeamento Canonico

Para cada certificadora, o processo recomendado passa a ter dois artefatos conceitualmente diferentes:

- mapeamento exploratorio
- mapeamento canonico

O mapeamento exploratorio serve para:

- descobrir campos candidatos
- medir cobertura
- identificar lacunas
- apoiar refinamentos iniciais

O mapeamento canonico serve para:

- registrar a versao estabilizada das regras de transformacao
- orientar a criacao recorrente do dataset `silver`
- preservar consistencia entre snapshots mensais

Regra operacional:

- primeiro, o agente gera e revisa o mapeamento exploratorio
- depois, estabiliza as regras e promove esse resultado a mapeamento canonico
- dali em diante, as execucoes recorrentes usam o mapeamento canonico
- revisoes futuras do mapeamento canonico devem ser conservadoras e explicitamente documentadas

## Unidade Recomendada de Silver

Recomenda-se que a granularidade principal da camada `silver` seja:

- um registro por projeto por `snapshot_date`

Isso permite:

- historico temporal
- reprocessamento por snapshot
- comparacao de mudancas cadastrais

## Estrutura Canonica Recomendada

A proposta inicial para a camada `silver` e usar uma estrutura unica por projeto com os seguintes blocos logicos.

### 1. Metadados do Registro

- `standard_name`
- `standard_acronym`
- `project_public_id`
- `project_internal_id`
- `project_url`
- `bronze_file_path`
- `source_file_name`

### 2. Identificacao do Projeto

- `project_name`
- `project_voluntary_status`
- `project_regulatory_status`
- `standard_program`
- `project_description`
- `project_methodology`
- `project_type`
- `sector`
- `project_category`
- `project_subcategories`
- `sdg_targets`

### 3. Entidades Relacionadas

- `project_developer`
- `project_owner`
- `project_operator`
- `validator_name`
- `verifier_name`

### 4. Localizacao

- `country`
- `state_or_region`
- `city_or_locality`
- `location_latitude`
- `location_longitude`
- `project_geometry`

### 5. Datas

- `snapshot_date`
- `reference_month`
- `registration_date`
- `status_date`
- `crediting_start_date`
- `crediting_end_date`
- `first_issuance_date`
- `last_issuance_date`

### 6. Quantidades e Indicadores

- `credits_issued_total`
- `credits_retired_total`
- `credits_cancelled_total`
- `credits_buffer_total`
- `estimated_annual_emission_reductions`
- `estimated_total_emission_reductions`
- `area_hectares`

## Primeira Lista de Campos Canonicos Prioritarios

Como primeiro passo do `mapeamento de campos`, a recomendacao e padronizar os campos abaixo entre todas as certificadoras.

Esses campos foram escolhidos por relevancia analitica e por recorrencia esperada nas fontes, mesmo quando algumas certificadoras nao os disponibilizarem.

Os nomes usados nesta secao devem ser os mesmos da `Estrutura Canonica Recomendada`.

## Descricao Resumida dos Campos da Estrutura Canonica

Esta secao descreve, de forma resumida, todos os campos listados na `Estrutura Canonica Recomendada`.

### Metadados do Registro

- `standard_name`
  - nome padrao da certificadora no dataset
- `standard_acronym`
  - sigla da certificadora em ingles
  - deve ser buscada preferencialmente na referencia de certificadoras
- `project_public_id`
  - identificador publico do projeto
- `project_internal_id`
  - identificador interno usado pela certificadora ou pelo endpoint
- `project_url`
  - url publica do projeto
- `bronze_file_path`
  - caminho do arquivo bruto principal usado para gerar o registro transformado
- `source_file_name`
  - nome do arquivo bruto de origem usado no processamento

### Identificacao do Projeto

- `project_name`
  - nome principal do projeto
- `project_voluntary_status`
  - status do projeto no contexto do mercado voluntario, preservando a nomenclatura da certificadora
- `project_regulatory_status`
  - status do projeto no contexto do mercado regulado, preservando a nomenclatura da certificadora
- `standard_program`
  - nome do programa, padrao ou iniciativa a que o projeto esta vinculado
- `project_description`
  - descricao textual principal do projeto
- `project_methodology`
  - uma ou mais metodologias textuais associadas ao projeto; este campo deve ser sempre salvo como lista, inclusive quando houver apenas um valor ou nenhum
- `project_type`
  - tipo do projeto segundo a classificacao da certificadora
- `sector`
  - um ou mais setores do projeto; este campo deve ser sempre salvo como lista
- `project_category`
  - categoria principal do projeto quando a fonte trouxer esse nivel de classificacao
- `project_subcategories`
  - subcategoria ou lista de subcategorias do projeto, incluindo classificacoes complementares como AFOLU quando a fonte expuser esse detalhamento
- `sdg_targets`
  - lista de metas associadas aos Objetivos de Desenvolvimento Sustentavel da ONU; este campo deve ser sempre salvo como lista

### Entidades Relacionadas

- `project_developer`
  - nome da entidade desenvolvedora do projeto
- `project_owner`
  - nome da entidade proprietaria do projeto
- `project_operator`
  - nome da entidade operadora ou responsavel pela execucao
- `validator_name`
  - entidade responsavel pela validacao do projeto
- `verifier_name`
  - entidade responsavel pela verificacao do projeto

### Localizacao

- `country`
  - valor de pais do projeto exatamente como vier no arquivo bruto, sem normalizacao nesta camada
- `state_or_region`
  - estado, provincia ou regiao administrativa do projeto
- `city_or_locality`
  - cidade, municipio, comunidade ou localidade informada pela fonte
  - descricao textual bruta da localizacao quando a fonte trouxer um campo livre
- `location_latitude`
  - latitude do projeto quando existir
- `location_longitude`
  - longitude do projeto quando existir
- `project_geometry`
  - geometria do projeto em formato GeoJSON-like (`Point`, `Polygon`, `MultiPolygon` etc.) quando a fonte expuser vertices ou objeto de geometria
  - quando nao houver geometria explicita e existirem latitude/longitude, pode ser derivado como `Point`

### Datas

- `snapshot_date`
  - data do snapshot no formato `YYYY-MM-DD`
- `reference_month`
  - primeiro dia do mes de `snapshot_date`, no formato `YYYY-MM-DD`
- `registration_date`
  - data de registro do projeto
- `status_date`
  - data associada ao status atual do projeto, quando existir
- `crediting_start_date`
  - data de inicio do periodo de crediting
- `crediting_end_date`
  - data de fim do periodo de crediting
- `first_issuance_date`
  - data da primeira emissao de creditos vinculada ao projeto
- `last_issuance_date`
  - data da emissao mais recente de creditos vinculada ao projeto

### Quantidades e Indicadores

- `credits_issued_total`
  - quantidade total de creditos emitidos para o projeto
- `credits_retired_total`
  - quantidade total de creditos aposentados ou retirados de circulacao
- `credits_cancelled_total`
  - quantidade total de creditos cancelados
- `credits_buffer_total`
  - quantidade total de creditos destinados a buffer, reserva ou mecanismo equivalente
- `estimated_annual_emission_reductions`
  - estimativa anual de reducoes ou remocoes de emissoes declarada pela fonte
- `estimated_total_emission_reductions`
  - estimativa total acumulada de reducoes ou remocoes de emissoes declarada pela fonte
- `area_hectares`
  - area do projeto em hectares

## Observacoes Importantes Sobre Semantica

- `estimated_annual_emission_reductions` deve ser tratado como o nome canonico mais seguro para campos como `estAnnualEmissionReductions`.
- Se a certificadora expuser remocoes, reducoes, reducoes evitadas ou estimativas anuais sob rotulos diferentes, a regra de mapeamento deve registrar isso claramente em `notes`.
- `credits_issued_total`, `credits_retired_total`, `credits_cancelled_total` e `credits_buffer_total` devem preservar a semantica exata da fonte e nao ser preenchidos por inferencia quando a certificadora nao expuser esses totais de forma confiavel.
- `project_voluntary_status` e `project_regulatory_status` nao devem ser consolidados automaticamente em um unico campo `project_status`.
- Cada certificadora pode expor apenas um dos mercados, ambos os mercados ou nenhum status confiavel; nessa situacao, o campo sem origem valida deve permanecer `null`.
- `project_methodology` deve aceitar um ou mais valores por projeto quando a certificadora expuser multiplas metodologias.
- Mesmo quando houver apenas uma metodologia, o valor final da `silver` deve ser uma lista com um item.
- Quando nao houver metodologia confiavel, o valor final deve ser a lista vazia `[]`.
- Quando a fonte trouxer varias metodologias, o mapeamento deve registrar claramente a regra adotada para manter a multiplicidade como lista ordenada.
- `project_category` deve guardar a classificacao principal do projeto.
- `project_subcategories` deve guardar classificacoes complementares do projeto, inclusive atividades AFOLU como reflorestamento, conservacao, ARR, IFM, REDD+ ou equivalentes quando a fonte expuser esse detalhamento.
- Quando a fonte trouxer apenas uma subcategoria, o mapeamento pode registrar um valor unico.
- Quando a fonte trouxer varias subcategorias, o mapeamento deve preservar a multiplicidade, preferencialmente como lista ordenada.
- `project_description` deve buscar a descricao principal mais rica do projeto, preferindo o detalhe quando ele for claramente superior ao resumo da lista.
- `country` deve preservar o valor bruto do pais como vier da certificadora, seja codigo, nome completo ou texto em idioma local.
- `sdg_targets` deve guardar identificadores canonicos das metas dos ODS, como `13.1`, `15.2` ou equivalente textual bruto quando a fonte nao expuser codigo estruturado.
- `sdg_targets` deve ser sempre uma lista, ainda que contenha apenas um valor ou nenhum.
- `sector` deve ser sempre uma lista, ainda que contenha apenas um valor ou nenhum.
- Campos numericos da `silver` nao devem usar uma unica heuristica global para separadores decimais e de milhar.
- A normalizacao numerica deve ser orientada pelo tipo canonico do campo, distinguindo ao menos coordenadas, contagens/totais e medidas decimais.
- Quando uma certificadora usar convencao numerica diferente do padrao predominante, o tratamento deve ser ajustado por override no builder da certificadora ou no transformador especifico do campo.
- Quando nao houver campo correspondente ou valor confiavel no dado bruto, o campo canonico deve permanecer `null` na `silver`.
- Regras de completude, imputacao, score de qualidade e tratamento de lacunas devem ficar para a camada `gold`, nao para a `silver`.

## Tabela Inicial de Padronizacao de Nomes

| Conceito de negocio | Nome canonico sugerido | Tipo esperado | Observacao |
| --- | --- | --- | --- |
| Nome da certificadora | `standard_name` | string | Valor padrao da certificadora |
| Sigla da certificadora | `standard_acronym` | string | Buscar na referencia de certificadoras |
| ID publico do projeto | `project_public_id` | string | Identificador exposto publicamente |
| ID interno do projeto | `project_internal_id` | string | Identificador tecnico do detalhe |
| URL publica do projeto | `project_url` | string | URL navegavel do projeto |
| Caminho do arquivo bruto | `bronze_file_path` | string | Caminho do bruto usado na transformacao |
| Nome do arquivo bruto | `source_file_name` | string | Nome do arquivo de origem processado |
| Nome do projeto | `project_name` | string | Campo textual principal |
| Status voluntario do projeto | `project_voluntary_status` | string | Usar para programas do mercado voluntario sem normalizar o texto |
| Status regulado do projeto | `project_regulatory_status` | string | Usar para programas do mercado regulado sem normalizar o texto |
| Nome do programa | `standard_program` | string | Programa ou iniciativa vinculada ao projeto |
| Descricao do projeto | `project_description` | string | Descricao principal consolidada |
| Metodologia do projeto | `project_methodology` | array[string] | Sempre salvar como lista; usar `[]` quando nao houver valor |
| Tipo do projeto | `project_type` | string | Classificacao textual da certificadora |
| Setor do projeto | `sector` | array[string] | Sempre salvar como lista; usar `[]` quando nao houver valor |
| Categoria do projeto | `project_category` | string | Categoria principal quando existir |
| Subcategorias do projeto | `project_subcategories` | string ou array[string] | Aceitar uma ou mais subcategorias, inclusive detalhamentos AFOLU |
| Metas ODS da ONU | `sdg_targets` | array[string] | Sempre salvar como lista; preferir codigos canonicos das metas, como `13.1` |
| Desenvolvedor do projeto | `project_developer` | string | Entidade desenvolvedora principal |
| Proprietario do projeto | `project_owner` | string | Entidade proprietaria principal |
| Operador do projeto | `project_operator` | string | Entidade operadora principal |
| Entidade de validacao | `validator_name` | string | Organismo responsavel pela validacao |
| Entidade de verificacao | `verifier_name` | string | Organismo responsavel pela verificacao |
| Pais | `country` | string | Preservar valor bruto da certificadora sem normalizacao |
| Estado ou regiao | `state_or_region` | string | Estado, provincia ou regiao administrativa |
| Cidade ou localidade | `city_or_locality` | string | Cidade, municipio ou localidade |
| Latitude | `location_latitude` | number | Coordenada geografica |
| Longitude | `location_longitude` | number | Coordenada geografica |
| Geometria do projeto | `project_geometry` | object | GeoJSON-like (`Point`, `Polygon`, `MultiPolygon`) derivado de geometry/vertices ou de latitude+longitude |
| Data do snapshot | `snapshot_date` | date | Formato `YYYY-MM-DD` |
| Mes de referencia | `reference_month` | date | Primeiro dia do mes |
| Data de registro | `registration_date` | date | Pode vir da lista ou detalhe |
| Data do status | `status_date` | date | Data associada ao status atual |
| Inicio do crediting | `crediting_start_date` | date | Pode vir da lista ou detalhe |
| Fim do crediting | `crediting_end_date` | date | Pode vir da lista ou detalhe |
| Primeira emissao | `first_issuance_date` | date | Data da primeira emissao de creditos |
| Ultima emissao | `last_issuance_date` | date | Data da emissao mais recente de creditos |
| Creditos emitidos totais | `credits_issued_total` | number | Total emitido para o projeto |
| Creditos aposentados totais | `credits_retired_total` | number | Total retirado de circulacao |
| Creditos cancelados totais | `credits_cancelled_total` | number | Total cancelado |
| Creditos de buffer totais | `credits_buffer_total` | number | Total destinado a buffer ou reserva |
| Estimativa anual de reducoes | `estimated_annual_emission_reductions` | number | Tratar como total/contagem, salvo override explicito |
| Estimativa total de reducoes | `estimated_total_emission_reductions` | number | Tratar como total/contagem, salvo override explicito |
| Area em hectares | `area_hectares` | number | Tratar como medida decimal; aceitar override de locale quando necessario |

## Regra Inicial Para Mapeamento Desses Campos

Para cada certificadora, o proximo passo deve ser construir uma tabela com:

- `target_field`
- `source_section`
- `source_path`
- `rule_type`
- `expected_type`
- `fallback_source_path`
- `notes`

Exemplo resumido:

| target_field | source_section | source_path | rule_type | expected_type | fallback_source_path | notes |
| --- | --- | --- | --- | --- | --- | --- |
| `project_name` | `list_data` | `Project Name` | `direct` | string | `detail_data.resourceName` | Preferir lista quando houver equivalencia clara |
| `crediting_start_date` | `list_data` | `Current Crediting Period Start Date` | `normalized` | date | `detail_data.project.startDate` | Converter para `YYYY-MM-DD` |
| `estimated_annual_emission_reductions` | `detail_data` | `estAnnualEmissionReductions` | `normalized` | number |  | Preservar unidade e semantica da fonte |

## Estrutura Fisica Recomendada

Uma opcao recomendada para a organizacao futura e:

```text
data/
└─ silver/
   └─ projects/
      └─ YYYYMMDD/
         └─ projects.json
```

Alternativamente, se o volume crescer:

```text
data/
└─ silver/
   └─ projects/
      └─ YYYYMMDD/
         ├─ projects.parquet
         └─ mapping_report.json
```

## Contrato Minimo de Mapeamento

Cada campo da `silver` deve ter uma regra explicita com estes elementos:

- `target_field`
- `source_layer`
- `source_section`
- `source_path`
- `rule_type`
- `transformation_rule`
- `fallback_rule`
- `notes`

Exemplo conceitual:

```json
{
  "target_field": "project_name",
  "source_layer": "bronze",
  "source_section": "list_data",
  "source_path": "Project Name",
  "rule_type": "direct",
  "transformation_rule": "copiar valor textual sem alterar conteudo",
  "fallback_rule": "usar detail_data.project.name se o campo da lista estiver ausente",
  "notes": "preferir nome vindo da lista quando houver equivalencia semantica"
}
```

## Tipos de Regra de Mapeamento

Padronizar o tipo da regra ajuda o Codex a decidir como preencher cada campo.

Tipos sugeridos:

- `direct`
  - copia direta da origem para o destino
- `rename`
  - mesmo valor, mas com nome canonico diferente
- `derived`
  - valor calculado a partir de um ou mais campos
- `normalized`
  - valor convertido para padrao comum, como data ou formato numerico
- `fallback`
  - campo que tenta uma origem principal e outra secundaria
- `aggregated`
  - soma, contagem ou consolidacao de subestruturas
- `constant`
  - valor fixo, como o nome da certificadora
- `lookup`
  - valor buscado em tabela de referencia externa, como a aba `standards_catalog` do `reference_dataset.xlsx`
- `unmapped`
  - conceito ainda nao mapeado

## Ordem Recomendada de Busca no Raw

Para preencher um campo canonico da `silver`, o Codex deve seguir esta ordem:

1. verificar se o valor existe em `source`, quando o campo for metadado do proprio snapshot
2. verificar `list_data` para campos cadastrais mais simples e estaveis
3. verificar `detail_data` para campos ricos, tecnicos ou listas complementares
4. aplicar fallback entre lista e detalhe quando a regra do campo permitir
5. registrar `null` quando nenhuma origem confiavel existir

## Regras de Prioridade Entre Lista e Detalhe

- Se a lista trouxer um identificador oficial do projeto, priorizar o da lista.
- Se o detalhe trouxer um campo mais completo do que a lista, priorizar o detalhe.
- Se lista e detalhe divergirem em campos textuais relevantes, manter o valor escolhido pela regra e registrar a divergencia no artefato de mapeamento ou na documentacao operacional da transformacao.
- Nao concatenar lista e detalhe automaticamente sem uma regra explicita.

## Padroes de Tipagem Recomendados

- datas: `YYYY-MM-DD`
- datetimes: `YYYY-MM-DDTHH:MM:SS`
- numeros inteiros: tipo numerico, nao string
- valores monetarios ou quantitativos: tipo numerico com unidade documentada
- booleanos: `true` ou `false`
- listas: listas explicitas, nao string separada por virgula
- ausencias: `null`

## Campos Canonicos Minimos Obrigatorios

Mesmo que parte do restante fique nula, recomenda-se que todo registro `silver` tenha pelo menos:

- `standard_name`
- `snapshot_date`
- `reference_month`
- `project_public_id`
- `project_internal_id`
- `project_url`
- `project_name`
- pelo menos um entre `project_voluntary_status` e `project_regulatory_status`, quando a certificadora expuser status do projeto

## Convencao Para Campos Sem Origem

Quando um campo canonico nao encontrar origem valida no `bronze`:

- o valor final deve ficar `null`
- o mapeamento deve registrar o campo como `unmapped` ou equivalente
- a ausencia nao deve ser corrigida por inferencia heuristica nesta camada
- qualquer tratamento de qualidade, completude ou enriquecimento deve acontecer somente na camada `gold`

## Como o Codex Deve Trabalhar

Ao criar a transformacao para uma certificadora, o Codex deve:

1. abrir exemplos reais de `bronze`
2. identificar onde cada conceito aparece em `source`, `list_data` e `detail_data`
3. montar o `mapeamento de campos` da certificadora para o schema canonico
4. explicitar fallback e regras de normalizacao
5. preservar rastreabilidade do caminho de origem
6. nao criar regra implicita sem documenta-la

## Artefatos Recomendados para Apoiar a Silver

Para sustentar a camada `silver`, recomenda-se criar futuramente:

- uma planilha de `mapeamento de campos` por certificadora
- um dicionario de dados canonico da camada `silver`
- uma tabela de `de_para` para status voluntario e regulatorio de projeto
- uma tabela de `de_para` para metodologias e codigos de metodologia
- uma tabela de `de_para` para paises e codigos

## Modelo Recomendado de Planilha de Mapeamento

Uma planilha editavel por humanos pode ter colunas como:

- `standard_name`
- `target_field`
- `source_section`
- `source_path`
- `rule_type`
- `priority`
- `fallback_source_path`
- `expected_type`
- `normalization_rule`
- `business_rule`
- `example_bronze_value`
- `example_silver_value`
- `status`
- `notes`

## Exemplo de Decisao de Mapeamento

Se uma certificadora usa:

- `Project ID` na lista
- `resourceIdentifier` no detalhe

e ambos representam o mesmo identificador publico, a camada `silver` deve convergir para:

- `project_public_id`

Se uma certificadora usa um `id` numerico interno para montar a URL de detalhe, esse valor deve convergir para:

- `project_internal_id`

## Tratamento de Conflitos

Quando houver conflito entre origem e destino:

- nao descartar o bruto
- escolher uma regra de precedencia documentada
- registrar observacao de conflito
- manter o caminho do campo de origem escolhido

## Evolucao do Documento

Este arquivo deve servir como base para:

- implementacao dos scripts de transformacao `bronze -> silver`
- construcao de planilhas de mapeamento
- revisao de qualidade dos dados canonicos
- orientacao futura do Codex em tarefas de padronizacao

Quando a camada `silver` comecar a ser implementada, este guia deve ser complementado por:

- dicionario de dados canonico
- especificacao fisica dos arquivos `silver` e `gold`
- convencoes de validacao
- regras de deduplicacao e historizacao
