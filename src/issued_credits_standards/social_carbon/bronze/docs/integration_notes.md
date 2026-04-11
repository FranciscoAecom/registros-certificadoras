# Integration Notes — Social Carbon Issued Credits

## Certificadora
- Nome: `social_carbon`
- Tipo de dado: créditos emitidos (SCU — Social Carbon Units)
- Plataforma: Bubble (wilder.earth)

## URLs Públicas
- Interface de busca (aba Issuances): `https://wilder.earth/social_carbon`

## Endpoint
- **URL**: `GET https://wilder.earth/api/1.1/obj/issuance`
- Mesma Bubble Data API pública usada para projetos (`/api/1.1/obj/project`)
- Paginação: parâmetros `limit` (máx 100) e `cursor`

## Outros Endpoints Descobertos
- Retirements: `GET https://wilder.earth/api/1.1/obj/retirement` (78 registros)
- Endpoints inexistentes: `credit_issuance`, `credit`, `cancelled` (404)

## Volume Observado (2026-04-01)
- Total: **16 registros** de issuance
- Todos cabem em uma única página (limit=100)

## Campos do Registro
| Campo | Tipo | Descrição |
|---|---|---|
| `Approved` | bool | Se a emissão foi aprovada |
| `Standard` | string | Sempre `"SOCIALCARBON"` |
| `Asset type` | string | Tipo de ativo (ex: `"SCU - Removal"`) |
| `Quantity requested` | int | Quantidade de SCUs emitidos |
| `Vintage` | string | Período do vintage (ex: `"2023 - 2023"` ou `"2022"`) |
| `Batch_ID` | string | Identificador do lote |
| `Serial Number Batch` | string | Faixa de números seriais |
| `Project` | string | Bubble `_id` do projeto associado |
| `Verifier` | string | Nome do verificador |
| `Monitoring period start` | datetime | Início do período de monitoramento (ISO) |
| `Monitoring period end` | datetime | Fim do período de monitoramento (ISO) |
| `Monitoring Period` | string | Bubble `_id` do período (pode ser `null`) |
| `CORSIA eligible` | bool | Elegibilidade CORSIA |
| `Issuance complete` | bool | Se a emissão está completa |
| `Payment received` | bool | Se o pagamento foi recebido |
| `Verification / Validation Files` | array | URLs de arquivos no CDN Bubble |
| `Created Date` | datetime | Data de criação do registro (ISO) |
| `Created By` | string | Bubble `_id` do criador |
| `_id` | string | Bubble internal ID do registro |

## Estratégia de Coleta
- Todos os registros são coletados em uma única execução (volume pequeno).
- Sem chunking mensal — desnecessário para 16 registros.
- Cada execução sobrescreve o arquivo anterior.
- Paginação implementada para futuro crescimento (cursor + limit=100).
- Saída: `data/issued_credits_standards/01_bronze/social_carbon/issuances/issuances.json`
- Ritmo conservador: 0.5s entre páginas, retry em caso de 429.

## Decisões de Manutenção
- Manter a Bubble Data API enquanto disponível; não usar scraping do DOM.
- Se o volume crescer significativamente, a paginação já está implementada.
- Campo `Project` contém o `_id` Bubble do projeto, linkável via `/api/1.1/obj/project/<_id>`.
