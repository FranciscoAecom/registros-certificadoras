# Integration Notes

## American Carbon Registry

- Certificadora: `american_carbon_registry`
- Sigla de referencia sugerida: `ACR`
- Status atual:
  - integracao validada
  - lista e detalhe implementados por HTML publico da plataforma APX

### URLs Publicas Confirmadas

- Lista publica:
  - `https://acr2.apx.com/myModule/rpt/myrpt.asp?r=111`
- Detalhe publico por projeto:
  - `https://acr2.apx.com/mymodule/reg/prjView.asp?id1=<project_internal_id>`
- Aba publica de documentos:
  - `https://acr2.apx.com/mymodule/reg/TabDocuments.asp?r=111&ad=Prpt&act=update&type=PRO&aProj=pub&tablename=doc&id1=<project_internal_id>`

### Comportamento Observado do Frontend

- A lista e uma tabela HTML publica hospedada em APX.
- A navegacao entre paginas ocorre via `POST` para a mesma rota `myrpt.asp?r=111`.
- A pagina inicial informa `20` paginas e expõe campos ocultos como:
  - `X999tablenumber=2`
  - `X999action=search`
  - `X999paging=On`
  - `X999whichpage=<n>`
- Cada pagina publica da lista traz `50` projetos.
- O detalhe principal e uma pagina HTML com pares label/valor em tabela.
- Os documentos publicos ficam em uma aba separada, tambem servida como HTML.

### Decisao Atual

- A ACR foi implementada sem navegador headless.
- `extract_project_list.py` usa a tabela HTML publica e reproduz a paginacao via `POST`.
- `extract_project_details.py` salva:
  - o HTML da pagina principal do projeto
  - o HTML da aba de documentos
  - os pares label/valor parseados
  - os links publicos de arquivos encontrados na aba de documentos
- O vinculo entre lista e detalhe usa:
  - `Project ID` como `project_public_id`
  - `id1` da URL `prjView.asp` como `project_internal_id`

### Observacao de TLS

- Em alguns ambientes Python, `acr2.apx.com` pode falhar com `CERTIFICATE_VERIFY_FAILED` quando a cadeia CA local estiver incompleta.
- Os scripts aceitam `--insecure-ssl` para contornar esse problema operacional mantendo a coleta serial e conservadora.
- O acesso com `urllib` foi mantido como base da integracao.
- Se o ambiente do usuario mudar, revalidar primeiro o handshake TLS antes de trocar a biblioteca HTTP.

### Regras de Implementacao para esta Integracao

- Preservar o padrao `source`, `list_data` e `detail_data` na camada `bronze`.
- Manter o ritmo base do projeto:
  - `0.5s` entre solicitacoes
  - `2s` a cada `10` solicitacoes
  - retry limitado com espera quando houver `429 Too Many Requests`
- Nao substituir a tabela HTML por scraping mais frágil enquanto a estrutura atual da APX continuar estavel.
