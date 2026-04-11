# Objetivo do script:
# Analisar os arquivos bronze da American Carbon Registry e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

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


DISPLAY_NAME = "American Carbon Registry"
BRONZE_SLUG = "american_carbon_registry"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


def sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)$", path.stem)
    if match:
        return int(match.group(1)), path.stem
    return 10**12, path.stem


def split_semicolon_values(value: Any) -> Any:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    parts = [part.strip() for part in str(clean_value).split(";") if part.strip()]
    return scalar_or_list(parts)


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


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "ACR",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "Project ID")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "project_internal_id")],
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
        "project_name": [
            path_candidate("detail_data", "project_fields.Project Name"),
            path_candidate("list_data", "Project Name"),
        ],
        "project_voluntary_status": [path_candidate("list_data", "Voluntary Status")],
        "project_regulatory_status": [path_candidate("list_data", "Compliance Program Status (ARB or Ecology)")],
        "standard_program": [],
        "project_description": [path_candidate("detail_data", "project_fields.Project Description", rule_type="rename")],
        "project_methodology": [path_candidate("list_data", "Project Methodology/Protocol")],
        "project_type": [path_candidate("list_data", "Project Type")],
        "sector": [],
        "project_category": [],
        "project_subcategories": [],
        "sdg_targets": [
            transformed_candidate(
                "list_data",
                "Sustainable Development Goal(s)",
                split_semicolon_values,
                "Preserva a lista textual de ODS como exposta pela ACR, separada por ponto e virgula.",
                "normalized",
            )
        ],
        "project_developer": [path_candidate("list_data", "Project Developer")],
        "project_owner": [path_candidate("detail_data", "project_fields.Authorized Project Designee")],
        "project_operator": [path_candidate("detail_data", "project_fields.Offset Project Operator")],
        "validator_name": [path_candidate("list_data", "ACR Project Validation")],
        "verifier_name": [path_candidate("list_data", "Current VVB")],
        "country": [
            path_candidate("detail_data", "project_fields.Project Site Country"),
            path_candidate("list_data", "Project Site Country"),
        ],
        "state_or_region": [
            path_candidate("detail_data", "project_fields.Project Site State (Primary)"),
            path_candidate("list_data", "Project Site State"),
        ],
        "city_or_locality": [],
        "location_latitude": [],
        "location_longitude": [],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "project_fields.Project Registration/Listing Date")],
        "status_date": [path_candidate("list_data", "Project Status Date")],
        "crediting_start_date": [path_candidate("list_data", "Current Crediting Period Start Date")],
        "crediting_end_date": [path_candidate("list_data", "Current Crediting Period End Date")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [
            path_candidate(
                "list_data",
                "Total Number of Credits Registered",
                rule_type="normalized",
                notes="Usa o total de creditos registrados da ACR como melhor aproximacao operacional para o total emitido no snapshot.",
            )
        ],
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



