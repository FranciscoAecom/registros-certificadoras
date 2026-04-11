# Objetivo do script:
# Consolidar os arquivos bronze da Gold Standard em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.
# Processo:
# 1. Definir configuracao da certificadora (nome, slug bronze, sigla).
# 2. Construir dicionario de transformadores campo a campo (build_transformers).
# 3. Registrar hooks de pos-build para sincronizar referencias (status, pais, metodologia).
# 4. Delegar ao framework compartilhado run_dataset(CONFIG) que:
#    a. Descompacta automaticamente o bronze e o silver se estiverem zipados.
#    b. Carrega os arquivos bronze do snapshot informado.
#    c. Aplica cada transformador para extrair e normalizar campos.
#    d. Gera o dataset silver (allprojects.json).
#    e. Gera o relatorio de qualidade (quality_report.json).
#    f. Gera o relatorio de mapeamento (mapping_report.json).
#    g. Compacta novamente o bronze e o silver ao final da execução.
# 5. Executar hooks de sincronizacao de referencias.
# 6. Retornar codigo de saida.


import re
import sys
from pathlib import Path
from typing import Any, Callable


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import (  # noqa: E402
    ensure_list,
    get_path,
    normalize_project_methodology,
    parse_coordinate,
    parse_count,
    parse_date,
    path_candidate,
    run_dataset,
    scalar_or_list,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Gold Standard"
BRONZE_SLUG = "gold_standard"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


# Ordena os arquivos de detalhe pelo identificador interno do projeto.
def sort_key(path: Path) -> int:
    return int(path.stem)


# Extrai o prefixo de codigo da metodologia quando ele estiver presente no texto.
def extract_methodology_code(value: Any) -> Any:
    if value in (None, ""):
        return None
    values = ensure_list(value)
    codes: list[str] = []
    for item in values:
        text = str(item).strip()
        match = re.match(r"^([A-Z]{2,}(?:[-_.][A-Z0-9]+)+|[A-Z]{2,}\d{3,})\b", text)
        if match:
            codes.append(match.group(1))
    return scalar_or_list(codes)


# Extrai os nomes dos ODS a partir do payload bruto da Gold Standard.
def extract_sdg_targets(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    names = [item.get("name") for item in value if isinstance(item, dict) and item.get("name")]
    return scalar_or_list(names)


# Combina programa e labels para construir um conjunto de subcategorias uteis.
def extract_project_subcategories(programme_of_activities: Any, labels: Any) -> Any:
    combined: list[Any] = []
    combined.extend(ensure_list(programme_of_activities))
    combined.extend(ensure_list(labels))
    return scalar_or_list(combined)


# Soma os totais do credits_summary para um status especifico do projeto.
def extract_credits_summary_total(value: Any, target_status: str) -> Any:
    if not isinstance(value, list):
        return None

    total = 0
    found = False
    for product_summary in value:
        if not isinstance(product_summary, dict):
            continue
        summary_items = product_summary.get("summary")
        if not isinstance(summary_items, list):
            continue
        for summary_item in summary_items:
            if not isinstance(summary_item, dict):
                continue
            if str(summary_item.get("status") or "").upper() != target_status.upper():
                continue
            current_total = summary_item.get("total")
            if current_total in (None, ""):
                continue
            parsed_total = parse_count(current_total)
            if parsed_total is None:
                continue
            total += float(parsed_total)
            found = True
    if not found:
        return None
    return int(total) if float(total).is_integer() else total


# Trata todos os status da Gold Standard como voluntarios ate nova definicao canonica.
def extract_voluntary_status(status: Any) -> Any:
    if status in (None, ""):
        return None
    return status


# Monta as regras de transformacao campo a campo para a camada silver.
def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: get_path(payload, "source.project_public_id"),
        "project_internal_id": lambda payload, _file_path: get_path(payload, "source.project_internal_id"),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: get_path(payload, "detail_data.name") or get_path(payload, "list_data.name"),
        "project_voluntary_status": lambda payload, _file_path: extract_voluntary_status(
            get_path(payload, "list_data.status") or get_path(payload, "detail_data.status")
        ),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: get_path(payload, "list_data.gsf_standards_version"),
        "project_description": lambda payload, _file_path: get_path(payload, "detail_data.description"),
        "project_methodology": lambda payload, _file_path: normalize_project_methodology(
            get_path(payload, "detail_data.methodology") or get_path(payload, "list_data.methodology")
        ),
        "project_type": lambda payload, _file_path: get_path(payload, "list_data.type"),
        "sector": lambda payload, _file_path: None,
        "project_category": lambda payload, _file_path: get_path(payload, "list_data.size"),
        "project_subcategories": lambda payload, _file_path: extract_project_subcategories(
            get_path(payload, "list_data.programme_of_activities"),
            get_path(payload, "list_data.labels"),
        ),
        "sdg_targets": lambda payload, _file_path: extract_sdg_targets(get_path(payload, "list_data.sustainable_development_goals")),
        "project_developer": lambda payload, _file_path: get_path(payload, "list_data.project_developer"),
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: None,
        "validator_name": lambda payload, _file_path: None,
        "verifier_name": lambda payload, _file_path: None,
        "country": lambda payload, _file_path: get_path(payload, "list_data.country"),
        "state_or_region": lambda payload, _file_path: get_path(payload, "list_data.state"),
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: parse_coordinate(
            get_path(payload, "detail_data.latitude") or get_path(payload, "list_data.latitude")
        ),
        "location_longitude": lambda payload, _file_path: parse_coordinate(
            get_path(payload, "detail_data.longitude") or get_path(payload, "list_data.longitude")
        ),
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: None,
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(get_path(payload, "list_data.crediting_period_start_date")),
        "crediting_end_date": lambda payload, _file_path: parse_date(get_path(payload, "list_data.crediting_period_end_date")),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: extract_credits_summary_total(
            get_path(payload, "detail_data.credits_summary"),
            "ISSUED",
        ),
        "credits_retired_total": lambda payload, _file_path: extract_credits_summary_total(
            get_path(payload, "detail_data.credits_summary"),
            "RETIRED",
        ),
        "credits_cancelled_total": lambda payload, _file_path: None,
        "credits_buffer_total": lambda payload, _file_path: None,
        "estimated_annual_emission_reductions": lambda payload, _file_path: parse_count(get_path(payload, "list_data.estimated_annual_credits")),
        "estimated_total_emission_reductions": lambda payload, _file_path: None,
        "area_hectares": lambda payload, _file_path: None,
    }


CONFIG = {
    "display_name": DISPLAY_NAME,
    "bronze_slug": BRONZE_SLUG,
    "reference_name": DISPLAY_NAME,
    "dataset_output_template": DATASET_OUTPUT_TEMPLATE,
    "failure_output_template": FAILURE_OUTPUT_TEMPLATE,
    "transformers": build_transformers,
    "sort_key": sort_key,
    "post_build_hooks": [sync_status_reference_for_projects, sync_country_reference_for_projects, sync_methodology_reference_for_projects],
}


if __name__ == "__main__":
    raise SystemExit(run_dataset(CONFIG))


