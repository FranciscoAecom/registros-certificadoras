# Objetivo do modulo:
# Aplicar normalizacao canonica por tipo de campo nos registros da camada silver.
# Processo:
# 1. Definir conjuntos DATE_FIELDS e DATETIME_FIELDS com nomes de campos canonicos.
# 2. Definir NUMERIC_FIELD_TYPES mapeando nomes de campos para (kind, style).
# 3. Prover funcoes de normalizacao canonica por tipo de campo.
# 4. Integrar tratamento de valores ausentes com conversao orientada por tipo.

import json
from typing import Any

from .dates import parse_date_to_iso, parse_datetime_to_iso
from .missing import normalize_missing
from .numbers import parse_number
from .text import normalize_multiline_text, normalize_text


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

MULTILINE_TEXT_FIELDS = {
    "project_description",
}

LIST_REQUIRED_FIELDS = {
    "project_methodology",
    "sdg_targets",
    "sector",
}


# Remove valores vazios e duplicados preservando a ordem original.
def unique_non_empty(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        clean_value = normalize_missing(value)
        if clean_value in (None, "", [], {}):
            continue
        key = (
            json.dumps(clean_value, ensure_ascii=False, sort_keys=True)
            if isinstance(clean_value, (dict, list))
            else str(clean_value)
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(clean_value)
    return result


# Garante que o valor seja tratado como lista para regras com multiplicidade.
def ensure_list(value: Any) -> list[Any]:
    clean_value = normalize_missing(value)
    if clean_value in (None, "", [], {}):
        return []
    if isinstance(clean_value, list):
        return unique_non_empty(clean_value)
    return [clean_value]


# Retorna um valor unico ou uma lista, conforme a quantidade encontrada.
def scalar_or_list(values: list[Any]) -> Any:
    clean_values = unique_non_empty(values)
    if not clean_values:
        return None
    if len(clean_values) == 1:
        return clean_values[0]
    return clean_values


# Normaliza um item individual preservando a semantica do valor original.
def _normalize_item(value: Any) -> Any:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    if isinstance(clean_value, str):
        return normalize_text(clean_value)
    if isinstance(clean_value, list):
        return unique_non_empty([_normalize_item(item) for item in clean_value])
    return clean_value


# Normaliza um valor de acordo com o campo canonico da silver.
def normalize_record_value(field_name: str, value: Any) -> Any:
    clean_value = normalize_missing(value)
    if field_name in LIST_REQUIRED_FIELDS:
        if clean_value is None:
            return []
        if isinstance(clean_value, list):
            normalized_items = [_normalize_item(item) for item in clean_value]
            return unique_non_empty(normalized_items)
        normalized_item = _normalize_item(clean_value)
        return [] if normalized_item is None else [normalized_item]

    if clean_value is None:
        return None

    if field_name in DATE_FIELDS:
        return parse_date_to_iso(clean_value)

    if field_name in DATETIME_FIELDS:
        return parse_datetime_to_iso(clean_value)

    if field_name in NUMERIC_FIELD_TYPES:
        number_kind, number_style = NUMERIC_FIELD_TYPES[field_name]
        return parse_number(clean_value, number_kind=number_kind, number_style=number_style)

    if isinstance(clean_value, list):
        normalized_items = [_normalize_item(item) for item in clean_value]
        normalized_list = unique_non_empty(normalized_items)
        if not normalized_list:
            return None
        return scalar_or_list(normalized_list)

    if isinstance(clean_value, str):
        if field_name in MULTILINE_TEXT_FIELDS:
            return normalize_multiline_text(clean_value)
        return normalize_text(clean_value)

    return clean_value


# Normaliza um registro completo da camada silver campo a campo.
def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {field_name: normalize_record_value(field_name, value) for field_name, value in record.items()}
