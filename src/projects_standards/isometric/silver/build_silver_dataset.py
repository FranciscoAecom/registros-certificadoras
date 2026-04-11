# Objetivo do script:
# Consolidar os arquivos bronze da Isometric em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.

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
    parse_date,
    path_candidate,
    run_dataset,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Isometric"
BRONZE_SLUG = "isometric"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


def sort_key(path: Path) -> str:
    return path.stem




def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(payload, "source.project_public_id", "list_data.id"),
        "project_internal_id": lambda payload, _file_path: first_non_empty(payload, "source.project_internal_id", "list_data.id"),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: first_non_empty(payload, "detail_data.name", "list_data.name"),
        "project_voluntary_status": lambda payload, _file_path: first_non_empty(payload, "detail_data.status", "list_data.status"),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "project_description": lambda payload, _file_path: first_non_empty(payload, "detail_data.description", "detail_data.shortDescription"),
        "project_methodology": lambda payload, _file_path: get_path(payload, "detail_data.protocol.name"),
        "project_type": lambda payload, _file_path: get_path(payload, "detail_data.process.displayName"),
        "sector": lambda payload, _file_path: first_non_empty(payload, "detail_data.process.pathway.name", "list_data.process.pathway.shortName"),
        "project_category": lambda payload, _file_path: get_path(payload, "detail_data.process.pathway.type"),
        "project_subcategories": lambda payload, _file_path: get_path(payload, "detail_data.process.displayName"),
        "sdg_targets": lambda payload, _file_path: None,
        "project_developer": lambda payload, _file_path: first_non_empty(payload, "detail_data.supplier.organisation.name", "list_data.supplier.organisation.name"),
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: None,
        "validator_name": lambda payload, _file_path: None,
        "verifier_name": lambda payload, _file_path: None,
        "country": lambda payload, _file_path: first_non_empty(payload, "detail_data.country.name", "list_data.country.isoAlpha3Code"),
        "state_or_region": lambda payload, _file_path: None,
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: None,
        "location_longitude": lambda payload, _file_path: None,
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: parse_date(get_path(payload, "detail_data.validatedAt")),
        "status_date": lambda payload, _file_path: parse_date(get_path(payload, "detail_data.validatedAt")),
        "crediting_start_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.creditingPeriodStart", "detail_data.projectStart")),
        "crediting_end_date": lambda payload, _file_path: parse_date(first_non_empty(payload, "detail_data.creditingPeriodEnd", "detail_data.projectEnd")),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: get_path(payload, "detail_data.creditBalance.total.credits"),
        "credits_retired_total": lambda payload, _file_path: get_path(payload, "detail_data.creditBalance.retired.credits"),
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



