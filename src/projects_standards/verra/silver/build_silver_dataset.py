# Objetivo do script:
# Consolidar os arquivos bronze da Verra em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.
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
    parse_count,
    parse_date,
    parse_decimal_measure,
    path_candidate,
    run_dataset,
    scalar_or_list,
)
from src.projects_standards.verra.silver.sync_country_reference import sync_country_reference_for_projects  # noqa: E402
from src.projects_standards.verra.silver.sync_methodology_reference import sync_methodology_reference_for_projects  # noqa: E402
from src.projects_standards.verra.silver.sync_status_reference import sync_status_reference_for_projects  # noqa: E402



DISPLAY_NAME = "Verra"
BRONZE_SLUG = "verra"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


# Coleta todos os valores uteis associados a um atributo estruturado.
def get_attribute_values(attributes: Any, code: str) -> list[Any]:
    if not isinstance(attributes, list):
        return []

    results: list[Any] = []
    for item in attributes:
        if not isinstance(item, dict) or item.get("code") != code:
            continue
        values = item.get("values")
        if not isinstance(values, list):
            continue
        for value_item in values:
            if not isinstance(value_item, dict):
                continue
            value = value_item.get("value")
            if value not in (None, ""):
                results.append(value)
    return results


# Retorna o primeiro valor util encontrado para um atributo estruturado.
def get_first_attribute_value(attributes: Any, code: str) -> Any:
    values = get_attribute_values(attributes, code)
    return values[0] if values else None


# Coleta os valores de um atributo presente no bloco detail_data.attributes.
def get_detail_attribute_values(payload: dict[str, Any], code: str) -> list[Any]:
    return get_attribute_values(get_path(payload, "detail_data.attributes"), code)


# Retorna o primeiro valor util de um atributo presente no detalhe.
def get_detail_attribute_value(payload: dict[str, Any], code: str) -> Any:
    return get_first_attribute_value(get_path(payload, "detail_data.attributes"), code)


# Coleta os valores de um atributo presente nos participationSummaries.
def get_participation_attribute_values(payload: dict[str, Any], code: str) -> list[Any]:
    summaries = get_path(payload, "detail_data.participationSummaries")
    if not isinstance(summaries, list):
        return []

    results: list[Any] = []
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        results.extend(get_attribute_values(summary.get("attributes"), code))
    return results


# Retorna o primeiro valor util de um atributo presente nos participationSummaries.
def get_participation_attribute_value(payload: dict[str, Any], code: str) -> Any:
    values = get_participation_attribute_values(payload, code)
    return values[0] if values else None


# Extrai as datas de inicio e fim do periodo de crediting a partir de texto livre.
def parse_crediting_period_dates(value: Any) -> tuple[str | None, str | None]:
    if value in (None, ""):
        return None, None
    text = str(value)
    matches = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", text)
    if len(matches) < 2:
        return None, None
    return parse_date(matches[0]), parse_date(matches[1])


# Ordena os arquivos de detalhe pelo identificador interno do projeto.
def sort_key(path: Path) -> int:
    return int(path.stem)


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
        "project_name": lambda payload, _file_path: get_path(payload, "detail_data.resourceName")
        or get_path(payload, "list_data.resourceName"),
        "project_voluntary_status": lambda payload, _file_path: get_participation_attribute_value(payload, "PROJECT_STATUS")
        or get_path(payload, "list_data.resourceStatus"),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: get_path(payload, "list_data.program"),
        "project_description": lambda payload, _file_path: get_path(payload, "detail_data.description"),
        "project_methodology": lambda payload, _file_path: normalize_project_methodology(
            get_participation_attribute_values(payload, "PROTOCOL_NAME")
            or ensure_list(get_path(payload, "list_data.protocols")),
            split_pattern=r"\s*[,;]\s*",
        ),
        "project_type": lambda payload, _file_path: get_path(payload, "list_data.version"),
        "sector": lambda payload, _file_path: get_path(payload, "list_data.protocolCategories")
        or get_participation_attribute_value(payload, "PRIMARY_PROJECT_CATEGORY_NAME"),
        "project_category": lambda payload, _file_path: get_participation_attribute_value(
            payload, "PRIMARY_PROJECT_CATEGORY_NAME"
        )
        or get_path(payload, "list_data.protocolCategories"),
        "project_subcategories": lambda payload, _file_path: scalar_or_list(
            get_participation_attribute_values(payload, "PROJECT_SUBCATERGORY_NAMES")
            or ensure_list(get_path(payload, "list_data.protocolSubCategories"))
        ),
        "sdg_targets": lambda payload, _file_path: scalar_or_list(
            ensure_list(get_path(payload, "list_data.programObjectives"))
        ),
        "project_developer": lambda payload, _file_path: get_participation_attribute_value(payload, "PROPONENT_NAME")
        or get_path(payload, "list_data.proponent"),
        "project_owner": lambda payload, _file_path: None,
        "project_operator": lambda payload, _file_path: get_path(payload, "list_data.operator"),
        "validator_name": lambda payload, _file_path: get_participation_attribute_value(payload, "VALIDATOR_NAME"),
        "verifier_name": lambda payload, _file_path: None,
        "country": lambda payload, _file_path: get_path(payload, "list_data.country"),
        "state_or_region": lambda payload, _file_path: get_detail_attribute_value(payload, "STATE_PROVINCE"),
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: get_path(payload, "detail_data.location.latitude"),
        "location_longitude": lambda payload, _file_path: get_path(payload, "detail_data.location.longitude"),
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: parse_date(get_path(payload, "list_data.projectRegistrationDate"))
        or parse_date(get_participation_attribute_value(payload, "PROJECT_REGISTRATION_DATE")),
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(
            get_path(payload, "list_data.creditingPeriodStartDate")
        )
        or parse_crediting_period_dates(get_participation_attribute_value(payload, "CREDIT_PERIOD_INFO"))[0],
        "crediting_end_date": lambda payload, _file_path: parse_date(
            get_path(payload, "list_data.creditingPeriodEndDate")
        )
        or parse_crediting_period_dates(get_participation_attribute_value(payload, "CREDIT_PERIOD_INFO"))[1],
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": lambda payload, _file_path: None,
        "credits_retired_total": lambda payload, _file_path: None,
        "credits_cancelled_total": lambda payload, _file_path: None,
        "credits_buffer_total": lambda payload, _file_path: None,
        "estimated_annual_emission_reductions": lambda payload, _file_path: parse_count(
            get_path(payload, "list_data.estAnnualEmissionReductions")
        )
        or parse_count(get_participation_attribute_value(payload, "EST_ANNUAL_EMISSION_REDCT")),
        "estimated_total_emission_reductions": lambda payload, _file_path: None,
        "area_hectares": lambda payload, _file_path: parse_decimal_measure(
            get_participation_attribute_value(payload, "PROJECT_ACREAGE")
        ),
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

