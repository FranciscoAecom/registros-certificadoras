# Objetivo do modulo:
# Padronizar parsing de valores numericos usados na camada silver com suporte a separadores localizados.
# Processo:
# 1. Definir tipos NumberKind (general, count, decimal_measure, coordinate) e NumberStyle.
# 2. Definir regex para extracao flexivel de tokens numericos.
# 3. Implementar _extract_number_token() para isolar numeros de texto.
# 4. Implementar _cast_number() para converter para int/float apos normalizacao de separadores.


import re
from typing import Any, Literal

from .missing import normalize_missing


NumberKind = Literal["general", "count", "decimal_measure", "coordinate"]
NumberStyle = Literal["auto", "dot_decimal", "comma_decimal"]

NUMBER_TOKEN_RE = re.compile(r"[-+]?\d[\d\s\u00A0\u202F.,]*")
SPACE_GROUP_RE = re.compile(r"(?<=\d)[\s\u00A0\u202F](?=\d)")


# Retorna o primeiro token com cara de numero preservando separadores para normalizacao posterior.
def _extract_number_token(value: Any) -> str | None:
    text = str(value).strip()
    match = NUMBER_TOKEN_RE.search(text)
    if not match:
        return None
    token = match.group(0).strip()
    token = SPACE_GROUP_RE.sub("", token)
    return token or None


# Converte o texto normalizado para int ou float conforme a presenca de casas decimais.
def _cast_number(number_text: str) -> int | float | None:
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", number_text):
        return None
    if "." in number_text:
        number = float(number_text)
        return int(number) if number.is_integer() else number
    return int(number_text)


# Resolve casos com ponto e virgula presentes no mesmo token.
def _normalize_mixed_separators(token: str, number_style: NumberStyle) -> str:
    if number_style == "comma_decimal":
        return token.replace(".", "").replace(",", ".")
    if number_style == "dot_decimal":
        return token.replace(",", "")

    last_dot = token.rfind(".")
    last_comma = token.rfind(",")
    if last_comma > last_dot:
        return token.replace(".", "").replace(",", ".")
    return token.replace(",", "")


# Resolve casos com apenas um tipo de separador no token.
def _normalize_single_separator(token: str, separator: str, number_kind: NumberKind, number_style: NumberStyle) -> str:
    count = token.count(separator)
    other_separator = "." if separator == "," else ","
    if other_separator in token:
        return token

    parts = token.split(separator)
    if count > 1:
        if all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            return "".join(parts)
        return token

    left, right = parts
    if not left or not right:
        return token

    if len(right) != 3:
        return token.replace(separator, ".")

    if separator == ",":
        if number_style == "dot_decimal":
            return left + right
        if number_style == "comma_decimal":
            return left + "." + right
    else:
        if number_style == "comma_decimal":
            return left + right
        if number_style == "dot_decimal":
            return left + "." + right

    if number_kind in {"coordinate", "decimal_measure"}:
        return left + "." + right
    return left + right


# Converte um valor textual ou numerico para numero usando heuristica orientada por tipo de campo.
def parse_number(
    value: Any,
    *,
    number_kind: NumberKind = "general",
    number_style: NumberStyle = "auto",
) -> int | float | None:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    if isinstance(clean_value, bool):
        return None
    if isinstance(clean_value, (int, float)):
        return clean_value

    token = _extract_number_token(clean_value)
    if token is None:
        return None

    if "," in token and "." in token:
        normalized = _normalize_mixed_separators(token, number_style)
        return _cast_number(normalized)

    if "," in token:
        normalized = _normalize_single_separator(token, ",", number_kind, number_style)
        return _cast_number(normalized)

    if "." in token:
        normalized = _normalize_single_separator(token, ".", number_kind, number_style)
        return _cast_number(normalized)

    return _cast_number(token)


# Converte valores com semantica de contagem ou total de creditos.
def parse_count(value: Any, *, number_style: NumberStyle = "auto") -> int | float | None:
    return parse_number(value, number_kind="count", number_style=number_style)


# Converte valores com semantica de medida decimal, como area.
def parse_decimal_measure(value: Any, *, number_style: NumberStyle = "auto") -> int | float | None:
    return parse_number(value, number_kind="decimal_measure", number_style=number_style)


# Converte coordenadas geograficas aceitando ponto ou virgula como separador decimal.
def parse_coordinate(value: Any, *, number_style: NumberStyle = "auto") -> int | float | None:
    return parse_number(value, number_kind="coordinate", number_style=number_style)


# Converte um valor conhecido para inteiro quando isso for possivel sem ambiguidade.
def parse_integer(value: Any) -> int | None:
    number = parse_count(value)
    if number is None:
        return None
    if isinstance(number, float) and not number.is_integer():
        return None
    return int(number)
