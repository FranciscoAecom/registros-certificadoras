# AGENTS

Este repositório coleta dados brutos de projetos de crédito de carbono de diferentes certificadoras.

Este arquivo define as regras base para qualquer agente de IA que trabalhe neste projeto.

## Objetivo do Projeto

- Extrair dados brutos por certificadora.
- Trabalhar em duas etapas distintas:
  - lista completa de projetos
  - detalhe individual de cada projeto
- Preservar o dado bruto sem transformar sua estrutura nesta camada.

## Estrutura Padrao

Todo agente deve respeitar esta organiza??o:

```text
src/
`-- projects_standards/
    |-- shared/
    |   |-- archive_data.py
    |   `-- silver/
    |       |-- framework.py
    |       |-- normalize.py
    |       |-- dates.py
    |       |-- text.py
    |       |-- numbers.py
    |       |-- missing.py
    |       `-- quality_checks.py
    `-- <certificadora>/
        |-- bronze/
        |   |-- extract_project_list.py
        |   |-- extract_project_details.py
        |   |-- docs/
        |   |   |-- integration_notes.md
        |   |   `-- <documento_auxiliar>.md
        |   `-- logs/
        |       `-- <arquivo_operacional>.json
        `-- silver/
            |-- build_silver_dataset.py
            |-- map_silver_fields.py
            |-- sync_status_reference.py
            |-- sync_country_reference.py
            |-- sync_methodology_reference.py
            |-- docs/
            |   `-- <documento_auxiliar>.md
            `-- logs/
                `-- <arquivo_operacional>.json

data/
`-- project_standards/
    |-- 00_reference/
    |   |-- reference_dataset.xlsx
    |   |-- README.md
    |   `-- reference_dataset_maintenance.md
    |-- 01_bronze/
    |   `-- <certificadora>/
    |       `-- YYYYMMDD.zip          <-- snapshot compactado em repouso
    |           (conteudo interno:)
    |           |-- list/
    |           |   `-- projects.json
    |           `-- projects/
    |               |-- <project_id>.json
    |               `-- ...
    |-- 02_silver/
    |   `-- <certificadora>/
    |       `-- YYYYMMDD/
    |           |-- allprojects.json
    |           |-- mapping_report.json
    |           `-- quality_report.json
    `-- 03_gold/
        `-- projects/
            |-- allprojects.json
            |-- schema.json
            `-- quality_report.json
```

## Regras de Arquitetura

- O diretório datado `YYYYMMDD` só deve ser criado durante a execução do script.
- `extract_project_list.py` deve baixar a lista bruta completa da certificadora.
- `extract_project_details.py` deve ler a lista de uma data específica e baixar um JSON por projeto.
- O dado bruto de detalhe deve ser salvo em um arquivo por projeto.
- O JSON bruto de detalhe deve preservar a separação entre origem e conteúdo:
  - `source`
  - `list_data`
  - `detail_data`
- `source` deve registrar metadados mínimos do snapshot e do identificador do projeto.
- Em arquivos de detalhe, `source` deve usar `carbon_standard` como nome padrão do identificador da certificadora.
- Em arquivos de detalhe, `source.snapshot_date` deve ser salvo em formato ISO `YYYY-MM-DD`.
- Em arquivos de detalhe, `source.reference_month` deve registrar o primeiro dia do mês de `snapshot_date`, também em formato ISO `YYYY-MM-DD`.
- Em arquivos de detalhe, `source` deve padronizar os identificadores como:
  - `project_public_id`
  - `project_internal_id`
- Em arquivos de detalhe, a URL pública do projeto deve ser registrada em `project_url`.
- Quando a lista da certificadora expuser simultaneamente identificador público e identificador interno, o registro bruto da lista deve preservar ambos e o script de detalhe deve preferir o identificador interno já salvo no snapshot, evitando redescoberta desnecessária em tempo de execução.
- `list_data` deve armazenar o registro bruto vindo da lista da certificadora para aquele projeto.
- `detail_data` deve armazenar o retorno bruto do detalhe da certificadora para aquele projeto.
- Não consolidar o bruto de detalhe em um único arquivo nesta camada.
- Ao final de cada execução de `extract_project_list.py` ou `extract_project_details.py`, o script deve compactar o diretório do snapshot em `.zip` usando `pack_directory` de `archive_data.py` e remover a pasta original.
- Antes de ler dados de um snapshot que possa estar compactado, o script deve verificar se existe o `.zip` correspondente e, se necessário, descompactá-lo usando `unpack_archive` de `archive_data.py`.
- A compactação e descompactação de snapshots devem usar exclusivamente as funções centralizadas em `src/projects_standards/shared/archive_data.py`, sem duplicar lógica de zipfile/shutil nos scripts individuais.
- Não criar campos derivados, consolidados ou combinados na camada `bronze`.
- Logs operacionais e memória técnica da integração devem ficar fora de `data/project_standards/01_bronze/`.
- Documentos auxiliares por certificadora devem ficar em `src/projects_standards/<certificadora>/bronze/docs/`, sem se misturar com os scripts Python.
- `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md` deve registrar conhecimento estável sobre endpoints, DOM, paginação, idioma, falhas recorrentes e decisões de manutenção.
- Ao iniciar a investigação de uma nova certificadora, registrar em `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md` pelo menos as URLs públicas conhecidas de lista e detalhe, mesmo antes da implementação dos scripts.
- O diretório `logs/` da certificadora deve armazenar histórico operacional por execução ou investigação sem misturar esses artefatos com o dado bruto.
- Sempre que tecnicamente viável, falhas pontuais por projeto devem ser registradas e a execução deve continuar para os próximos projetos.
- Sempre que tecnicamente viável, falhas de sessão externa, navegador ou conexão devem acionar tentativa de retomada da coleta antes de encerrar o script.
- Sempre que a fonte responder com bloqueio temporário por volume, como `429 Too Many Requests`, o script deve aplicar espera, retry limitado e retomada do mesmo item antes de registrar falha definitiva e seguir a coleta.
- O padrão base de ritmo a ser buscado nas coletas é:
  - `0.5s` entre solicitações
  - `2s` a cada `10` solicitações
  - retry limitado com espera quando houver `429 Too Many Requests`
- Quando uma certificadora exigir ritmo mais conservador, o script pode endurecer esses valores, desde que isso fique documentado em `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md`.
- Scripts que abram navegador, subprocesso, sessão HTTP persistente, websocket, arquivo temporário ou outro recurso externo devem encerrar esses recursos explicitamente ao fim da execução.
- O encerramento explícito deve acontecer em bloco `finally`, contexto gerenciado equivalente ou rotina de teardown registrada para interrupções, evitando processos órfãos e memória retida após o script.
- Transformações analíticas devem ficar para a camada `gold`.
- A camada `silver` pode aplicar padronização determinística e rastreável de valores, desde que não altere o fato de negócio observado no `bronze`.
- Regras compartilhadas de padronização da `silver` devem ser centralizadas em `src/projects_standards/shared/silver/`, e não duplicadas em cada certificadora.
- `framework.py` da `silver` deve atuar como orquestrador compartilhado de mapeamento e geração de dataset.
- Funções de normalização, parsing e validação da `silver` devem ficar separadas em módulos próprios, para reduzir duplicação e facilitar manutenção.
- Tabelas de referência editáveis por usuários devem ficar em `data/project_standards/00_reference/`.
- Para referências operacionais editáveis por humanos, preferir `.xlsx` em vez de `.json`.
- Ao fim de cada construção de `silver`, o processo deve sincronizar automaticamente no `data/project_standards/00_reference/reference_dataset.xlsx` as novas formas observadas de países, metodologias, status e SDGs presentes em todos os datasets `silver` disponíveis.
- Essa sincronização automática da referência consolidada deve preservar colunas curadas manualmente e inserir apenas novas formas observadas, além de preencher correspondências exatas seguras quando houver.
- Na aba `standards_catalog` do `reference_dataset.xlsx`, a coluna `standard_acronym` deve funcionar como chave única da certificadora.
- A `sigla` não pode se repetir entre certificadoras diferentes.
- Na aba `countries_observed_mapping` do `reference_dataset.xlsx`, a coluna `country_raw` deve catalogar todas as formas brutas observadas no campo `country` da camada `silver`, sem deduplicacao por certificadora.
- No processo de mapeamento da camada `bronze` para a camada `silver`, o agente deve inspecionar uma amostra híbrida de pelo menos `10%` dos arquivos de detalhe disponíveis no snapshot analisado.
- Quando `10%` resultar em fração, o agente deve arredondar para cima.
- Em snapshots pequenos, a inspeção deve cobrir no mínimo `10` arquivos de detalhe, ou todos os arquivos quando houver menos de `10`.
- A estratégia padrão da amostra híbrida deve combinar:
  - uma parte dos maiores arquivos do snapshot, para aumentar a chance de capturar projetos com mais campos preenchidos
  - uma parte aleatória, para reduzir viés e preservar chance de capturar projetos menores ou menos densos
- Sempre que possível, além dessa estratégia híbrida, o agente deve buscar diversidade na amostra, cobrindo projetos em diferentes status, tipos, programas ou fases quando esses sinais existirem no bruto.
- O mapeamento descoberto nessa etapa inicial deve ser tratado como exploratório até ser revisado e estabilizado.
- Depois de estabilizado, cada certificadora deve passar a ter um mapeamento canônico, usado como referência fixa nas execuções recorrentes do processo `bronze -> silver`.
- Em execuções mensais regulares, o agente não deve redescobrir o mapeamento do zero; deve reaplicar o mapeamento canônico vigente da certificadora.
- Alterações no mapeamento canônico devem ser conservadoras e acontecer apenas quando houver campo novo, mudança estrutural da fonte ou correção necessária de interpretação.
- Toda alteração no mapeamento canônico deve ser registrada explicitamente na documentação da certificadora.

## Estado Atual do Mapeamento Silver

- O repositório já possui builders `silver` operacionais para múltiplas certificadoras.
- Esses builders podem ser usados para gerar datasets recorrentes, mas isso não equivale, por si só, à promoção automática do mapeamento para estado canônico.
- Até que exista registro explícito na documentação da certificadora em `src/projects_standards/<certificadora>/silver/docs/`, o status oficial do mapeamento deve ser tratado como `exploratório com uso operacional`.
- Promoção para `mapeamento canônico` exige registro explícito da decisão na documentação da certificadora.
- Na ausência desse registro explícito, agentes não devem afirmar que a certificadora já tem mapeamento canônico estabilizado.

## Regras de Implementação

- Priorizar API oficial ou endpoint usado pelo frontend da certificadora.
- Evitar scraping de HTML quando existir endpoint mais estável.
- Quando a certificadora não expuser API pública utilizável, é aceitável usar navegador headless para renderizar o frontend e extrair o DOM final.
- Em cenários de frontend SPA sem API pública acessível, preferir automação conservadora do navegador ao scraping de HTML cru sem renderização.
- Não usar paralelismo nas coletas sem decisão explícita do usuário.
- Sempre expor parâmetros como `--date`, e quando fizer sentido `--limit`, `--max-pages`, `--sleep-seconds` e `--timeout`.
- Em integrações sujeitas a rate limit, expor também parâmetros de retry e pausa adicional quando isso ajudar a tornar a coleta resiliente e configurável.
- Os scripts devem mostrar progresso no terminal.
- Scripts de detalhe devem mostrar no terminal relatórios simples de progresso a cada `10` projetos concluídos, com percentual concluído e tempo restante estimado por média dos itens já processados.
- Cada script Python deve conter, no início do arquivo, um comentário curto explicando objetivamente o objetivo do script.
- Imediatamente após o bloco de objetivo, cada script Python deve conter um bloco de comentário `# Processo:` descrevendo os passos executados pelo script em lista numerada, para facilitar manutenção e leitura rápida.
- O bloco de processo deve ser conciso, orientado à sequência de operações do script, e não deve repetir o objetivo.
- Cada função deve ter um comentário imediatamente acima de sua definição, explicando de forma objetiva o que ela faz.
- Os scripts devem conter comentários curtos e objetivos nos blocos não triviais, explicando a intenção da coleta, do parsing e da persistência.
- Evitar comentários redundantes em linhas óbvias; comentar apenas o que ajuda manutenção e leitura rápida.
- Comentários de cabeçalho e de função devem ser curtos, específicos e orientados à intenção do código, evitando descrições vagas.
- Em integrações com recursos externos de longa duração, os scripts devem explicitar no código onde ocorre o teardown de navegador, sessão, subprocesso e artefatos temporários.
- O JSON salvo deve ser UTF-8 e manter a resposta bruta o mais fiel possível.
- Sempre que uma nova dependência Python for introduzida, o agente deve atualizar `requirements.txt` no mesmo trabalho.
- Nenhuma dependência nova deve ser adicionada sem registrar sua necessidade nos documentos dos agentes quando isso alterar o padrão do projeto.
- Arquivos temporários de exploração, downloads auxiliares e artefatos intermediários não devem permanecer no workspace final.
- Perfis temporários de navegador headless ou diretórios `.tmp_*` usados em depuração também devem ser removidos ao final da execução ou investigação.
- Quando esse tipo de arquivo for inevitável durante investigação, o agente deve removê-lo ao final e registrar padrões apropriados no `.gitignore` quando fizer sentido.

## Dependências

- O projeto deve manter um arquivo [requirements.txt](c:/Users/pedro.almeida/registrosCertificadoras/requirements.txt) na raiz.
- Esse arquivo deve listar todas as dependências Python necessárias até o estado atual do repositório.
- Ao criar scripts, conversores, planilhas ou rotinas novas que dependam de bibliotecas externas, o agente deve:
  1. adicionar a dependência ao `requirements.txt`
  2. ajustar os documentos de agentes se a dependência mudar uma convenção do projeto
  3. evitar instalar bibliotecas desnecessárias

## Padroes de Nome

- Nomes de scripts curtos e explicitos:
  - `extract_project_list.py`
  - `extract_project_details.py`
  - `build_silver_dataset.py`
  - `map_silver_fields.py`
  - `sync_status_reference.py`
- Nome da certificadora em minusculas no caminho:
  - `verra`
  - `gold_standard`
- A organizacao esperada do codigo por certificadora e:
  - `src/projects_standards/<certificadora>/bronze/` para extracao e artefatos operacionais da camada bruta
  - `src/projects_standards/<certificadora>/silver/` para scripts e artefatos da constru??o da `silver`
  - `src/projects_standards/shared/silver/` para regras compartilhadas de qualidade, parsing, normalizacao e validacao

## Regras de Operação

- Toda execução deve ser orientada por snapshot de data no formato `YYYYMMDD`.
- Testes curtos devem ser feitos antes de cargas completas.
- Ao repetir uma execução para a mesma data, sobrescrever os arquivos gerados por aquele script é aceitável.
- Se houver risco de bloqueio por volume, preferir execução serial com pausas.
- Em coletas de detalhe, preferir retomada automática e conclusão da lista mesmo quando houver falhas parciais.
- Em processos `bronze -> silver`, o mapeamento inicial não deve ser definido apenas por inspeção de poucos arquivos escolhidos por conveniência; ele deve respeitar a amostra mínima híbrida prevista neste projeto.
- Em processos `bronze -> silver`, a execução recorrente da transformação deve obedecer ao mapeamento canônico estabilizado da certificadora, preservando consistência entre snapshots mensais.
- Na camada `silver`, textos devem passar por trim e redução de espaços excedentes quando isso não alterar a semântica do valor observado.
- Na camada `silver`, campos vazios ou marcadores usuais de ausência devem ser padronizados para `null`.
- Na camada `silver`, campos `date` devem usar `YYYY-MM-DD`.
- Na camada `silver`, campos `datetime`, quando existirem no schema ou nos metadados do dataset, devem usar `YYYY-MM-DDTHH:MM:SS`.
- Na camada `silver`, `project_methodology`, `sdg_targets` e `sector` devem ser sempre listas; quando não houver valor confiável, esses campos devem ser gravados como `[]`.
- Ambiguidades de separadores numéricos não devem ser resolvidas alterando o `bronze`; esse tratamento deve acontecer apenas na `silver`.
- O parsing numérico da `silver` deve ser orientado pelo tipo canônico do campo, distinguindo ao menos coordenadas, contagens/totais e medidas decimais.
- Quando uma certificadora usar convenção numérica específica, a regra deve ser implementada como override explícito no builder ou transformador do campo correspondente.

## Estado Atual Implementado

- Equitable Earth:
  - lista por endpoint público consumido pelo frontend
  - detalhe por endpoint público consumido pelo frontend
- American Carbon Registry:
  - lista por HTML público paginado da plataforma APX
  - detalhe por HTML público da plataforma APX
- TERO:
  - lista por endpoint público oficial do WordPress REST
  - detalhe por endpoint público oficial do WordPress REST
- Social Carbon:
  - lista por endpoint público consumido pelo frontend
  - detalhe por endpoint público consumido pelo frontend
- BioCarbon:
  - lista por endpoint público consumido pelo frontend
  - detalhe por endpoint público consumido pelo frontend
- Verra:
  - lista por endpoint oficial do frontend
  - detalhe por endpoint oficial do frontend
- Gold Standard:
  - lista por endpoint público consumido pelo frontend
  - detalhe por endpoint público consumido pelo frontend
- Cercarbono:
  - lista por endpoint público consumido pelo frontend
  - detalhe por endpoint público consumido pelo frontend
- Climate Action Reserve:
  - lista por HTML público paginado da plataforma APX
  - detalhe por HTML público da plataforma APX
- Isometric:
  - lista por endpoint GraphQL público usado pelo frontend
  - detalhe por endpoint GraphQL público usado pelo frontend
- Plan Vivo:
  - lista por HTML público paginado
  - detalhe por HTML público do projeto
- Puro.earth:
  - lista por payload embutido no HTML público do frontend
  - detalhe por payloads e blocos públicos embutidos no HTML do projeto
- Referências:
  - `reference_dataset.xlsx`

## Estado Atual da Silver

- Certificadoras com `bronze` e `silver` implementados no repositório:
  - `american_carbon_registry`
  - `biocarbon`
  - `cercarbono`
  - `climate_action_reserve`
  - `equitable_earth`
  - `gold_standard`
  - `isometric`
  - `plan_vivo`
  - `puro_earth`
  - `social_carbon`
  - `tero`
  - `verra`
- Status documental do mapeamento por certificadora:
  - `mapeamento canônico formalizado`: nenhuma certificadora com promoção explícita encontrada até `2026-03-31`
  - `mapeamento exploratório com uso operacional`: todas as certificadoras acima que já possuem `silver_field_mapping.md` e `build_silver_dataset.py`
- Enquanto não houver promoção explícita na documentação da certificadora, o builder atual deve ser entendido como regra operacional vigente, mas ainda não como mapeamento canônico formalizado.

## Expectativa para Novas Certificadoras

Ao adicionar uma nova certificadora, o agente deve:

1. Identificar se existe API oficial ou endpoint usado pelo frontend.
2. Implementar primeiro `src/projects_standards/<certificadora>/bronze/extract_project_list.py`.
3. Implementar depois `src/projects_standards/<certificadora>/bronze/extract_project_details.py`.
4. Criar, quando aplic?vel, `src/projects_standards/<certificadora>/silver/map_silver_fields.py`, `src/projects_standards/<certificadora>/silver/build_silver_dataset.py` e `src/projects_standards/<certificadora>/silver/sync_status_reference.py`.
   - Quando aplicável, criar também `sync_country_reference.py` e `sync_methodology_reference.py`.
5. Reutilizar a mesma estrutura de pastas, imports e par?metros.
6. Manter o mesmo padr?o de logs no terminal e registrar conhecimento est?vel em `bronze/docs/` e decis?es da transforma??o em `silver/docs/`.

## Documentos de Apoio

### Documentos Gerais de Agentes

| Documento | Caminho relativo | Conteúdo |
|---|---|---|
| Premissas do Projeto | `docs/agentes/premissas_projeto.md` | Escopo, modelo de coleta, estrutura de código e dados, convenções de scripts, regras de qualidade silver, regras de mapeamento bronze-silver |
| Fluxos Operacionais | `docs/agentes/fluxos_operacionais.md` | Fluxo 1 (lista), Fluxo 2 (detalhe), Fluxo 3 (referências), Fluxo 4 (mapeamento bronze-silver), Fluxo 5 (construção silver), Fluxo 6 (construção gold), regras de retomada e padrão de saída no terminal |
| Guia Bronze | `docs/agentes/guia_bronze.md` | Objetivo da camada bronze, estrutura de dados e código, blocos `source`/`list_data`/`detail_data`, estratégia de integração, ritmo de coleta, resiliência e retomada, teardown, convenções de scripts, logs e documentação da integração |
| Guia Silver | `docs/agentes/guia_silver.md` | Papel da camada silver, princípios de transformação, regra de amostragem para mapeamento, padronização de valores, estrutura canônica recomendada com descrição de todos os campos |
| Guia Gold | `docs/agentes/guia_gold.md` | Objetivo e escopo da gold, unidade de registro, deduplicação mensal, chaves `project_history_id` e `record_id`, padronizações obrigatórias (SDGs, metodologias, país, status), regra de backup |
| Fluxo Gold | `docs/agentes/fluxo_gold.md` | Passos detalhados do Fluxo 6 de construção da gold, regras permanentes de reconstrução integral e backup |
| Mapeamento Gold | `docs/agentes/mapeamento_gold.md` | Desenho operacional do mapeamento silver-gold, tabela campo a campo com `source_type` (direct, renamed, derived) e regras de derivação |
| Modelagem SQLite Gold | `docs/agentes/modelagem_sqlite_gold.md` | Modelagem relacional do banco SQLite da gold, tabelas de referência, entidades centrais (`projects`, `project_history`), tabelas relacionais do histórico, metadados operacionais |

### Referências Editáveis

| Documento | Caminho relativo | Conteúdo |
|---|---|---|
| Reference Dataset | `data/project_standards/00_reference/reference_dataset.xlsx` | Workbook canônico com abas: `standards_catalog`, `countries_standard`, `countries_observed_mapping`, `standards_status`, `common_pipeline_status`, `sdg_goals`, `sdg_targets`, `sdg_observed_mapping`, `sectoral_scopes`, `technical_areas`, `methodologies` |
| Manutenção da Referência | `data/project_standards/00_reference/reference_dataset_maintenance.md` | Regras de manutenção e governança do `reference_dataset.xlsx` |
| README Referência | `data/project_standards/00_reference/README.md` | Descrição geral da pasta de referências |

### Documentação por Certificadora — Bronze (`integration_notes.md`)

Cada arquivo registra endpoints, DOM, paginação, idioma, falhas recorrentes e decisões de manutenção da coleta.

| Certificadora | Caminho relativo |
|---|---|
| American Carbon Registry | `src/projects_standards/american_carbon_registry/bronze/docs/integration_notes.md` |
| BioCarbon | `src/projects_standards/biocarbon/bronze/docs/integration_notes.md` |
| Cercarbono | `src/projects_standards/cercarbono/bronze/docs/integration_notes.md` |
| Equitable Earth | `src/projects_standards/equitable_earth/bronze/docs/integration_notes.md` |
| Gold Standard | `src/projects_standards/gold_standard/bronze/docs/integration_notes.md` |
| Isometric | `src/projects_standards/isometric/bronze/docs/integration_notes.md` |
| Plan Vivo | `src/projects_standards/plan_vivo/bronze/docs/integration_notes.md` |
| Puro.earth | `src/projects_standards/puro_earth/bronze/docs/integration_notes.md` |
| Social Carbon | `src/projects_standards/social_carbon/bronze/docs/integration_notes.md` |
| TERO | `src/projects_standards/tero/bronze/docs/integration_notes.md` |
| Verra | `src/projects_standards/verra/bronze/docs/integration_notes.md` |

Observação: `climate_action_reserve` ainda não possui `integration_notes.md`.

### Documentação por Certificadora — Silver (`silver_field_mapping.md`)

Cada arquivo registra o mapeamento de campos bronze-silver, cobertura, decisões de transformação e status do mapeamento.

| Certificadora | Caminho relativo |
|---|---|
| American Carbon Registry | `src/projects_standards/american_carbon_registry/silver/docs/silver_field_mapping.md` |
| BioCarbon | `src/projects_standards/biocarbon/silver/docs/silver_field_mapping.md` |
| Cercarbono | `src/projects_standards/cercarbono/silver/docs/silver_field_mapping.md` |
| Climate Action Reserve | `src/projects_standards/climate_action_reserve/silver/docs/silver_field_mapping.md` |
| Equitable Earth | `src/projects_standards/equitable_earth/silver/docs/silver_field_mapping.md` |
| Gold Standard | `src/projects_standards/gold_standard/silver/docs/silver_field_mapping.md` |
| Isometric | `src/projects_standards/isometric/silver/docs/silver_field_mapping.md` |
| Plan Vivo | `src/projects_standards/plan_vivo/silver/docs/silver_field_mapping.md` |
| Puro.earth | `src/projects_standards/puro_earth/silver/docs/silver_field_mapping.md` |
| Social Carbon | `src/projects_standards/social_carbon/silver/docs/silver_field_mapping.md` |
| TERO | `src/projects_standards/tero/silver/docs/silver_field_mapping.md` |
| Verra | `src/projects_standards/verra/silver/docs/silver_field_mapping.md` |

