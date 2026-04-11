# Objetivo do script:
# Baixar os dados brutos de créditos emitidos (issuances) da Isometric,
# consultando o endpoint GraphQL público e salvando todos os registros em arquivo único.
# Cada execução sobrescreve o arquivo anterior para garantir completude.
# Processo:
# 1. Ler argumentos CLI (--page-size, --timeout, --retry-attempts, --max-pages).
# 2. Montar caminhos de saida e logs a partir da raiz do projeto.
# 3. Exibir cabecalho com parametros da execucao.
# 4. Paginar via GraphQL (POST edge.isometric.com) com query IssuancesQuery e cursor.
# 5. Para cada pagina, coletar nodes com dados de issuance, projeto, supplier e credit batches.
# 6. Acumular nodes ate hasNextPage ser false ou atingir --max-pages.
# 7. Montar payload com bloco source (carbon_standard, endpoint, record_count, total_count) e data.
# 8. Salvar em arquivo unico issuances.json, sobrescrevendo o anterior.
# 9. Gravar log de falha se houver e exibir resumo final.


import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request


API_URL = "https://edge.isometric.com"
PAGE_URL = "https://registry.isometric.com/?tab=issuances"
DEFAULT_PAGE_SIZE = 100
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 10.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

# Query GraphQL para buscar issuances com dados de projeto, supplier e credit batches.
GRAPHQL_QUERY = """
query IssuancesQuery($first: Int!, $after: String) {
  issuances(first: $first, last: 0, after: $after) {
    nodes {
      id
      createdAt
      creditBatchSizeTotal { credits creditsKg }
      bufferPoolBatchSize { credits creditsKg }
      supplierBatchSize { credits creditsKg }
      project {
        id
        name
        status
        durability
        country { isoAlpha3Code name }
        process { pathway { shortName name } }
      }
      supplier {
        id
        organisation { id name }
      }
      supplierCreditBatches {
        id
        serialNumber
        issuedAt
        sequesteredOn
        status
        countryOfIssue
        ccpApproved
        size { credits creditsKg }
        feedstockName
      }
      bufferPoolCreditBatches {
        id
        serialNumber
        issuedAt
        sequesteredOn
        status
        countryOfIssue
        size { credits creditsKg }
      }
      ghgStatement {
        id
        reportingPeriodStartAt
        reportingPeriodEndAt
        status
      }
    }
    pageInfo { hasNextPage endCursor }
    totalCount
  }
}
""".strip()


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os dados brutos de issuances da Isometric."
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Registros por página GraphQL. Padrão: {DEFAULT_PAGE_SIZE}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout por requisição em segundos. Padrão: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Tentativas adicionais em caso de erro. Padrão: {DEFAULT_RETRY_ATTEMPTS}.",
    )
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=DEFAULT_RETRY_SLEEP_SECONDS,
        help=f"Espera entre tentativas. Padrão: {DEFAULT_RETRY_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Intervalo entre páginas. Padrão: {DEFAULT_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Páginas entre pausas extras. Padrão: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=f"Pausa extra a cada lote de páginas. Padrão: {DEFAULT_BATCH_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limita o número de páginas para testes.",
    )
    return parser.parse_args()


# Retorna o horário atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Monta os caminhos de saída a partir da raiz do projeto.
def build_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[4]
    output_dir = root / "data" / "issued_credits_standards" / "01_bronze" / "isometric" / "issuances"
    logs_dir = Path(__file__).resolve().parent / "logs"
    return output_dir, logs_dir


# Executa uma query GraphQL com retry para 429 e falhas de rede.
def fetch_page(
    page_size: int,
    after: str | None,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    variables: dict[str, Any] = {"first": page_size}
    if after is not None:
        variables["after"] = after

    body = json.dumps({"query": GRAPHQL_QUERY, "variables": variables}).encode("utf-8")
    attempts_total = retry_attempts + 1
    attempt = 1

    while True:
        req = request.Request(
            url=API_URL,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))

            # GraphQL pode retornar erros com status 200
            if "errors" in raw and not raw.get("data"):
                raise RuntimeError(
                    f"Erro GraphQL: {json.dumps(raw['errors'], ensure_ascii=False)[:500]}"
                )
            return raw
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts_total:
                print(
                    f"  429 Too Many Requests; aguardando {retry_sleep_seconds:.1f}s "
                    f"(tentativa {attempt}/{attempts_total})"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            details = ""
            try:
                details = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise RuntimeError(
                f"Erro HTTP {exc.code}. Resposta: {details[:500]}"
            ) from exc
        except error.URLError as exc:
            if attempt < attempts_total:
                print(
                    f"  Falha de rede; aguardando {retry_sleep_seconds:.1f}s "
                    f"(tentativa {attempt}/{attempts_total})"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            raise RuntimeError(f"Falha de rede: {exc}") from exc


# Busca todos os registros paginando pelo cursor GraphQL.
def fetch_all(
    page_size: int,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
    sleep_seconds: float,
    batch_size: int,
    batch_sleep_seconds: float,
    max_pages: int | None,
) -> tuple[list[dict[str, Any]], int]:
    all_nodes: list[dict[str, Any]] = []
    after: str | None = None
    page = 0
    total_count = 0

    while True:
        page += 1
        print(f"  Página {page} ...")

        raw = fetch_page(page_size, after, timeout, retry_attempts, retry_sleep_seconds)
        issuances = raw["data"]["issuances"]
        nodes = issuances["nodes"]
        page_info = issuances["pageInfo"]
        total_count = issuances["totalCount"]

        all_nodes.extend(nodes)
        print(f"    {len(nodes)} registros nesta página ({len(all_nodes)}/{total_count} total)")

        # Checa se atingiu o fim ou limite de páginas
        if not page_info["hasNextPage"]:
            break
        if max_pages is not None and page >= max_pages:
            print(f"  Limite de {max_pages} páginas atingido.")
            break

        after = page_info["endCursor"]

        # Ritmo entre páginas
        if batch_size > 0 and page % batch_size == 0:
            time.sleep(batch_sleep_seconds)
        else:
            time.sleep(sleep_seconds)

    return all_nodes, total_count


# Salva o JSON no disco.
def save_data(output_dir: Path, data: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "issuances.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# Grava o log de falha da execução.
def write_failure_log(logs_dir: Path, error_info: dict[str, Any]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"extract_issued_credits_failures_{datetime.now().strftime('%Y%m%d')}.json"
    payload = {
        "source": {
            "carbon_standard": "isometric",
            "script": "extract_issued_credits.py",
        },
        "updated_at": utc_now_iso(),
        "failure_count": 1,
        "failures": [error_info],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Orquestra o fluxo principal do script.
def main() -> int:
    args = parse_args()
    output_dir, logs_dir = build_paths()

    print("=" * 60)
    print("Extracao de creditos emitidos (issuances) — Isometric")
    print("=" * 60)
    print(f"Endpoint: {API_URL}")
    print(f"Diretorio de saida: {output_dir}")
    print(f"Page size: {args.page_size}")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    print(f"Retry: {args.retry_attempts} tentativas com espera de {args.retry_sleep_seconds:.1f}s")
    print(f"Sleep entre paginas: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada {args.batch_size} paginas: {args.batch_sleep_seconds:.1f}s")
    if args.max_pages is not None:
        print(f"Modo de teste: limite de {args.max_pages} paginas")
    print("=" * 60)

    start_time = time.time()

    try:
        print("\nColetando todos os registros de issuance ...")
        nodes, total_count = fetch_all(
            page_size=args.page_size,
            timeout=args.timeout,
            retry_attempts=args.retry_attempts,
            retry_sleep_seconds=args.retry_sleep_seconds,
            sleep_seconds=args.sleep_seconds,
            batch_size=args.batch_size,
            batch_sleep_seconds=args.batch_sleep_seconds,
            max_pages=args.max_pages,
        )
    except Exception as exc:
        elapsed = time.time() - start_time
        print(f"\nFALHA na coleta: {exc}")
        print(f"Tempo decorrido: {elapsed:.1f}s")
        write_failure_log(logs_dir, {
            "captured_at": utc_now_iso(),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        })
        return 1

    # Monta payload final com metadados
    payload = {
        "source": {
            "carbon_standard": "isometric",
            "endpoint": API_URL,
            "extracted_at": utc_now_iso(),
            "record_count": len(nodes),
            "total_count_reported": total_count,
        },
        "data": nodes,
    }

    path = save_data(output_dir, payload)
    elapsed = time.time() - start_time

    # Resumo final
    print("\n" + "=" * 60)
    print("Resumo da execucao")
    print("=" * 60)
    print(f"Total reportado pela API: {total_count}")
    print(f"Total de registros coletados: {len(nodes)}")
    print(f"Arquivo salvo: {path}")
    print(f"Tempo total: {elapsed:.1f}s")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
