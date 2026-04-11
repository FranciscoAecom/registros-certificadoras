# Objetivo do script:
# Baixar a lista bruta completa de projetos da certificadora e salvar o snapshot em data/project_standards/01_bronze/<certificadora>/<date>/list/projects.json.
# Processo:
# 1. Ler argumentos CLI (--date, parametros de ritmo e retry).
# 2. Validar data e montar diretorio de saida do snapshot.
# 3. Descompactar o snapshot da data solicitada se estiver zipado.
# 4. Exibir cabecalho com parametros da execucao.
# 5. Consultar endpoint da certificadora com paginacao.
# 6. Acumular todos os registros da lista.
# 7. Salvar snapshot completo em JSON no diretorio list/ do snapshot.
# 8. Compactar o diretorio do snapshot em ZIP.
# 9. Exibir resumo da execucao.


import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_directory, unpack_archive


PAGE_URL = "https://registry.isometric.com/?tab=projects"
API_URL = "https://edge.isometric.com"
QUERY_NAME = "RegistryHomePage_ProjectsQuery"
DEFAULT_PAGE_SIZE = 100
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 5.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
GRAPHQL_QUERY = """
query RegistryHomePage_ProjectsQuery(
  $first: Int
  $after: String
  $sort: ProjectSort
  $filter: ProjectFilter
) {
  projects(after: $after first: $first sort: $sort filter: $filter) {
    nodes {
      id
      name
      status
      country { isoAlpha3Code }
      durability
      creditBalance { total { creditsKg } }
      process { pathway { shortName } }
      supplier { id organisation { id name imageUrl } }
    }
    pageInfo { hasNextPage endCursor }
    totalCount
  }
}
""".strip()
PROJECT_STATUSES = ["UNDER_VALIDATION", "VALIDATED", "VALIDATION_UNSUCCESSFUL", "CANCELLED"]


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa a lista bruta de projetos da Isometric.")
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help=f"Tamanho da pagina GraphQL. Padrao: {DEFAULT_PAGE_SIZE}.")
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS, help=f"Intervalo entre requisicoes. Padrao: {DEFAULT_SLEEP_SECONDS}.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Quantidade de paginas entre pausas extras. Padrao: {DEFAULT_BATCH_SIZE}.")
    parser.add_argument("--batch-sleep-seconds", type=float, default=DEFAULT_BATCH_SLEEP_SECONDS, help=f"Pausa extra a cada lote de paginas. Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}.")
    parser.add_argument("--retry-attempts", type=int, default=DEFAULT_RETRY_ATTEMPTS, help=f"Tentativas adicionais quando houver 429. Padrao: {DEFAULT_RETRY_ATTEMPTS}.")
    parser.add_argument("--retry-sleep-seconds", type=float, default=DEFAULT_RETRY_SLEEP_SECONDS, help=f"Espera entre tentativas apos 429. Padrao: {DEFAULT_RETRY_SLEEP_SECONDS}.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.")
    parser.add_argument("--max-pages", type=int, default=None, help="Limita o numero de paginas para testes.")
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


# Monta os caminhos de entrada e saida usados pelo script.
def build_paths(snapshot_date: str) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[4]
    output_path = root / "data" / "project_standards" / "01_bronze" / "isometric" / snapshot_date / "list" / "projects.json"
    errors_path = Path(__file__).resolve().parent / "logs" / f"extract_project_list_failures_{snapshot_date}.json"
    return output_path, errors_path


# Grava o log consolidado de falhas da execucao.
def write_failure_log(errors_path: Path, snapshot_date: str, failures: list[dict[str, Any]]) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {"certificadora": "isometric", "snapshot_date": snapshot_date, "script": "extract_project_list.py"},
        "updated_at": utc_now_iso(),
        "failure_count": len(failures),
        "failures": failures,
    }
    errors_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Referer": PAGE_URL,
        "Origin": "https://registry.isometric.com",
        "X-Frontend-Env": "production",
        "X-Frontend-Platform": "registry",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }


# Monta os dados auxiliares usados pelo restante do fluxo.
def build_variables(page_size: int, cursor: str | None) -> dict[str, Any]:
    return {
        "first": page_size,
        "after": cursor,
        "sort": {"field": "NAME", "direction": "ASCENDING"},
        "filter": {"statusIn": PROJECT_STATUSES},
    }


# Busca uma pagina de resultados na fonte remota.
def fetch_page(page_size: int, cursor: str | None, timeout: float, retry_attempts: int, retry_sleep_seconds: float) -> tuple[list[dict[str, Any]], dict[str, Any], int | None]:
    payload = {"query": GRAPHQL_QUERY, "variables": build_variables(page_size=page_size, cursor=cursor), "operationName": QUERY_NAME}
    attempts_total = retry_attempts + 1
    attempt = 1
    while True:
        req = request.Request(url=API_URL, method="POST", headers=build_headers(), data=json.dumps(payload).encode("utf-8"))
        try:
            with request.urlopen(req, timeout=timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts_total:
                print(
                    f"429 Too Many Requests na lista; aguardando {retry_sleep_seconds:.1f}s "
                    f"antes da tentativa {attempt + 1}/{attempts_total}"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Erro HTTP {exc.code} ao consultar a Isometric. Resposta: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar a Isometric: {exc}") from exc

        errors_payload = response_payload.get("errors")
        if errors_payload:
            raise RuntimeError(f"Resposta GraphQL com erro da Isometric: {json.dumps(errors_payload, ensure_ascii=False)}")
        connection = response_payload.get("data", {}).get("projects")
        if not isinstance(connection, dict):
            raise RuntimeError("Resposta inesperada da Isometric: a conexao 'projects' nao foi encontrada.")
        nodes = connection.get("nodes")
        page_info = connection.get("pageInfo")
        total_count = connection.get("totalCount")
        if not isinstance(nodes, list):
            raise RuntimeError("Resposta inesperada da Isometric: 'projects.nodes' nao e uma lista.")
        if not isinstance(page_info, dict):
            raise RuntimeError("Resposta inesperada da Isometric: 'projects.pageInfo' nao foi encontrado.")
        if total_count is not None and not isinstance(total_count, int):
            raise RuntimeError("Resposta inesperada da Isometric: 'projects.totalCount' invalido.")
        return nodes, page_info, total_count


# Percorre a fonte paginada e acumula todos os projetos da lista.
def fetch_all_projects(page_size: int, sleep_seconds: float, batch_size: int, batch_sleep_seconds: float, timeout: float, retry_attempts: int, retry_sleep_seconds: float, max_pages: int | None) -> dict[str, Any]:
    all_projects: list[dict[str, Any]] = []
    total_count: int | None = None
    cursor: str | None = None
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break
        print(f"Iniciando consulta da pagina {page} (first={page_size}, after={cursor or 'null'})")
        batch, page_info, batch_total_count = fetch_page(page_size=page_size, cursor=cursor, timeout=timeout, retry_attempts=retry_attempts, retry_sleep_seconds=retry_sleep_seconds)
        if total_count is None and batch_total_count is not None:
            total_count = batch_total_count
        all_projects.extend(batch)
        total_display = total_count if total_count is not None else "?"
        print(f"Pagina {page}: coletados {len(batch)} projetos (acumulado {len(all_projects)}/{total_display})")
        has_next_page = bool(page_info.get("hasNextPage"))
        cursor = page_info.get("endCursor")
        if not has_next_page or not cursor:
            break
        if batch_size > 0 and batch_sleep_seconds > 0 and page % batch_size == 0:
            print(f"pausa extra de {batch_sleep_seconds:.1f}s apos {page} paginas")
            time.sleep(batch_sleep_seconds)
        page += 1
        if sleep_seconds > 0:
            print(f"Aguardando {sleep_seconds:.1f}s antes da proxima pagina")
            time.sleep(sleep_seconds)

    payload: dict[str, Any] = {
        "source": {
            "page_url": PAGE_URL,
            "api_url": API_URL,
            "query_name": QUERY_NAME,
            "extraction_method": "graphql_frontend_endpoint",
            "project_identifier_mapping": {"project_public_id": "id", "project_internal_id": "id"},
        },
        "retrieved_at": utc_now_iso(),
        "page_size": page_size,
        "projects": all_projects,
    }
    if total_count is not None:
        payload["total_count"] = total_count
    if max_pages is not None:
        payload["partial"] = True
    return payload


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)
    if args.page_size <= 0:
        raise SystemExit("--page-size deve ser maior que zero.")
    if args.max_pages is not None and args.max_pages <= 0:
        raise SystemExit("--max-pages deve ser maior que zero.")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size deve ser maior que zero.")
    if args.retry_attempts < 0:
        raise SystemExit("--retry-attempts nao pode ser negativo.")

    output_path, errors_path = build_paths(snapshot_date)

    # Descompacta o snapshot da data solicitada se estiver zipado
    snapshot_dir = output_path.parent.parent
    zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
    if not snapshot_dir.exists() and zip_path.exists():
        unpack_archive(zip_path, label="bronze", step=1, total=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=[])
    print("Iniciando extracao da lista de projetos da Isometric")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"URL da pagina: {PAGE_URL}")
    print(f"Endpoint da API: {API_URL}")
    print(f"Query GraphQL: {QUERY_NAME}")
    print(f"Page size: {args.page_size}")
    print(f"Sleep entre paginas: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada lote: {args.batch_sleep_seconds:.1f}s a cada {args.batch_size} paginas")
    print(f"Retry em 429: {args.retry_attempts} tentativas adicionais com espera de {args.retry_sleep_seconds:.1f}s")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    if args.max_pages is not None:
        print(f"Modo de teste ativado: max_pages={args.max_pages}")
    print(f"Arquivo de saida: {output_path}")
    print(f"Arquivo de falhas: {errors_path}")

    try:
        payload = fetch_all_projects(page_size=args.page_size, sleep_seconds=args.sleep_seconds, batch_size=args.batch_size, batch_sleep_seconds=args.batch_sleep_seconds, timeout=args.timeout, retry_attempts=args.retry_attempts, retry_sleep_seconds=args.retry_sleep_seconds, max_pages=args.max_pages)
    except Exception as exc:
        write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=[{"captured_at": utc_now_iso(), "stage": "list_download", "error_type": type(exc).__name__, "error_message": str(exc)}])
        raise

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Arquivo salvo em: {output_path}")
    print(f"Total de projetos salvos: {len(payload['projects'])}")
    if payload.get("total_count") is not None:
        print(f"Total informado pela API: {payload['total_count']}")
    print("Execucao finalizada em modo parcial" if payload.get("partial") else "Execucao finalizada com sucesso")

    # Compacta o diretorio do snapshot em ZIP
    snapshot_dir = output_path.parent.parent
    pack_directory(snapshot_dir, label="bronze", step=1, total=1)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
