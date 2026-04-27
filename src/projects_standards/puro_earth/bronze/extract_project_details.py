# Objetivo do script:
# Ler a lista bruta de uma data especifica, consultar o detalhe de cada projeto e salvar um JSON bronze por projeto.
# Processo:
# 1. Ler argumentos CLI (--date, --limit, parametros de ritmo e retry).
# 2. Descompactar o snapshot se estiver salvo em ZIP simples ou bundle core+spatial.
# 3. Carregar lista de projetos do snapshot da data informada.
# 4. Identificar projetos pendentes (sem arquivo de detalhe ou com --force).
# 5. Exibir cabecalho com parametros da execucao.
# 6. Para cada projeto, consultar o endpoint de detalhe da certificadora.
# 7. Montar payload com source, list_data e detail_data.
# 8. Salvar um JSON por projeto no diretorio projects/ do snapshot.
# 9. Exibir progresso a cada 10 projetos (percentual e tempo restante).
# 10. Registrar falhas individuais sem interromper a execucao.
# 11. Exibir resumo final e gravar log de falhas se houver.
# 12. Compactar o snapshot em bundle core + partes espaciais quando aplicavel.


import argparse
import json
import re
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_snapshot_bundle, unpack_snapshot_bundle


PAGE_URL = "https://registry.puro.earth/projects"
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_SLEEP_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_SLEEP_SECONDS = 5.0
DEFAULT_PROGRESS_REPORT_EVERY = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
TRANSACTIONS_MARKER = r'\"transactions\":['


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa e estrutura os detalhes dos projetos da Puro.earth."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument("--limit", type=int, default=None, help="Limita o numero de projetos para teste.")
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
        help=f"Quantidade de downloads antes da pausa extra. Padrao: {DEFAULT_BATCH_SIZE}.",
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
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
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
    list_path = root / "data" / "project_standards" / "01_bronze" / "puro_earth" / snapshot_date / "list" / "projects.json"
    projects_dir = root / "data" / "project_standards" / "01_bronze" / "puro_earth" / snapshot_date / "projects"
    errors_path = Path(__file__).resolve().parent / "logs" / f"extract_project_details_failures_{snapshot_date}.json"
    return list_path, projects_dir, errors_path


# Grava o log consolidado de falhas da execucao.
def write_failure_log(errors_path: Path, snapshot_date: str, failures: list[dict[str, Any]]) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {"certificadora": "puro_earth", "snapshot_date": snapshot_date, "script": "extract_project_details.py"},
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
        project_id = project.get("projectId")
        if not project_id:
            print(
                f"aviso: projeto na posicao {index} sem projectId, ignorando",
                file=sys.stderr,
            )
            continue
        cleaned_projects.append(project)

    return cleaned_projects


# Busca os dados necessarios na fonte remota.
def fetch_project_html(project_id: str, timeout: float, retry_attempts: int, retry_sleep_seconds: float) -> str:
    project_url = f"{PAGE_URL}/{project_id}"
    attempts_total = retry_attempts + 1
    attempt = 1
    while True:
        req = request.Request(
            url=project_url,
            method="GET",
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": PAGE_URL,
            },
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts_total:
                print(
                    f"429 Too Many Requests para {project_id}; aguardando {retry_sleep_seconds:.1f}s "
                    f"antes da tentativa {attempt + 1}/{attempts_total}"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Erro HTTP {exc.code} ao consultar o projeto {project_id}. Resposta: {details}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar o projeto {project_id}: {exc}") from exc


# Interpreta o HTML do detalhe e organiza os blocos principais do projeto.
def parse_detail_html(page_html: str) -> dict[str, Any]:
    # O detalhe mistura informacoes renderizadas no HTML e dados embutidos do frontend.
    return {
        "project_name": _extract_first_match(page_html, r"<h1[^>]*>(.*?)</h1>"),
        "project_overview": _extract_project_overview(page_html),
        "credits_summary": _extract_credits_summary(page_html),
        "transactions": _extract_transactions(page_html),
        "documents": _extract_documents(page_html),
    }


# Executa uma etapa auxiliar do fluxo principal do script.
def _extract_project_overview(page_html: str) -> dict[str, Any]:
    # O overview e apresentado como pares rotulo/valor na area principal da pagina.
    overview: dict[str, Any] = {}
    matches = re.findall(
        r'<p class="text-sm font-medium text-neutral-50">(.*?)</p><div class="text-lg font-medium">(.*?)</div>',
        page_html,
        re.IGNORECASE | re.DOTALL,
    )

    for bronze_label, bronze_value in matches:
        label = _normalize_text(_strip_tags(bronze_label)).lower()
        value_html = bronze_value.strip()

        if label == "project identifier":
            overview["project_identifier"] = _normalize_text(_strip_tags(value_html))
        elif label == "supplier":
            overview["supplier"] = _normalize_text(_strip_tags(value_html))
        elif label == "methodology":
            overview["methodology"] = {
                "name": _extract_first_match(value_html, r"<a[^>]*>(.*?)</a>") or _normalize_text(_strip_tags(value_html)),
                "url": _extract_href(value_html),
            }
        elif label == "puro standard general rules":
            overview["general_rules"] = {
                "version": _extract_first_match(value_html, r"<a[^>]*>(.*?)</a>")
                or _normalize_text(_strip_tags(value_html)),
                "url": _extract_href(value_html),
            }
        elif label == "crediting period":
            overview["crediting_period"] = _normalize_text(_strip_tags(value_html))
        elif label == "host country":
            overview["host_country"] = _normalize_text(_strip_tags(value_html))
        elif label == "sustainable development goals":
            overview["sustainable_development_goals"] = re.findall(
                r'alt="([^"]+)"',
                value_html,
                re.IGNORECASE,
            )

    return overview


# Executa uma etapa auxiliar do fluxo principal do script.
def _extract_credits_summary(page_html: str) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    patterns = {
        "issued_corcs": r'Issued CORCs.*?<div class="text-\[32px\] font-medium leading-9">([^<]+)</div>',
        "retired_corcs": r'Retired CORCs</div><div class="text-\[32px\] font-medium leading-9">([^<]+)</div>',
    }
    for key, pattern in patterns.items():
        value = _extract_first_match(page_html, pattern)
        if value is not None:
            summary[key] = value
    return summary


# Executa uma etapa auxiliar do fluxo principal do script.
def _extract_transactions(page_html: str) -> list[dict[str, Any]]:
    # As transacoes aparecem em um payload JSON embutido no HTML do detalhe.
    start = page_html.find(TRANSACTIONS_MARKER)
    if start == -1:
        return []

    in_string = False
    escape = False
    level = 0
    end: int | None = None

    for index, char in enumerate(page_html[start:], start=start):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "[":
            level += 1
        elif char == "]":
            level -= 1
            if level == 0:
                end = index + 1
                break

    if end is None:
        return []

    bronze_payload = page_html[start:end]
    decoded_payload = bronze_payload.encode("utf-8").decode("unicode_escape")
    prefix = '"transactions":'
    if decoded_payload.startswith(prefix):
        decoded_payload = decoded_payload[len(prefix) :]

    transactions = json.loads(decoded_payload)
    if not isinstance(transactions, list):
        return []
    return transactions


# Executa uma etapa auxiliar do fluxo principal do script.
def _extract_documents(page_html: str) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    matches = re.findall(
        r'<a href="(https://puro\.earth/odoo/documents/[^"]+)"[^>]*>.*?<div[^>]*>([^<]+)<div',
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    for url, filename in matches:
        documents.append(
            {
                "url": url,
                "filename": _normalize_text(filename),
            }
        )
    return _dedupe_documents(documents)


# Executa uma etapa auxiliar do fluxo principal do script.
def _extract_href(value_html: str) -> str | None:
    match = re.search(r'href="([^"]+)"', value_html, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


# Executa uma etapa auxiliar do fluxo principal do script.
def _extract_first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _normalize_text(_strip_tags(match.group(1)))


# Remove tags HTML preservando apenas o texto relevante.
def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


# Normaliza o texto extraido do HTML para uso no payload final.
def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


# Remove documentos duplicados preservando a ordem original.
def _dedupe_documents(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for document in documents:
        url = document.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(document)
    return deduped


# Salva o detalhe bruto do projeto no diretorio de destino.
def save_project_details(projects_dir: Path, project_id: str, payload: dict[str, Any]) -> None:
    output_path = projects_dir / f"{project_id}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Verifica se o arquivo de saida existente ja pode ser reaproveitado.
def existing_output_is_valid(output_path: Path, project_id: str) -> bool:
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
    return isinstance(source, dict) and isinstance(detail_data, dict) and source.get("project_public_id") == project_id


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

    # Descompacta o snapshot se estiver em ZIP simples ou bundle core+spatial
    snapshot_dir = list_path.parent.parent
    zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
    unpacked = False
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
    write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=[])

    print("Iniciando extracao de detalhes de projetos da Puro.earth")
    print(f"Lista carregada de: {list_path}")
    print(f"Total detectado na lista: {total_detected}")
    print(f"Total a processar nesta execucao: {total_to_process}")
    print(f"URL base de detalhe: {PAGE_URL}/<projectId>")
    print(f"Pausa entre projetos: {args.sleep_seconds} segundos")
    print(
        "Pausa extra a cada bloco: "
        f"{args.batch_sleep_seconds} segundos a cada {args.batch_size} projetos"
    )
    print(
        f"Retry em 429: {args.retry_attempts} tentativas adicionais com espera de "
        f"{args.retry_sleep_seconds:.1f}s"
    )
    print(f"Arquivo de falhas: {errors_path}")
    print(f"Diretorio de saida: {projects_dir}")

    success_count = 0
    failure_count = 0
    skipped_count = 0
    started_at = time.perf_counter()

    for index, list_project in enumerate(projects, start=1):
        project_id = str(list_project["projectId"]).strip()
        project_url = f"{PAGE_URL}/{project_id}"
        output_path = projects_dir / f"{project_id}.json"
        if not args.overwrite_existing and existing_output_is_valid(output_path, project_id):
            skipped_count += 1
            print(f"pulando projeto {project_id} ({index}/{total_to_process}): detalhe ja salvo")
            completed_items = success_count + failure_count + skipped_count
            if completed_items % DEFAULT_PROGRESS_REPORT_EVERY == 0 or completed_items == total_to_process:
                print_progress_report(started_at=started_at, completed_items=completed_items, total_items=total_to_process)
            continue
        print(f"inicio download do projeto {project_id} ({index}/{total_to_process})")

        try:
            page_html = fetch_project_html(
                project_id=project_id,
                timeout=args.timeout,
                retry_attempts=args.retry_attempts,
                retry_sleep_seconds=args.retry_sleep_seconds,
            )
            detail_data = parse_detail_html(page_html)
            # O bronze segue o padrao comum do projeto para facilitar a transformacao depois.
            payload = {
                "source": build_project_source(
                    carbon_standard="puro_earth",
                    snapshot_date=snapshot_date,
                    project_public_id=project_id,
                    project_internal_id=project_id,
                    project_url=project_url,
                ),
                "list_data": list_project,
                "detail_data": detail_data,
            }
            save_project_details(projects_dir=projects_dir, project_id=project_id, payload=payload)
            success_count += 1
            print(f"fim download do projeto {project_id}")
        except Exception as exc:
            failure_count += 1
            print(f"falha no projeto {project_id}: {exc}", file=sys.stderr)
            append_failure_entry(
                errors_path=errors_path,
                snapshot_date=snapshot_date,
                entry={
                    "captured_at": utc_now_iso(),
                    "project_public_id": project_id,
                    "project_internal_id": project_id,
                    "project_url": project_url,
                    "stage": "project_download",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "list_data": list_project,
                    "traceback": traceback.format_exc(),
                },
            )

        completed_items = success_count + failure_count + skipped_count
        if completed_items % DEFAULT_PROGRESS_REPORT_EVERY == 0 or completed_items == total_to_process:
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

    # Compacta o snapshot em bundle core + partes espaciais quando aplicavel
    pack_snapshot_bundle(snapshot_dir, label="bronze", step=1, total=1)

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc