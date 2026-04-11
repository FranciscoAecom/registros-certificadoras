# Objetivo do script:
# Analisar os arquivos bronze da Isometric e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

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
    run_mapping,
)


DISPLAY_NAME = "Isometric"
BRONZE_SLUG = "isometric"
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
                extractor=lambda payload, _file_path: "ISM",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "id")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "id")],
        "project_url": [path_candidate("source", "project_url")],
        "bronze_file_path": [path_candidate("file_system", "bronze_file_path", rule_type="derived", notes="Derivado do caminho do arquivo de detalhe no filesystem.")],
        "source_file_name": [path_candidate("file_system", "source_file_name", rule_type="derived", notes="Derivado do nome do arquivo de detalhe no filesystem.")],
        "project_name": [path_candidate("detail_data", "name"), path_candidate("list_data", "name")],
        "project_voluntary_status": [path_candidate("detail_data", "status"), path_candidate("list_data", "status")],
        "project_regulatory_status": [],
        "standard_program": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "project_description": [path_candidate("detail_data", "description"), path_candidate("detail_data", "shortDescription")],
        "project_methodology": [path_candidate("detail_data", "protocol.name")],
        "project_type": [path_candidate("detail_data", "process.displayName")],
        "sector": [path_candidate("detail_data", "process.pathway.name"), path_candidate("list_data", "process.pathway.shortName")],
        "project_category": [path_candidate("detail_data", "process.pathway.type")],
        "project_subcategories": [path_candidate("detail_data", "process.displayName")],
        "sdg_targets": [],
        "project_developer": [path_candidate("detail_data", "supplier.organisation.name"), path_candidate("list_data", "supplier.organisation.name")],
        "project_owner": [],
        "project_operator": [],
        "validator_name": [],
        "verifier_name": [],
        "country": [path_candidate("detail_data", "country.name"), path_candidate("list_data", "country.isoAlpha3Code")],
        "state_or_region": [],
        "city_or_locality": [],
        "location_latitude": [],
        "location_longitude": [],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [path_candidate("detail_data", "validatedAt")],
        "status_date": [path_candidate("detail_data", "validatedAt")],
        "crediting_start_date": [path_candidate("detail_data", "creditingPeriodStart"), path_candidate("detail_data", "projectStart")],
        "crediting_end_date": [path_candidate("detail_data", "creditingPeriodEnd"), path_candidate("detail_data", "projectEnd")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [path_candidate("detail_data", "creditBalance.total.credits")],
        "credits_retired_total": [path_candidate("detail_data", "creditBalance.retired.credits")],
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



