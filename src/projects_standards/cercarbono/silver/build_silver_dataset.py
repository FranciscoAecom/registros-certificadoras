# Objetivo do script:
# Consolidar os arquivos bronze da Cercarbono em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.

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
    parse_date,
    path_candidate,
    run_dataset,
    scalar_or_list,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Cercarbono"
BRONZE_SLUG = "cercarbono"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


def sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)$", path.stem)
    if match:
        return int(match.group(1)), path.stem
    return 10**12, path.stem


def ensure_clean_list(values: list[Any]) -> Any:
    clean_values: list[Any] = []
    for value in values:
        cleaned = normalize_missing(value)
        if cleaned in (None, "", [], {}):
            continue
        if cleaned not in clean_values:
            clean_values.append(cleaned)
    return scalar_or_list(clean_values)


def extract_methodology_codes(payload: dict[str, Any], _: Path) -> Any:
    methodologies = get_path(payload, "list_data.methodology")
    if not isinstance(methodologies, list):
        return None

    codes: list[str] = []
    for item in methodologies:
        if not isinstance(item, dict):
            continue
        description = normalize_missing(item.get("description"))
        methodology_id = normalize_missing(item.get("methodologyId"))
        if description is not None:
            match = re.search(r"\b([A-Z]{2,}(?:[-_.][A-Z0-9]+)+|[A-Z]{2,}\d{2,})\b", str(description))
            if match:
                codes.append(match.group(1))
                continue
        if methodology_id is not None:
            codes.append(str(methodology_id))
    return ensure_clean_list(codes)


def extract_methodology_names(payload: dict[str, Any], _: Path) -> Any:
    methodologies = get_path(payload, "list_data.methodology")
    if not isinstance(methodologies, list):
        return None
    return ensure_clean_list([item.get("description") for item in methodologies if isinstance(item, dict)])


def extract_project_type(payload: dict[str, Any], _: Path) -> Any:
    methodologies = get_path(payload, "list_data.methodology")
    if not isinstance(methodologies, list):
        return None
    return ensure_clean_list([item.get("type_mechanism") for item in methodologies if isinstance(item, dict)])


def extract_project_category(payload: dict[str, Any], _: Path) -> Any:
    methodologies = get_path(payload, "list_data.methodology")
    if not isinstance(methodologies, list):
        return None
    return ensure_clean_list([item.get("type_avoidance_removals") for item in methodologies if isinstance(item, dict)])


def extract_project_subcategories(payload: dict[str, Any], _: Path) -> Any:
    protocols = get_path(payload, "list_data.protocols")
    if not isinstance(protocols, list):
        return None
    return ensure_clean_list([item.get("description") for item in protocols if isinstance(item, dict)])


def extract_sdg_targets(payload: dict[str, Any], _: Path) -> Any:
    goals = get_path(payload, "list_data.projectsGlobalGoal")
    if not isinstance(goals, list):
        return None
    return ensure_clean_list([item.get("description") for item in goals if isinstance(item, dict)])


def extract_project_description(payload: dict[str, Any], _: Path) -> Any:
    return first_non_empty(
        payload,
        "detail_data.project.descriptionProjectIng",
        "detail_data.project.descriptionProject",
        "list_data.name",
    )


def extract_preferred_location(payload: dict[str, Any]) -> dict[str, Any] | None:
    locations = get_path(payload, "detail_data.locations")
    if not isinstance(locations, list):
        return None

    preferred = None
    for location in locations:
        if not isinstance(location, dict):
            continue
        if location.get("checked") is True:
            return location
        if preferred is None:
            preferred = location
    return preferred if isinstance(preferred, dict) else None


def extract_location_field(payload: dict[str, Any], _: Path, field_name: str) -> Any:
    preferred = extract_preferred_location(payload)
    if not isinstance(preferred, dict):
        return None
    return normalize_missing(preferred.get(field_name))


def extract_coordinate(payload: dict[str, Any], _: Path, coordinate_name: str) -> Any:
    preferred = extract_preferred_location(payload)
    if not isinstance(preferred, dict):
        return None
    data_map = preferred.get("dataMap")
    if not isinstance(data_map, dict):
        return None
    return normalize_missing(data_map.get(coordinate_name))


def extract_issued_total(payload: dict[str, Any], _: Path) -> Any:
    items = get_path(payload, "detail_data.certificatedVerification")
    if not isinstance(items, list):
        return None
    total = 0
    found = False
    for item in items:
        if not isinstance(item, dict):
            continue
        current = normalize_missing(item.get("total"))
        if current is None:
            continue
        total += int(str(current).replace(",", ""))
        found = True
    return total if found else None


def make_direct_transformer(path: str) -> Callable[[dict[str, Any], Path], Any]:
    return lambda payload, _file_path: normalize_missing(get_path(payload, path))




def extract_registration_date(payload: dict[str, Any], _: Path) -> Any:
    return parse_date(get_path(payload, "detail_data.project.date"))


def extract_crediting_start(payload: dict[str, Any], _: Path) -> Any:
    return parse_date(
        first_non_empty(
            payload,
            "detail_data.project.periodInit",
            "detail_data.project.projectsCreditingPeriod.0.periodInit",
        )
    )


def extract_crediting_end(payload: dict[str, Any], _: Path) -> Any:
    return parse_date(
        first_non_empty(
            payload,
            "detail_data.project.periodEnd",
            "detail_data.project.projectsCreditingPeriod.0.periodEnd",
        )
    )


def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": make_direct_transformer("source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(payload, "source.project_public_id", "list_data.code"),
        "project_internal_id": lambda payload, _file_path: first_non_empty(payload, "source.project_internal_id", "list_data.id"),
        "project_url": make_direct_transformer("source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.project.name", "list_data.name"),
        "project_voluntary_status": make_direct_transformer("list_data.projectStage"),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: first_non_empty(payload, "list_data.standard", "detail_data.project.standarDescription"),
        "project_description": extract_project_description,
        "project_methodology": extract_methodology_names,
        "project_type": extract_project_type,
        "sector": make_direct_transformer("list_data.sectorsText"),
        "project_category": extract_project_category,
        "project_subcategories": extract_project_subcategories,
        "sdg_targets": extract_sdg_targets,
        "project_developer": make_direct_transformer("list_data.developer"),
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: None,
        "validator_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.project.validator", "list_data.verifier"),
        "verifier_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.project.verifier", "list_data.verifier"),
        "country": lambda payload, file_path: extract_location_field(payload, file_path, "countryDescription") or first_non_empty(payload, "list_data.locationText"),
        "state_or_region": lambda payload, file_path: extract_location_field(payload, file_path, "regionDescription"),
        "city_or_locality": lambda payload, file_path: extract_location_field(payload, file_path, "cityDescription"),
        "location_latitude": lambda payload, file_path: extract_coordinate(payload, file_path, "latitude"),
        "location_longitude": lambda payload, file_path: extract_coordinate(payload, file_path, "longitude"),
        "snapshot_date": make_direct_transformer("source.snapshot_date"),
        "reference_month": make_direct_transformer("source.reference_month"),
        "registration_date": extract_registration_date,
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": extract_crediting_start,
        "crediting_end_date": extract_crediting_end,
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": extract_issued_total,
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



