# Objetivo do script:
# Analisar os arquivos bronze da Social Carbon e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

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
    get_path,
    normalize_project_methodology,
    path_candidate,
    run_mapping,
)


DISPLAY_NAME = "Social Carbon"
BRONZE_SLUG = "social_carbon"
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
                extractor=lambda payload, _file_path: "SC",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "Project ID")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "_id")],
        "project_url": [path_candidate("source", "project_url")],
        "bronze_file_path": [path_candidate("file_system", "bronze_file_path", rule_type="derived", notes="Derivado do caminho do arquivo de detalhe no filesystem.")],
        "source_file_name": [path_candidate("file_system", "source_file_name", rule_type="derived", notes="Derivado do nome do arquivo de detalhe no filesystem.")],
        "project_name": [path_candidate("detail_data", "Project Name"), path_candidate("list_data", "Project Name")],
        "project_voluntary_status": [path_candidate("detail_data", "Project Status"), path_candidate("list_data", "Project Status")],
        "project_regulatory_status": [],
        "standard_program": [path_candidate("detail_data", "Standard"), path_candidate("list_data", "Standard")],
        "project_description": [path_candidate("detail_data", "Description"), path_candidate("list_data", "Description")],
        "project_methodology": [
            CandidateSource(
                source_section="detail_data",
                source_path="Methodology",
                rule_type="normalized",
                notes="Separa multiplas metodologias quando a Social Carbon as expuser em uma unica string delimitada por virgula ou ponto e virgula.",
                extractor=lambda payload, _file_path: normalize_project_methodology(
                    get_path(payload, "detail_data.Methodology") or get_path(payload, "list_data.Methodology"),
                    split_pattern=r"\s*[,;]\s*",
                ),
            )
        ],
        "project_type": [path_candidate("detail_data", "Project Type"), path_candidate("list_data", "Project Type")],
        "sector": [],
        "project_category": [path_candidate("detail_data", "Project Type"), path_candidate("list_data", "Project Type")],
        "project_subcategories": [],
        "sdg_targets": [path_candidate("detail_data", "SDGs"), path_candidate("list_data", "SDGs")],
        "project_developer": [path_candidate("detail_data", "Project Proponent(s)_TEXT"), path_candidate("list_data", "Project Proponent(s)_TEXT")],
        "project_owner": [],
        "project_operator": [],
        "validator_name": [path_candidate("detail_data", "validator"), path_candidate("list_data", "validator")],
        "verifier_name": [path_candidate("detail_data", "verifier"), path_candidate("list_data", "verifier")],
        "country": [path_candidate("detail_data", "Country"), path_candidate("list_data", "Country")],
        "state_or_region": [],
        "city_or_locality": [],
        "location_latitude": [path_candidate("detail_data", "Latitude"), path_candidate("list_data", "Latitude")],
        "location_longitude": [path_candidate("detail_data", "Longitude"), path_candidate("list_data", "Longitude")],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "Created Date"), path_candidate("list_data", "Created Date")],
        "status_date": [],
        "crediting_start_date": [path_candidate("detail_data", "Crediting period start"), path_candidate("list_data", "Crediting period start")],
        "crediting_end_date": [path_candidate("detail_data", "Crediting period end"), path_candidate("list_data", "Crediting period end")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [],
        "credits_retired_total": [],
        "credits_cancelled_total": [],
        "credits_buffer_total": [],
        "estimated_annual_emission_reductions": [path_candidate("detail_data", "Estimated Annual Emission Reductions"), path_candidate("list_data", "Estimated Annual Emission Reductions")],
        "estimated_total_emission_reductions": [],
        "area_hectares": [path_candidate("detail_data", "Total Project Area"), path_candidate("list_data", "Total Project Area")],
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



