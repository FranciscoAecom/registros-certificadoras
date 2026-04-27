# Fluxos Operacionais

## Fluxo 1: Lista de Projetos

Objetivo:

- baixar a lista completa de projetos da certificadora
- salvar o bruto em `list/projects.json`

Passos esperados:

1. Receber `--date YYYYMMDD`.
2. Se existir snapshot compactado para a mesma data (`YYYYMMDD.zip`, `YYYYMMDD_core.zip` ou `YYYYMMDD_core_001.zip`), descompactar usando as funções centralizadas de `archive_data.py`.
3. Criar o diretório de saída da data somente durante a execução.
4. Consultar a API paginada da certificadora.
5. Acumular todos os projetos.
6. Salvar o snapshot bruto.
7. Compactar o diretório do snapshot usando o formato de bundle centralizado de `archive_data.py` e remover a pasta original.
8. Exibir resumo final no terminal.
9. Manter comentário inicial do script e comentários objetivos antes de cada função usada no fluxo.

Fallback aceito:

- se não houver API pública utilizável, o script pode renderizar a página em navegador headless
- nesse caso, a extração deve ocorrer sobre o DOM final já renderizado
- esse fallback deve continuar respeitando paginação, ritmo conservador e logs de progresso
- quando a API pública exigir header estável exposto pelo próprio frontend, esse caminho ainda é preferível ao navegador, desde que a origem do header fique documentada em `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md`
- quando a aplicação expuser Data API pública estável no próprio domínio, como em integrações Bubble, esse caminho deve ser preferido ao scraping do DOM
- quando o site expuser custom post type público em WordPress REST, esse caminho deve ser preferido ao scraping de cards e páginas renderizadas
- quando a fonte pública for uma tabela HTML estável hospedada pela própria plataforma da certificadora, com paginação reproduzível por formulário ou query string, esse fluxo ainda é aceitável e deve ser documentado em `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md`
- quando a integração ainda estiver em investigação, registrar primeiro em `src/projects_standards/<certificadora>/bronze/docs/integration_notes.md` as páginas públicas de lista e detalhe e a natureza do shell de frontend antes de escolher a estratégia final de coleta

## Fluxo 2: Detalhe por Projeto

Objetivo:

- ler a lista já salva
- percorrer projeto a projeto
- salvar um JSON bruto por projeto

Passos esperados:

1. Receber `--date YYYYMMDD`.
2. Se o snapshot estiver compactado como `YYYYMMDD.zip`, `YYYYMMDD_core.zip` ou `YYYYMMDD_core_001.zip`, descompactar usando as funções centralizadas de `archive_data.py`.
3. Ler `data/project_standards/01_bronze/<certificadora>/YYYYMMDD/list/projects.json`.
3. Extrair o identificador do projeto.
4. Consultar o endpoint de detalhe.
5. Salvar `data/project_standards/01_bronze/<certificadora>/YYYYMMDD/projects/<id>.json`.
6. Persistir o arquivo bruto com a estrutura:
   - `source`
   - `list_data`
   - `detail_data`
7. Em `source`, usar `carbon_standard` como nome padrão da certificadora.
8. Em `source`, salvar `snapshot_date` em formato ISO `YYYY-MM-DD`.
9. Em `source`, salvar `reference_month` com o primeiro dia do mês de `snapshot_date`, também em formato ISO `YYYY-MM-DD`.
10. Em `source`, padronizar os identificadores como `project_public_id` e `project_internal_id`.
11. Em `source`, usar `project_url` como nome padrão da URL pública do projeto.
12. Não gerar campos consolidados ou derivados na camada `bronze`.
13. Quando a lista já trouxer o identificador interno exigido pelo detalhe, reutilizar esse valor salvo no snapshot em vez de redescobri-lo durante a coleta.
14. Mostrar progresso projeto a projeto no terminal.
15. Exibir relatórios simples de progresso no terminal a cada `10` projetos concluídos, com percentual concluído e tempo restante estimado pela média dos itens já processados.
16. Persistir falhas operacionais em `src/projects_standards/<certificadora>/bronze/logs/` com contexto suficiente para diagnóstico e rerun.
17. Quando um projeto falhar, registrar a falha e continuar a execução para os próximos projetos, sempre que isso for tecnicamente viável.
18. Quando a fonte responder com bloqueio temporário, como `429 Too Many Requests`, aguardar, repetir o mesmo projeto por um número limitado de tentativas e só então registrar a falha definitiva.
19. Quando a sessão de navegador, conexão remota ou contexto externo cair no meio da coleta, tentar reinicializar e retomar a lista antes de encerrar o script.
20. Antes de encerrar o processo, executar teardown explícito dos recursos externos abertos pela coleta.
21. Compactar o diretório do snapshot usando o formato de bundle centralizado de `archive_data.py` e remover a pasta original.
22. Manter comentário inicial do script e comentários objetivos antes de cada função usada no fluxo.

Observacao:

- O Fluxo 2 termina na persistencia do `bronze`.
- Qualquer mapeamento, normalizacao, padronizacao tipada e validacao da `silver` pertence ao Fluxo 4 e ao Fluxo 5, nunca ao script de detalhe do `bronze`.

## Regras de Segurança Operacional

- Não usar scraping agressivo.
- Preferir chamadas equivalentes às do frontend oficial.
- Não usar paralelismo sem autorização explícita.
- Inserir pausas entre requisições quando houver risco de bloqueio.
- Quando houver indício de rate limit, combinar pausas entre requisições com retry limitado e espera incremental ou fixa antes de desistir do item.
- O ritmo padrão a ser buscado é `0.5s` entre solicitações e `2s` a cada `10` solicitações, salvo quando a integração documentar necessidade de valores mais conservadores.
- Encerrar explicitamente navegador, subprocesso, sessão persistente, websocket e diretórios temporários em `finally` ou contexto equivalente.
- Regras de qualidade e padronização da `silver` devem ser centralizadas em `src/projects_standards/shared/silver/`, com `framework.py` responsável pela orquestração compartilhada.

## Regras de Teste

Antes de rodar uma carga completa:

- rodar lista com `--max-pages`
- rodar detalhe com `--limit`
- validar o conteúdo salvo
- só depois executar a carga integral

## Fluxo 3: Referências Editáveis

Objetivo:

- manter tabelas de apoio editáveis por usuários
- registrar catálogos e futuros `de_para`

Passos esperados:

1. Preferir `data/project_standards/00_reference/.../*.xlsx`.
2. Tratar `data/project_standards/00_reference/reference_dataset.xlsx` como workbook canônico do projeto.
3. Manter nomes de colunas estáveis.
4. Evitar acoplamento dessas planilhas com a camada `bronze`.
5. Se uma rotina depender de biblioteca externa para gerar ou atualizar essas planilhas, registrar a dependência em `requirements.txt`.
6. Na aba `standards_catalog`, validar que a coluna `standard_acronym` permanece única antes de inserir ou alterar registros.

## Fluxo 4: Mapeamento Bronze para Silver

Objetivo:

- mapear os campos brutos da certificadora para o schema canônico da camada `silver`
- reduzir o risco de `unmapped` incorreto causado por amostra pobre
- estabilizar um mapeamento canônico para uso recorrente

Passos esperados:

1. Identificar o snapshot `bronze` a ser analisado.
2. Levantar o total de arquivos de detalhe disponíveis no snapshot.
3. Definir uma amostra híbrida de pelo menos `10%` desses arquivos para inspeção do mapeamento.
4. Quando `10%` resultar em fração, arredondar o tamanho da amostra para cima.
5. Quando houver menos de `10` arquivos, inspecionar todos; quando houver `10` ou mais, inspecionar pelo menos `10`.
6. Na estratégia padrão, compor essa amostra híbrida com parte dos maiores arquivos do snapshot e parte aleatória.
7. Sempre que possível, dar preferência a uma amostra híbrida com diversidade de status, tipo de projeto, programa ou outra segmentação relevante exposta pela certificadora.
8. Usar essa amostra para avaliar cobertura e plausibilidade dos campos candidatos antes de marcar um campo como `unmapped`.
9. Registrar no documento de mapeamento da certificadora a regra de amostragem adotada quando ela fugir da estratégia híbrida padrão.
10. Refinar iterativamente o mapeamento até chegar a uma versão estável e confiável.
11. Promover essa versão estável a mapeamento canônico da certificadora.
12. Nas execuções recorrentes mensais, usar o mapeamento canônico como referência fixa para a transformação `bronze -> silver`.
13. Só revisar o mapeamento canônico quando houver motivo concreto, como campo novo, mudança estrutural da fonte ou correção necessária.

Observação:

- A estratégia híbrida de `10%` é o padrão mínimo do projeto.
- A parte formada pelos maiores arquivos existe para aumentar a chance de capturar campos preenchidos e estruturas mais completas.
- A parte aleatória existe para reduzir viés do tamanho do arquivo.
- Quando o agente identificar grande heterogeneidade entre fases, status ou tipos de projeto, uma abordagem melhor é combinar a estratégia híbrida com estratos por categoria, desde que isso fique documentado.
- O fluxo operacional ideal passa a ter duas fases:
  - fase exploratória de descoberta e estabilização do mapeamento
  - fase recorrente de transformação usando o mapeamento canônico já estabilizado

## Fluxo 5: Construcao da Silver

Objetivo:

- aplicar o mapeamento can?nico `bronze -> silver` da certificadora
- padronizar valores de forma determin?stica e rastre?vel
- gerar o dataset final em `data/project_standards/02_silver/<certificadora>/YYYYMMDD/allprojects.json`

Passos esperados:

1. Executar o builder em `src/projects_standards/<certificadora>/silver/build_silver_dataset.py`.
2. O framework da `silver` descompacta automaticamente o snapshot `bronze` (legado `YYYYMMDD.zip` ou bundle `YYYYMMDD_core.zip` / `YYYYMMDD_core_001.zip`) antes de ler os dados, usando as funções centralizadas de `archive_data.py`.
3. Executar junto a sincronizacao de status em `src/projects_standards/<certificadora>/silver/sync_status_reference.py`, de forma automatica ao fim do builder ou manual quando necessario.
4. Executar junto a sincronizacao de paises em `src/projects_standards/<certificadora>/silver/sync_country_reference.py`, de forma automatica ao fim do builder ou manual quando necessario.
5. Ao fim de cada construcao da `silver`, sincronizar tambem no `data/project_standards/00_reference/reference_dataset.xlsx` todas as formas observadas de:
   - paises
   - metodologias
   - status
   - SDGs
6. Essa sincronizacao consolidada deve considerar todos os datasets `silver` disponiveis, para que a base de referencia permaneça completa e reflita novas variacoes observadas no historico.
7. O processo automatico nao deve sobrescrever colunas curadas manualmente na referencia; ele deve apenas inserir novas formas observadas e preencher correspondencias exatas seguras quando houver.
8. Ler o snapshot `bronze` da certificadora e aplicar o mapeamento canonico vigente.
9. Usar o pacote compartilhado `src/projects_standards/shared/silver/` para regras transversais de parsing, normalizacao e validacao.
10. Padronizar qualquer valor vazio para `null`, independentemente do tipo do campo.
11. Padronizar campos textuais com trim e reducao de espacos excedentes quando isso nao alterar a semantica observada.
12. Padronizar campos `date` como `YYYY-MM-DD`.
13. Padronizar campos `datetime`, quando existirem, como `YYYY-MM-DDTHH:MM:SS`.
14. Preservar rastreabilidade ate o `bronze` e nao inventar valores ausentes.
15. Registrar falhas operacionais do builder em `src/projects_standards/<certificadora>/silver/logs/` quando houver.
16. Ao final, o framework recompacta o snapshot `bronze` usando o formato de bundle centralizado de `archive_data.py` e remove a pasta descompactada.
17. Remover artefatos temporarios de teste ou depuracao ao final da execucao.

Observacao:

- Se ainda nao houver promocao explicita do mapeamento da certificadora para estado canônico em `src/projects_standards/<certificadora>/silver/docs/`, o builder pode operar com o melhor mapeamento exploratorio vigente, mas esse status deve continuar documentado como `exploratorio com uso operacional`.

## Regras de Retomada

- O script deve ser capaz de rerodar sobre a mesma data.
- Sobrescrita de arquivos gerados pelo próprio script é aceitável.
- Falhas pontuais devem ser registradas no terminal de forma clara.
- Falhas pontuais também devem poder ser inspecionadas depois da execução por meio de um arquivo operacional em `src/projects_standards/<certificadora>/bronze/logs/`.
- Em fluxos de detalhe, o comportamento preferencial é concluir a lista com sucessos e falhas registradas, e não abortar no primeiro erro pontual.

## Padrão de Saída no Terminal

### Lista

Mensagens esperadas:

- início da execução
- página consultada
- quantidade coletada na página
- acumulado
- pausa intencional
- caminho do arquivo salvo
- total final

### Detalhe

Mensagens esperadas:

- total de projetos detectados
- início do download do projeto `<id>`
- fim do download do projeto `<id>`
- percentual concluído e tempo estimado restante ao longo do processamento
- falha no projeto `<id>`, se houver
- resumo com sucessos e falhas

## Parâmetros Recomendados

### Scripts de Lista

- `--date`
- `--page-size`
- `--sleep-seconds`
- `--timeout`
- `--max-pages`

### Scripts de Detalhe

- `--date`
- `--limit`
- `--sleep-seconds`
- `--batch-size`
- `--batch-sleep-seconds`
- `--request-sleep-seconds`
- `--progress-report-every`
- `--retry-attempts`
- `--retry-sleep-seconds`
- `--timeout`

## Critério para Novas Certificadoras

Uma nova certificadora só deve entrar no padrão do projeto quando:

1. houver definição clara do endpoint de lista
2. houver definição clara do endpoint de detalhe
3. os dois scripts seguirem a estrutura de pastas do projeto
4. os logs de terminal estiverem implementados
5. os blocos não triviais do código estiverem comentados de forma objetiva
6. o teardown dos recursos externos estiver explícito e validado

## Regra Permanente sobre Dependências

Sempre que um agente:

- adicionar biblioteca Python nova
- criar rotina que exija biblioteca externa
- mudar a forma oficial de persistência de referências

ele deve atualizar:

1. `requirements.txt`
2. os documentos de agentes relevantes

## Regra Permanente sobre Arquivos Temporários

Sempre que um agente:

- baixar arquivos auxiliares para inspeção
- gerar exportações locais intermediárias
- salvar HTML, CSV, JS, cookies ou respostas temporárias fora das pastas oficiais do projeto

ele deve:

1. remover esses arquivos ao final do trabalho
2. evitar deixá-los na raiz do repositório
3. atualizar o `.gitignore` quando houver risco de recorrência


## Sincronizacao de metodologias

Ao final de cada `build_silver_dataset.py`, o processo tambem deve sincronizar no `reference_dataset.xlsx` novas combinacoes observadas de `standard_acronym` e `project_methodology` presentes no dataset `silver`.

Na normalizacao final do dataset `silver`, os campos `project_methodology`, `sdg_targets` e `sector` devem sair sempre como listas, inclusive quando houver apenas um valor ou nenhum.

Nos campos numericos da `silver`, o processo deve aplicar parsing orientado por tipo canonico de campo, diferenciando pelo menos coordenadas, contagens/totais e medidas decimais.

Quando houver convencao numerica especifica de uma certificadora ou campo, o builder deve aplicar override explicito sem alterar o `bronze`.

## Fluxo 6: Construcao da Gold

Objetivo:

- consolidar todos os projetos `silver` em uma base unica
- manter apenas um registro do projeto por `reference_month`
- aplicar os mapeamentos padronizados de referencia para consumo analitico

Passos esperados:

1. Descobrir todos os datasets `silver` disponiveis no repositorio.
2. Ler todos os projetos de todas as standards e snapshots elegiveis.
3. Construir `project_history_id` e `record_id`.
4. Deduplicar o projeto dentro do mesmo `reference_month`, mantendo o registro mais atualizado do mes.
5. Padronizar SDGs via referencia.
6. Padronizar pais via referencia.
7. Relacionar metodologias a `technical_area_id`.
8. Derivar `sectoral_scope_id` por relacionamento com `technical_areas`.
9. Resolver um unico `standard_reported_project_status` conforme a regra de negocio da standard e do `project_market`.
10. Mapear o status efetivo para o status padrao de pipeline.
11. Gerar a base `gold` completa em JSON.
12. Gerar `schema.json` e `quality_report.json`.
13. Se existirem artefatos anteriores, criar uma pasta timestampada em `backup/` antes da sobrescrita.
14. Mover para essa pasta, mantendo os nomes originais:
   - `allprojects.json`
   - `quality_report.json`

Observacao:

- A `gold` deve ser sempre reconstruida em sua completude.
- O processo `silver -> gold` nao deve depender de append incremental como estrategia oficial.
