# Objetivo do modulo:
# Reunir validacoes simples de qualidade para apoiar a camada silver sem alterar o payload final.
# Processo:
# 1. Definir REQUIRED_FIELDS obrigatorios (standard_name, snapshot_date, project_public_id, etc.).
# 2. Definir DATE_FIELDS, DATETIME_FIELDS e NUMERIC_FIELD_TYPES para regras de validacao.
# 3. Prover funcoes de validacao que coletam problemas de qualidade sem alterar registros.
# 4. Usado durante transformacao silver para auditar cobertura e corretude do mapeamento.

from typing import Any

from .dates import parse_date_to_iso, parse_datetime_to_iso
from .numbers import parse_number


REQUIRED_FIELDS = {
    "standard_name",
    "snapshot_date",
    "reference_month",
    "project_public_id",
    "project_internal_id",
    "project_url",
    "project_name",
}

DATE_FIELDS = {
    "snapshot_date",
    "reference_month",
    "registration_date",
    "status_date",
    "crediting_start_date",
    "crediting_end_date",
    "first_issuance_date",
    "last_issuance_date",
}

DATETIME_FIELDS = {
    "generated_at",
}

NUMERIC_FIELD_TYPES = {
    "location_latitude": ("coordinate", "auto"),
    "location_longitude": ("coordinate", "auto"),
    "credits_issued_total": ("count", "auto"),
    "credits_retired_total": ("count", "auto"),
    "credits_cancelled_total": ("count", "auto"),
    "credits_buffer_total": ("count", "auto"),
    "estimated_annual_emission_reductions": ("count", "auto"),
    "estimated_total_emission_reductions": ("count", "auto"),
    "area_hectares": ("decimal_measure", "auto"),
}


# Valida se os campos minimos obrigatorios foram preenchidos no registro.
def validate_required_fields(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field_name in REQUIRED_FIELDS:
        if record.get(field_name) is None:
            issues.append(f"required:{field_name}")
    return issues


# Valida se campos de data e datetime estao no formato esperado da silver.
def validate_date_fields(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field_name in DATE_FIELDS:
        value = record.get(field_name)
        if value is None:
            continue
        if parse_date_to_iso(value) is None:
            issues.append(f"invalid_date:{field_name}")
    for field_name in DATETIME_FIELDS:
        value = record.get(field_name)
        if value is None:
            continue
        if parse_datetime_to_iso(value) is None:
            issues.append(f"invalid_datetime:{field_name}")
    return issues


# Valida se campos numericos sao conversiveis para numero na silver.
def validate_numeric_fields(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field_name, (number_kind, number_style) in NUMERIC_FIELD_TYPES.items():
        value = record.get(field_name)
        if value is None:
            continue
        if parse_number(value, number_kind=number_kind, number_style=number_style) is None:
            issues.append(f"invalid_number:{field_name}")
    return issues


# Agrega as validacoes simples de qualidade para um registro da silver.
def collect_quality_issues(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    issues.extend(validate_required_fields(record))
    issues.extend(validate_date_fields(record))
    issues.extend(validate_numeric_fields(record))
    return issues
