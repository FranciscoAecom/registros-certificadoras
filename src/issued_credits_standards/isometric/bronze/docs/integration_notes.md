# Integration Notes — Isometric Issued Credits

## Certificadora
- Nome: `isometric`
- Tipo de dado: créditos emitidos (carbon removal issuances)
- Cada crédito = 1 tonne CO₂ removida da atmosfera

## URLs Públicas
- Interface de busca (aba Issuances): `https://registry.isometric.com/?tab=issuances`

## Endpoint
- **URL**: `POST https://edge.isometric.com`
- **Tipo**: GraphQL
- Mesmo endpoint usado para projetos (`RegistryHomePage_ProjectsQuery`)
- Introspection habilitada (permite descoberta de schema)

## Query GraphQL
- **Nome**: `IssuancesQuery`
- **Paginação**: cursor-based (`first`, `after`, `last`)
- **Retorno**: `IssuanceConnection` com `nodes`, `pageInfo` e `totalCount`
- O parâmetro `last` é obrigatório na query (fixado em `0`)

## Volume Observado (2026-04-01)
- Total: **297 issuances**
- 3 páginas de 100 registros

## Estrutura do Registro (Issuance)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | ID | Identificador único da issuance (ex: `iss_1KN4715T51S0BCKZ`) |
| `createdAt` | DateTime | Data/hora de criação (ISO com timezone) |
| `creditBatchSizeTotal` | CreditQuantity | Total de créditos emitidos (`credits` em tonnes, `creditsKg`) |
| `bufferPoolBatchSize` | CreditQuantity | Porção alocada ao buffer pool |
| `supplierBatchSize` | CreditQuantity | Porção alocada ao supplier |
| `project` | Project | Projeto associado (id, name, status, durability, country, pathway) |
| `supplier` | Supplier | Supplier (id, organisation name) |
| `supplierCreditBatches` | [CreditBatch] | Batches do supplier (serial, issuedAt, sequesteredOn, status, country, size) |
| `bufferPoolCreditBatches` | [CreditBatch] | Batches do buffer pool |
| `ghgStatement` | GhgStatement | Declaração GHG (id, reportingPeriod start/end, status) |

## Campos Relevantes do CreditBatch
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | ID | Identificador do batch |
| `serialNumber` | String | Número serial (ex: `ISO-1-MOMBA-BRA-68X8-2025-0-46001`) |
| `issuedAt` | DateTime | Data de emissão |
| `sequesteredOn` | Date | Data do sequestro |
| `status` | Enum | Status do batch (`ACTIVE`, etc.) |
| `countryOfIssue` | String | País de emissão (ISO alpha-3) |
| `ccpApproved` | Boolean | Aprovação CCP |
| `size` | CreditQuantity | Tamanho do batch (`credits`, `creditsKg`) |
| `feedstockName` | String | Nome do feedstock (pode ser `null`) |

## Estratégia de Coleta
- Todos os registros são coletados em cada execução (sobrescreve arquivo anterior).
- Paginação cursor-based com page size de 100.
- Sem chunking mensal — volume gerenciável (~300 registros).
- Saída: `data/issued_credits_standards/01_bronze/isometric/issuances/issuances.json`
- Ritmo: 0.5s entre páginas, 2s a cada 10 páginas, retry em caso de 429.

## Decisões de Manutenção
- Manter GraphQL enquanto a introspection e o endpoint público estiverem estáveis.
- Se o volume crescer significativamente, a paginação cursor-based já está implementada.
- Campos da query foram escolhidos para capturar os dados visíveis no frontend público.
