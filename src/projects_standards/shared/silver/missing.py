# Objetivo do modulo:
# Tratar marcadores de ausencia e valores vazios de forma padronizada na camada silver.
# Processo:
# 1. Definir conjunto MISSING_TEXT_MARKERS (N/A, NULL, TBD, NOT AVAILABLE, etc.).
# 2. Implementar is_missing() para avaliar se valor deve ser tratado como ausente.
# 3. Implementar normalize_missing() para converter ausencias e marcadores para None.
# 4. Tratar colecoes, strings e primitivos com logica consistente.

from typing import Any


MISSING_TEXT_MARKERS = {
    "",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "TBD",
    "NOT AVAILABLE",
    "NOT APPLICABLE",
}


# Avalia se o valor deve ser tratado como ausente na silver.
def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    if isinstance(value, str):
        text = value.strip()
        return not text or text.upper() in MISSING_TEXT_MARKERS
    return False


# Converte vazios e marcadores textuais de ausencia para None.
def normalize_missing(value: Any) -> Any:
    if is_missing(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value


# Alias semantico para trechos do codigo que queiram explicitar a intencao.
def empty_to_none(value: Any) -> Any:
    return normalize_missing(value)
