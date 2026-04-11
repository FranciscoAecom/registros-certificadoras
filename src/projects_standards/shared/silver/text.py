# Objetivo do modulo:
# Padronizar textos da camada silver com trim e reducao de espacos excedentes.
# Processo:
# 1. Definir regex WHITESPACE_RE para sequencias de espacos consecutivos.
# 2. Implementar strip_text() para remover espacos iniciais e finais.
# 3. Implementar collapse_whitespace() para reduzir espacos internos a um unico.
# 4. Implementar normalize_text() e normalize_multiline_text() preservando semantica.

import re
from typing import Any

from .missing import normalize_missing


WHITESPACE_RE = re.compile(r"\s+")


# Remove espacos excedentes nas extremidades sem alterar o restante do texto.
def strip_text(value: Any) -> str | None:
    clean_value = normalize_missing(value)
    if clean_value is None:
        return None
    return str(clean_value).strip()


# Colapsa qualquer sequencia de espacos internos em um unico espaco.
def collapse_whitespace(value: Any) -> str | None:
    text = strip_text(value)
    if text is None:
        return None
    return WHITESPACE_RE.sub(" ", text)


# Normaliza um texto simples para a representacao canonica da silver.
def normalize_text(value: Any) -> str | None:
    return collapse_whitespace(value)


# Normaliza texto multiline preservando quebras relevantes entre linhas nao vazias.
def normalize_multiline_text(value: Any) -> str | None:
    text = strip_text(value)
    if text is None:
        return None

    lines = [collapse_whitespace(line) for line in re.split(r"\r?\n", text)]
    clean_lines = [line for line in lines if line]
    if not clean_lines:
        return None
    return "\n".join(clean_lines)
