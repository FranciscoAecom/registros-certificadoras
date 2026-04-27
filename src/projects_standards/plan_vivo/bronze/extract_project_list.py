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
import re
import sys
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib import error, parse, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_snapshot_bundle, unpack_snapshot_bundle


PAGE_URL = "https://www.planvivo.org/projects/carbon?q="
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
DETAIL_PATH_PATTERN = re.compile(r"^/projects/([^/?#]+)$")


class PlanVivoProjectsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.projects_by_url: dict[str, dict[str, Any]] = {}
        self.current_project_url: str | None = None
        self.capture_field: str | None = None
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        class_name = attributes.get("class") or ""
        if tag == "a":
            href = attributes.get("href") or ""
            parsed_href = parse.urlparse(parse.urljoin(PAGE_URL, href))
            match = DETAIL_PATH_PATTERN.match(parsed_href.path)
            if match:
                project_url = parsed_href._replace(query="", fragment="").geturl()
                self.current_project_url = project_url
                self.projects_by_url.setdefault(project_url, {"project_slug": match.group(1), "project_url": project_url, "project_title": None, "summary": None, "tags": []})
        if self.current_project_url is None:
            return
        if tag == "h3":
            self.capture_field = "project_title"
            self.text_parts = []
        elif tag == "p" and "leading-snug" in class_name:
            self.capture_field = "summary"
            self.text_parts = []
        elif tag == "span" and "tag" in class_name.split():
            self.capture_field = "tags"
            self.text_parts = []

    def handle_data(self, data: str) -> None:
        if self.capture_field is not None:
            self.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture_field is None or self.current_project_url is None or tag not in {"h3", "p", "span"}:
            return
        value = " ".join(part.strip() for part in self.text_parts if part.strip()).strip()
        self.text_parts = []
        if not value:
            self.capture_field = None
            return
        project = self.projects_by_url[self.current_project_url]
        if self.capture_field == "tags":
            if value not in project["tags"]:
                project["tags"].append(value)
        else:
            project[self.capture_field] = value
        self.capture_field = None

    def get_projects(self) -> list[dict[str, Any]]:
        return list(self.projects_by_url.values())


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa a lista bruta de projetos de carbono da Plan Vivo.")
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS, help=f"Intervalo entre paginas. Padrao: {DEFAULT_SLEEP_SECONDS}.")
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
    output_path = root / "data" / "project_standards" / "01_bronze" / "plan_vivo" / snapshot_date / "list" / "projects.json"
    errors_path = Path(__file__).resolve().parent / "logs" / f"extract_project_list_failures_{snapshot_date}.json"
    return output_path, errors_path


# Grava o log consolidado de falhas da execucao.
def write_failure_log(errors_path: Path, snapshot_date: str, failures: list[dict[str, Any]]) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {"certificadora": "plan_vivo", "snapshot_date": snapshot_date, "script": "extract_project_list.py"},
        "updated_at": utc_now_iso(),
        "failure_count": len(failures),
        "failures": failures,
    }
    errors_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"}


# Busca o HTML de uma pagina de lista ou detalhe.
def fetch_page_html(page_url: str, timeout: float, retry_attempts: int, retry_sleep_seconds: float) -> str:
    attempts_total = retry_attempts + 1
    attempt = 1
    while True:
        req = request.Request(url=page_url, method="GET", headers=build_headers())
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
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
            raise RuntimeError(f"Erro HTTP {exc.code} ao consultar a Plan Vivo. Resposta: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar a Plan Vivo: {exc}") from exc


# Extrai a URL da proxima pagina quando houver paginacao.
def extract_next_page_url(page_html: str) -> str | None:
    match = re.search(r'<link\s+rel="next"\s+href="([^"]+)"', page_html, re.IGNORECASE)
    return parse.urljoin(PAGE_URL, match.group(1)) if match else None


# Interpreta o conteudo da lista e retorna os projetos encontrados.
def parse_projects(page_html: str) -> list[dict[str, Any]]:
    parser = PlanVivoProjectsParser()
    parser.feed(page_html)
    projects = [project for project in parser.get_projects() if project.get("project_title") and "Certified Carbon" in project.get("tags", [])]
    if not projects:
        raise RuntimeError("Nenhum projeto foi encontrado na pagina da Plan Vivo.")
    return projects


# Percorre a fonte paginada e acumula todos os projetos da lista.
def fetch_all_projects(sleep_seconds: float, batch_size: int, batch_sleep_seconds: float, timeout: float, retry_attempts: int, retry_sleep_seconds: float, max_pages: int | None) -> dict[str, Any]:
    all_projects: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    visited_page_urls: list[str] = []
    page_number = 1
    current_page_url: str | None = PAGE_URL

    while current_page_url is not None:
        if max_pages is not None and page_number > max_pages:
            break
        print(f"Iniciando consulta da pagina {page_number}: {current_page_url}")
        page_html = fetch_page_html(page_url=current_page_url, timeout=timeout, retry_attempts=retry_attempts, retry_sleep_seconds=retry_sleep_seconds)
        page_projects = parse_projects(page_html)
        new_projects = 0
        for project in page_projects:
            project_url = str(project["project_url"])
            if project_url in seen_urls:
                continue
            seen_urls.add(project_url)
            all_projects.append(project)
            new_projects += 1
        visited_page_urls.append(current_page_url)
        print(f"Pagina {page_number}: coletados {new_projects} projetos novos (acumulado {len(all_projects)})")
        if max_pages is not None and page_number >= max_pages:
            break
        next_page_url = extract_next_page_url(page_html)
        if next_page_url is None:
            break
        if batch_size > 0 and batch_sleep_seconds > 0 and page_number % batch_size == 0:
            print(f"pausa extra de {batch_sleep_seconds:.1f}s apos {page_number} paginas")
            time.sleep(batch_sleep_seconds)
        page_number += 1
        current_page_url = next_page_url
        if sleep_seconds > 0:
            print(f"Aguardando {sleep_seconds:.1f}s antes da proxima pagina")
            time.sleep(sleep_seconds)

    payload: dict[str, Any] = {
        "source": {
            "page_url": PAGE_URL,
            "page_urls": visited_page_urls,
            "project_identifier_mapping": {"project_public_id": "project_slug", "project_internal_id": "project_slug"},
            "extraction_method": "html_pagination_and_project_cards",
        },
        "retrieved_at": utc_now_iso(),
        "projects": all_projects,
    }
    if max_pages is not None:
        payload["partial"] = True
    return payload


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)
    if args.max_pages is not None and args.max_pages <= 0:
        raise SystemExit("--max-pages deve ser maior que zero.")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size deve ser maior que zero.")
    if args.retry_attempts < 0:
        raise SystemExit("--retry-attempts nao pode ser negativo.")
    output_path, errors_path = build_paths(snapshot_date)

    # Descompacta o snapshot da data solicitada se estiver em ZIP simples ou bundle core+spatial
    snapshot_dir = output_path.parent.parent
    zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
    core_zip_path = snapshot_dir.parent / f"{snapshot_dir.name}_core.zip"
    core_part_paths = list(snapshot_dir.parent.glob(f"{snapshot_dir.name}_core_*.zip"))
    if not snapshot_dir.exists() and (zip_path.exists() or core_zip_path.exists() or core_part_paths):
        unpack_snapshot_bundle(snapshot_dir.parent, snapshot_dir.name, label="bronze", step=1, total=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=[])
    print("Iniciando extracao da lista de projetos da Plan Vivo")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"URL da pagina inicial: {PAGE_URL}")
    print(f"Sleep entre paginas: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada lote: {args.batch_sleep_seconds:.1f}s a cada {args.batch_size} paginas")
    print(f"Retry em 429: {args.retry_attempts} tentativas adicionais com espera de {args.retry_sleep_seconds:.1f}s")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    if args.max_pages is not None:
        print(f"Modo de teste ativado: max_pages={args.max_pages}")
    print(f"Arquivo de saida: {output_path}")
    print(f"Arquivo de falhas: {errors_path}")
    try:
        payload = fetch_all_projects(sleep_seconds=args.sleep_seconds, batch_size=args.batch_size, batch_sleep_seconds=args.batch_sleep_seconds, timeout=args.timeout, retry_attempts=args.retry_attempts, retry_sleep_seconds=args.retry_sleep_seconds, max_pages=args.max_pages)
    except Exception as exc:
        write_failure_log(errors_path=errors_path, snapshot_date=snapshot_date, failures=[{"captured_at": utc_now_iso(), "stage": "list_download", "error_type": type(exc).__name__, "error_message": str(exc)}])
        raise
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Arquivo salvo em: {output_path}")
    print(f"Total de projetos salvos: {len(payload['projects'])}")
    print("Execucao finalizada em modo parcial" if payload.get("partial") else "Execucao finalizada com sucesso")

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
