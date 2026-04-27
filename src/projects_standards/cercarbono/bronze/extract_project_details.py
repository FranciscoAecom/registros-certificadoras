# Objetivo do script:
# Ler a lista bruta de uma data especifica, consultar o detalhe de cada projeto e salvar um JSON bronze por projeto.
# Processo:
# 1. Ler argumentos CLI (--date, --limit, parametros de ritmo, retry e empacotamento espacial).
# 2. Descompactar o snapshot se estiver salvo em ZIP simples ou bundle core+spatial.
# 3. Carregar lista de projetos do snapshot da data informada.
# 4. Identificar projetos pendentes (sem arquivo de detalhe ou com --force).
# 5. Exibir cabecalho com parametros da execucao.
# 6. Para cada projeto, consultar o endpoint de detalhe da certificadora.
# 7. Baixar anexos cartograficos quando existirem e salva-los como arquivos do snapshot.
# 8. Montar payload com source, list_data e detail_data apontando para os arquivos espaciais.
# 8. Salvar um JSON por projeto no diretorio projects/ do snapshot.
# 9. Exibir progresso a cada 10 projetos (percentual e tempo restante).
# 10. Registrar falhas individuais sem interromper a execucao.
# 11. Exibir resumo final e gravar log de falhas se houver.
# 12. Compactar o snapshot em bundle core + partes espaciais.


import argparse
import json
import re
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from runtime_cleanup import managed_execution

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import (
    DEFAULT_SPATIAL_PART_MAX_BYTES,
    pack_snapshot_bundle,
    unpack_snapshot_bundle,
)


PAGE_URL_TEMPLATE = "https://www.ecoregistry.io/projects/{project_internal_id}"
API_URL_TEMPLATE = "https://api-front.ecoregistry.io/platform/project/public/{project_internal_id}"
PROJECT_DOCUMENTS_URL_TEMPLATE = "https://api-front.ecoregistry.io/platform/projectDocument/get-by-project-id/{project_internal_id}/{verification_number}"
PROJECT_LOCATION_DOCUMENT_DOWNLOAD_URL_TEMPLATE = "https://api-front.ecoregistry.io/platform/projectLocationsDocuments/download/{document_id}"
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_PROGRESS_REPORT_EVERY = 10
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_SPATIAL_SUBDIR_NAME = "spatial"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os detalhes brutos dos projetos da Cercarbono."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument("--limit", type=int, default=None, help="Limita o numero de projetos para teste.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=(f"Intervalo entre requisicoes para reduzir agressividade. Padrao: {DEFAULT_SLEEP_SECONDS}."),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(f"Quantidade de downloads concluidos antes da pausa extra. Padrao: {DEFAULT_BATCH_SIZE}."),
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=(
            "Pausa extra aplicada a cada bloco de downloads concluidos. "
            f"Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}."
        ),
    )
    parser.add_argument(
        "--progress-report-every",
        type=int,
        default=DEFAULT_PROGRESS_REPORT_EVERY,
        help=(
            "Intervalo de projetos concluidos entre relatorios curtos de progresso. "
            f"Padrao: {DEFAULT_PROGRESS_REPORT_EVERY}."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--spatial-part-max-bytes",
        type=int,
        default=DEFAULT_SPATIAL_PART_MAX_BYTES,
        help="Teto em bytes para cada ZIP spatial_<n>. Padrao seguro abaixo do limite do Git LFS.",
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
def build_paths(snapshot_date: str) -> tuple[Path, Path, Path, Path]:
    root = Path(__file__).resolve().parents[4]
    snapshot_dir = root / "data" / "project_standards" / "01_bronze" / "cercarbono" / snapshot_date
    list_path = snapshot_dir / "list" / "projects.json"
    projects_dir = snapshot_dir / "projects"
    spatial_dir = snapshot_dir / DEFAULT_SPATIAL_SUBDIR_NAME
    return snapshot_dir, list_path, projects_dir, spatial_dir


# Monta o caminho do log de falhas para o snapshot informado.
def build_failure_log_path(snapshot_date: str) -> Path:
    return Path(__file__).resolve().parent / "logs" / f"extract_project_details_failures_{snapshot_date}.json"


# Normaliza o valor para uso seguro em nomes de arquivo.
def sanitize_filename(value: str, fallback: str = "project") -> str:
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', "_", value).strip()
    return cleaned or fallback


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
            "script": "extract_project_details.py",
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
def build_headers(project_internal_id: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT,
        "Platform": "ecoregistry",
        "Lng": "en",
        "Referer": PAGE_URL_TEMPLATE.format(project_internal_id=project_internal_id),
        "Origin": "https://www.ecoregistry.io",
    }


# Busca um JSON remoto e valida o formato basico esperado.
def fetch_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    req = request.Request(url=url, method="GET", headers=headers)

    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {exc.code} ao consultar {url}. Resposta: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de rede ao consultar {url}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Resposta inesperada para {url}: era esperado um objeto JSON.")

    return payload


# Carrega os projetos salvos no snapshot bruto da lista.
def load_projects(list_path: Path) -> list[dict[str, Any]]:
    if not list_path.exists():
        raise SystemExit(f"Arquivo da lista nao encontrado: {list_path}")

    payload = json.loads(list_path.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    if not isinstance(projects, list):
        raise SystemExit(
            f"Arquivo da lista invalido: chave 'projects' ausente ou invalida em {list_path}"
        )

    cleaned_projects: list[dict[str, Any]] = []
    for index, project in enumerate(projects, start=1):
        project_code = project.get("code")
        project_id = project.get("id")
        if not project_code or project_id is None:
            print(
                f"aviso: projeto na posicao {index} sem code ou id, ignorando",
                file=sys.stderr,
            )
            continue
        cleaned_projects.append(project)

    return cleaned_projects


# Busca o detalhe bruto de um projeto na fonte remota.
def fetch_project_details(project_internal_id: str, timeout: float) -> dict[str, Any]:
    # Reutilizamos o endpoint JSON publico do frontend da pagina de detalhe.
    return fetch_json(
        url=API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
        headers=build_headers(project_internal_id),
        timeout=timeout,
    )


# Lista os grupos de documentos disponiveis para a verificacao publica ativa.
def fetch_project_documents(
    project_internal_id: str,
    verification_number: int,
    timeout: float,
) -> list[dict[str, Any]]:
    payload = fetch_json(
        url=PROJECT_DOCUMENTS_URL_TEMPLATE.format(
            project_internal_id=project_internal_id,
            verification_number=verification_number,
        ),
        headers=build_headers(project_internal_id),
        timeout=timeout,
    )
    documents = payload.get("documents")
    if not isinstance(documents, list):
        return []
    return [group for group in documents if isinstance(group, dict)]


# Filtra documentos cartograficos do payload de documentos do projeto.
def collect_spatial_documents(document_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for group in document_groups:
        group_name = str(group.get("name") or "").strip()
        documents = group.get("documents")
        if not isinstance(documents, list):
            continue

        for document in documents:
            if not isinstance(document, dict):
                continue
            document_type = str(document.get("type") or "").strip()
            document_name = str(document.get("name") or "").strip()
            if document_type != "documentLocation" and group_name.lower() != "cartography":
                continue
            results.append(
                {
                    "groupName": group_name,
                    "id": document.get("id"),
                    "name": document_name,
                    "type": document_type,
                    "created": document.get("created"),
                    "updated": document.get("updated"),
                    "last": document.get("last"),
                    "hash": document.get("hash"),
                }
            )
    return results


# Resolve a URL publica temporaria do ZIP cartografico para um documento espacial.
def fetch_spatial_document_download_info(
    project_internal_id: str,
    document_id: str,
    timeout: float,
) -> dict[str, Any]:
    payload = fetch_json(
        url=PROJECT_LOCATION_DOCUMENT_DOWNLOAD_URL_TEMPLATE.format(document_id=document_id),
        headers=build_headers(project_internal_id),
        timeout=timeout,
    )
    if "url" not in payload:
        raise RuntimeError(
            f"Resposta sem URL de download para o documento espacial {document_id} do projeto {project_internal_id}."
        )
    return payload


# Baixa o binario bruto de um documento remoto.
def fetch_document_bytes(url: str, timeout: float) -> tuple[bytes, str]:
    req = request.Request(
        url=url,
        method="GET",
        headers={
            "Accept": "*/*",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.read(), str(response.headers.get("Content-Type") or "")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {exc.code} ao baixar {url}. Resposta: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de rede ao baixar {url}: {exc}") from exc


# Infere a extensao mais segura para o documento espacial.
def infer_spatial_extension(
    *,
    source_url: str,
    response_content_type: str,
    suggested_name: str,
) -> str:
    lower_name = suggested_name.lower()
    for suffix in (".zip", ".kmz", ".kml", ".geojson", ".shp", ".dbf", ".cpg", ".sbn", ".sbx", ".shx", ".prj", ".jpg", ".jpeg", ".png"):
        if lower_name.endswith(suffix):
            return suffix

    lower_content_type = response_content_type.lower()
    if "zip" in lower_content_type:
        return ".zip"
    if "google-earth.kmz" in lower_content_type:
        return ".kmz"
    if "google-earth.kml" in lower_content_type:
        return ".kml"
    if "geo+json" in lower_content_type or "geojson" in lower_content_type:
        return ".geojson"
    if "jpeg" in lower_content_type or "jpg" in lower_content_type:
        return ".jpg"
    if "png" in lower_content_type:
        return ".png"

    source_suffix = Path(parse.urlparse(source_url).path).suffix.lower()
    return source_suffix


# Persiste o documento espacial no snapshot e retorna o caminho relativo salvo.
def persist_spatial_document(
    *,
    snapshot_dir: Path,
    spatial_subdir_name: str,
    project_id: str,
    document_index: int,
    source_url: str,
    suggested_name: str,
    response_content_type: str,
    raw_bytes: bytes,
) -> str:
    extension = infer_spatial_extension(
        source_url=source_url,
        response_content_type=response_content_type,
        suggested_name=suggested_name,
    )
    fallback_name = f"document_{document_index:03d}{extension}"
    safe_name = sanitize_filename(suggested_name, fallback_name)
    if extension and not safe_name.lower().endswith(extension):
        safe_name = f"{safe_name}{extension}"

    relative_path = Path(spatial_subdir_name) / project_id / f"{document_index:03d}_{safe_name}"
    target_path = snapshot_dir / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(raw_bytes)
    return relative_path.as_posix()


# Baixa e preserva anexos cartograficos ZIP do projeto dentro do payload bronze.
def enrich_spatial_documents(
    detail_payload: dict[str, Any],
    *,
    snapshot_dir: Path,
    spatial_subdir_name: str,
    project_public_id: str,
    project_internal_id: str,
    timeout: float,
) -> None:
    project_data = detail_payload.get("project")
    if not isinstance(project_data, dict):
        return

    verification_number = project_data.get("verificationNumber")
    if not isinstance(verification_number, int):
        return

    document_groups = fetch_project_documents(
        project_internal_id=project_internal_id,
        verification_number=verification_number,
        timeout=timeout,
    )
    spatial_documents = collect_spatial_documents(document_groups)
    if not spatial_documents:
        return

    enriched_documents: list[dict[str, Any]] = []
    for document_index, spatial_document in enumerate(spatial_documents, start=1):
        enriched = dict(spatial_document)
        document_id = spatial_document.get("id")
        if document_id is None:
            enriched["downloadError"] = "Documento cartografico sem id."
            enriched_documents.append(enriched)
            continue

        try:
            download_info = fetch_spatial_document_download_info(
                project_internal_id=project_internal_id,
                document_id=str(document_id),
                timeout=timeout,
            )
            download_url = str(download_info.get("url") or "").strip()
            enriched["downloadInfo"] = download_info
            if not download_url:
                raise RuntimeError("Resposta de download sem campo url.")

            raw_bytes, response_content_type = fetch_document_bytes(download_url, timeout)
            enriched["contentType"] = response_content_type
            enriched["storageMode"] = "snapshot_file"
            enriched["snapshotRelativePath"] = persist_spatial_document(
                snapshot_dir=snapshot_dir,
                spatial_subdir_name=spatial_subdir_name,
                project_id=project_public_id,
                document_index=document_index,
                source_url=download_url,
                suggested_name=str(spatial_document.get("name") or f"document_{document_index:03d}"),
                response_content_type=response_content_type,
                raw_bytes=raw_bytes,
            )
            enriched["byteSize"] = len(raw_bytes)
        except Exception as exc:  # noqa: BLE001
            enriched["downloadError"] = str(exc)

        enriched_documents.append(enriched)

    if enriched_documents:
        detail_payload["spatial_documents"] = enriched_documents


# Salva o detalhe bruto do projeto no diretorio de destino.
def save_project_details(projects_dir: Path, project_public_id: str, payload: dict[str, Any]) -> None:
    output_path = projects_dir / f"{project_public_id}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    with managed_execution(script_name="cercarbono/extract_project_details.py"):
        args = parse_args()
        snapshot_date = validate_date(args.date)

        if args.limit is not None and args.limit <= 0:
            raise SystemExit("--limit deve ser maior que zero.")
        if args.batch_size <= 0:
            raise SystemExit("--batch-size deve ser maior que zero.")

        snapshot_dir, list_path, projects_dir, spatial_dir = build_paths(snapshot_date)
        failure_log_path = build_failure_log_path(snapshot_date)

        # Descompacta o snapshot se estiver zipado
        zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
        core_zip_path = snapshot_dir.parent / f"{snapshot_dir.name}_core.zip"
        core_part_paths = list(snapshot_dir.parent.glob(f"{snapshot_dir.name}_core_*.zip"))
        if not snapshot_dir.exists() and (zip_path.exists() or core_zip_path.exists() or core_part_paths):
            unpack_snapshot_bundle(snapshot_dir.parent, snapshot_dir.name, label="bronze", step=1, total=1)

        projects = load_projects(list_path)
        total_detected = len(projects)
        if args.limit is not None:
            projects = projects[: args.limit]

        total_to_process = len(projects)
        projects_dir.mkdir(parents=True, exist_ok=True)
        write_failure_log(
            log_path=failure_log_path,
            snapshot_date=snapshot_date,
            failure_entries=[],
        )

        print("Iniciando extracao de detalhes de projetos da Cercarbono")
        print(f"Lista carregada de: {list_path}")
        print(f"Total detectado na lista: {total_detected}")
        print(f"Total a processar nesta execucao: {total_to_process}")
        print(f"Endpoint de detalhe: {API_URL_TEMPLATE}")
        print("Encerramento de recursos: contexto gerenciado com limpeza explicita no fim da execucao")
        print(f"Pausa entre projetos: {args.sleep_seconds} segundos")
        print(
            "Pausa extra a cada bloco: "
            f"{args.batch_sleep_seconds} segundos a cada {args.batch_size} projetos"
        )
        print(f"Diretorio de saida: {projects_dir}")
        print(f"Diretorio espacial do snapshot: {spatial_dir}")
        print(f"Arquivo de falhas: {failure_log_path}")

        success_count = 0
        failure_count = 0
        skipped_count = 0
        started_at = time.perf_counter()

        for index, list_project in enumerate(projects, start=1):
            project_public_id = sanitize_filename(str(list_project["code"]).strip())
            project_internal_id = str(list_project["id"]).strip()
            project_url = PAGE_URL_TEMPLATE.format(project_internal_id=project_internal_id)
            print(f"inicio download do projeto {project_public_id} ({index}/{total_to_process})")

            try:
                detail_payload = fetch_project_details(
                    project_internal_id=project_internal_id,
                    timeout=args.timeout,
                )
                enrich_spatial_documents(
                    detail_payload=detail_payload,
                    snapshot_dir=snapshot_dir,
                    spatial_subdir_name=DEFAULT_SPATIAL_SUBDIR_NAME,
                    project_public_id=project_public_id,
                    project_internal_id=project_internal_id,
                    timeout=args.timeout,
                )
                payload = {
                    "source": build_project_source(
                        carbon_standard="cercarbono",
                        snapshot_date=snapshot_date,
                        project_public_id=project_public_id,
                        project_internal_id=project_internal_id,
                        project_url=project_url,
                    ),
                    "list_data": list_project,
                    "detail_data": detail_payload,
                }
                save_project_details(
                    projects_dir=projects_dir,
                    project_public_id=project_public_id,
                    payload=payload,
                )
                success_count += 1
                print(f"fim download do projeto {project_public_id}")
            except Exception as exc:
                failure_count += 1
                print(f"falha no projeto {project_public_id}: {exc}", file=sys.stderr)
                append_failure_entry(
                    log_path=failure_log_path,
                    snapshot_date=snapshot_date,
                    entry={
                        "captured_at": utc_now_iso(),
                        "project_public_id": project_public_id,
                        "project_internal_id": project_internal_id,
                        "stage": "project_download",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "project_url": project_url,
                        "list_data": list_project,
                        "traceback": traceback.format_exc(),
                    },
                )

            completed_items = success_count + failure_count + skipped_count
            if completed_items % args.progress_report_every == 0 or completed_items == total_to_process:
                print_progress_report(started_at=started_at, completed_items=completed_items, total_items=total_to_process)
            if index < total_to_process:
                time.sleep(max(0.0, args.sleep_seconds))
                if index % args.batch_size == 0:
                    print(
                        "pausa extra de "
                        f"{args.batch_sleep_seconds} segundos apos {index} projetos"
                    )
                    time.sleep(max(0.0, args.batch_sleep_seconds))

        print("resumo final:")
        print(f"projetos com sucesso: {success_count}")
        print(f"projetos com falha: {failure_count}")
        print(f"projetos pulados: {skipped_count}")
        print(f"diretorio de saida: {projects_dir}")

        # Compacta o snapshot em bundle core + partes espaciais
        pack_snapshot_bundle(
            snapshot_dir,
            label="bronze",
            step=1,
            total=1,
            spatial_subdir_name=DEFAULT_SPATIAL_SUBDIR_NAME,
            spatial_part_max_bytes=args.spatial_part_max_bytes,
        )

        return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
