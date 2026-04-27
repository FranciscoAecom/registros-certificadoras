# Objetivo do script:
# Baixar a lista bruta completa de projetos da certificadora e salvar o snapshot em data/project_standards/01_bronze/<certificadora>/<date>/list/projects.json.
# Processo:
# 1. Ler argumentos CLI (--date, parametros de ritmo e retry).
# 2. Validar data e montar diretorio de saida do snapshot.
# 3. Descompactar o snapshot da data solicitada se estiver salvo em ZIP simples ou bundle core+spatial.
# 4. Exibir cabecalho com parametros da execucao.
# 5. Consultar endpoint da certificadora com paginacao.
# 6. Acumular todos os registros da lista.
# 7. Salvar snapshot completo em JSON no diretorio list/ do snapshot.
# 8. Compactar o snapshot em bundle core + partes espaciais quando aplicavel.
# 9. Exibir resumo da execucao.


import argparse
import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from runtime_cleanup import managed_execution

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_snapshot_bundle, unpack_snapshot_bundle


PAGE_URL = "https://www.ecoregistry.io/projects-list/cercarbono-co2"
API_URL = "https://api-front.ecoregistry.io/platform/project/public-by-standard/cercarbono-co2"
STANDARD_SLUG = "cercarbono-co2"
DEFAULT_SLEEP_SECONDS = 0.0
DEFAULT_TIMEOUT_SECONDS = 30.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa a lista bruta de projetos da Cercarbono."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Data de referencia no formato YYYYMMDD.",
    )
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
        help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Parametro de teste padronizado. Para esta fonte, apenas 1 pagina e suportada.",
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
    return root / "data" / "project_standards" / "01_bronze" / "cercarbono" / snapshot_date / "list" / "projects.json"


# Monta o caminho do log de falhas para o snapshot informado.
def build_failure_log_path(snapshot_date: str) -> Path:
    return Path(__file__).resolve().parent / "logs" / f"extract_project_list_failures_{snapshot_date}.json"


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
            "certificadora": "cercarbono",
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
    write_failure_log(log_path=log_path, snapshot_date=snapshot_date, failure_entries=failures)


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT,
        "Platform": "ecoregistry",
        "Lng": "en",
        "Referer": PAGE_URL,
        "Origin": "https://www.ecoregistry.io",
    }


# Busca os dados necessarios na fonte remota.
def fetch_projects_payload(timeout: float) -> dict[str, Any]:
    # Reutilizamos o endpoint JSON publico consumido pela propria pagina da registry.
    req = request.Request(
        url=API_URL,
        method="GET",
        headers=build_headers(),
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erro HTTP {exc.code} ao consultar a Cercarbono. Resposta: {details}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de rede ao consultar a Cercarbono: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Resposta inesperada da Cercarbono: era esperado um objeto JSON.")

    projects = payload.get("projects")
    if not isinstance(projects, list):
        raise RuntimeError("Resposta inesperada da Cercarbono: chave 'projects' ausente ou invalida.")

    return payload


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    with managed_execution(script_name="cercarbono/extract_project_list.py"):
        args = parse_args()
        snapshot_date = validate_date(args.date)

        if args.max_pages is not None and args.max_pages <= 0:
            raise SystemExit("--max-pages deve ser maior que zero.")
        if args.max_pages not in {None, 1}:
            raise SystemExit("A Cercarbono entrega a lista em um unico endpoint. Use --max-pages 1 para teste.")

        output_path = build_output_path(snapshot_date)

        # Descompacta o snapshot da data solicitada se estiver em ZIP simples ou bundle core+spatial
        snapshot_dir = output_path.parent.parent
        zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
        core_zip_path = snapshot_dir.parent / f"{snapshot_dir.name}_core.zip"
        core_part_paths = list(snapshot_dir.parent.glob(f"{snapshot_dir.name}_core_*.zip"))
        if not snapshot_dir.exists() and (zip_path.exists() or core_zip_path.exists() or core_part_paths):
            unpack_snapshot_bundle(snapshot_dir.parent, snapshot_dir.name, label="bronze", step=1, total=1)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        failure_log_path = build_failure_log_path(snapshot_date)
        write_failure_log(log_path=failure_log_path, snapshot_date=snapshot_date, failure_entries=[])

        print("Iniciando extracao da lista de projetos da Cercarbono")
        print(f"Data do snapshot: {snapshot_date}")
        print(f"URL da pagina: {PAGE_URL}")
        print(f"Endpoint da API: {API_URL}")
        print("Metodo de extracao: endpoint JSON publico consumido pelo frontend")
        print("Encerramento de recursos: contexto gerenciado com limpeza explicita no fim da execucao")
        print(f"Timeout por requisicao: {args.timeout:.1f}s")
        if args.max_pages is not None:
            print(f"Modo de teste ativado: max_pages={args.max_pages}")
        print(f"Arquivo de saida: {output_path}")
        print(f"Arquivo de falhas: {failure_log_path}")

        try:
            payload = fetch_projects_payload(timeout=args.timeout)
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

        output_payload: dict[str, Any] = {
            "source": {
                "page_url": PAGE_URL,
                "api_url": API_URL,
                "standard_slug": STANDARD_SLUG,
                "project_identifier_mapping": {
                    "project_public_id": "code",
                    "project_internal_id": "id",
                },
            },
            "retrieved_at": utc_now_iso(),
            "status": payload.get("status"),
            "standard_name": payload.get("standardName"),
            "standard_id": payload.get("standardId"),
            "standard_metadata": payload.get("standardMetaData"),
            "projects": payload.get("projects", []),
        }

        if args.max_pages is not None:
            output_payload["partial"] = True

        output_path.write_text(
            json.dumps(output_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Arquivo salvo em: {output_path}")
        print(f"Total de projetos salvos: {len(output_payload['projects'])}")
        print("Execucao finalizada com sucesso")

        # Compacta o snapshot em bundle core + partes espaciais quando aplicavel
        snapshot_dir = output_path.parent.parent
        pack_snapshot_bundle(snapshot_dir, label="bronze", step=1, total=1)

        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
