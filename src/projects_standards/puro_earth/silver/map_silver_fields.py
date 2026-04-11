# Objetivo do script:
# Analisar os arquivos bronze da Puro.earth e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.

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
    scalar_or_list,
    path_candidate,
    run_mapping,
)


DISPLAY_NAME = "Puro.earth"
BRONZE_SLUG = "puro_earth"
MAPPING_OUTPUT_PATH = CURRENT_DIR / "docs" / "silver_field_mapping.md"


def sort_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.stem), path.stem
    except ValueError:
        return 10**12, path.stem


def extract_sdgs(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    return scalar_or_list([item.get("name") for item in value if isinstance(item, dict)])


def extract_first_issuance_date(payload: dict[str, Any], _: Path) -> Any:
    items = []
    for transaction in payload.get("detail_data", {}).get("transactions", []):
        if not isinstance(transaction, dict):
            continue
        for bundle in transaction.get("bundles", []):
            if isinstance(bundle, dict) and bundle.get("issuanceDate"):
                items.append(bundle["issuanceDate"])
    return min(items) if items else None


def extract_last_issuance_date(payload: dict[str, Any], _: Path) -> Any:
    items = []
    for transaction in payload.get("detail_data", {}).get("transactions", []):
        if not isinstance(transaction, dict):
            continue
        for bundle in transaction.get("bundles", []):
            if isinstance(bundle, dict) and bundle.get("issuanceDate"):
                items.append(bundle["issuanceDate"])
    return max(items) if items else None


def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    return {
        "standard_name": [path_candidate("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "PE",
            )
        ],
        "project_public_id": [path_candidate("source", "project_public_id"), path_candidate("list_data", "projectId")],
        "project_internal_id": [path_candidate("source", "project_internal_id"), path_candidate("list_data", "projectId")],
        "project_url": [path_candidate("source", "project_url")],
        "bronze_file_path": [path_candidate("file_system", "bronze_file_path", rule_type="derived", notes="Derivado do caminho do arquivo de detalhe no filesystem.")],
        "source_file_name": [path_candidate("file_system", "source_file_name", rule_type="derived", notes="Derivado do nome do arquivo de detalhe no filesystem.")],
        "project_name": [path_candidate("detail_data", "project_name"), path_candidate("list_data", "name")],
        "project_voluntary_status": [],
        "project_regulatory_status": [],
        "standard_program": [path_candidate("detail_data", "project_overview.general_rules.version"), path_candidate("list_data", "generalRules.version")],
        "project_description": [],
        "project_methodology": [path_candidate("detail_data", "project_overview.methodology.name"), path_candidate("list_data", "methodology.name")],
        "project_type": [path_candidate("detail_data", "project_overview.methodology.name")],
        "sector": [],
        "project_category": [],
        "project_subcategories": [],
        "sdg_targets": [
            CandidateSource(
                source_section="list_data",
                source_path="sdgs",
                rule_type="normalized",
                notes="Usa a lista estruturada de ODS exposta pela listagem do projeto.",
                extractor=lambda payload, _file_path: extract_sdgs(payload.get("list_data", {}).get("sdgs")),
            )
        ],
        "project_developer": [path_candidate("detail_data", "project_overview.supplier"), path_candidate("list_data", "supplierName")],
        "project_owner": [],
        "project_operator": [],
        "validator_name": [],
        "verifier_name": [],
        "country": [path_candidate("detail_data", "project_overview.host_country")],
        "state_or_region": [],
        "city_or_locality": [],
        "location_latitude": [path_candidate("list_data", "latitude")],
        "location_longitude": [path_candidate("list_data", "longitude")],
        "snapshot_date": [path_candidate("source", "snapshot_date")],
        "reference_month": [path_candidate("source", "reference_month")],
        "registration_date": [],
        "status_date": [],
        "crediting_start_date": [path_candidate("list_data", "creditingPeriodStart")],
        "crediting_end_date": [path_candidate("list_data", "creditingPeriodEnd")],
        "first_issuance_date": [
            CandidateSource(
                source_section="detail_data",
                source_path="transactions[].bundles[].issuanceDate",
                rule_type="aggregate",
                notes="Usa a menor issuanceDate encontrada nos bundles transacionais.",
                extractor=extract_first_issuance_date,
            )
        ],
        "last_issuance_date": [
            CandidateSource(
                source_section="detail_data",
                source_path="transactions[].bundles[].issuanceDate",
                rule_type="aggregate",
                notes="Usa a maior issuanceDate encontrada nos bundles transacionais.",
                extractor=extract_last_issuance_date,
            )
        ],
        "credits_issued_total": [path_candidate("detail_data", "credits_summary.issued_corcs")],
        "credits_retired_total": [path_candidate("detail_data", "credits_summary.retired_corcs")],
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



