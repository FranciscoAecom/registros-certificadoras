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
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import parse, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_directory, unpack_archive

try:
    from .runtime_cleanup import managed_execution
except ImportError:
    from runtime_cleanup import managed_execution


PAGE_URL = "https://globalcarbontrace.io/registry/biocarbon/gei/projects"
API_BASE_URL = "https://api.globalcarbontrace.io"
API_KEY = "SboCiHaHxtC2xRM92hpBjy1S2Y5La7IwjeB76z"
LIST_API_URL = f"{API_BASE_URL}/api/public/initiatives"
DEFAULT_SLEEP_SECONDS = 0.0
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_LANGUAGE = "en"
DEFAULT_PAGE_SIZE = 200


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa a lista bruta de projetos da BioCarbon Registry."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=(
            "Parametro mantido por padrao do projeto. "
            f"Padrao: {DEFAULT_SLEEP_SECONDS}."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout total por operacao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limita o numero de paginas da API para testes.",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Idioma preferencial das respostas da API. Padrao: {DEFAULT_LANGUAGE}.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Tamanho da pagina da API. Padrao: {DEFAULT_PAGE_SIZE}.",
    )
    return parser.parse_args()


# Valida a data informada e garante o formato YYYYMMDD.
def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise SystemExit(f"--date invalida: {value}. Use YYYYMMDD.") from exc
    return value


# Monta o caminho do arquivo de saida para o snapshot informado.
def build_output_path(snapshot_date: str) -> Path:
    root = Path(__file__).resolve().parents[4]
    return root / "data" / "project_standards" / "01_bronze" / "biocarbon" / snapshot_date / "list" / "projects.json"


# Monta o caminho do log de falhas para o snapshot informado.
def build_failure_log_path(snapshot_date: str) -> Path:
    return (
        Path(__file__).resolve().parent
        / "logs"
        / f"extract_project_list_failures_{snapshot_date}.json"
    )


# Retorna o horario atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Le o log de falhas existente quando ele ja estiver salvo.
def read_failure_log(log_path: Path) -> dict[str, Any]:
    if not log_path.exists():
        return {}

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Arquivo de log de falhas invalido: {log_path}")
    return payload


# Grava o log consolidado de falhas da execucao.
def write_failure_log(
    log_path: Path,
    snapshot_date: str,
    failure_entries: list[dict[str, Any]],
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {
            "certificadora": "biocarbon",
            "snapshot_date": snapshot_date,
            "script": "extract_project_list.py",
        },
        "updated_at": utc_now_iso(),
        "failure_count": len(failure_entries),
        "failures": failure_entries,
    }
    log_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Acrescenta uma falha ao log operacional sem perder o historico atual.
def append_failure_entry(
    log_path: Path,
    snapshot_date: str,
    entry: dict[str, Any],
) -> None:
    payload = read_failure_log(log_path)
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    failures.append(entry)
    write_failure_log(
        log_path=log_path,
        snapshot_date=snapshot_date,
        failure_entries=failures,
    )


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }


# Busca um payload JSON na fonte remota com as regras de resiliencia da integracao.
def fetch_json(
    url: str,
    *,
    timeout: float,
    params: dict[str, Any] | None = None,
) -> Any:
    if params:
        query = parse.urlencode(
            [(key, value) for key, value in params.items() if value is not None],
            doseq=True,
        )
        url = f"{url}?{query}"

    req = request.Request(url=url, method="GET", headers=build_headers())
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# Percorre a fonte paginada e acumula todos os projetos da lista.
def fetch_all_projects(
    *,
    timeout: float,
    max_pages: int | None,
    language: str,
    page_size: int,
) -> dict[str, Any]:
    all_projects: list[dict[str, Any]] = []
    current_page = 1
    total_pages: int | None = None
    total_records: int | None = None

    while True:
        payload = fetch_json(
            LIST_API_URL,
            timeout=timeout,
            params={
                "language": language,
                "page": current_page,
                "per_page": page_size,
            },
        )
        page_projects = payload.get("data")
        if not isinstance(page_projects, list):
            raise RuntimeError(
                "Resposta inesperada da API da BioCarbon: chave 'data' ausente ou invalida."
            )

        total_pages = payload.get("last_page")
        total_records = payload.get("total")
        all_projects.extend(page_projects)

        if total_pages is not None:
            print(
                f"Pagina {current_page}: coletados {len(page_projects)} projetos "
                f"(acumulado {len(all_projects)} projetos, pagina {current_page}/{total_pages})"
            )
        else:
            print(
                f"Pagina {current_page}: coletados {len(page_projects)} projetos "
                f"(acumulado {len(all_projects)} projetos)"
            )

        if max_pages is not None and current_page >= max_pages:
            break

        next_page_url = payload.get("next_page_url")
        if not next_page_url:
            break

        current_page += 1

    return {
        "projects": all_projects,
        "total_pages": total_pages,
        "pages_collected": current_page,
        "total_records": total_records,
        "page_size": page_size,
    }


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    with managed_execution(script_name="biocarbon/extract_project_list.py"):
        args = parse_args()
        snapshot_date = validate_date(args.date)

        if args.max_pages is not None and args.max_pages <= 0:
            raise SystemExit("--max-pages deve ser maior que zero.")
        if args.page_size <= 0:
            raise SystemExit("--page-size deve ser maior que zero.")

        output_path = build_output_path(snapshot_date)

        # Descompacta o snapshot da data solicitada se estiver zipado
        snapshot_dir = output_path.parent.parent
        zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
        if not snapshot_dir.exists() and zip_path.exists():
            unpack_archive(zip_path, label="bronze", step=1, total=1)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        failure_log_path = build_failure_log_path(snapshot_date)
        write_failure_log(
            log_path=failure_log_path,
            snapshot_date=snapshot_date,
            failure_entries=[],
        )

        print("Iniciando extracao da lista de projetos da BioCarbon Registry")
        print(f"Data do snapshot: {snapshot_date}")
        print(f"URL da pagina: {PAGE_URL}")
        print(f"Endpoint da API: {LIST_API_URL}")
        print("Metodo de extracao: API publica com x-api-key exposta no bundle do frontend")
        print(f"Idioma da API: {args.language}")
        print(f"Page size da API: {args.page_size}")
        print(f"Timeout por operacao: {args.timeout:.1f}s")
        if args.max_pages is not None:
            print(f"Modo de teste ativado: max_pages={args.max_pages}")
        print(f"Arquivo de saida: {output_path}")
        print(f"Arquivo de falhas: {failure_log_path}")

        try:
            data = fetch_all_projects(
                timeout=args.timeout,
                max_pages=args.max_pages,
                language=args.language,
                page_size=args.page_size,
            )
        except Exception as exc:
            append_failure_entry(
                log_path=failure_log_path,
                snapshot_date=snapshot_date,
                entry={
                    "captured_at": utc_now_iso(),
                    "stage": "list_collection",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            raise

        payload: dict[str, Any] = {
            "source": {
                "page_url": PAGE_URL,
                "api_url": LIST_API_URL,
                "extraction_method": "public_api_with_x_api_key_from_frontend_bundle",
                "language": args.language,
                "page_size": args.page_size,
                "project_identifier_mapping": {
                    "project_public_id": "project_id",
                    "project_internal_id": "id",
                },
            },
            "retrieved_at": utc_now_iso(),
            "total_pages": data["total_pages"],
            "pages_collected": data["pages_collected"],
            "total_records": data["total_records"],
            "projects": data["projects"],
        }

        if args.max_pages is not None:
            payload["partial"] = True

        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Arquivo salvo em: {output_path}")
        print(f"Total de projetos salvos: {len(data['projects'])}")
        if data.get("total_pages") is not None:
            print(f"Total de paginas informado pela API: {data['total_pages']}")
        if data.get("total_records") is not None:
            print(f"Total de registros informado pela API: {data['total_records']}")
        if payload.get("partial"):
            print("Execucao finalizada em modo parcial")
        else:
            print("Execucao finalizada com sucesso")

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
