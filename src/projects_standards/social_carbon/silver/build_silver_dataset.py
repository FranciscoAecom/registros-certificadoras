# Objetivo do script:
# Consolidar os arquivos bronze da Social Carbon em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.

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
    first_non_empty,
    get_path,
    parse_coordinate,
    parse_count,
    parse_date,
    parse_decimal_measure,
    normalize_project_methodology,
    path_candidate,
    run_dataset,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Social Carbon"
BRONZE_SLUG = "social_carbon"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


def sort_key(path: Path) -> str:
    return path.stem




def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(payload, "source.project_public_id", "list_data.Project ID"),
        "project_internal_id": lambda payload, _file_path: first_non_empty(payload, "source.project_internal_id", "list_data._id"),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Name", "list_data.Project Name"),
        "project_voluntary_status": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Status", "list_data.Project Status"),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: first_non_empty(payload, "detail_data.Standard", "list_data.Standard"),
        "project_description": lambda payload, _file_path: first_non_empty(payload, "detail_data.Description", "list_data.Description"),
        "project_methodology": lambda payload, _file_path: normalize_project_methodology(
            first_non_empty(payload, "detail_data.Methodology", "list_data.Methodology"),
            split_pattern=r"\s*[,;]\s*",
        ),
        "project_type": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Type", "list_data.Project Type"),
        "sector": lambda payload, _file_path: None,
        "project_category": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Type", "list_data.Project Type"),
        "project_subcategories": lambda payload, _file_path: None,
        "sdg_targets": lambda payload, _file_path: first_non_empty(payload, "detail_data.SDGs", "list_data.SDGs"),
        "project_developer": lambda payload, _file_path: first_non_empty(payload, "detail_data.Project Proponent(s)_TEXT", "list_data.Project Proponent(s)_TEXT"),
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: None,
        "validator_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.validator", "list_data.validator"),
        "verifier_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.verifier", "list_data.verifier"),
        "country": lambda payload, _file_path: first_non_empty(payload, "detail_data.Country", "list_data.Country"),
        "state_or_region": lambda payload, _file_path: None,
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: parse_coordinate(first_non_empty(payload, "detail_data.Latitude", "list_data.Latitude")),
        "location_longitude": lambda payload, _file_path: parse_coordinate(first_non_empty(payload, "detail_data.Longitude", "list_data.Longitude")),
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.Created Date", "list_data.Created Date")),
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.Crediting period start", "list_data.Crediting period start")),
        "crediting_end_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.Crediting period end", "list_data.Crediting period end")),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: None,
        "credits_retired_total": lambda payload, _file_path: None,
        "credits_cancelled_total": lambda payload, _file_path: None,
        "credits_buffer_total": lambda payload, _file_path: None,
        "estimated_annual_emission_reductions": lambda payload, _file_path: parse_count(first_non_empty(payload, "detail_data.Estimated Annual Emission Reductions", "list_data.Estimated Annual Emission Reductions")),
        "estimated_total_emission_reductions": lambda payload, _file_path: None,
        "area_hectares": lambda payload, _file_path: parse_decimal_measure(first_non_empty(payload, "detail_data.Total Project Area", "list_data.Total Project Area")),
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



