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
import time
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
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
PROJECTS_MARKER = r'[{\"projectId\"'


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa a lista bruta de projetos da Puro.earth."
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
        help=f"Parametro mantido por padrao do projeto. Padrao: {DEFAULT_SLEEP_SECONDS}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Quantidade de paginas entre pausas extras. Padrao: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--batch-sleep-seconds",
        type=float,
        default=DEFAULT_BATCH_SLEEP_SECONDS,
        help=f"Pausa extra a cada lote de paginas. Padrao: {DEFAULT_BATCH_SLEEP_SECONDS}.",
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


# Retorna o horario atual em formato ISO UTC.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Monta os caminhos de entrada e saida usados pelo script.
def build_paths(snapshot_date: str) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[4]
    output_path = root / "data" / "project_standards" / "01_bronze" / "puro_earth" / snapshot_date / "list" / "projects.json"
    errors_path = Path(__file__).resolve().parent / "logs" / f"extract_project_list_failures_{snapshot_date}.json"
    return output_path, errors_path


# Grava o log consolidado de falhas da execucao.
def write_failure_log(errors_path: Path, snapshot_date: str, failures: list[dict[str, Any]]) -> None:
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {"certificadora": "puro_earth", "snapshot_date": snapshot_date, "script": "extract_project_list.py"},
        "updated_at": utc_now_iso(),
        "failure_count": len(failures),
        "failures": failures,
    }
    errors_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Monta os headers HTTP usados nas requisicoes da integracao.
def build_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }


# Busca o HTML de uma pagina de lista ou detalhe.
def fetch_page_html(timeout: float, retry_attempts: int, retry_sleep_seconds: float) -> str:
    attempts_total = retry_attempts + 1
    attempt = 1
    while True:
        req = request.Request(url=PAGE_URL, method="GET", headers=build_headers())
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
            raise RuntimeError(
                f"Erro HTTP {exc.code} ao consultar a Puro.earth. Resposta: {details}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar a Puro.earth: {exc}") from exc


# Extrai os projetos do payload embutido no HTML da pagina.
def extract_projects_from_embedded_payload(page_html: str) -> list[dict[str, Any]]:
    # A lista vem embutida no HTML do Next.js; aqui extraimos exatamente esse payload.
    start = page_html.find(PROJECTS_MARKER)
    if start == -1:
        raise RuntimeError(
            "Nao foi possivel localizar o payload embutido de projetos da Puro.earth."
        )

    in_string = False
    escape = False
    level = 0
    end: int | None = None

    for index, char in enumerate(page_html[start:], start=start):
        # Percorremos caractere a caractere para achar o fechamento correto do array JSON.
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
        raise RuntimeError(
            "Nao foi possivel determinar o fim do payload embutido de projetos da Puro.earth."
        )

    bronze_payload = page_html[start:end]
    decoded_payload = bronze_payload.encode("utf-8").decode("unicode_escape")
    projects = json.loads(decoded_payload)

    if not isinstance(projects, list):
        raise RuntimeError(
            "Resposta inesperada da Puro.earth: era esperada uma lista de projetos."
        )

    return projects


# Extrai a contagem total de projetos exibida pela fonte.
def extract_total_count(page_html: str) -> int | None:
    marker = 'children":"Projects"'
    marker_index = page_html.find(marker)
    if marker_index == -1:
        return None

    window = page_html[marker_index : marker_index + 500]
    count_match = None
    for token in ['children":"', "children\":\""]:
        search_start = window.find(token, len(marker))
        if search_start != -1:
            search_start += len(token)
            search_end = window.find('"', search_start)
            if search_end != -1:
                candidate = window[search_start:search_end].replace("Â", "").replace("\xa0", "")
                if candidate.isdigit():
                    count_match = int(candidate)
                    break

    return count_match


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)

    if args.max_pages is not None and args.max_pages <= 0:
        raise SystemExit("--max-pages deve ser maior que zero.")
    if args.max_pages not in {None, 1}:
        raise SystemExit(
            "A Puro.earth entrega a lista em uma unica pagina. Use --max-pages 1 para teste."
        )
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

    print("Iniciando extracao da lista de projetos da Puro.earth")
    print(f"Data do snapshot: {snapshot_date}")
    print(f"URL da pagina: {PAGE_URL}")
    print("Metodo de extracao: payload embutido no frontend Next.js")
    print(f"Sleep entre requisicoes: {args.sleep_seconds:.1f}s")
    print(f"Pausa a cada lote: {args.batch_sleep_seconds:.1f}s a cada {args.batch_size} paginas")
    print(
        f"Retry em 429: {args.retry_attempts} tentativas adicionais com espera de "
        f"{args.retry_sleep_seconds:.1f}s"
    )
    print(f"Timeout por requisicao: {args.timeout:.1f}s")
    if args.max_pages is not None:
        print(f"Modo de teste ativado: max_pages={args.max_pages}")
    print(f"Arquivo de saida: {output_path}")
    print(f"Arquivo de falhas: {errors_path}")

    try:
        print("Carregando pagina da Puro.earth")
        page_html = fetch_page_html(
            timeout=args.timeout,
            retry_attempts=args.retry_attempts,
            retry_sleep_seconds=args.retry_sleep_seconds,
        )

        print("Extraindo payload embutido de projetos")
        projects = extract_projects_from_embedded_payload(page_html)
        total_count = extract_total_count(page_html)
    except Exception as exc:
        write_failure_log(
            errors_path=errors_path,
            snapshot_date=snapshot_date,
            failures=[{
                "captured_at": utc_now_iso(),
                "stage": "list_download",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }],
        )
        raise

    payload: dict[str, Any] = {
        "source": {
            "page_url": PAGE_URL,
            "extraction_method": "embedded_nextjs_payload",
            "project_identifier_mapping": {
                "project_public_id": "projectId",
                "project_internal_id": "projectId",
            },
        },
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "projects": projects,
    }

    if total_count is not None:
        payload["total_count"] = total_count

    if args.max_pages is not None:
        payload["partial"] = True

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Arquivo salvo em: {output_path}")
    print(f"Total de projetos salvos: {len(projects)}")
    if total_count is not None:
        print(f"Total informado pela pagina: {total_count}")
        if total_count != len(projects):
            print(
                "aviso: total salvo difere do total exibido na pagina "
                f"({len(projects)} vs {total_count})",
                file=sys.stderr,
            )
    if payload.get("partial"):
        print("Execucao finalizada em modo parcial")
    else:
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
