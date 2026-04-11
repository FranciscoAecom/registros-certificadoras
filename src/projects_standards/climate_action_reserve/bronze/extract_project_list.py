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
import csv
import json
import re
import sys
import time
from datetime import UTC, datetime
from html import unescape
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib import error, parse, request

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.projects_standards.shared.archive_data import pack_directory, unpack_archive


PAGE_URL = "https://thereserve2.apx.com/myModule/rpt/myrpt.asp?r=111"
BASE_URL = "https://thereserve2.apx.com"
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_TIMEOUT_SECONDS = 30.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa a lista bruta de projetos da Climate Action Reserve."
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
            "Pausa entre a carga da pagina e o download do CSV. "
            f"Padrao: {DEFAULT_SLEEP_SECONDS}."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout por requisicao em segundos. Padrao: {DEFAULT_TIMEOUT_SECONDS}.",
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
    return (
        root
        / "data"
        / "project_standards"
        / "01_bronze"
        / "climate_action_reserve"
        / snapshot_date
        / "list"
        / "projects.json"
    )


# Monta o opener HTTP usado pela integracao.
def build_opener() -> request.OpenerDirector:
    # A exportacao depende de sessao, por isso usamos um opener com cookies.
    cookie_jar = CookieJar()
    return request.build_opener(request.HTTPCookieProcessor(cookie_jar))


# Busca o HTML de uma pagina de lista ou detalhe.
def fetch_page_html(opener: request.OpenerDirector, timeout: float) -> str:
    req = request.Request(
        url=PAGE_URL,
        method="GET",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    try:
        with opener.open(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erro HTTP {exc.code} ao carregar a pagina da CAR. Resposta: {details}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de rede ao carregar a pagina da CAR: {exc}") from exc


# Extrai os valores relevantes do conteudo informado.
def extract_download_form(page_html: str) -> tuple[str, dict[str, str]]:
    # A pagina entrega um formulario nativo de exportacao do relatorio em CSV.
    form_match = re.search(
        r'<FORM id="frmDownload".*?ACTION="([^"]+)".*?>(.*?)</FORM>',
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    if not form_match:
        raise RuntimeError("Nao foi possivel localizar o formulario de download da CAR.")

    action = unescape(form_match.group(1))
    form_html = form_match.group(2)

    inputs = re.findall(
        r'<INPUT[^>]*name="([^"]+)"[^>]*value\s*=\s*"([^"]*)"',
        form_html,
        flags=re.IGNORECASE,
    )
    if not inputs:
        raise RuntimeError("Nao foi possivel extrair os campos do formulario de download.")

    form_data = {name: unescape(value) for name, value in inputs}
    return action, form_data


# Extrai a contagem total de projetos exibida pela fonte.
def extract_total_count(page_html: str) -> int | None:
    match = re.search(r"1\s*-\s*50\s*:\s*(\d+)", page_html)
    if not match:
        return None
    return int(match.group(1))


# Executa uma etapa auxiliar do fluxo principal do script.
def download_csv(
    opener: request.OpenerDirector,
    action: str,
    form_data: dict[str, str],
    timeout: float,
) -> str:
    # Em vez de raspar a tabela HTML, reutilizamos a exportacao CSV oficial da CAR.
    export_url = parse.urljoin(BASE_URL, action)
    encoded_body = parse.urlencode(form_data).encode("utf-8")
    req = request.Request(
        url=export_url,
        data=encoded_body,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": PAGE_URL,
            "Origin": BASE_URL,
            "Accept": "text/csv,text/plain,*/*",
        },
    )

    try:
        with opener.open(req, timeout=timeout) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erro HTTP {exc.code} ao baixar o CSV da CAR. Resposta: {details}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de rede ao baixar o CSV da CAR: {exc}") from exc


# Interpreta os dados informados e retorna a estrutura normalizada.
def parse_csv_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(csv_text.splitlines())
    return [dict(row) for row in reader]


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)
    output_path = build_output_path(snapshot_date)

    # Descompacta o snapshot da data solicitada se estiver zipado
    snapshot_dir = output_path.parent.parent
    zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
    if not snapshot_dir.exists() and zip_path.exists():
        unpack_archive(zip_path, label="bronze", step=1, total=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Iniciando extracao da lista de projetos da Climate Action Reserve")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"URL da pagina: {PAGE_URL}")
    print(f"Sleep entre pagina e export: {max(0.0, args.sleep_seconds):.1f}s")
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    print(f"Arquivo de saida: {output_path}")

    opener = build_opener()

    print("Carregando pagina da CAR para obter sessao e formulario de export")
    page_html = fetch_page_html(opener=opener, timeout=args.timeout)
    total_count = extract_total_count(page_html)
    action, form_data = extract_download_form(page_html)
    export_url = parse.urljoin(BASE_URL, action)

    print(f"Formulario de export localizado: {export_url}")
    if total_count is not None:
        print(f"Total informado na pagina: {total_count}")

    if args.sleep_seconds > 0:
        print(
            f"Aguardando {max(0.0, args.sleep_seconds):.1f}s antes do download do CSV"
        )
        time.sleep(max(0.0, args.sleep_seconds))

    print("Baixando CSV nativo da CAR")
    csv_text = download_csv(
        opener=opener,
        action=action,
        form_data=form_data,
        timeout=args.timeout,
    )

    print("Convertendo CSV para estrutura JSON")
    # O CSV e convertido para lista de dicionarios para seguir o padrao do projeto.
    projects = parse_csv_rows(csv_text)

    payload: dict[str, Any] = {
        "source": {
            "page_url": PAGE_URL,
            "export_url": export_url,
            "project_identifier_mapping": {
                "project_public_id": "Project ID",
                "project_internal_id": "numeric_suffix(Project ID)",
            },
        },
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "projects": projects,
    }
    if total_count is not None:
        payload["total_count"] = total_count

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Arquivo salvo em: {output_path}")
    print(f"Total de projetos salvos: {len(projects)}")
    if total_count is not None and total_count != len(projects):
        print(
            "aviso: total salvo difere do total exibido na pagina "
            f"({len(projects)} vs {total_count})",
            file=sys.stderr,
        )
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
