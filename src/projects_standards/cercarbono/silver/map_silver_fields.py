# Objetivo do script:
# Analisar os arquivos bronze da Cercarbono e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

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
    ensure_list,
    get_path,
    normalize_missing,
    path_candidate,
    run_mapping,
    scalar_or_list,
    transformed_candidate,
)


DISPLAY_NAME = "Cercarbono"
BRONZE_SLUG = "cercarbono"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


def sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)$", path.stem)
    if match:
        return int(match.group(1)), path.stem
    return 10**12, path.stem


def extract_methodology_codes(value: Any) -> Any:
    if not isinstance(value, list):
        return None

    codes: list[str] = []
    for item in value:
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
    return scalar_or_list(codes)


def extract_methodology_names(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("description") for item in value if isinstance(item, dict)])


def extract_project_description(payload: dict[str, Any], _: Path) -> Any:
    return normalize_missing(
        get_path(payload, "detail_data.project.descriptionProjectIng")
        or get_path(payload, "detail_data.project.descriptionProject")
        or get_path(payload, "list_data.name")
    )


def extract_sdg_targets(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("description") for item in value if isinstance(item, dict)])


def extract_protocols(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("description") for item in value if isinstance(item, dict)])


def extract_type_mechanism(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("type_mechanism") for item in value if isinstance(item, dict)])


def extract_type_avoidance_removals(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("type_avoidance_removals") for item in value if isinstance(item, dict)])


def extract_best_location(payload: dict[str, Any], field_name: str) -> Any:
    locations = get_path(payload, "detail_data.locations")
    if not isinstance(locations, list):
        return None

    preferred = None
    for location in locations:
        if not isinstance(location, dict):
            continue
        if location.get("checked") is True:
            preferred = location
            break
        if preferred is None:
            preferred = location

    if not isinstance(preferred, dict):
        return None
    return normalize_missing(preferred.get(field_name))


def location_candidate(field_name: str, notes: str = "") -> CandidateSource:
    return CandidateSource(
        source_section="detail_data",
        source_path=f"locations[*].{field_name}",
        rule_type="selection",
        notes=notes,
        extractor=lambda payload, _file_path: extract_best_location(payload, field_name),
    )


def extract_best_coordinate(payload: dict[str, Any], coordinate_name: str) -> Any:
    locations = get_path(payload, "detail_data.locations")
    if not isinstance(locations, list):
        return None

    preferred = None
    for location in locations:
        if not isinstance(location, dict):
            continue
        if location.get("checked") is True:
            preferred = location
            break
        if preferred is None:
            preferred = location

    if not isinstance(preferred, dict):
        return None
    data_map = preferred.get("dataMap")
    if not isinstance(data_map, dict):
        return None
    return normalize_missing(data_map.get(coordinate_name))


def coordinate_candidate(coordinate_name: str) -> CandidateSource:
    return CandidateSource(
        source_section="detail_data",
        source_path=f"locations[*].dataMap.{coordinate_name}",
        rule_type="selection",
        notes="Seleciona a coordenada da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe.",
        extractor=lambda payload, _file_path: extract_best_coordinate(payload, coordinate_name),
    )


def extract_credits_issued(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    totals: list[Any] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        total = normalize_missing(item.get("total"))
        if total is not None:
            totals.append(total)
    if not totals:
        return None
    return sum(int(str(total).replace(",", "")) for total in totals)


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "CCR",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "code")],
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
        "project_name": [path_candidate("detail_data", "project.name"), path_candidate("list_data", "name")],
        "project_voluntary_status": [path_candidate("list_data", "projectStage")],
        "standard_program": [path_candidate("list_data", "standard"), path_candidate("detail_data", "project.standarDescription")],
        "project_description": [
            CandidateSource(
                source_section="detail_data",
                source_path="project.descriptionProjectIng",
                rule_type="fallback",
                notes="Prioriza a descricao em ingles do detalhe, com fallback para a descricao principal em espanhol.",
                extractor=extract_project_description,
            )
        ],
        "project_methodology": [
            transformed_candidate(
                "list_data",
                "methodology",
                extract_methodology_names,
                "Usa a lista estruturada de metodologias da Cercarbono.",
                "normalized",
            )
        ],
        "project_type": [
            transformed_candidate(
                "list_data",
                "methodology",
                extract_type_mechanism,
                "Usa o tipo de mecanismo da metodologia quando a Cercarbono o expuser.",
                "normalized",
            )
        ],
        "sector": [path_candidate("list_data", "sectorsText")],
        "project_category": [
            transformed_candidate(
                "list_data",
                "methodology",
                extract_type_avoidance_removals,
                "Usa a classificacao Avoidance ou Removal associada a metodologia.",
                "normalized",
            )
        ],
        "project_subcategories": [
            transformed_candidate(
                "list_data",
                "protocols",
                extract_protocols,
                "Usa os protocolos associados ao projeto como classificacao complementar.",
                "normalized",
            )
        ],
        "sdg_targets": [
            transformed_candidate(
                "list_data",
                "projectsGlobalGoal",
                extract_sdg_targets,
                "Mantem a representacao textual bruta dos ODS expostos pela Cercarbono, pois o snapshot nao traz codigo estruturado de target.",
                "normalized",
            )
        ],
        "project_developer": [path_candidate("list_data", "developer")],
        "validator_name": [path_candidate("detail_data", "project.validator"), path_candidate("list_data", "verifier")],
        "verifier_name": [path_candidate("detail_data", "project.verifier"), path_candidate("list_data", "verifier")],
        "country": [
            location_candidate(
                "countryDescription",
                "Seleciona o pais da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe.",
            ),
            path_candidate("list_data", "locationText"),
        ],
        "state_or_region": [
            location_candidate(
                "regionDescription",
                "Seleciona a regiao da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe.",
            )
        ],
        "city_or_locality": [
            location_candidate(
                "cityDescription",
                "Seleciona a cidade ou localidade da localizacao marcada como checked=true, com fallback para a primeira localizacao do detalhe.",
            )
        ],
        "location_latitude": [coordinate_candidate("latitude")],
        "location_longitude": [coordinate_candidate("longitude")],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "project.date")],
        "crediting_start_date": [path_candidate("detail_data", "project.periodInit"), path_candidate("detail_data", "project.projectsCreditingPeriod.0.periodInit")],
        "crediting_end_date": [path_candidate("detail_data", "project.periodEnd"), path_candidate("detail_data", "project.projectsCreditingPeriod.0.periodEnd")],
        "credits_issued_total": [
            transformed_candidate(
                "detail_data",
                "certificatedVerification",
                extract_credits_issued,
                "Soma os totais de certificatedVerification para representar os creditos emitidos no snapshot.",
                "aggregate",
            )
        ],
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



