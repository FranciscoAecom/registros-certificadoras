# Objetivo do script:
# Consolidar os arquivos bronze da BioCarbon em um unico dataset JSON na camada silver seguindo o schema canonico do projeto.
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



DISPLAY_NAME = "BioCarbon"
BRONZE_SLUG = "biocarbon"
DATASET_OUTPUT_TEMPLATE = ROOT_DIR / "data" / "project_standards" / "02_silver" / BRONZE_SLUG / "{date}" / "allprojects.json"
FAILURE_OUTPUT_TEMPLATE = CURRENT_DIR / "logs" / "build_silver_dataset_failures_{date}.json"


# Ordena os arquivos de detalhe pelo identificador publico.
def sort_key(path: Path) -> str:
    return path.stem


# Extrai codigos de metodologias a partir da lista estruturada da BioCarbon.
def extract_methodology_codes(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("code") for item in value if isinstance(item, dict)])


# Extrai nomes de metodologias a partir da lista estruturada da BioCarbon.
def extract_methodology_names(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("name") for item in value if isinstance(item, dict)])


# Extrai os ODS usando a melhor representacao textual estruturada da BioCarbon.
def extract_sdg_targets(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    targets: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        for key in ("text_cadt", "text_thallo", "name"):
            candidate = normalize_missing(item.get(key))
            if candidate is not None:
                targets.append(candidate)
                break
    return scalar_or_list(targets)


# Soma os valores numericos de uma lista de registros.
def sum_amounts(items: Any) -> int | None:
    if not isinstance(items, list):
        return None
    total = 0
    found = False
    for item in items:
        if not isinstance(item, dict):
            continue
        amount = parse_count(item.get("amount"))
        if amount is None:
            continue
        total += int(amount)
        found = True
    return total if found else None


# Calcula o total emitido apenas quando o bronze explicita os creditos emitidos.
def extract_issued_total(payload: dict[str, Any], _: Path) -> Any:
    carbon_credits = get_path(payload, "detail_data.carbon_credits")
    if not isinstance(carbon_credits, dict):
        return None
    if carbon_credits.get("last_page") not in (None, 0, 1):
        return None
    return sum_amounts(carbon_credits.get("data"))


# Calcula o total de retiros apenas quando o bronze contem todas as paginas no mesmo payload.
def extract_retired_total(payload: dict[str, Any], _: Path) -> Any:
    retreats = get_path(payload, "detail_data.retreats")
    if not isinstance(retreats, dict):
        return None
    if retreats.get("last_page") not in (None, 0, 1):
        return None
    return sum_amounts(retreats.get("data"))


# Monta as regras de transformacao campo a campo para a camada silver.
def build_transformers(standard_acronym: str | None) -> dict[str, Callable[[dict[str, Any], Path], Any]]:
    return {
        "standard_name": lambda payload, _file_path: get_path(payload, "source.carbon_standard"),
        "standard_acronym": lambda payload, _file_path: standard_acronym,
        "project_public_id": lambda payload, _file_path: first_non_empty(
            payload,
            "source.project_public_id",
            "list_data.project_id",
            "detail_data.project.initiative.code",
        ),
        "project_internal_id": lambda payload, _file_path: first_non_empty(
            payload,
            "source.project_internal_id",
            "list_data.id",
            "detail_data.project.initiative.id",
        ),
        "project_url": lambda payload, _file_path: get_path(payload, "source.project_url"),
        "bronze_file_path": lambda payload, file_path: path_candidate("file_system", "bronze_file_path").extractor(payload, file_path),
        "source_file_name": lambda payload, file_path: path_candidate("file_system", "source_file_name").extractor(payload, file_path),
        "project_name": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.name",
            "list_data.project_name",
        ),
        "project_voluntary_status": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.status",
            "list_data.status",
        ),
        "project_regulatory_status": lambda payload, _file_path: None,
        "standard_program": lambda payload, _file_path: get_path(payload, "detail_data.project.initiative.applicable_standard"),
        "project_description": lambda payload, _file_path: get_path(payload, "detail_data.project.initiative.description"),
        "project_methodology": lambda payload, _file_path: extract_methodology_names(
            get_path(payload, "detail_data.project.initiative.methodologies")
        ),
        "project_type": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.type_project_name",
            "list_data.type_project_name",
        ),
        "sector": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.sector_name",
            "list_data.sector_name",
        ),
        "project_category": lambda payload, _file_path: get_path(payload, "detail_data.project.initiative.type_project.short_name"),
        "project_subcategories": lambda payload, _file_path: get_path(payload, "detail_data.project.initiative.type_project.name"),
        "sdg_targets": lambda payload, _file_path: extract_sdg_targets(
            get_path(payload, "detail_data.project.initiative.objetives")
        ),
        "project_developer": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.holder_name",
            "list_data.holder_name",
        ),
        "project_owner": lambda payload, _file_path: get_path(payload, "detail_data.project.initiative.holder.holder"),
        "project_operator": lambda payload, _file_path: normalize_missing(
            get_path(payload, "detail_data.project.initiative.participants")
        ),
        "validator_name": lambda payload, _file_path: get_path(payload, "detail_data.project.initiative.validation_body.name"),
        "verifier_name": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.ovv",
            "list_data.ovv",
        ),
        "country": lambda payload, _file_path: first_non_empty(
            payload,
            "detail_data.project.initiative.country",
            "list_data.country",
        ),
        "state_or_region": lambda payload, _file_path: None,
        "city_or_locality": lambda payload, _file_path: None,
        "location_latitude": lambda payload, _file_path: parse_coordinate(
            get_path(payload, "detail_data.project.initiative.latitude")
        ),
        "location_longitude": lambda payload, _file_path: parse_coordinate(
            get_path(payload, "detail_data.project.initiative.longitude")
        ),
        "snapshot_date": lambda payload, _file_path: get_path(payload, "source.snapshot_date"),
        "reference_month": lambda payload, _file_path: get_path(payload, "source.reference_month"),
        "registration_date": lambda payload, _file_path: parse_date(
            first_non_empty(
                payload,
                "detail_data.project.initiative.acceptance_date",
                "detail_data.project.initiative.certification_acceptance_date",
            )
        ),
        "status_date": lambda payload, _file_path: None,
        "crediting_start_date": lambda payload, _file_path: parse_date(
            first_non_empty(
                payload,
                "detail_data.project.initiative.quantification_period_start",
                "list_data.quantification_period_start",
            )
        ),
        "crediting_end_date": lambda payload, _file_path: parse_date(
            first_non_empty(
                payload,
                "detail_data.project.initiative.quantification_period_end",
                "list_data.quantification_period_end",
            )
        ),
        "first_issuance_date": lambda payload, _file_path: None,
        "last_issuance_date": lambda payload, _file_path: None,
        "credits_issued_total": extract_issued_total,
        "credits_retired_total": extract_retired_total,
        "credits_cancelled_total": lambda payload, _file_path: None,
        "credits_buffer_total": lambda payload, _file_path: None,
        "estimated_annual_emission_reductions": lambda payload, _file_path: None,
        "estimated_total_emission_reductions": lambda payload, _file_path: parse_count(
            get_path(payload, "detail_data.project.initiative.total_reductions_general")
        ),
        "area_hectares": lambda payload, _file_path: None,
    }


CONFIG = {
    "display_name": DISPLAY_NAME,
    "bronze_slug": BRONZE_SLUG,
    "reference_name": "BioCarbon Registry",
    "dataset_output_template": DATASET_OUTPUT_TEMPLATE,
    "failure_output_template": FAILURE_OUTPUT_TEMPLATE,
    "transformers": build_transformers,
    "sort_key": sort_key,
    "post_build_hooks": [sync_status_reference_for_projects, sync_country_reference_for_projects, sync_methodology_reference_for_projects],
}


if __name__ == "__main__":
    raise SystemExit(run_dataset(CONFIG))


