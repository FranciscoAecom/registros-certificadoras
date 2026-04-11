# Objetivo do script:
# Analisar os arquivos bronze da Equitable Earth e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

# Processo:
# 1. Ler argumentos CLI (--date, --output, --sample-fraction, --limit).
# 2. Carregar amostra hibrida de arquivos bronze do snapshot (maiores + aleatorios).
# 3. Inspecionar campos presentes em list_data e detail_data de cada arquivo.
# 4. Mapear campos bronze para o schema canonico silver com regras de extracao.
# 5. Calcular cobertura percentual de cada campo candidato na amostra.
# 6. Gerar relatorio de mapeamento em JSON ou Markdown.

import re
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
)


DISPLAY_NAME = "Equitable Earth"
BRONZE_SLUG = "equitable_earth"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


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


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "EQE",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "programAssignedIdentifier")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "resourceIdentifier")],
        "project_url": [path_candidate("source", "project_url")],
        "bronze_file_path": [path_candidate("file_system", "bronze_file_path", rule_type="derived", notes="Derivado do caminho do arquivo de detalhe no filesystem.")],
        "source_file_name": [path_candidate("file_system", "source_file_name", rule_type="derived", notes="Derivado do nome do arquivo de detalhe no filesystem.")],
        "project_name": [path_candidate("list_data", "resourceProgramName")],
        "project_voluntary_status": [path_candidate("list_data", "resourceProgramStatusName"), path_candidate("detail_data", "resource.programs.0.status.name")],
        "project_regulatory_status": [],
        "standard_program": [
            CandidateSource(
                source_section="detail_data",
                source_path="resource.programs[0].name",
                rule_type="fallback",
                notes="Prioriza o nome do programa no detalhe, com fallback para o codigo tecnico do programa na origem.",
                extractor=extract_program_name,
            )
        ],
        "project_description": [
            CandidateSource(
                source_section="detail_data",
                source_path="resource.programs[0].description",
                rule_type="direct",
                notes="Descricao institucional exposta no bloco de programas do detalhe.",
                extractor=extract_program_description,
            )
        ],
        "project_methodology": [path_candidate("list_data", "programProtocol"), path_candidate("detail_data", "protocol_versions.0.name")],
        "project_type": [path_candidate("list_data", "resourceTypeName")],
        "sector": [],
        "project_category": [],
        "project_subcategories": [],
        "sdg_targets": [],
        "project_developer": [
            CandidateSource(
                source_section="detail_data",
                source_path="proponents.legalEntities[0].name",
                rule_type="fallback",
                notes="Prioriza o nome estruturado do proponente no detalhe, com fallback para a string da lista.",
                extractor=extract_developer,
            )
        ],
        "project_owner": [],
        "project_operator": [],
        "validator_name": [],
        "verifier_name": [],
        "country": [
            CandidateSource(
                source_section="detail_data",
                source_path="resource.naturalGeography.address.countryIso2Code",
                rule_type="fallback",
                notes="Usa o codigo do pais no detalhe, com fallback para o codigo iso3 da lista.",
                extractor=extract_country,
            )
        ],
        "state_or_region": [path_candidate("detail_data", "resource.naturalGeography.address.countrySubdivisionName")],
        "city_or_locality": [path_candidate("detail_data", "resource.naturalGeography.address.municipality")],
        "location_latitude": [],
        "location_longitude": [],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [],
        "status_date": [],
        "crediting_start_date": [path_candidate("detail_data", "crediting_periods.currentCreditingPeriod.startDateInclusive"), path_candidate("list_data", "projectStartDate")],
        "crediting_end_date": [path_candidate("detail_data", "crediting_periods.currentCreditingPeriod.endDateExclusive")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [],
        "credits_retired_total": [],
        "credits_cancelled_total": [],
        "credits_buffer_total": [],
        "estimated_annual_emission_reductions": [],
        "estimated_total_emission_reductions": [],
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



