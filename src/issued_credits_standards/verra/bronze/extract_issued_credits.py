# Objetivo do script:
# Baixar os dados brutos de créditos de carbono emitidos (VCUs) da Verra,
# consultando mês a mês pelo endpoint público do frontend e salvando um arquivo JSON por mês.
# Todos os meses no intervalo solicitado são sempre recoletados para garantir completude.
# Processo:
# 1. Ler argumentos CLI (--start-month, --end-month, parametros de ritmo e retry).
# 2. Gerar lista de meses (YYYY-MM) no intervalo solicitado.
# 3. Exibir cabecalho com parametros da execucao.
# 4. Para cada mes, montar payload com filtro de data (issuanceStartInclusive/issuanceEndInclusive).
# 5. Consultar POST /uiapi/asset/asset/search com retry para 429 e falhas de rede.
# 6. Montar payload com bloco source (carbon_standard, issuance_month, endpoint, record_count) e data.
# 7. Salvar JSON do mes em data/issued_credits_standards/01_bronze/verra/issuances/YYYY-MM.json.
# 8. Sobrescrever arquivo existente para garantir completude.
# 9. Exibir progresso a cada 10 meses (percentual e tempo restante).
# 10. Gravar log de falhas se houver e exibir resumo final.


import argparse
import calendar
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request


BASE_URL = "https://registry.verra.org/uiapi/asset/asset/search"
PAGE_URL = "https://registry.verra.org/app/search/VCS/VCUs"
FIRST_ISSUANCE_YEAR = 2009
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 10.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os dados brutos de VCUs emitidos da Verra, mês a mês."
    )
    parser.add_argument(
        "--start-month",
        default=None,
        help="Primeiro mês a coletar, formato YYYY-MM. Padrão: 2009-01.",
    )
    parser.add_argument(
        "--end-month",
        default=None,
        help="Último mês a coletar, formato YYYY-MM. Padrão: mês atual.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Intervalo entre requisições. Padrão: {DEFAULT_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Quantidade de meses entre pausas extras. Padrão: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=f"Pausa extra a cada lote de meses. Padrão: {DEFAULT_BATCH_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Tentativas adicionais quando houver 429. Padrão: {DEFAULT_RETRY_ATTEMPTS}.",
    )
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=DEFAULT_RETRY_SLEEP_SECONDS,
        help=f"Espera entre tentativas após 429. Padrão: {DEFAULT_RETRY_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout por requisição em segundos. Padrão: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita o número de meses a coletar (para testes).",
    )
    return parser.parse_args()


# Retorna o horário atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Valida e retorna (year, month) a partir de string YYYY-MM.
def parse_month(value: str) -> tuple[int, int]:
    try:
        dt = datetime.strptime(value, "%Y-%m")
        return dt.year, dt.month
    except ValueError as exc:
        raise SystemExit(f"Formato de mês inválido: {value}. Use YYYY-MM.") from exc


# Gera lista de tuplas (year, month) entre start e end (inclusive).
def generate_month_range(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    months = []
    y, m = start
    ey, em = end
    while (y, m) <= (ey, em):
        months.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return months


# Monta os caminhos de saída a partir da raiz do projeto.
def build_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[4]
    output_dir = root / "data" / "issued_credits_standards" / "01_bronze" / "verra" / "issuances"
    logs_dir = Path(__file__).resolve().parent / "logs"
    return output_dir, logs_dir


# Retorna o caminho do arquivo de saída para um mês específico.
def month_file_path(output_dir: Path, year: int, month: int) -> Path:
    return output_dir / f"{year:04d}-{month:02d}.json"


# Consulta o endpoint da Verra para um intervalo de datas e retorna a resposta bruta.
def fetch_month(
    year: int,
    month: int,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    payload = {
        "program": "VCS",
        "issuanceTypeCodes": ["ISSUE"],
        "issuanceStartInclusive": start_date,
        "issuanceEndInclusive": end_date,
    }

    body = json.dumps(payload).encode("utf-8")
    attempts_total = retry_attempts + 1
    attempt = 1

    while True:
        req = request.Request(
            url=BASE_URL,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "Origin": "https://registry.verra.org",
                "Referer": PAGE_URL,
            },
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
                records = raw.get("value", [])
                return {
                    "source": {
                        "carbon_standard": "verra",
                        "program": "VCS",
                        "issuance_month": f"{year:04d}-{month:02d}",
                        "query_start": start_date,
                        "query_end": end_date,
                        "endpoint": BASE_URL,
                        "extracted_at": utc_now_iso(),
                        "record_count": len(records),
                    },
                    "data": records,
                }
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
                f"Erro HTTP {exc.code} ao consultar mês {year:04d}-{month:02d}. Resposta: {details}"
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
                f"Falha de rede ao consultar mês {year:04d}-{month:02d}: {exc}"
            ) from exc


# Salva o JSON de um mês no disco.
def save_month(output_dir: Path, year: int, month: int, data: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = month_file_path(output_dir, year, month)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# Grava o log consolidado de falhas da execução.
def write_failure_log(logs_dir: Path, failures: list[dict[str, Any]]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"extract_issued_credits_failures_{datetime.now().strftime('%Y%m%d')}.json"
    payload = {
        "source": {
            "carbon_standard": "verra",
            "script": "extract_issued_credits.py",
        },
        "updated_at": utc_now_iso(),
        "failure_count": len(failures),
        "failures": failures,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Orquestra o fluxo principal do script.
def main() -> int:
    args = parse_args()

    now = datetime.now(UTC)
    current_year, current_month = now.year, now.month

    # Define intervalo de meses
    if args.start_month:
        start = parse_month(args.start_month)
    else:
        start = (FIRST_ISSUANCE_YEAR, 1)

    if args.end_month:
        end = parse_month(args.end_month)
    else:
        end = (current_year, current_month)

    if start > end:
        raise SystemExit(f"--start-month ({start[0]:04d}-{start[1]:02d}) é posterior a --end-month ({end[0]:04d}-{end[1]:02d}).")

    months = generate_month_range(start, end)
    if args.limit is not None:
        months = months[:args.limit]

    output_dir, logs_dir = build_paths()
    failures: list[dict[str, Any]] = []

    # Todos os meses do intervalo são coletados (sobrescreve existentes)
    months_to_fetch = months
    total = len(months_to_fetch)

    print("=" * 60)
    print("Extracao de creditos emitidos (VCUs) — Verra")
    print("=" * 60)
    print(f"Intervalo: {start[0]:04d}-{start[1]:02d} a {end[0]:04d}-{end[1]:02d}")
    print(f"Meses a coletar: {total}")
    print(f"Diretorio de saida: {output_dir}")
    print(f"Endpoint: {BASE_URL}")
    print(f"Sleep entre meses: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada {args.batch_size} meses: {args.batch_sleep_seconds:.1f}s")
    print(f"Retry em 429: {args.retry_attempts} tentativas com espera de {args.retry_sleep_seconds:.1f}s")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    if args.limit is not None:
        print(f"Modo de teste: limite de {args.limit} meses")
    print("=" * 60)

    if total == 0:
        print("\nNenhum mes novo para coletar. Execucao encerrada.")
        return 0

    completed = 0
    total_records = 0
    start_time = time.time()

    for idx, (y, m) in enumerate(months_to_fetch, 1):
        month_label = f"{y:04d}-{m:02d}"
        print(f"\n[{idx}/{total}] Coletando {month_label} ...")

        try:
            data = fetch_month(
                year=y,
                month=m,
                timeout=args.timeout,
                retry_attempts=args.retry_attempts,
                retry_sleep_seconds=args.retry_sleep_seconds,
            )
            count = data["source"]["record_count"]
            path = save_month(output_dir, y, m, data)
            completed += 1
            total_records += count
            print(f"  {count} registros salvos em {path.name}")
        except Exception as exc:
            print(f"  FALHA: {exc}")
            failures.append({
                "captured_at": utc_now_iso(),
                "month": month_label,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            })

        # Relatório de progresso a cada 10 meses concluídos
        if idx % 10 == 0 or idx == total:
            elapsed = time.time() - start_time
            avg = elapsed / idx
            remaining = avg * (total - idx)
            pct = (idx / total) * 100
            print(f"\n  --- Progresso: {idx}/{total} ({pct:.1f}%) | "
                  f"Registros acumulados: {total_records} | "
                  f"Tempo restante estimado: {remaining:.0f}s ---")

        # Ritmo entre requisições
        if idx < total:
            if args.batch_size > 0 and idx % args.batch_size == 0:
                time.sleep(args.batch_sleep_seconds)
            else:
                time.sleep(args.sleep_seconds)

    # Grava log de falhas
    if failures:
        write_failure_log(logs_dir, failures)

    # Resumo final
    elapsed_total = time.time() - start_time
    print("\n" + "=" * 60)
    print("Resumo da execucao")
    print("=" * 60)
    print(f"Meses coletados com sucesso: {completed}/{total}")
    print(f"Total de registros coletados: {total_records}")
    print(f"Falhas: {len(failures)}")
    print(f"Tempo total: {elapsed_total:.1f}s")
    if failures:
        print(f"Log de falhas: {logs_dir}")
        for f in failures:
            print(f"  - {f['month']}: {f['error_message'][:100]}")
    print("=" * 60)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
