#!/usr/bin/env python3
# Objetivo: Capturar screenshots, PDFs e KML/KMZ dos projetos listados no CSV de verificacao da Verra.
# Processo:
# 1. Ler o CSV de verificacao e o log existente para retomar sem duplicar projetos concluidos.
# 2. Acessar a pagina publica do projeto para gerar screenshot com espera de renderizacao.
# 3. Consultar o endpoint de detalhe da Verra e baixar PDFs/KML/KMZ com ritmo conservador.
# 4. Salvar um log JSON incremental para acompanhamento e retomada segura.

import csv
import json
import random
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASE_DIR = (
    ROOT
    / "data"
    / "project_standards"
    / "03_gold"
    / "projects"
    / "Verra"
    / "Resultados"
    / "v04"
    / "Verificacao"
)
CSV_PATH = next((p for p in BASE_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".csv"), None)
if CSV_PATH is None:
    raise SystemExit(f"Nao encontrei o CSV em {BASE_DIR}")

LOG_PATH = BASE_DIR / "project_capture_log.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)
DETAIL_ENDPOINT = "https://registry.verra.org/uiapi/resource/resourceSummary/{project_id}"
PROJECT_SLEEP = 3.0
DOC_SLEEP = 4.0
BATCH_SIZE = 5
BATCH_SLEEP = 20.0
RETRY_ATTEMPTS = 6
RETRY_SLEEP = 8.0
MAX_RETRY_SLEEP = 120.0
TIMEOUT = 120

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]
CHROME_PATH = next((str(p) for p in CHROME_CANDIDATES if p.exists()), None)
if not CHROME_PATH:
    raise SystemExit("Nao foi encontrado Chrome/Edge para screenshot headless.")

OPENER = urllib.request.build_opener()
OPENER.addheaders = [("User-Agent", USER_AGENT)]


# Calcula o atraso progressivo usado nos retries de rede.
def retry_delay(attempt_index: int) -> float:
    base = RETRY_SLEEP * (2**attempt_index)
    return min(MAX_RETRY_SLEEP, base + random.uniform(0, 0.5))


# Faz a leitura resiliente do JSON de detalhe da Verra.
def request_json(url: str):
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            with OPENER.open(url, timeout=TIMEOUT) as response:
                status = getattr(response, "status", response.getcode())
                data = response.read()
            if status >= 400:
                raise urllib.error.HTTPError(url, status, f"HTTP {status}", None, None)
            return json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < RETRY_ATTEMPTS:
                time.sleep(retry_delay(attempt))
                continue
            raise
        except Exception:
            if attempt < RETRY_ATTEMPTS:
                time.sleep(retry_delay(attempt))
                continue
            raise


# Extrai um nome de arquivo sugerido a partir do cabecalho de download.
def parse_content_disposition(header: str | None) -> str | None:
    if not header:
        return None
    match = re.search(r"filename\*?=(?:UTF-8''|\"?)([^\";]+)", header, flags=re.IGNORECASE)
    if not match:
        return None
    return urllib.parse.unquote(match.group(1)).strip()


# Normaliza nomes de arquivos para Windows.
def sanitize_filename(name: str, fallback: str) -> str:
    value = (name or "").strip() or fallback
    for char in '<>:"/\\|?*':
        value = value.replace(char, "_")
    value = " ".join(value.split())
    return value[:180] or fallback


# Decide o tipo do arquivo considerando metadados e cabecalhos HTTP.
def infer_kind(document: dict, url: str, content_type: str = "") -> str:
    lower_name = (document.get("name") or document.get("fileName") or "").lower()
    lower_type = (document.get("documentType") or document.get("type") or "").lower()
    lower_url = url.lower()
    lower_ct = content_type.lower()
    if ".kmz" in lower_name or ".kmz" in lower_url or ".kmz" in lower_type or "kmz" in lower_ct:
        return "kmz"
    if (
        ".kml" in lower_name
        or ".kml" in lower_url
        or ".kml" in lower_type
        or "kml" in lower_ct
        or "google-earth.kml" in lower_ct
    ):
        return "kml"
    return "pdf"


# Retorna a extensao padrao para cada tipo baixado.
def preferred_extension(kind: str) -> str:
    return {"pdf": ".pdf", "kml": ".kml", "kmz": ".kmz"}[kind]


# Baixa um documento da Verra com retry e grava no diretorio do projeto.
def download_file(document: dict, destination_dir: Path, index: int):
    url = document["url"]
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with OPENER.open(request, timeout=TIMEOUT) as response:
                status = getattr(response, "status", response.getcode())
                data = response.read()
                content_type = (response.headers.get("Content-Type") or "").lower()
                final_url = response.geturl()
                content_disposition = response.headers.get("Content-Disposition")
            if status >= 400:
                raise urllib.error.HTTPError(url, status, f"HTTP {status}", None, None)

            kind = infer_kind(document, final_url, content_type)
            extension = preferred_extension(kind)
            server_name = parse_content_disposition(content_disposition)
            source_name = (
                document.get("name")
                or document.get("fileName")
                or server_name
                or f"{kind}_{index}{extension}"
            )
            filename = sanitize_filename(source_name, f"{kind}_{index}{extension}")
            if not filename.lower().endswith(extension):
                filename = f"{filename}{extension}"

            destination = destination_dir / filename
            destination.write_bytes(data)
            return {
                "kind": kind,
                "name": filename,
                "url": url,
                "path": str(destination),
                "content_type": content_type,
                "bytes": len(data),
                "final_url": final_url,
            }
        except urllib.error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < RETRY_ATTEMPTS:
                time.sleep(retry_delay(attempt))
                continue
            raise
        except Exception:
            if attempt < RETRY_ATTEMPTS:
                time.sleep(retry_delay(attempt))
                continue
            raise


# Consolida todos os documentos publicados no detalhe do projeto.
def collect_documents(payload: dict):
    documents = []
    for group in payload.get("documentGroups") or []:
        entries = group.get("documents") or []
        if not entries:
            entries = group.get("projectDocuments") or []
        for document in entries:
            uri = (document.get("uri") or "").strip()
            if not uri:
                continue
            documents.append(
                {
                    "url": uri,
                    "name": (document.get("name") or document.get("fileName") or "").strip(),
                    "documentType": document.get("documentType"),
                    "type": document.get("type"),
                    "group": group.get("description") or group.get("code"),
                }
            )
    return documents


# Captura o screenshot da pagina publica usando espera virtual para a SPA renderizar.
def take_screenshot(url: str, destination: Path):
    command = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=15000",
        "--window-size=1600,2200",
        f"--screenshot={destination}",
        url,
    ]
    subprocess.run(command, check=True, timeout=TIMEOUT)


# Carrega o log incremental ja salvo para permitir retomada segura.
def load_log() -> dict:
    if not LOG_PATH.exists():
        return {"projects": {}}
    return json.loads(LOG_PATH.read_text(encoding="utf-8"))


# Salva o log incremental de captura em disco.
def save_log(log_data: dict):
    LOG_PATH.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")


# Retorna o identificador de projeto lido do CSV.
def extract_project_id(row: dict) -> str | None:
    for key in ("project_id", "project_public_id", "resourceIdentifier", "id"):
        value = (row.get(key) or "").strip()
        if value:
            return value
    return None


# Monta a URL publica do projeto da Verra.
def build_project_url(project_id: str) -> str:
    return f"https://registry.verra.org/app/projectDetail/VCS/{project_id}"


# Executa a captura completa de um projeto e retorna o resumo para o log.
def process_project(project_id: str, destination_dir: Path):
    project_url = build_project_url(project_id)
    screenshot_path = destination_dir / "page.png"
    take_screenshot(project_url, screenshot_path)

    detail_url = DETAIL_ENDPOINT.format(project_id=project_id)
    payload = request_json(detail_url)
    documents = collect_documents(payload)

    downloaded = []
    for index, document in enumerate(documents, start=1):
        downloaded.append(download_file(document, destination_dir, index))
        if index < len(documents):
            time.sleep(DOC_SLEEP)

    return {
        "project_id": project_id,
        "project_url": project_url,
        "screenshot": str(screenshot_path),
        "document_count": len(downloaded),
        "documents": downloaded,
    }


# Fluxo principal de leitura do CSV, retomada e captura incremental.
def main():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    log_data = load_log()
    project_log = log_data.setdefault("projects", {})
    completed = 0

    for row in rows:
        project_id = extract_project_id(row)
        if not project_id:
            continue
        if project_log.get(project_id, {}).get("status") == "done":
            continue

        destination_dir = BASE_DIR / project_id
        destination_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = process_project(project_id, destination_dir)
            project_log[project_id] = {
                "status": "done",
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            project_log[project_id] = {
                "status": "error",
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": str(exc),
            }
        save_log(log_data)
        completed += 1

        if completed % BATCH_SIZE == 0:
            time.sleep(BATCH_SLEEP)
        else:
            time.sleep(PROJECT_SLEEP)


if __name__ == "__main__":
    main()
