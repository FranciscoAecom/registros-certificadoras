# Objetivo do script:
# Consolidar os arquivos bronze da Climate Action Reserve em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import (  # noqa: E402
    first_non_empty,
    get_path,
    normalize_missing,
    parse_count,
    parse_date,
    path_candidate,
    run_dataset,
    scalar_or_list,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Climate Action Reserve"
BRONZE_SLUG = "climate_action_reserve"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


def sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)$", path.stem)
    if match:
        return int(match.group(1)), path.stem
    return 10**12, path.stem


def parse_project_type_code(value: Any) -> Any:
    text = normalize_missing(value)
    if text is None:
        return None
    match = re.match(r"^([A-Z]{2,}(?:[-_.][A-Z0-9]+)+|[A-Z]{2,}\d{2,})\b", str(text))
    return match.group(1) if match else None


def split_semicolon_values(value: Any) -> Any:
    text = normalize_missing(value)
    if text is None:
        return None
    parts = [part.strip() for part in str(text).split(";") if part.strip()]
    clean_parts = [part for part in parts if part]
    return scalar_or_list(clean_parts)


def make_direct_transformer(path: str) -> Callable[[dict[str, Any], Path], Any]:
    return lambda payload, _file_path: normalize_missing(get_path(payload, path))




def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": make_direct_transformer("source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(payload, "source.project_public_id", "list_data.Project ID"),
        "project_internal_id": make_direct_transformer("source.project_internal_id"),
        "project_url": make_direct_transformer("source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Name", "list_data.Project Name"),
        "project_voluntary_status": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Status", "list_data.Status"),
        "project_regulatory_status": make_direct_transformer("list_data.Compliance Program Status"),
        "standard_program": make_direct_transformer("source.carbon_standard"),
        "project_description": make_direct_transformer("detail_data.Project Description"),
        "project_methodology": lambda payload, _file_path: None,
        "project_type": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Type", "list_data.Project Type"),
        "sector": lambda payload, _file_path: None,
        "project_category": lambda payload, _file_path: None,
        "project_subcategories": lambda payload, _file_path: split_semicolon_values(get_path(payload, "list_data.Additional Certification(s)")),
        "sdg_targets": lambda payload, _file_path: split_semicolon_values(get_path(payload, "list_data.SDG Impact")),
        "project_developer": make_direct_transformer("list_data.Project Developer"),
        "project_owner": make_direct_transformer("list_data.Project Owner"),
        "project_operator": lambda payload, _file_path: first_non_empty(payload, "detail_data.Offset Project Operator", "list_data.Offset Project Operator"),
        "validator_name": lambda payload, _file_path: first_non_empty(payload, "list_data.Verification Body", "detail_data.Verification Bodies"),
        "verifier_name": lambda payload, _file_path: first_non_empty(payload, "list_data.Verification Body", "detail_data.Verification Bodies"),
        "country": lambda payload, _file_path: first_non_empty(payload, "detail_data.Country", "list_data.Project Site Country"),
        "state_or_region": lambda payload, _file_path: first_non_empty(payload, "detail_data.State/Province/Department", "list_data.Project Site State"),
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: None,
        "location_longitude": lambda payload, _file_path: None,
        "snapshot_date": make_direct_transformer("source.snapshot_date"),
        "reference_month": make_direct_transformer("source.reference_month"),
        "registration_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.Project Registered Date", "list_data.Project Registered Date")),
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.Project Reporting Start Date", "detail_data.Project Commencement Date")),
        "crediting_end_date": lambda payload, _file_path: parse_date(get_path(payload, "detail_data.Crediting Period Expires")),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: parse_count(get_path(payload, "list_data.Total Number of Offset Credits Registered ")),
        "credits_retired_total": lambda payload, _file_path: None,
        "credits_cancelled_total": lambda payload, _file_path: None,
        "credits_buffer_total": lambda payload, _file_path: None,
        "estimated_annual_emission_reductions": lambda payload, _file_path: None,
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



