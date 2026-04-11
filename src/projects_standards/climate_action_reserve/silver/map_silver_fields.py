# Objetivo do script:
# Analisar os arquivos bronze da Climate Action Reserve e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

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
    normalize_missing,
    path_candidate,
    run_mapping,
    scalar_or_list,
    transformed_candidate,
)


DISPLAY_NAME = "Climate Action Reserve"
BRONZE_SLUG = "climate_action_reserve"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


def sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)$", path.stem)
    if match:
        return int(match.group(1)), path.stem
    return 10**12, path.stem


def parse_project_type_code(value: Any) -> Any:
    text = normalize_missing(value)
    if text is None:
        return None
    match = re.match(r"^([A-Z]{2,}(?:[-_.][A-Z0-9]+)+|[A-Z]{2,}\d{2,})\b", str(text))
    return match.group(1) if match else None


def split_semicolon_values(value: Any) -> Any:
    text = normalize_missing(value)
    if text is None:
        return None
    parts = [part.strip() for part in str(text).split(";") if part.strip()]
    return scalar_or_list(parts)


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "CAR",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "Project ID")],
        "project_internal_id": [path_candidate("source", "project_internal_id")],
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
        "project_name": [path_candidate("detail_data", "Project Name"), path_candidate("list_data", "Project Name")],
        "project_voluntary_status": [path_candidate("detail_data", "Project Status"), path_candidate("list_data", "Status")],
        "project_regulatory_status": [path_candidate("list_data", "Compliance Program Status")],
        "standard_program": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "project_description": [path_candidate("detail_data", "Project Description")],
        "project_methodology": [],
        "project_type": [path_candidate("detail_data", "Project Type"), path_candidate("list_data", "Project Type")],
        "sector": [],
        "project_category": [],
        "project_subcategories": [
            transformed_candidate(
                "list_data",
                "Additional Certification(s)",
                split_semicolon_values,
                "Divide certificacoes adicionais separadas por ponto e virgula quando presentes.",
                "normalized",
            )
        ],
        "sdg_targets": [
            transformed_candidate(
                "list_data",
                "SDG Impact",
                split_semicolon_values,
                "Mantem o texto bruto de SDG Impact, dividido por ponto e virgula quando necessario.",
                "normalized",
            )
        ],
        "project_developer": [path_candidate("list_data", "Project Developer")],
        "project_owner": [path_candidate("list_data", "Project Owner")],
        "project_operator": [path_candidate("detail_data", "Offset Project Operator"), path_candidate("list_data", "Offset Project Operator")],
        "validator_name": [path_candidate("list_data", "Verification Body"), path_candidate("detail_data", "Verification Bodies")],
        "verifier_name": [path_candidate("list_data", "Verification Body"), path_candidate("detail_data", "Verification Bodies")],
        "country": [path_candidate("detail_data", "Country"), path_candidate("list_data", "Project Site Country")],
        "state_or_region": [path_candidate("detail_data", "State/Province/Department"), path_candidate("list_data", "Project Site State")],
        "city_or_locality": [],
        "location_latitude": [],
        "location_longitude": [],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "Project Registered Date"), path_candidate("list_data", "Project Registered Date")],
        "status_date": [],
        "crediting_start_date": [path_candidate("detail_data", "Project Reporting Start Date"), path_candidate("detail_data", "Project Commencement Date")],
        "crediting_end_date": [path_candidate("detail_data", "Crediting Period Expires")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [path_candidate("list_data", "Total Number of Offset Credits Registered ")],
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



