# Objetivo do modulo:
# Padronizar parsing e formatacao de datas e datetimes usados na camada silver.
# Processo:
# 1. Definir tupla DATE_FORMATS com 14 padroes de data comuns (ISO, US, EU, texto).
# 2. Definir tupla DATETIME_FORMATS com 6 padroes de datetime.
# 3. Prover funcao de conversao de formatos variados para ISO YYYY-MM-DD.
# 4. Prover funcao de conversao para ISO YYYY-MM-DDTHH:MM:SS.

from datetime import date, datetime, timezone
from typing import Any

from .missing import normalize_missing


DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d %b %Y",
    "%d %B %Y",
)

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%d/%m/%Y %H:%M:%S",
)


# Formata um valor date ou datetime para YYYY-MM-DD.
def format_date_iso(value: date | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


# Formata um datetime para YYYY-MM-DDTHH:MM:SS.
def format_datetime_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat(sep="T")


# Converte um valor conhecido para datetime quando o parsing for possivel.
def parse_datetime_to_iso(value: Any) -> str | None:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    if isinstance(clean_value, datetime):
        return format_datetime_iso(clean_value)
    if isinstance(clean_value, date):
        return datetime.combine(clean_value, datetime.min.time()).isoformat(sep="T")

    text = str(clean_value).strip()
    for fmt in DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return format_datetime_iso(parsed)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return format_datetime_iso(parsed)
    except ValueError:
        return None


# Converte um valor conhecido para data ISO YYYY-MM-DD.
def parse_date_to_iso(value: Any) -> str | None:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    if isinstance(clean_value, datetime):
        return format_date_iso(clean_value)
    if isinstance(clean_value, date):
        return clean_value.isoformat()

    datetime_value = parse_datetime_to_iso(clean_value)
    if datetime_value is not None:
        return datetime_value[:10]

    text = str(clean_value).strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        return None


# Alias curto para regras de mapeamento orientadas a data.
def parse_date(value: Any) -> str | None:
    return parse_date_to_iso(value)


# Alias curto para regras de mapeamento orientadas a datetime.
def parse_datetime(value: Any) -> str | None:
    return parse_datetime_to_iso(value)
