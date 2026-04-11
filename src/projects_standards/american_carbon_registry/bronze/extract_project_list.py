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
import re
import sys
import time
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib import error, parse, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_directory, unpack_archive


LIST_PAGE_URL = "https://acr2.apx.com/myModule/rpt/myrpt.asp?r=111"
BASE_URL = "https://acr2.apx.com"
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


# Decodifica o corpo HTTP respeitando o charset declarado ou usando fallbacks adequados para o legado APX.
def decode_response_body(body: bytes, charset: str | None) -> str:
    candidate_encodings: list[str] = []
    if charset:
        candidate_encodings.append(charset)
    candidate_encodings.extend(["utf-8", "cp1252", "latin-1"])

    tried: set[str] = set()
    for encoding in candidate_encodings:
        normalized = encoding.lower()
        if normalized in tried:
            continue
        tried.add(normalized)
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue

    return body.decode("utf-8", errors="replace")


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa a lista bruta de projetos da American Carbon Registry.")
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS, help=f"Intervalo entre paginas. Padrao: {DEFAULT_SLEEP_SECONDS}.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Quantidade de paginas entre pausas extras. Padrao: {DEFAULT_BATCH_SIZE}.")
    parser.add_argument("--batch-sleep-seconds", type=float, default=DEFAULT_BATCH_SLEEP_SECONDS, help=f"Pausa extra a cada lote de paginas. Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}.")
    parser.add_argument("--retry-attempts", type=int, default=DEFAULT_RETRY_ATTEMPTS, help=f"Tentativas adicionais quando houver 429. Padrao: {DEFAULT_RETRY_ATTEMPTS}.")
    parser.add_argument("--retry-sleep-seconds", type=float, default=DEFAULT_RETRY_SLEEP_SECONDS, help=f"Espera entre tentativas apos 429. Padrao: {DEFAULT_RETRY_SLEEP_SECONDS}.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.")
    parser.add_argument("--max-pages", type=int, default=None, help="Limita a quantidade de paginas para testes.")
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
    output_path = root / "data" / "project_standards" / "01_bronze" / "american_carbon_registry" / snapshot_date / "list" / "projects.json"
    errors_path = Path(__file__).resolve().parent / "logs" / f"extract_project_list_failures_{snapshot_date}.json"
    return output_path, errors_path


# Grava o log consolidado de falhas da execucao.
def write_failure_log(errors_path: Path, snapshot_date: str, failures: list[dict[str, Any]]) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {"certificadora": "american_carbon_registry", "snapshot_date": snapshot_date, "script": "extract_project_list.py"},
        "updated_at": utc_now_iso(),
        "failure_count": len(failures),
        "failures": failures,
    }
    errors_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers(*, referer: str | None = None, content_type: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if referer:
        headers["Referer"] = referer
    if content_type:
        headers["Content-Type"] = content_type
    return headers


# Busca um conteudo textual na fonte remota com as regras de resiliencia da integracao.
def fetch_text(url: str, *, timeout: float, retry_attempts: int, retry_sleep_seconds: float, data: bytes | None = None, referer: str | None = None) -> str:
    attempts_total = retry_attempts + 1
    attempt = 1
    while True:
        req = request.Request(
            url=url,
            method="POST" if data is not None else "GET",
            headers=build_headers(referer=referer, content_type="application/x-www-form-urlencoded" if data is not None else None),
            data=data,
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                body = response.read()
                return decode_response_body(body, response.headers.get_content_charset())
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts_total:
                print(
                    f"429 Too Many Requests na ACR; aguardando {retry_sleep_seconds:.1f}s "
                    f"antes da tentativa {attempt + 1}/{attempts_total}"
                )
                time.sleep(retry_sleep_seconds)
                attempt += 1
                continue
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Erro HTTP {exc.code} ao consultar {url}. Resposta: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar {url}: {exc}") from exc


# Normaliza espacos e texto auxiliar antes do parsing.
def normalize_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


# Extrai a quantidade total de paginas a partir do HTML da lista.
def extract_total_pages(page_html: str) -> int | None:
    match = re.search(r"Page Number between 1 and (\d+)", page_html, re.IGNORECASE)
    return int(match.group(1)) if match else None


# Extrai as linhas tabulares da lista de projetos a partir do HTML.
def extract_rows(page_html: str) -> tuple[list[str], list[dict[str, Any]]]:
    row_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.IGNORECASE | re.DOTALL)
    headers: list[str] | None = None
    projects: list[dict[str, Any]] = []
    for row_html in row_matches:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.IGNORECASE | re.DOTALL)
        if not cells:
            continue
        cleaned_cells = [normalize_text(cell) for cell in cells]
        if headers is None and "Project ID" in cleaned_cells and "Project Name" in cleaned_cells:
            headers = cleaned_cells
            continue
        if headers is None or len(cells) != len(headers):
            continue

        record: dict[str, Any] = {}
        for header, cell_html, cell_text in zip(headers, cells, cleaned_cells):
            record[header] = cell_text
            link_match = re.search(r'href="([^"]+)"', cell_html, re.IGNORECASE)
            if link_match:
                record[f"{header} URL"] = parse.urljoin(BASE_URL, link_match.group(1))
        if record.get("Project ID") and record.get("Project Name"):
            detail_url = record.get("Project Name URL")
            if detail_url:
                id_match = re.search(r"id1=(\d+)", detail_url)
                if id_match:
                    record["project_internal_id"] = id_match.group(1)
            projects.append(record)

    if headers is None:
        raise RuntimeError("Nao foi possivel localizar o cabecalho da tabela de projetos da ACR.")
    return headers, projects


# Busca o HTML de uma pagina de lista ou detalhe.
def fetch_page_html(page_number: int, *, timeout: float, retry_attempts: int, retry_sleep_seconds: float) -> str:
    if page_number == 1:
        return fetch_text(LIST_PAGE_URL, timeout=timeout, retry_attempts=retry_attempts, retry_sleep_seconds=retry_sleep_seconds)
    body = parse.urlencode(
        {
            "X999myquery": "",
            "X999tablenumber": "2",
            "X999csv": "",
            "X999sort": "",
            "X999action": "search",
            "X999actionfield": "",
            "X999field": "",
            "X999paging": "On",
            "X999whichpage": str(page_number),
        }
    ).encode("utf-8")
    return fetch_text(LIST_PAGE_URL, timeout=timeout, retry_attempts=retry_attempts, retry_sleep_seconds=retry_sleep_seconds, data=body, referer=LIST_PAGE_URL)


# Percorre a fonte paginada e acumula todos os projetos da lista.
def fetch_all_projects(*, sleep_seconds: float, batch_size: int, batch_sleep_seconds: float, timeout: float, retry_attempts: int, retry_sleep_seconds: float, max_pages: int | None) -> dict[str, Any]:
    all_projects: list[dict[str, Any]] = []
    page_headers: list[str] | None = None
    total_pages: int | None = None
    page_number = 1

    while True:
        if max_pages is not None and page_number > max_pages:
            break
        print(f"Iniciando consulta da pagina {page_number}")
        page_html = fetch_page_html(page_number, timeout=timeout, retry_attempts=retry_attempts, retry_sleep_seconds=retry_sleep_seconds)
        current_total_pages = extract_total_pages(page_html)
        if total_pages is None:
            total_pages = current_total_pages
        headers, page_projects = extract_rows(page_html)
        if page_headers is None:
            page_headers = headers
        all_projects.extend(page_projects)
        print(f"Pagina {page_number}: coletados {len(page_projects)} projetos (acumulado {len(all_projects)})")
        if total_pages is not None and page_number >= total_pages:
            break
        if not page_projects:
            break
        if batch_size > 0 and batch_sleep_seconds > 0 and page_number % batch_size == 0:
            print(f"pausa extra de {batch_sleep_seconds:.1f}s apos {page_number} paginas")
            time.sleep(batch_sleep_seconds)
        page_number += 1
        if sleep_seconds > 0:
            print(f"Aguardando {sleep_seconds:.1f}s antes da proxima pagina")
            time.sleep(sleep_seconds)

    return {
        "source": {
            "page_url": LIST_PAGE_URL,
            "extraction_method": "acr_public_html_report_table",
            "project_identifier_mapping": {
                "project_public_id": "Project ID",
                "project_internal_id": "project_internal_id",
            },
        },
        "retrieved_at": utc_now_iso(),
        "headers": page_headers or [],
        "total_pages": total_pages,
        "projects": all_projects,
    }


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)
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

    print("Iniciando extracao da lista de projetos da American Carbon Registry")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"URL da pagina: {LIST_PAGE_URL}")
    print(f"Sleep entre paginas: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada lote: {args.batch_sleep_seconds:.1f}s a cada {args.batch_size} paginas")
    print(f"Retry em 429: {args.retry_attempts} tentativas adicionais com espera de {args.retry_sleep_seconds:.1f}s")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    if args.max_pages is not None:
        print(f"Modo de teste ativado: max_pages={args.max_pages}")
    print(f"Arquivo de saida: {output_path}")
    print(f"Arquivo de falhas: {errors_path}")

    try:
        payload = fetch_all_projects(
            sleep_seconds=args.sleep_seconds,
            batch_size=args.batch_size,
            batch_sleep_seconds=args.batch_sleep_seconds,
            timeout=args.timeout,
            retry_attempts=args.retry_attempts,
            retry_sleep_seconds=args.retry_sleep_seconds,
            max_pages=args.max_pages,
        )
    except Exception as exc:
        write_failure_log(
            errors_path=errors_path,
            snapshot_date=snapshot_date,
            failures=[{"captured_at": utc_now_iso(), "stage": "list_download", "error_type": type(exc).__name__, "error_message": str(exc)}],
        )
        raise

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Arquivo salvo em: {output_path}")
    print(f"Total de projetos salvos: {len(payload['projects'])}")
    if payload.get("total_pages") is not None:
        print(f"Total de paginas detectado: {payload['total_pages']}")
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
