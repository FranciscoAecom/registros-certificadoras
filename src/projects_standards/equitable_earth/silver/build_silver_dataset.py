# Objetivo do script:
# Consolidar os arquivos bronze da Equitable Earth em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.

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
    parse_decimal_measure,
    path_candidate,
    run_dataset,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Equitable Earth"
BRONZE_SLUG = "equitable_earth"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


def sort_key(path: Path) -> str:
    return path.stem


def extract_protocol_code(value: Any) -> Any:
    text = normalize_missing(value)
    if text is None:
        return None
    match = re.match(r"^([A-Z]\d+)", str(text))
    return match.group(1) if match else None


def extract_program_name(payload: dict[str, Any], _: Path) -> Any:
    programs = get_path(payload, "detail_data.resource.programs")
    if isinstance(programs, list) and programs:
        return normalize_missing(programs[0].get("name"))
    return normalize_missing(get_path(payload, "source.program_code"))


def extract_program_description(payload: dict[str, Any], _: Path) -> Any:
    programs = get_path(payload, "detail_data.resource.programs")
    if isinstance(programs, list) and programs:
        return normalize_missing(programs[0].get("description"))
    return None


def extract_developer(payload: dict[str, Any], _: Path) -> Any:
    legal_entities = get_path(payload, "detail_data.proponents.legalEntities")
    if isinstance(legal_entities, list) and legal_entities:
        return normalize_missing(legal_entities[0].get("name")) or normalize_missing(legal_entities[0].get("dbaName"))
    return normalize_missing(get_path(payload, "list_data.resourceProponentList"))


def extract_country(payload: dict[str, Any], _: Path) -> Any:
    return (
        normalize_missing(get_path(payload, "detail_data.resource.naturalGeography.address.countryIso2Code"))
        or normalize_missing(get_path(payload, "list_data.countryIso3Code"))
    )


def extract_area_hectares(payload: dict[str, Any], _: Path) -> Any:
    unit = normalize_missing(get_path(payload, "detail_data.resource.naturalGeography.areaUnitCode"))
    area = get_path(payload, "detail_data.resource.naturalGeography.area")
    if area is None:
        return None
    if unit is None or str(unit).strip().lower() == "ha":
        return parse_decimal_measure(area)
    return None




def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(payload, "source.project_public_id", "list_data.programAssignedIdentifier"),
        "project_internal_id": lambda payload, _file_path: first_non_empty(payload, "source.project_internal_id", "list_data.resourceIdentifier"),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: get_path(payload, "list_data.resourceProgramName"),
        "project_voluntary_status": lambda payload, _file_path: first_non_empty(payload, "list_data.resourceProgramStatusName", "detail_data.resource.programs.0.status.name"),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": extract_program_name,
        "project_description": extract_program_description,
        "project_methodology": lambda payload, _file_path: first_non_empty(payload, "list_data.programProtocol", "detail_data.protocol_versions.0.name"),
        "project_type": lambda payload, _file_path: get_path(payload, "list_data.resourceTypeName"),
        "sector": lambda payload, _file_path: None,
        "project_category": lambda payload, _file_path: None,
        "project_subcategories": lambda payload, _file_path: None,
        "sdg_targets": lambda payload, _file_path: None,
        "project_developer": extract_developer,
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: None,
        "validator_name": lambda payload, _file_path: None,
        "verifier_name": lambda payload, _file_path: None,
        "country": extract_country,
        "state_or_region": lambda payload, _file_path: get_path(payload, "detail_data.resource.naturalGeography.address.countrySubdivisionName"),
        "city_or_locality": lambda payload, _file_path: get_path(payload, "detail_data.resource.naturalGeography.address.municipality"),
        "location_latitude": lambda payload, _file_path: None,
        "location_longitude": lambda payload, _file_path: None,
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: None,
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.crediting_periods.currentCreditingPeriod.startDateInclusive", "list_data.projectStartDate")),
        "crediting_end_date": lambda payload, _file_path: parse_date(get_path(payload, "detail_data.crediting_periods.currentCreditingPeriod.endDateExclusive")),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: None,
        "credits_retired_total": lambda payload, _file_path: None,
        "credits_cancelled_total": lambda payload, _file_path: None,
        "credits_buffer_total": lambda payload, _file_path: None,
        "estimated_annual_emission_reductions": lambda payload, _file_path: None,
        "estimated_total_emission_reductions": lambda payload, _file_path: None,
        "area_hectares": extract_area_hectares,
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



