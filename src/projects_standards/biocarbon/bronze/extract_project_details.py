# Objetivo do script:
# Ler a lista bruta de uma data especifica, consultar o detalhe de cada projeto e salvar um JSON bronze por projeto.
# Processo:
# 1. Ler argumentos CLI (--date, --limit, parametros de ritmo e retry).
# 2. Descompactar o snapshot se estiver zipado.
# 3. Carregar lista de projetos do snapshot da data informada.
# 4. Identificar projetos pendentes (sem arquivo de detalhe ou com --force).
# 5. Exibir cabecalho com parametros da execucao.
# 6. Para cada projeto, consultar o endpoint de detalhe da certificadora.
# 7. Montar payload com source, list_data e detail_data.
# 8. Salvar um JSON por projeto no diretorio projects/ do snapshot.
# 9. Exibir progresso a cada 10 projetos (percentual e tempo restante).
# 10. Registrar falhas individuais sem interromper a execucao.
# 11. Exibir resumo final e gravar log de falhas se houver.
# 12. Compactar o diretorio do snapshot em ZIP.


import argparse
import json
import re
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib import parse, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_directory, unpack_archive

try:
    from .runtime_cleanup import managed_execution
except ImportError:
    from runtime_cleanup import managed_execution


API_BASE_URL = "https://api.globalcarbontrace.io"
API_KEY = "SboCiHaHxtC2xRM92hpBjy1S2Y5La7IwjeB76z"
LIST_API_URL = f"{API_BASE_URL}/api/public/initiatives"
DETAIL_API_URL_TEMPLATE = f"{API_BASE_URL}/api/ghg/projects/{{project_internal_id}}"
CREDITS_API_URL_TEMPLATE = (
    f"{API_BASE_URL}/api/ghg/carbon-credits/project/{{project_internal_id}}"
)
RETREATS_API_URL_TEMPLATE = (
    f"{API_BASE_URL}/api/ghg/retreats/project/{{project_internal_id}}"
)
DETAIL_URL_TEMPLATE = "https://globalcarbontrace.io/registry/biocarbon/gei/project/{project_internal_id}"
DEFAULT_SLEEP_SECONDS = 1.0
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_LANGUAGE = "en"
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 5.0
DEFAULT_PROGRESS_REPORT_EVERY = 10


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os detalhes brutos dos projetos da BioCarbon Registry."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de projetos processados para testes.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=(
            "Intervalo entre projetos para reduzir agressividade. "
            f"Padrao: {DEFAULT_SLEEP_SECONDS}."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Quantidade de projetos entre pausas mais longas. "
            f"Padrao: {DEFAULT_BATCH_SIZE}."
        ),
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=(
            "Pausa aplicada a cada lote de projetos para reduzir risco de rate limit. "
            f"Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout total por operacao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Idioma preferencial das respostas da API. Padrao: {DEFAULT_LANGUAGE}.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=(
            "Quantidade maxima de tentativas adicionais quando a API responder 429. "
            f"Padrao: {DEFAULT_RETRY_ATTEMPTS}."
        ),
    )
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=DEFAULT_RETRY_SLEEP_SECONDS,
        help=(
            "Tempo de espera entre tentativas apos 429 Too Many Requests. "
            f"Padrao: {DEFAULT_RETRY_SLEEP_SECONDS}."
        ),
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Sobrescreve detalhes ja salvos para a mesma data.",
    )
    return parser.parse_args()


# Valida a data informada e garante o formato YYYYMMDD.
def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise SystemExit(f"--date invalida: {value}. Use YYYYMMDD.") from exc
    return value


# Monta os metadados padronizados de source para o arquivo bronze de detalhe.
def build_project_source(
    *,
    carbon_standard: str,
    snapshot_date: str,
    project_public_id: str,
    project_internal_id: str,
    project_url: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = datetime.strptime(snapshot_date, "%Y%m%d").date()
    source = {
        "carbon_standard": carbon_standard,
        "snapshot_date": snapshot.isoformat(),
        "reference_month": snapshot.replace(day=1).isoformat(),
        "project_public_id": project_public_id,
        "project_internal_id": project_internal_id,
        "project_url": project_url,
    }
    if extra_fields:
        source.update(extra_fields)
    return source


# Monta os caminhos de entrada e saida usados pelo script.
def build_paths(snapshot_date: str) -> tuple[Path, Path, Path]:
    root = Path(__file__).resolve().parents[4]
    list_path = root / "data" / "project_standards" / "01_bronze" / "biocarbon" / snapshot_date / "list" / "projects.json"
    projects_dir = root / "data" / "project_standards" / "01_bronze" / "biocarbon" / snapshot_date / "projects"
    errors_path = (
        Path(__file__).resolve().parent
        / "logs"
        / f"extract_project_details_failures_{snapshot_date}.json"
    )
    return list_path, projects_dir, errors_path


# Carrega os registros salvos no snapshot bruto da lista.
def load_list_records(list_path: Path) -> list[dict[str, Any]]:
    if not list_path.exists():
        raise SystemExit(f"Lista de projetos nao encontrada: {list_path}")

    payload = json.loads(list_path.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    if not isinstance(projects, list):
        raise SystemExit(f"Arquivo de lista invalido: {list_path}")
    return projects


# Gera a chave de comparacao usada para registros vindos da lista.
def make_list_key(project: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(project.get("project_id") or project.get("card_title") or "").strip(),
        str(project.get("project_name") or project.get("card_id") or "").strip(),
        str(project.get("holder_name") or project.get("card_holder") or "").strip(),
    )


# Gera a chave de comparacao usada para registros vindos da API.
def make_api_key(project: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(project.get("project_id") or "").strip(),
        str(project.get("project_name") or "").strip(),
        str(project.get("holder_name") or "").strip(),
    )


# Normaliza o valor para uso seguro em nomes de arquivo.
def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', "_", value).strip()
    return cleaned or "project"


# Resolve o identificador publico do projeto a partir dos dados disponiveis.
def resolve_project_public_id(project: dict[str, Any], index: int) -> str:
    return sanitize_filename(
        str(
            project.get("project_id")
            or project.get("card_title")
            or project.get("card_id")
            or f"biocarbon_project_{index}"
        )
    )


# Retorna o horario atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Formata uma duracao em segundos para leitura rapida no terminal.
def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


# Estima o tempo restante com base no tempo medio por item ja processado.
def estimate_remaining_seconds(started_at: float, completed_items: int, total_items: int) -> float:
    if completed_items <= 0 or total_items <= completed_items:
        return 0.0
    elapsed_seconds = max(0.0, time.perf_counter() - started_at)
    average_seconds = elapsed_seconds / completed_items
    remaining_items = total_items - completed_items
    return average_seconds * remaining_items


# Emite um relatorio curto de progresso com percentual concluido e tempo restante medio.
def print_progress_report(started_at: float, completed_items: int, total_items: int) -> None:
    if total_items <= 0 or completed_items <= 0:
        return
    percent_complete = (completed_items / total_items) * 100
    remaining_seconds = estimate_remaining_seconds(
        started_at=started_at,
        completed_items=completed_items,
        total_items=total_items,
    )
    print(
        f"progresso: {completed_items}/{total_items} ({percent_complete:.1f}%) | "
        f"tempo restante estimado: {format_duration(remaining_seconds)}"
    )


# Le o log de falhas existente quando ele ja estiver salvo.
def read_failure_log(errors_path: Path) -> dict[str, Any]:
    if not errors_path.exists():
        return {}

    payload = json.loads(errors_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Arquivo de log de falhas invalido: {errors_path}")
    return payload


# Grava o log consolidado de falhas da execucao.
def write_failure_log(
    errors_path: Path,
    snapshot_date: str,
    failure_entries: list[dict[str, Any]],
) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {
            "certificadora": "biocarbon",
            "snapshot_date": snapshot_date,
            "script": "extract_project_details.py",
        },
        "updated_at": utc_now_iso(),
        "failure_count": len(failure_entries),
        "failures": failure_entries,
    }
    errors_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Acrescenta uma falha ao log operacional sem perder o historico atual.
def append_failure_entry(
    errors_path: Path,
    snapshot_date: str,
    entry: dict[str, Any],
) -> None:
    payload = read_failure_log(errors_path)
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    failures.append(entry)
    write_failure_log(
        errors_path=errors_path,
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


# Busca o indice auxiliar de projetos exposto pela fonte remota.
def fetch_registry_index(timeout: float, language: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    payload = fetch_json(
        LIST_API_URL,
        timeout=timeout,
        params={
            "language": language,
            "per_page": 200,
        },
    )
    items = payload.get("data")
    if not isinstance(items, list):
        raise RuntimeError("Resposta inesperada da lista API da BioCarbon: chave 'data' ausente ou invalida.")
    return {make_api_key(item): item for item in items}


# Busca o conjunto de payloads necessario para montar o detalhe do projeto.
def fetch_project_bundle(
    project_internal_id: str,
    timeout: float,
    language: str,
) -> dict[str, Any]:
    project_payload = fetch_json(
        DETAIL_API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
        timeout=timeout,
        params={"language": language},
    )
    carbon_credits_payload = fetch_json(
        CREDITS_API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
        timeout=timeout,
        params={
            "sortField": "created_at",
            "sortDirection": "desc",
            "per_page": 100,
        },
    )
    retreats_payload = fetch_json(
        RETREATS_API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
        timeout=timeout,
        params={
            "sortField": "created_at",
            "sortDirection": "desc",
        },
    )
    return {
        "project": project_payload,
        "carbon_credits": carbon_credits_payload,
        "retreats": retreats_payload,
    }


# Repete a coleta do bundle do projeto quando houver falhas transitorias.
def fetch_project_bundle_with_retry(
    project_internal_id: str,
    timeout: float,
    language: str,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    attempts_total = retry_attempts + 1
    attempt = 1

    while True:
        try:
            return fetch_project_bundle(
                project_internal_id=project_internal_id,
                timeout=timeout,
                language=language,
            )
        except HTTPError as exc:
            if exc.code != 429 or attempt >= attempts_total:
                raise

            print(
                "429 Too Many Requests para "
                f"detail_id={project_internal_id}; aguardando {retry_sleep_seconds:.1f}s "
                f"antes da tentativa {attempt + 1}/{attempts_total}"
            )
            time.sleep(retry_sleep_seconds)
            attempt += 1


# Verifica se o arquivo de saida existente ja pode ser reaproveitado.
def existing_output_is_valid(output_path: Path, project_public_id: str) -> bool:
    if not output_path.exists():
        return False

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    if not isinstance(payload, dict):
        return False
    source = payload.get("source")
    detail_data = payload.get("detail_data")
    if not isinstance(source, dict) or not isinstance(detail_data, dict):
        return False
    return source.get("project_public_id") == project_public_id


# Percorre os projetos do snapshot e processa cada item da coleta.
def process_projects(
    records: list[dict[str, Any]],
    projects_dir: Path,
    errors_path: Path,
    snapshot_date: str,
    language: str,
    sleep_seconds: float,
    batch_size: int,
    batch_sleep_seconds: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
    timeout: float,
    limit: int | None,
    overwrite_existing: bool,
) -> tuple[int, int, int]:
    projects_dir.mkdir(parents=True, exist_ok=True)
    write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failure_entries=[])

    registry_index = fetch_registry_index(timeout=timeout, language=language)
    target_records = records[:limit] if limit is not None else records
    success_count = 0
    failure_count = 0
    skipped_count = 0
    started_at = time.perf_counter()

    for index, list_record in enumerate(target_records, start=1):
        project_public_id = resolve_project_public_id(list_record, index)
        output_path = projects_dir / f"{project_public_id}.json"

        if not overwrite_existing and existing_output_is_valid(output_path, project_public_id):
            skipped_count += 1
            print(
                f"pulando projeto {project_public_id} ({index}/{len(target_records)}): detalhe ja salvo"
            )
            completed_items = success_count + failure_count + skipped_count
            if completed_items % DEFAULT_PROGRESS_REPORT_EVERY == 0 or completed_items == len(target_records):
                print_progress_report(started_at=started_at, completed_items=completed_items, total_items=len(target_records))
            continue

        print(f"inicio download do projeto {project_public_id} ({index}/{len(target_records)})")
        try:
            bronze_internal_id = list_record.get("id")
            if bronze_internal_id is not None:
                project_internal_id = str(bronze_internal_id)
                registry_row = registry_index.get(make_list_key(list_record), list_record)
            else:
                registry_row = registry_index.get(make_list_key(list_record))
                if registry_row is None:
                    raise RuntimeError(
                        "Projeto nao encontrado na lista publica da API da BioCarbon pelo trio "
                        "(project_id/card_title, project_name/card_id, holder_name/card_holder)."
                    )
                project_internal_id = str(registry_row["id"])

            detail_data = fetch_project_bundle_with_retry(
                project_internal_id=project_internal_id,
                timeout=timeout,
                language=language,
                retry_attempts=retry_attempts,
                retry_sleep_seconds=retry_sleep_seconds,
            )
            payload = {
                "source": build_project_source(
                    carbon_standard="biocarbon",
                    snapshot_date=snapshot_date,
                    project_public_id=project_public_id,
                    project_internal_id=project_internal_id,
                    project_url=DETAIL_URL_TEMPLATE.format(project_internal_id=project_internal_id),
                    extra_fields={
                        "detail_api_url": DETAIL_API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
                        "language": language,
                        "extraction_method": "public_api_with_x_api_key_from_frontend_bundle",
                    },
                ),
                "list_data": list_record,
                "detail_data": detail_data,
            }
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            success_count += 1
            print(f"fim download do projeto {project_public_id} (detail_id={project_internal_id})")
        except Exception as exc:
            failure_count += 1
            print(f"falha no projeto {project_public_id}: {exc}", file=sys.stderr)
            append_failure_entry(
                errors_path=errors_path,
                snapshot_date=snapshot_date,
                entry={
                    "captured_at": utc_now_iso(),
                    "project_public_id": project_public_id,
                    "stage": "project_download",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "list_data": list_record,
                    "traceback": traceback.format_exc(),
                },
            )

        completed_items = success_count + failure_count + skipped_count
        if completed_items % DEFAULT_PROGRESS_REPORT_EVERY == 0 or completed_items == len(target_records):
            print_progress_report(started_at=started_at, completed_items=completed_items, total_items=len(target_records))
        if batch_size > 0 and batch_sleep_seconds > 0 and index % batch_size == 0 and index < len(target_records):
            print(
                f"pausa de lote apos {index} projetos: aguardando {batch_sleep_seconds:.1f}s"
            )
            time.sleep(batch_sleep_seconds)

        if sleep_seconds > 0 and index < len(target_records):
            time.sleep(sleep_seconds)

    return success_count, failure_count, skipped_count


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main(args: argparse.Namespace) -> int:
    snapshot_date = validate_date(args.date)
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit deve ser maior que zero.")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size deve ser maior que zero.")
    if args.retry_attempts < 0:
        raise SystemExit("--retry-attempts nao pode ser negativo.")

    list_path, projects_dir, errors_path = build_paths(snapshot_date)

    # Descompacta o snapshot se estiver zipado
    snapshot_dir = list_path.parent.parent
    zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
    unpacked = False
    if not snapshot_dir.exists() and zip_path.exists():
        unpack_archive(zip_path, label="bronze", step=1, total=1)
        unpacked = True

    records = load_list_records(list_path=list_path)
    total_to_process = args.limit or len(records)

    print("Iniciando extracao de detalhes dos projetos da BioCarbon Registry")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"Lista de origem: {list_path}")
    print(f"Diretorio de saida: {projects_dir}")
    print(f"Arquivo de falhas: {errors_path}")
    print(f"Lista API de apoio: {LIST_API_URL}")
    print(f"Endpoint de detalhe: {DETAIL_API_URL_TEMPLATE}")
    print("Metodo de extracao: API publica com x-api-key exposta no bundle do frontend")
    print(f"Idioma da API: {args.language}")
    print(f"Sleep entre projetos: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada lote: {args.batch_sleep_seconds:.1f}s a cada {args.batch_size} projetos")
    print(
        f"Retry em 429: {args.retry_attempts} tentativas adicionais com espera de "
        f"{args.retry_sleep_seconds:.1f}s"
    )
    print(f"Timeout por operacao: {args.timeout:.1f}s")
    print(
        "Persistencia existente: "
        + ("sobrescrever arquivos ja salvos" if args.overwrite_existing else "pular arquivos ja salvos")
    )
    print(f"Total detectado na lista: {len(records)}")
    print(f"Total a processar nesta execucao: {total_to_process}")

    with managed_execution(script_name="biocarbon/extract_project_details.py"):
        success_count, failure_count, skipped_count = process_projects(
            records=records,
            projects_dir=projects_dir,
            errors_path=errors_path,
            snapshot_date=snapshot_date,
            language=args.language,
            sleep_seconds=args.sleep_seconds,
            batch_size=args.batch_size,
            batch_sleep_seconds=args.batch_sleep_seconds,
            retry_attempts=args.retry_attempts,
            retry_sleep_seconds=args.retry_sleep_seconds,
            timeout=args.timeout,
            limit=args.limit,
            overwrite_existing=args.overwrite_existing,
        )

    print(
        "Execucao finalizada. "
        f"Sucessos: {success_count}. Falhas: {failure_count}. Pulados: {skipped_count}."
    )

    # Compacta o diretorio do snapshot em ZIP
    pack_directory(snapshot_dir, label="bronze", step=1, total=1)

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    parsed_args = parse_args()
    try:
        raise SystemExit(main(parsed_args))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc