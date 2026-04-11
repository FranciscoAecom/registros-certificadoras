# Objetivo do script:
# Analisar os arquivos bronze da Plan Vivo e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

# Processo:
# 1. Ler argumentos CLI (--date, --output, --sample-fraction, --limit).
# 2. Carregar amostra hibrida de arquivos bronze do snapshot (maiores + aleatorios).
# 3. Inspecionar campos presentes em list_data e detail_data de cada arquivo.
# 4. Mapear campos bronze para o schema canonico silver com regras de extracao.
# 5. Calcular cobertura percentual de cada campo candidato na amostra.
# 6. Gerar relatorio de mapeamento em JSON ou Markdown.

import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import (  # noqa: E402
    CandidateSource,
    path_candidate,
    transformed_candidate,
    run_mapping,
)


DISPLAY_NAME = "Plan Vivo"
BRONZE_SLUG = "plan_vivo"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


def sort_key(path: Path) -> str:
    return path.stem


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "PV",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "project_slug")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "project_slug")],
        "project_url": [path_candidate("source", "project_url"), path_candidate("detail_data", "canonical_url")],
        "bronze_file_path": [path_candidate("file_system", "bronze_file_path", rule_type="derived", notes="Derivado do caminho do arquivo de detalhe no filesystem.")],
        "source_file_name": [path_candidate("file_system", "source_file_name", rule_type="derived", notes="Derivado do nome do arquivo de detalhe no filesystem.")],
        "project_name": [path_candidate("detail_data", "page_title"), path_candidate("list_data", "project_title")],
        "project_voluntary_status": [path_candidate("list_data", "tags.0")],
        "project_regulatory_status": [],
        "standard_program": [path_candidate("detail_data", "project_summary.certified_beneath")],
        "project_description": [path_candidate("detail_data", "about_the_project"), path_candidate("list_data", "summary"), path_candidate("detail_data", "meta_description")],
        "project_methodology": [],
        "project_type": [path_candidate("detail_data", "project_summary.activities")],
        "sector": [],
        "project_category": [path_candidate("detail_data", "project_summary.activities")],
        "project_subcategories": [],
        "sdg_targets": [],
        "project_developer": [path_candidate("detail_data", "project_summary.coordinators"), path_candidate("detail_data", "project_summary.coordinators.0")],
        "project_owner": [],
        "project_operator": [],
        "validator_name": [],
        "verifier_name": [],
        "country": [path_candidate("detail_data", "project_summary.country")],
        "state_or_region": [],
        "city_or_locality": [],
        "location_latitude": [],
        "location_longitude": [],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "project_summary.start_date")],
        "status_date": [],
        "crediting_start_date": [path_candidate("detail_data", "project_summary.start_date")],
        "crediting_end_date": [],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [
            transformed_candidate(
                "detail_data",
                "project_summary.pvcs_issued_to_date",
                lambda value: value,
                notes="Usa o total de PVCs emitidos ate a data exibido na capa do projeto.",
                rule_type="direct",
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



