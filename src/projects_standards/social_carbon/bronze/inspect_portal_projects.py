# Objetivo do script:
# Auditar os registros expostos pelo portal da Social Carbon e salvar um retrato exploratorio em logs/, sem misturar esses dados com o bronze oficial do registry.
# Processo:
# 1. Ler argumentos CLI (--date, parametros de ritmo e retry).
# 2. Consultar a Data API publica do portal com paginacao.
# 3. Acumular todos os registros expostos pelo objeto project.
# 4. Classificar os registros em categorias exploratorias.
# 5. Consolidar metricas simples de status, padrao e completude.
# 6. Salvar o retrato exploratorio em JSON no diretorio logs/.
# 7. Exibir um resumo curto no terminal.


import argparse
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request


PORTAL_PAGE_URL = "https://portal.socialcarbon.org"
PORTAL_API_URL = "https://portal.socialcarbon.org/api/1.1/obj/project"
DEFAULT_PAGE_SIZE = 25
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 5.0


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita os registros expostos pelo portal da Social Carbon."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Tamanho da pagina Bubble. Padrao: {DEFAULT_PAGE_SIZE}.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Intervalo entre requisicoes. Padrao: {DEFAULT_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Quantidade de paginas entre pausas extras. Padrao: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=f"Pausa extra a cada lote de paginas. Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Tentativas adicionais quando houver 429. Padrao: {DEFAULT_RETRY_ATTEMPTS}.",
    )
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=DEFAULT_RETRY_SLEEP_SECONDS,
        help=f"Espera entre tentativas apos 429. Padrao: {DEFAULT_RETRY_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limita a quantidade de paginas para testes.",
    )
    return parser.parse_args()


# Valida a data informada e garante o formato YYYYMMDD.
def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise SystemExit(f"--date invalida: {value}. Use YYYYMMDD.") from exc
    return value


# Retorna o horario atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Monta o caminho do arquivo de saida da auditoria.
def build_output_path(snapshot_date: str) -> Path:
    return (
        Path(__file__).resolve().parent
        / "logs"
        / f"portal_project_audit_{snapshot_date}.json"
    )


# Busca um payload JSON na fonte remota com as regras de resiliencia da integracao.
def fetch_json(
    url: str,
    *,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
    params: dict[str, Any] | None = None,
) -> Any:
    if params:
        query = parse.urlencode(
            [(key, value) for key, value in params.items() if value is not None],
            doseq=True,
        )
        url = f"{url}?{query}"

    attempts_total = retry_attempts + 1
    attempt = 1

    while True:
        req = request.Request(
            url=url,
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts_total:
                print(
                    f"429 Too Many Requests no portal; aguardando {retry_sleep_seconds:.1f}s "
                    f"antes da tentativa {attempt + 1}/{attempts_total}"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Erro HTTP {exc.code} ao consultar o portal da Social Carbon. Resposta: {details}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar o portal da Social Carbon: {exc}") from exc


# Busca uma pagina de resultados no portal.
def fetch_page(
    *,
    cursor: int,
    page_size: int,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    payload = fetch_json(
        PORTAL_API_URL,
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_sleep_seconds=retry_sleep_seconds,
        params={
            "limit": page_size,
            "cursor": cursor,
        },
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Resposta inesperada do portal da Social Carbon: era esperado um objeto.")
    response_payload = payload.get("response")
    if not isinstance(response_payload, dict):
        raise RuntimeError(
            "Resposta inesperada do portal da Social Carbon: chave 'response' ausente ou invalida."
        )
    results = response_payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError(
            "Resposta inesperada do portal da Social Carbon: chave 'results' ausente ou invalida."
        )
    return response_payload


# Percorre o portal paginado e acumula todos os registros do objeto project.
def fetch_all_projects(
    *,
    page_size: int,
    sleep_seconds: float,
    batch_size: int,
    batch_sleep_seconds: float,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
    max_pages: int | None,
) -> list[dict[str, Any]]:
    all_projects: list[dict[str, Any]] = []
    page_number = 0
    cursor = 0
    remaining: int | None = None

    while True:
        if max_pages is not None and page_number >= max_pages:
            break

        page_number += 1
        print(f"iniciando consulta da pagina {page_number} do portal (cursor={cursor}, limit={page_size})")
        page_payload = fetch_page(
            cursor=cursor,
            page_size=page_size,
            timeout=timeout,
            retry_attempts=retry_attempts,
            retry_sleep_seconds=retry_sleep_seconds,
        )
        batch = page_payload["results"]
        remaining_raw = page_payload.get("remaining")
        remaining = remaining_raw if isinstance(remaining_raw, int) else None
        all_projects.extend(batch)

        total_display = len(all_projects) + remaining if remaining is not None else "?"
        print(
            f"pagina {page_number}: coletados {len(batch)} registros "
            f"(acumulado {len(all_projects)}/{total_display})"
        )

        if not batch or remaining == 0:
            break

        cursor += len(batch)
        if batch_size > 0 and batch_sleep_seconds > 0 and page_number % batch_size == 0:
            print(
                f"pausa de lote apos {page_number} paginas: aguardando {batch_sleep_seconds:.1f}s"
            )
            time.sleep(batch_sleep_seconds)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return all_projects


# Classifica um registro do portal para separar publicados, pre-registro e registros incompletos.
def classify_portal_record(project: dict[str, Any]) -> str:
    project_id = str(project.get("Project ID") or "").strip()
    standard = str(project.get("Standard") or "").strip()
    status = str(project.get("Status") or project.get("Project Status") or "").strip()

    if project_id:
        return "published_registry_project"
    if status.lower() == "pre-registration":
        return "pre_registration_or_draft"
    if standard == "SOCIALCARBON":
        return "socialcarbon_incomplete_record"
    return "non_standard_or_unclassified"


# Gera um retrato consolidado dos registros expostos pelo portal.
def build_audit_payload(snapshot_date: str, projects: list[dict[str, Any]]) -> dict[str, Any]:
    classified_records: list[dict[str, Any]] = []
    classification_counter: Counter[str] = Counter()
    standard_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()

    for project in projects:
        classification = classify_portal_record(project)
        classification_counter[classification] += 1
        standard_counter[str(project.get("Standard") or "")] += 1
        status_counter[str(project.get("Status") or project.get("Project Status") or "")] += 1
        classified_records.append(
            {
                "_id": project.get("_id"),
                "project_id": project.get("Project ID"),
                "registry_id": project.get("Registry_ID"),
                "standard": project.get("Standard"),
                "name": project.get("Name") or project.get("Project Name"),
                "status": project.get("Status") or project.get("Project Status"),
                "country": project.get("Country"),
                "classification": classification,
                "raw": project,
            }
        )

    return {
        "source": {
            "certificadora": "social_carbon",
            "snapshot_date": snapshot_date,
            "page_url": PORTAL_PAGE_URL,
            "api_url": PORTAL_API_URL,
            "script": "inspect_portal_projects.py",
            "purpose": "exploratory_portal_audit",
            "note": "Este arquivo nao integra o bronze oficial do registry; ele registra o universo exploratorio do portal.",
        },
        "retrieved_at": utc_now_iso(),
        "summary": {
            "total_records": len(projects),
            "records_with_project_id": sum(1 for p in projects if str(p.get("Project ID") or "").strip()),
            "records_with_registry_id": sum(1 for p in projects if str(p.get("Registry_ID") or "").strip()),
            "classification_counts": dict(sorted(classification_counter.items())),
            "standard_counts": dict(sorted(standard_counter.items())),
            "status_counts": dict(sorted(status_counter.items())),
        },
        "records": classified_records,
    }


# Orquestra a auditoria exploratoria do portal e imprime um resumo final.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)

    if args.page_size <= 0:
        raise SystemExit("--page-size deve ser maior que zero.")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size deve ser maior que zero.")
    if args.retry_attempts < 0:
        raise SystemExit("--retry-attempts nao pode ser negativo.")

    output_path = build_output_path(snapshot_date)

    print("Iniciando auditoria exploratoria do portal da Social Carbon")
    print(f"Data de referencia: {snapshot_date}")
    print(f"URL do portal: {PORTAL_PAGE_URL}")
    print(f"Endpoint da API: {PORTAL_API_URL}")
    print(f"Page size: {args.page_size}")
    print(f"Sleep entre solicitacoes: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada lote: {args.batch_sleep_seconds:.1f}s a cada {args.batch_size} paginas")
    print(
        f"Retry em 429: {args.retry_attempts} tentativas adicionais "
        f"com espera de {args.retry_sleep_seconds:.1f}s"
    )
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    if args.max_pages is not None:
        print(f"Modo de teste ativado: max_pages={args.max_pages}")
    print(f"Arquivo de saida: {output_path}")

    projects = fetch_all_projects(
        page_size=args.page_size,
        sleep_seconds=args.sleep_seconds,
        batch_size=args.batch_size,
        batch_sleep_seconds=args.batch_sleep_seconds,
        timeout=args.timeout,
        retry_attempts=args.retry_attempts,
        retry_sleep_seconds=args.retry_sleep_seconds,
        max_pages=args.max_pages,
    )

    payload = build_audit_payload(snapshot_date, projects)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload["summary"]
    print(f"Total de registros expostos pelo portal: {summary['total_records']}")
    print(f"Com Project ID preenchido: {summary['records_with_project_id']}")
    print(f"Com Registry_ID preenchido: {summary['records_with_registry_id']}")
    print(f"Classificacao exploratoria: {summary['classification_counts']}")
    print(f"Arquivo salvo em: {output_path}")
    print("Auditoria finalizada com sucesso")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
