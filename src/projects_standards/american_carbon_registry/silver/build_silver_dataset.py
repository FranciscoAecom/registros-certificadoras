# Objetivo do script:
# Consolidar os arquivos bronze da American Carbon Registry em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.
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
    first_non_empty,
    get_path,
    normalize_missing,
    normalize_project_methodology,
    parse_count,
    parse_date,
    path_candidate,
    run_dataset,
    scalar_or_list,
)
from sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "American Carbon Registry"
BRONZE_SLUG = "american_carbon_registry"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


# Ordena os arquivos de detalhe pelo numero interno do projeto quando ele existir no nome.
def sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)$", path.stem)
    if match:
        return int(match.group(1)), path.stem
    return 10**12, path.stem


# Divide uma string delimitada por ponto e virgula em uma lista canonica.
def split_semicolon_values(value: Any) -> Any:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    parts = [part.strip() for part in str(clean_value).split(";") if part.strip()]
    return scalar_or_list(parts)


# Extrai o prefixo de codigo da metodologia quando ele estiver presente no texto.
def extract_methodology_code(value: Any) -> Any:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None

    values = ensure_list(clean_value)
    codes: list[str] = []
    for item in values:
        text = str(item).strip()
        match = re.match(r"^([A-Z]{2,}(?:[-_.][A-Z0-9]+)+|[A-Z]{2,}\d{2,})\b", text)
        if match:
            codes.append(match.group(1))
    return scalar_or_list(codes)


# Monta as regras de transformacao campo a campo para a camada silver.
def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(
            payload,
            "source.project_public_id",
            "list_data.Project ID",
            "detail_data.project_fields.Project ID",
        ),
        "project_internal_id": lambda payload, _file_path: first_non_empty(
            payload,
            "source.project_internal_id",
            "list_data.project_internal_id",
        ),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project_fields.Project Name",
            "list_data.Project Name",
        ),
        "project_voluntary_status": lambda payload, _file_path: normalize_missing(
            get_path(payload, "list_data.Voluntary Status")
        ),
        "project_regulatory_status": lambda payload, _file_path: normalize_missing(
            get_path(payload, "list_data.Compliance Program Status (ARB or Ecology)")
        ),
        "standard_program": lambda payload, _file_path: None,
        "project_description": lambda payload, _file_path: normalize_missing(
            get_path(payload, "detail_data.project_fields.Project Description")
        ),
        "project_methodology": lambda payload, _file_path: normalize_project_methodology(
            normalize_missing(get_path(payload, "list_data.Project Methodology/Protocol"))
        ),
        "project_type": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project_fields.Project Type",
            "list_data.Project Type",
        ),
        "sector": lambda payload, _file_path: None,
        "project_category": lambda payload, _file_path: None,
        "project_subcategories": lambda payload, _file_path: None,
        "sdg_targets": lambda payload, _file_path: split_semicolon_values(
            get_path(payload, "list_data.Sustainable Development Goal(s)")
        ),
        "project_developer": lambda payload, _file_path: normalize_missing(
            get_path(payload, "list_data.Project Developer")
        ),
        "project_owner": lambda payload, _file_path: normalize_missing(
            get_path(payload, "detail_data.project_fields.Authorized Project Designee")
        ),
        "project_operator": lambda payload, _file_path: normalize_missing(
            get_path(payload, "detail_data.project_fields.Offset Project Operator")
        ),
        "validator_name": lambda payload, _file_path: normalize_missing(
            get_path(payload, "list_data.ACR Project Validation")
        ),
        "verifier_name": lambda payload, _file_path: normalize_missing(
            get_path(payload, "list_data.Current VVB")
        ),
        "country": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project_fields.Project Site Country",
            "list_data.Project Site Country",
        ),
        "state_or_region": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project_fields.Project Site State (Primary)",
            "list_data.Project Site State",
        ),
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: None,
        "location_longitude": lambda payload, _file_path: None,
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: parse_date(
            get_path(payload, "detail_data.project_fields.Project Registration/Listing Date")
        ),
        "status_date": lambda payload, _file_path: parse_date(get_path(payload, "list_data.Project Status Date")),
        "crediting_start_date": lambda payload, _file_path: parse_date(
            get_path(payload, "list_data.Current Crediting Period Start Date")
        ),
        "crediting_end_date": lambda payload, _file_path: parse_date(
            get_path(payload, "list_data.Current Crediting Period End Date")
        ),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: parse_count(
            get_path(payload, "list_data.Total Number of Credits Registered")
        ),
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


