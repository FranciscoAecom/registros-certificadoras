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
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_directory, unpack_archive


TENANT_CODE = "ERS"
PROGRAM_CODE = "ERS_MEASUREMENT_STANDARD"
LIST_PAGE_URL = "https://registry.eq-earth.com/report/resource/PUBLIC/ERS_MEASUREMENT_STANDARD"
DETAIL_URL_TEMPLATE = (
    "https://registry.eq-earth.com/dataroom/ERS/ERS_MEASUREMENT_STANDARD/byIdentifier/{project_internal_id}"
)
RESOURCE_API_URL_TEMPLATE = (
    "https://optimal-gateway.apx.com/resource/resource/{project_internal_id}/form/"
    "DATAROOM_ERS_MEASUREMENT_STANDARD"
)
PROPONENTS_API_URL = "https://optimal-gateway.apx.com/legalentity/api/legalEntity/byIdentifier"
PROTOCOL_VERSION_API_URL_TEMPLATE = (
    "https://optimal-gateway.apx.com/resource/program/{program_code}/{program_version}/protocolVersion"
)
CREDITING_PERIODS_API_URL_TEMPLATE = (
    "https://optimal-gateway.apx.com/resource/protocol/{protocol_code}/{protocol_version}/"
    "creditingPeriods/{crediting_start_date}/{today_iso}"
)
PUBLIC_FILES_API_URL = "https://optimal-gateway.apx.com/fileRegistry/api/file/report/file/public"
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 5.0
DEFAULT_PROGRESS_REPORT_EVERY = 10


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os detalhes brutos dos projetos da Equitable Earth."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de projetos para testes.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Intervalo entre projetos. Padrao: {DEFAULT_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Quantidade de projetos entre pausas extras. Padrao: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=f"Pausa extra a cada lote de projetos. Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}.",
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
        help=f"Timeout por operacao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Sobrescreve arquivos de detalhe ja salvos para a mesma data.",
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


# Monta os caminhos de entrada e saida usados pelo script.
def build_paths(snapshot_date: str) -> tuple[Path, Path, Path]:
    root = Path(__file__).resolve().parents[4]
    list_path = (
        root / "data" / "project_standards" / "01_bronze" / "equitable_earth" / snapshot_date / "list" / "projects.json"
    )
    projects_dir = root / "data" / "project_standards" / "01_bronze" / "equitable_earth" / snapshot_date / "projects"
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


# Normaliza o valor para uso seguro em nomes de arquivo.
def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', "_", value).strip()
    return cleaned or "project"


# Resolve o identificador publico do projeto a partir dos dados disponiveis.
def resolve_project_public_id(project: dict[str, Any], index: int) -> str:
    return sanitize_filename(
        str(project.get("programAssignedIdentifier") or f"equitable_earth_project_{index}")
    )


# Grava o log consolidado de falhas da execucao.
def write_failure_log(errors_path: Path, snapshot_date: str, failures: list[dict[str, Any]]) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {
            "certificadora": "equitable_earth",
            "snapshot_date": snapshot_date,
            "script": "extract_project_details.py",
        },
        "updated_at": utc_now_iso(),
        "failure_count": len(failures),
        "failures": failures,
    }
    errors_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Le o log de falhas existente quando ele ja estiver salvo.
def read_failure_log(errors_path: Path) -> dict[str, Any]:
    if not errors_path.exists():
        return {}
    payload = json.loads(errors_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


# Acrescenta uma falha ao log operacional sem perder o historico atual.
def append_failure_entry(errors_path: Path, snapshot_date: str, entry: dict[str, Any]) -> None:
    payload = read_failure_log(errors_path)
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    failures.append(entry)
    write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=failures)


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers(*, include_tenant_header: bool = True, content_type: str | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if include_tenant_header:
        headers["apx_s"] = TENANT_CODE
    if content_type is not None:
        headers["Content-Type"] = content_type
    return headers


# Busca um payload JSON na fonte remota com as regras de resiliencia da integracao.
def fetch_json(
    url: str,
    *,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
    params: dict[str, Any] | None = None,
    data: bytes | None = None,
    method: str = "GET",
    headers: dict[str, str] | None = None,
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
            method=method,
            headers=headers or build_headers(),
            data=data,
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts_total:
                print(
                    f"429 Too Many Requests para {url}; aguardando {retry_sleep_seconds:.1f}s "
                    f"antes da tentativa {attempt + 1}/{attempts_total}"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Erro HTTP {exc.code} ao consultar {url}. Resposta: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar {url}: {exc}") from exc


# Busca o payload principal de detalhe do recurso.
def fetch_resource_detail(
    project_internal_id: str,
    *,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    payload = fetch_json(
        RESOURCE_API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_sleep_seconds=retry_sleep_seconds,
        headers=build_headers(),
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Resposta inesperada do detalhe EQE: era esperado um objeto JSON.")
    return payload


# Busca os proponentes publicos vinculados ao recurso.
def fetch_proponents(
    legal_entity_identifiers: list[str],
    *,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    if not legal_entity_identifiers:
        return {"legalEntities": []}
    return fetch_json(
        PROPONENTS_API_URL,
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_sleep_seconds=retry_sleep_seconds,
        params={"sourceSystemCode": TENANT_CODE},
        data=json.dumps({"identifiers": legal_entity_identifiers}).encode("utf-8"),
        method="POST",
        headers=build_headers(content_type="application/json"),
    )


# Busca as versoes de protocolo vinculadas ao recurso.
def fetch_protocol_versions(
    *,
    program_code: str,
    program_version: str,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> Any:
    return fetch_json(
        PROTOCOL_VERSION_API_URL_TEMPLATE.format(
            program_code=program_code,
            program_version=program_version,
        ),
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_sleep_seconds=retry_sleep_seconds,
        headers=build_headers(),
    )


# Busca os periodos de crediting vinculados ao recurso.
def fetch_crediting_periods(
    *,
    protocol_code: str,
    protocol_version: str,
    crediting_start_date: str,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> Any:
    return fetch_json(
        CREDITING_PERIODS_API_URL_TEMPLATE.format(
            protocol_code=protocol_code,
            protocol_version=protocol_version,
            crediting_start_date=crediting_start_date,
            today_iso=date.today().isoformat(),
        ),
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_sleep_seconds=retry_sleep_seconds,
        headers=build_headers(),
    )


# Busca os arquivos publicos vinculados ao recurso.
def fetch_public_files(
    *,
    src_account_id: str,
    project_internal_id: str,
    timeout: float,
    retry_attempts: int,
    retry_sleep_seconds: float,
) -> Any:
    return fetch_json(
        PUBLIC_FILES_API_URL,
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_sleep_seconds=retry_sleep_seconds,
        params={
            "$skip": 0,
            "$top": 20,
            "$count": "true",
            "srcResourceId": project_internal_id,
            "srcAccountId": src_account_id,
        },
        headers=build_headers(),
    )


# Extrai a referencia principal de protocolo do payload do recurso.
def extract_protocol_reference(resource_payload: dict[str, Any]) -> tuple[str | None, str | None]:
    inputs = resource_payload.get("inputs")
    if not isinstance(inputs, list):
        return None, None
    for resource_input in inputs:
        protocols = resource_input.get("protocols")
        if not isinstance(protocols, list):
            continue
        for protocol_entry in protocols:
            if not isinstance(protocol_entry, dict):
                continue
            protocol_version = protocol_entry.get("protocolVersion") or protocol_entry.get("protocol")
            if not isinstance(protocol_version, dict):
                continue
            code = protocol_version.get("code")
            version = protocol_version.get("version")
            if code and version:
                return str(code), str(version)
    return None, None


# Extrai a referencia principal de programa do payload do recurso.
def extract_program_reference(resource_payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    programs = resource_payload.get("programs")
    if not isinstance(programs, list) or not programs:
        return None, None, None
    program_entry = programs[0]
    if not isinstance(program_entry, dict):
        return None, None, None
    program_version = program_entry.get("programVersion")
    if isinstance(program_version, dict):
        return (
            str(program_version.get("code") or "") or None,
            str(program_version.get("version") or "") or None,
            str(program_entry.get("originalCreditingPeriodStartDate") or "") or None,
        )
    return None, None, str(program_entry.get("originalCreditingPeriodStartDate") or "") or None


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
    *,
    records: list[dict[str, Any]],
    projects_dir: Path,
    errors_path: Path,
    snapshot_date: str,
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
    write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=[])

    target_records = records[:limit] if limit is not None else records
    success_count = 0
    failure_count = 0
    skipped_count = 0
    started_at = time.perf_counter()

    for index, list_record in enumerate(target_records, start=1):
        project_public_id = resolve_project_public_id(list_record, index)
        project_internal_id = str(list_record.get("resourceIdentifier") or "").strip()
        if not project_internal_id:
            failure_count += 1
            append_failure_entry(
                errors_path=errors_path,
                snapshot_date=snapshot_date,
                entry={
                    "captured_at": utc_now_iso(),
                    "project_public_id": project_public_id,
                    "stage": "pre_validation",
                    "error_type": "RuntimeError",
                    "error_message": "Registro de lista sem resourceIdentifier.",
                    "list_data": list_record,
                },
            )
            completed_items = success_count + failure_count + skipped_count
            if completed_items % DEFAULT_PROGRESS_REPORT_EVERY == 0 or completed_items == len(target_records):
                print_progress_report(started_at=started_at, completed_items=completed_items, total_items=len(target_records))
            continue

        output_path = projects_dir / f"{project_public_id}.json"
        if not overwrite_existing and existing_output_is_valid(output_path, project_public_id):
            skipped_count += 1
            print(f"pulando projeto {project_public_id} ({index}/{len(target_records)}): detalhe ja salvo")
            completed_items = success_count + failure_count + skipped_count
            if completed_items % DEFAULT_PROGRESS_REPORT_EVERY == 0 or completed_items == len(target_records):
                print_progress_report(started_at=started_at, completed_items=completed_items, total_items=len(target_records))
            continue

        print(f"inicio download do projeto {project_public_id} ({index}/{len(target_records)})")
        try:
            resource_payload = fetch_resource_detail(
                project_internal_id=project_internal_id,
                timeout=timeout,
                retry_attempts=retry_attempts,
                retry_sleep_seconds=retry_sleep_seconds,
            )

            proponent_identifiers = [
                str(item.get("legalEntityIdentifier"))
                for item in resource_payload.get("proponents", [])
                if isinstance(item, dict) and item.get("legalEntityIdentifier")
            ]
            proponents_payload = fetch_proponents(
                proponent_identifiers,
                timeout=timeout,
                retry_attempts=retry_attempts,
                retry_sleep_seconds=retry_sleep_seconds,
            )

            program_code, program_version, crediting_start_date = extract_program_reference(resource_payload)
            protocol_code, protocol_version = extract_protocol_reference(resource_payload)

            protocol_versions_payload: Any = None
            if program_code and program_version:
                protocol_versions_payload = fetch_protocol_versions(
                    program_code=program_code,
                    program_version=program_version,
                    timeout=timeout,
                    retry_attempts=retry_attempts,
                    retry_sleep_seconds=retry_sleep_seconds,
                )

            crediting_periods_payload: Any = None
            if protocol_code and protocol_version and crediting_start_date:
                crediting_periods_payload = fetch_crediting_periods(
                    protocol_code=protocol_code,
                    protocol_version=protocol_version,
                    crediting_start_date=crediting_start_date,
                    timeout=timeout,
                    retry_attempts=retry_attempts,
                    retry_sleep_seconds=retry_sleep_seconds,
                )

            account = resource_payload.get("account")
            src_account_id = ""
            if isinstance(account, dict):
                src_account_id = str(account.get("srcAcctId") or "").strip()

            public_files_payload: Any = None
            if src_account_id:
                public_files_payload = fetch_public_files(
                    src_account_id=src_account_id,
                    project_internal_id=project_internal_id,
                    timeout=timeout,
                    retry_attempts=retry_attempts,
                    retry_sleep_seconds=retry_sleep_seconds,
                )

            payload = {
                "source": build_project_source(
                    carbon_standard="equitable_earth",
                    snapshot_date=snapshot_date,
                    project_public_id=project_public_id,
                    project_internal_id=project_internal_id,
                    project_url=DETAIL_URL_TEMPLATE.format(project_internal_id=project_internal_id),
                    extra_fields={
                        "resource_api_url": RESOURCE_API_URL_TEMPLATE.format(project_internal_id=project_internal_id),
                        "tenant_code_header": TENANT_CODE,
                        "program_code": PROGRAM_CODE,
                        "extraction_method": "public_resource_and_reporting_apis_with_apx_s_header",
                    },
                ),
                "list_data": list_record,
                "detail_data": {
                    "resource": resource_payload,
                    "proponents": proponents_payload,
                    "protocol_versions": protocol_versions_payload,
                    "crediting_periods": crediting_periods_payload,
                    "public_files": public_files_payload,
                },
            }
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            success_count += 1
            print(f"fim download do projeto {project_public_id} (resourceIdentifier={project_internal_id})")
        except Exception as exc:
            failure_count += 1
            print(f"falha no projeto {project_public_id}: {exc}", file=sys.stderr)
            append_failure_entry(
                errors_path=errors_path,
                snapshot_date=snapshot_date,
                entry={
                    "captured_at": utc_now_iso(),
                    "project_public_id": project_public_id,
                    "project_internal_id": project_internal_id,
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
            print(f"pausa de lote apos {index} projetos: aguardando {batch_sleep_seconds:.1f}s")
            time.sleep(batch_sleep_seconds)
        if sleep_seconds > 0 and index < len(target_records):
            time.sleep(sleep_seconds)

    return success_count, failure_count, skipped_count


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
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

    records = load_list_records(list_path)
    total_to_process = args.limit or len(records)

    print("Iniciando extracao de detalhes dos projetos da Equitable Earth")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"Lista de origem: {list_path}")
    print(f"Diretorio de saida: {projects_dir}")
    print(f"Arquivo de falhas: {errors_path}")
    print(f"URL publica da lista: {LIST_PAGE_URL}")
    print(f"Program code: {PROGRAM_CODE}")
    print(f"Header apx_s: {TENANT_CODE}")
    print(f"Sleep entre solicitacoes: {args.sleep_seconds:.1f}s")
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

    success_count, failure_count, skipped_count = process_projects(
        records=records,
        projects_dir=projects_dir,
        errors_path=errors_path,
        snapshot_date=snapshot_date,
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
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc