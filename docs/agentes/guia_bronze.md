# Guia da Camada Bronze — Project Standards

## Objetivo

A camada `bronze` armazena o dado bruto coletado de cada certificadora de crédito de carbono, sem qualquer transformação analítica.

Ela existe para:

- preservar a resposta original da fonte como registro imutável
- permitir reprocessamento futuro sem depender da disponibilidade da fonte
- garantir rastreabilidade de cada projeto até o snapshot de origem
- isolar a coleta das etapas de padronização e consolidação

## Papel da Camada Bronze

A camada `bronze` deve:

- guardar o dado bruto o mais fiel possível à resposta da fonte
- separar claramente lista de projetos e detalhe por projeto
- versionar os dados por data de execução no formato `YYYYMMDD`
- manter um arquivo por projeto no detalhe, sem consolidar em arquivo único

A camada `bronze` não deve:

- normalizar, padronizar ou transformar valores
- criar campos derivados, consolidados ou combinados
- misturar dados brutos com logs operacionais ou documentação técnica
- consolidar o detalhe de todos os projetos em um único arquivo

## Estrutura de Dados

Em repouso, cada snapshot é armazenado como ZIP:

```text
data/project_standards/01_bronze/<certificadora>/YYYYMMDD.zip
```

Durante a execução, o conteúdo descompactado segue a estrutura:

```text
data/project_standards/01_bronze/<certificadora>/YYYYMMDD/
├── list/
│   └── projects.json
└── projects/
    ├── <project_id>.json
    └── ...
```

- O diretório datado `YYYYMMDD` só deve ser criado durante a execução do script.
- O snapshot temporal vem antes de `list/` e `projects/`.
- O snapshot é obrigatório porque a execução ocorre tipicamente no máximo uma vez por mês.
- Ao término da execução, o script recompacta o snapshot em `.zip` e remove a pasta original.

## Estrutura de Código

```text
src/projects_standards/<certificadora>/bronze/
├── extract_project_list.py
├── extract_project_details.py
├── docs/
│   ├── integration_notes.md
│   └── <documento_auxiliar>.md
└── logs/
    └── <arquivo_operacional>.json
```

- Scripts de extração ficam diretamente em `bronze/`.
- Documentação técnica da integração fica em `bronze/docs/`.
- Logs operacionais ficam em `bronze/logs/`.
- Esses artefatos não devem existir dentro de `data/project_standards/01_bronze/`.

## Arquivo de Lista (`projects.json`)

O script `extract_project_list.py` deve:

- baixar a lista bruta completa da certificadora
- salvar em um único arquivo `projects.json`
- manter a resposta bruta sem transformação

## Arquivo de Detalhe por Projeto (`<project_id>.json`)

Cada arquivo de detalhe deve conter exatamente três blocos de nível raiz:

```json
{
  "source": { ... },
  "list_data": { ... },
  "detail_data": { ... }
}
```

### Bloco `source`

Registra metadados mínimos do snapshot e do identificador do projeto.

Campos obrigatórios:

| Campo | Tipo | Regra |
|---|---|---|
| `carbon_standard` | string | Nome padrão da certificadora |
| `snapshot_date` | string | Data do snapshot em formato ISO `YYYY-MM-DD` |
| `reference_month` | string | Primeiro dia do mês de `snapshot_date`, formato ISO `YYYY-MM-DD` |
| `project_public_id` | string | Identificador público do projeto |
| `project_internal_id` | string | Identificador interno usado pela certificadora ou endpoint |
| `project_url` | string | URL pública do projeto, quando existir |

Regras:

- `carbon_standard` é o nome padrão do identificador da certificadora dentro de `source`
- Quando a lista já trouxer `project_public_id` e `project_internal_id`, ambos devem ser preservados no snapshot bruto e reutilizados pelo script de detalhe, evitando redescoberta em tempo de execução

### Bloco `list_data`

Armazena o registro bruto vindo da lista da certificadora para aquele projeto, sem qualquer transformação.

### Bloco `detail_data`

Armazena o retorno bruto do detalhe da certificadora para aquele projeto, sem qualquer transformação.

## Estratégia de Integração

Ordem de preferência para coleta de dados:

1. API oficial ou endpoint usado pelo frontend da certificadora
2. Data API pública estável no domínio da certificadora (ex: integrações Bubble)
3. Custom post type público em WordPress REST
4. Tabela HTML estável com paginação reproduzível por formulário ou query string
5. Navegador headless para renderizar frontend SPA e extrair o DOM final

Regra geral:

- Evitar scraping de HTML quando existir endpoint mais estável
- Quando a API pública exigir header estável exposto pelo próprio frontend, preferir esse caminho ao navegador, documentando a origem do header em `integration_notes.md`
- Em cenários de frontend SPA sem API pública acessível, preferir automação conservadora do navegador ao scraping de HTML cru sem renderização

## Ritmo de Coleta

O padrão base de ritmo a ser buscado nas coletas é:

- `0.5s` entre solicitações
- `2s` a cada `10` solicitações
- retry limitado com espera quando houver `429 Too Many Requests`

Regras complementares:

- Não usar paralelismo nas coletas sem decisão explícita do usuário
- Quando uma certificadora exigir ritmo mais conservador, o script pode endurecer esses valores, desde que isso fique documentado em `integration_notes.md`
- Em integrações sujeitas a rate limit, expor parâmetros de retry e pausa adicional para tornar a coleta resiliente e configurável

## Resiliência e Retomada

- Falhas pontuais por projeto devem ser registradas e a execução deve continuar para os próximos projetos, sempre que tecnicamente viável
- Falhas de sessão externa, navegador ou conexão devem acionar tentativa de retomada da coleta antes de encerrar o script
- Quando a fonte responder com `429 Too Many Requests`, o script deve aplicar espera, retry limitado e retomada do mesmo item antes de registrar falha definitiva
- Em coletas de detalhe, preferir retomada automática e conclusão da lista mesmo quando houver falhas parciais

## Teardown de Recursos Externos

Scripts que abram navegador, subprocesso, sessão HTTP persistente, websocket, arquivo temporário ou outro recurso externo devem:

- encerrar esses recursos explicitamente ao fim da execução
- fazer o encerramento em bloco `finally`, contexto gerenciado equivalente ou rotina de teardown registrada para interrupções
- não deixar processos órfãos ou memória retida após o script
- explicitar no código onde ocorre o teardown

## Convenções de Scripts

### Parâmetros Obrigatórios

| Script | Parâmetros obrigatórios | Parâmetros opcionais |
|---|---|---|
| `extract_project_list.py` | `--date` | `--max-pages`, `--sleep-seconds`, `--timeout` |
| `extract_project_details.py` | `--date` | `--limit`, `--sleep-seconds`, `--timeout` |

- Em integrações sujeitas a rate limit, expor também parâmetros de retry e pausa adicional

### Saída no Terminal

**Lista:**

- início da execução
- página consultada e quantidade coletada
- acumulado
- pausas intencionais
- caminho do arquivo salvo
- total final

**Detalhe:**

- início da execução
- progresso projeto a projeto
- relatório simples a cada `10` projetos: percentual concluído e tempo restante estimado por média dos itens já processados
- falhas pontuais com contexto
- caminho de cada arquivo salvo
- resumo final (sucesso, falhas, total)

### Comentários no Código

- Cada script deve conter no início um comentário curto com o objetivo do script
- Cada função deve ter um comentário imediatamente acima da definição explicando sua responsabilidade
- Blocos não triviais devem ter comentários curtos explicando a intenção
- Evitar comentários redundantes em linhas óbvias
- Comentários devem priorizar clareza operacional e intenção, evitando textos genéricos

### Formato de Saída

- JSON salvo em UTF-8
- Resposta bruta preservada o mais fiel possível
- Ao repetir uma execução para a mesma data, sobrescrever os arquivos gerados é aceitável

## Compactação de Snapshots

Os snapshots de bronze são armazenados compactados para reduzir o tamanho do repositório.

Regras:

- Ao final de cada execução de `extract_project_list.py` ou `extract_project_details.py`, o script deve compactar o diretório do snapshot em `.zip` usando `pack_directory` de `archive_data.py` e remover a pasta original.
- Antes de ler dados de um snapshot que possa estar compactado, o script deve verificar se existe o `.zip` correspondente e, se necessário, descompactá-lo usando `unpack_archive` de `archive_data.py`.
- A compactação e descompactação devem usar exclusivamente as funções centralizadas em `src/projects_standards/shared/archive_data.py`.
- Nenhum script individual deve duplicar lógica de `zipfile` ou `shutil` para esse fim.
- O framework da camada `silver` também gerencia automaticamente a descompactação do bronze antes do processamento e a recompactação após a geração do dataset.

## Logs Operacionais

- Devem ficar em `src/projects_standards/<certificadora>/bronze/logs/`
- Devem registrar contexto de execução, erros e evidências úteis para rerun ou diagnóstico
- Em coletas por projeto, devem registrar falhas sem impedir a continuidade da lista
- Não devem se misturar com os dados brutos em `data/project_standards/01_bronze/`

## Documentação da Integração

O arquivo `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md` deve registrar:

- endpoints utilizados (URLs, métodos, payloads)
- estrutura do DOM quando aplicável
- regras de paginação
- idioma da fonte
- falhas recorrentes conhecidas
- decisões de manutenção e ritmo customizado

Regras:

- Ao iniciar a investigação de uma nova certificadora, registrar pelo menos as URLs públicas conhecidas de lista e detalhe, mesmo antes da implementação dos scripts
- Quando a integração ainda estiver em investigação, registrar a natureza do frontend antes de escolher a estratégia final de coleta
- Quando o ritmo for endurecido para uma certificadora, documentar os valores adotados

## Regras de Teste

Antes de rodar uma carga completa:

1. Rodar lista com `--max-pages` para validar paginação e formato
2. Rodar detalhe com `--limit` para validar estrutura e persistência
3. Validar o conteúdo salvo
4. Só depois executar a carga integral

## Regras de Operação

- Toda execução deve ser orientada por snapshot de data no formato `YYYYMMDD`
- O diretório de data não deve existir previamente por convenção manual; ele nasce na execução
- Ao repetir uma execução para a mesma data, sobrescrever os arquivos gerados é aceitável
- Se houver risco de bloqueio por volume, preferir execução serial com pausas
- Arquivos temporários de exploração, downloads auxiliares e artefatos intermediários não devem permanecer no workspace final
- Perfis temporários de navegador headless ou diretórios `.tmp_*` devem ser removidos ao final da execução
