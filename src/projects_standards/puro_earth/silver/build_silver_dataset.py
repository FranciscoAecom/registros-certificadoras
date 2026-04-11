# Objetivo do script:
# Consolidar os arquivos bronze da Puro.earth em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.

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

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import (  # noqa: E402
    get_path,
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



DISPLAY_NAME = "Puro.earth"
BRONZE_SLUG = "puro_earth"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


def sort_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.stem), path.stem
    except ValueError:
        return 10**12, path.stem


def extract_sdgs(payload: dict[str, Any], _: Path) -> Any:
    values = []
    for item in payload.get("list_data", {}).get("sdgs", []):
        if isinstance(item, dict) and item.get("name"):
            values.append(item["name"])
    return scalar_or_list(values)


def extract_first_issuance_date(payload: dict[str, Any], _: Path) -> Any:
    items = []
    for transaction in payload.get("detail_data", {}).get("transactions", []):
        if not isinstance(transaction, dict):
            continue
        for bundle in transaction.get("bundles", []):
            if isinstance(bundle, dict) and bundle.get("issuanceDate"):
                items.append(bundle["issuanceDate"])
    return parse_date(min(items)) if items else None


def extract_last_issuance_date(payload: dict[str, Any], _: Path) -> Any:
    items = []
    for transaction in payload.get("detail_data", {}).get("transactions", []):
        if not isinstance(transaction, dict):
            continue
        for bundle in transaction.get("bundles", []):
            if isinstance(bundle, dict) and bundle.get("issuanceDate"):
                items.append(bundle["issuanceDate"])
    return parse_date(max(items)) if items else None




def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: get_path(payload, "source.project_public_id"),
        "project_internal_id": lambda payload, _file_path: get_path(payload, "source.project_internal_id"),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: get_path(payload, "detail_data.project_name") or get_path(payload, "list_data.name"),
        "project_voluntary_status": lambda payload, _file_path: "Registered",
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: get_path(payload, "detail_data.project_overview.general_rules.version") or get_path(payload, "list_data.generalRules.version"),
        "project_description": lambda payload, _file_path: None,
        "project_methodology": lambda payload, _file_path: get_path(payload, "detail_data.project_overview.methodology.name") or get_path(payload, "list_data.methodology.name"),
        "project_type": lambda payload, _file_path: get_path(payload, "detail_data.project_overview.methodology.name"),
        "sector": lambda payload, _file_path: None,
        "project_category": lambda payload, _file_path: None,
        "project_subcategories": lambda payload, _file_path: None,
        "sdg_targets": extract_sdgs,
        "project_developer": lambda payload, _file_path: get_path(payload, "detail_data.project_overview.supplier") or get_path(payload, "list_data.supplierName"),
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: None,
        "validator_name": lambda payload, _file_path: None,
        "verifier_name": lambda payload, _file_path: None,
        "country": lambda payload, _file_path: get_path(payload, "detail_data.project_overview.host_country"),
        "state_or_region": lambda payload, _file_path: None,
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: parse_coordinate(get_path(payload, "list_data.latitude")),
        "location_longitude": lambda payload, _file_path: parse_coordinate(get_path(payload, "list_data.longitude")),
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: None,
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(get_path(payload, "list_data.creditingPeriodStart")),
        "crediting_end_date": lambda payload, _file_path: parse_date(get_path(payload, "list_data.creditingPeriodEnd")),
        "first_issuance_date": extract_first_issuance_date,
        "last_issuance_date": extract_last_issuance_date,
        "credits_issued_total": lambda payload, _file_path: parse_count(get_path(payload, "detail_data.credits_summary.issued_corcs")),
        "credits_retired_total": lambda payload, _file_path: parse_count(get_path(payload, "detail_data.credits_summary.retired_corcs")),
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



