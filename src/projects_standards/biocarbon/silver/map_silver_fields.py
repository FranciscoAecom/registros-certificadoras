# Objetivo do script:
# Analisar os arquivos bronze da BioCarbon e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

# Processo:
# 1. Ler argumentos CLI (--date, --output, --sample-fraction, --limit).
# 2. Carregar amostra hibrida de arquivos bronze do snapshot (maiores + aleatorios).
# 3. Inspecionar campos presentes em list_data e detail_data de cada arquivo.
# 4. Mapear campos bronze para o schema canonico silver com regras de extracao.
# 5. Calcular cobertura percentual de cada campo candidato na amostra.
# 6. Gerar relatorio de mapeamento em JSON ou Markdown.

import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import (  # noqa: E402
    CandidateSource,
    get_path,
    normalize_missing,
    path_candidate,
    run_mapping,
    scalar_or_list,
    transformed_candidate,
)


DISPLAY_NAME = "BioCarbon"
BRONZE_SLUG = "biocarbon"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


def sort_key(path: Path) -> str:
    return path.stem


def extract_methodology_codes(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("code") for item in value if isinstance(item, dict)])


def extract_methodology_names(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("name") for item in value if isinstance(item, dict)])


def extract_sdg_targets(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    targets: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        for key in ("text_cadt", "text_thallo", "name"):
            if normalize_missing(item.get(key)):
                targets.append(item[key])
                break
    return scalar_or_list(targets)


def extract_retired_total(payload: dict[str, Any], _: Path) -> Any:
    retreats = get_path(payload, "detail_data.retreats")
    if not isinstance(retreats, dict):
        return None
    if retreats.get("last_page") not in (None, 0, 1):
        return None

    items = retreats.get("data")
    if not isinstance(items, list):
        return None

    total = 0
    found = False
    for item in items:
        if not isinstance(item, dict):
            continue
        amount = normalize_missing(item.get("amount"))
        if amount is None:
            continue
        total += int(str(amount).replace(",", ""))
        found = True
    return total if found else None


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "BCR",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "project_id")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "id")],
        "project_url": [path_candidate("source", "project_url")],
        "bronze_file_path": [
            path_candidate(
                "file_system",
                "bronze_file_path",
                rule_type="derived",
                notes="Derivado do caminho do arquivo de detalhe no filesystem.",
            )
        ],
        "source_file_name": [
            path_candidate(
                "file_system",
                "source_file_name",
                rule_type="derived",
                notes="Derivado do nome do arquivo de detalhe no filesystem.",
            )
        ],
        "project_name": [path_candidate("detail_data", "project.initiative.name"), path_candidate("list_data", "project_name")],
        "project_voluntary_status": [path_candidate("detail_data", "project.initiative.status")],
        "project_regulatory_status": [],
        "standard_program": [path_candidate("detail_data", "project.initiative.applicable_standard")],
        "project_description": [path_candidate("detail_data", "project.initiative.description")],
        "project_methodology": [
            transformed_candidate(
                "detail_data",
                "project.initiative.methodologies",
                extract_methodology_names,
                "Extrai os nomes de metodologia da lista estruturada de metodologias da BioCarbon.",
                "normalized",
            )
        ],
        "project_type": [path_candidate("detail_data", "project.initiative.type_project_name"), path_candidate("list_data", "type_project_name")],
        "sector": [path_candidate("detail_data", "project.initiative.sector_name"), path_candidate("list_data", "sector_name")],
        "project_category": [path_candidate("detail_data", "project.initiative.type_project.short_name")],
        "project_subcategories": [path_candidate("detail_data", "project.initiative.type_project.name")],
        "sdg_targets": [
            transformed_candidate(
                "detail_data",
                "project.initiative.objetives",
                extract_sdg_targets,
                "Usa os ODS estruturados da BioCarbon, priorizando text_cadt e text_thallo.",
                "normalized",
            )
        ],
        "project_developer": [path_candidate("detail_data", "project.initiative.holder_name")],
        "project_owner": [path_candidate("detail_data", "project.initiative.holder.holder")],
        "project_operator": [path_candidate("detail_data", "project.initiative.participants")],
        "validator_name": [path_candidate("detail_data", "project.initiative.validation_body.name")],
        "verifier_name": [path_candidate("detail_data", "project.initiative.ovv")],
        "country": [path_candidate("detail_data", "project.initiative.country"), path_candidate("list_data", "country")],
        "state_or_region": [],
        "city_or_locality": [],
        "location_latitude": [path_candidate("detail_data", "project.initiative.latitude")],
        "location_longitude": [path_candidate("detail_data", "project.initiative.longitude")],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "project.initiative.acceptance_date")],
        "status_date": [],
        "crediting_start_date": [
            path_candidate("detail_data", "project.initiative.quantification_period_start"),
            path_candidate("list_data", "quantification_period_start"),
        ],
        "crediting_end_date": [
            path_candidate("detail_data", "project.initiative.quantification_period_end"),
            path_candidate("list_data", "quantification_period_end"),
        ],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [
            path_candidate(
                "detail_data",
                "project.initiative.verified_reductions",
                rule_type="normalized",
                notes="Usa o total de reducoes verificadas exposto pela propria iniciativa como total emitido do snapshot.",
            )
        ],
        "credits_retired_total": [
            CandidateSource(
                source_section="detail_data",
                source_path="retreats.data",
                rule_type="conditional_aggregate",
                notes="Soma os retiros apenas quando o payload bruto contem todas as paginas em uma unica resposta (last_page=1).",
                extractor=extract_retired_total,
            )
        ],
        "credits_cancelled_total": [],
        "credits_buffer_total": [],
        "estimated_annual_emission_reductions": [],
        "estimated_total_emission_reductions": [path_candidate("detail_data", "project.initiative.total_reductions_general")],
        "area_hectares": [],
    }


CONFIG = {
    "display_name": DISPLAY_NAME,
    "bronze_slug": BRONZE_SLUG,
    "mapping_output_path": MAPPING_OUTPUT_PATH,
    "mapping_candidates": build_candidate_sources,
    "sort_key": sort_key,
}


if __name__ == "__main__":
    raise SystemExit(run_mapping(CONFIG))



