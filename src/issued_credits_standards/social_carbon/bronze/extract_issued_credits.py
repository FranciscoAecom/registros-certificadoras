# Objetivo do script:
# Baixar os dados brutos de créditos emitidos (SCUs) da Social Carbon,
# consultando a Data API pública do Bubble e salvando todos os registros em arquivo único.
# Cada execução sobrescreve o arquivo anterior para garantir completude.
# Processo:
# 1. Ler argumentos CLI (--timeout, --retry-attempts, --sleep-seconds).
# 2. Montar caminhos de saida e logs a partir da raiz do projeto.
# 3. Exibir cabecalho com parametros da execucao.
# 4. Paginar pela Bubble Data API (GET /api/1.1/obj/issuance) com cursor e limit=100.
# 5. Acumular todos os registros de todas as paginas.
# 6. Montar payload com bloco source (carbon_standard, endpoint, record_count) e data.
# 7. Salvar em arquivo unico issuances.json, sobrescrevendo o anterior.
# 8. Gravar log de falha se houver e exibir resumo final.


import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request


BASE_URL = "https://wilder.earth/api/1.1/obj/issuance"
PAGE_URL = "https://wilder.earth/social_carbon"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 10.0
DEFAULT_SLEEP_SECONDS = 0.5
# Bubble Data API retorna até 100 por página
BUBBLE_PAGE_LIMIT = 100
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os dados brutos de SCUs emitidos da Social Carbon."
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
        help=f"Intervalo entre páginas da API. Padrão: {DEFAULT_SLEEP_SECONDS}.",
    )
    return parser.parse_args()


# Retorna o horário atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Monta os caminhos de saída a partir da raiz do projeto.
def build_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[4]
    output_dir = root / "data" / "issued_credits_standards" / "01_bronze" / "social_carbon" / "issuances"
    logs_dir = Path(__file__).resolve().parent / "logs"
    return output_dir, logs_dir


# Busca uma página de registros da Bubble Data API com retry.
def fetch_page(
    cursor: int,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    url = f"{BASE_URL}?limit={BUBBLE_PAGE_LIMIT}&cursor={cursor}"
    attempts_total = retry_attempts + 1
    attempt = 1

    while True:
        req = request.Request(
            url=url,
            method="GET",
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
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
                f"Erro HTTP {exc.code} ao consultar cursor={cursor}. Resposta: {details}"
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
            raise RuntimeError(
                f"Falha de rede ao consultar cursor={cursor}: {exc}"
            ) from exc


# Busca todos os registros paginando pela Bubble Data API.
def fetch_all(
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
    sleep_seconds: float,
) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    cursor = 0
    page = 1

    while True:
        print(f"  Página {page} (cursor={cursor}) ...")
        raw = fetch_page(cursor, timeout, retry_attempts, retry_sleep_seconds)
        response = raw.get("response", {})
        results = response.get("results", [])
        remaining = response.get("remaining", 0)

        all_records.extend(results)
        print(f"    {len(results)} registros nesta página, {remaining} restantes")

        if remaining <= 0:
            break

        cursor += len(results)
        page += 1
        time.sleep(sleep_seconds)

    return all_records


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
            "carbon_standard": "social_carbon",
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
    print("Extracao de creditos emitidos (SCUs) — Social Carbon")
    print("=" * 60)
    print(f"Endpoint: {BASE_URL}")
    print(f"Diretorio de saida: {output_dir}")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    print(f"Retry: {args.retry_attempts} tentativas com espera de {args.retry_sleep_seconds:.1f}s")
    print(f"Sleep entre paginas: {args.sleep_seconds:.1f}s")
    print("=" * 60)

    start_time = time.time()

    try:
        print("\nColetando todos os registros de issuance ...")
        records = fetch_all(
            timeout=args.timeout,
            retry_attempts=args.retry_attempts,
            retry_sleep_seconds=args.retry_sleep_seconds,
            sleep_seconds=args.sleep_seconds,
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
            "carbon_standard": "social_carbon",
            "endpoint": BASE_URL,
            "extracted_at": utc_now_iso(),
            "record_count": len(records),
        },
        "data": records,
    }

    path = save_data(output_dir, payload)
    elapsed = time.time() - start_time

    # Resumo final
    print("\n" + "=" * 60)
    print("Resumo da execucao")
    print("=" * 60)
    print(f"Total de registros coletados: {len(records)}")
    print(f"Arquivo salvo: {path}")
    print(f"Tempo total: {elapsed:.1f}s")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
