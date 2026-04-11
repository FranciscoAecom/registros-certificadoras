# Integration Notes — Verra Issued Credits

## Certificadora
- Nome: `verra`
- Programa: VCS (Verified Carbon Standard)
- Tipo de dado: créditos de carbono emitidos (VCU issuances)

## Natureza dos Dados
- Dados de emissão de créditos de carbono são **imutáveis** por compliance e transparência.
- Apesar da imutabilidade, o script sempre recoleta todos os meses do intervalo solicitado para garantir completude.
- Cada registro representa um bloco de VCUs emitidos, não um projeto.

## URLs Públicas
- Interface de busca (aba VCUs): `https://registry.verra.org/app/search/VCS/VCUs`

## Endpoint
- **URL**: `POST https://registry.verra.org/uiapi/asset/asset/search`
- **Content-Type**: `application/json`
- Descoberto via análise do JS do frontend (`main.*.js`), que diferencia `programType`:
  - `PROJECT` → `/uiapi/resource/resource/search`
  - `ISSUANCE` → `/uiapi/asset/asset/search`
  - `BUFFER` → `/uiapi/resource/resourceBuffer/search`

## Parâmetros do Payload
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `program` | string | sim | Código do programa. Fixo `"VCS"` |
| `issuanceTypeCodes` | array | sim | Código do tipo de emissão. Fixo `["ISSUE"]` para VCUs emitidos |
| `issuanceStartInclusive` | string | recomendado | Data inicial do filtro, formato `YYYY-MM-DD` |
| `issuanceEndInclusive` | string | recomendado | Data final do filtro, formato `YYYY-MM-DD` |
| `$skip` | int | não | **Ignorado pela API** — não faz paginação real |
| `$top` | int | não | **Ignorado pela API** — não limita resultados |

## Comportamento de Paginação
- A API **ignora** `$skip` e `$top`.
- Retorna **todos** os registros que satisfazem o filtro de data.
- Sem filtro de data, a requisição pode dar timeout (>300K registros).
- Com filtro mensal, o volume é gerenciável (até ~10K registros por mês em anos de pico).

## Volume Observado (2026-04-01)
| Ano | Registros |
|---|---|
| 2009 | 7.102 |
| 2010 | 4.267 |
| 2011 | 6.766 |
| 2012 | 11.227 |
| 2013 | 9.229 |
| 2014 | 10.480 |
| 2015 | 38.348 |
| 2016 | 8.597 |
| 2017 | 8.676 |
| 2018 | 9.566 |
| 2019 | 18.487 |
| 2020 | 26.923 |
| 2021 | 95.331 |
| 2022 | 28.681 |
| 2023 | 19.751 |
| 2024 | 10.596 |
| 2025 | 4.671 |
| 2026 | 638 |
| **Total** | **~319.336** |

## Campos do Registro
| Campo | Tipo | Descrição |
|---|---|---|
| `issuanceDate` | string | Data da emissão (`YYYY-MM-DD`) |
| `instrumentType` | string | Tipo de instrumento (ex: `"VCU"`) |
| `vintageStart` | string | Início do período de vintage |
| `vintageEnd` | string | Fim do período de vintage |
| `reportingPeriodStart` | string | Início do período de reporte |
| `reportingPeriodEnd` | string | Fim do período de reporte |
| `resourceIdentifier` | string | ID do projeto associado |
| `resourceName` | string | Nome do projeto |
| `region` | string | Região do projeto |
| `country` | string | País do projeto |
| `protocolCategory` | string | Categoria do protocolo/metodologia |
| `protocol` | string | Metodologia utilizada |
| `totalVintageQuantity` | int | Quantidade total do vintage |
| `quantity` | int | Quantidade deste bloco |
| `serialNumbers` | string | Números seriais dos VCUs |
| `externalSerialNumber` | string | Número serial externo (quando existir) |
| `additionalCertifications` | string | Certificações adicionais |
| `retiredCancelled` | bool | Se o bloco foi aposentado/cancelado |
| `retireOrCancelDate` | string | Data de aposentadoria/cancelamento |
| `retirementBeneficiary` | string | Beneficiário da aposentadoria |
| `retirementReason` | string | Razão da aposentadoria |
| `retirementDetails` | string | Detalhes da aposentadoria |
| `inputTypes` | string | Tipos de input |
| `holdingIdentifier` | string | Identificador da holding |
| `programObjectives` | string | Objetivos do programa (SDGs) |

## Estratégia de Coleta
- Consulta **mês a mês** por `issuanceDate`, usando `issuanceStartInclusive` e `issuanceEndInclusive`.
- Sem paralelismo.
- Todos os meses do intervalo solicitado são sempre coletados (sobrescreve arquivos existentes).
- Dados salvos em `data/issued_credits_standards/01_bronze/verra/issuances/YYYY-MM.json`.
- Ritmo conservador: 0.5s entre requisições, retry em caso de 429.

## Decisões de Manutenção
- Não trocar o endpoint oficial por scraping do HTML enquanto a API continuar estável.
- Se a API passar a respeitar paginação no futuro, ajustar o script para paginar.
- Monitorar se o comportamento de ignorar `$skip`/`$top` se mantém.
