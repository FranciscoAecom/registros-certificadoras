# Objetivo do script:
# Reparar o workbook consolidado de referencias sincronizando cabecalhos das tabelas e metadados OOXML.
# Processo:
# 1. Ler argumentos CLI (--workbook opcional, padrao reference_dataset.xlsx).
# 2. Carregar workbook e validar estrutura.
# 3. Remover autofiltros problematicos.
# 4. Sincronizar cabecalhos das tabelas em todas as abas.
# 5. Validar estrutura OOXML ponta a ponta.
# 6. Gravar workbook reparado.


from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.projects_standards.shared.reference.build_reference_dataset import (  # noqa: E402
    DEFAULT_OUTPUT_PATH,
    strip_worksheet_autofilters,
    sync_table_headers,
    validate_reference_dataset,
)


# Monta o parser de argumentos do reparador do workbook consolidado.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repara o workbook reference_dataset.xlsx mantendo compatibilidade com o Excel."
    )
    parser.add_argument(
        "--workbook",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Workbook XLSX a ser reparado. Padrao: {DEFAULT_OUTPUT_PATH}",
    )
    return parser


# Executa a rotina de reparo estrutural do workbook consolidado.
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    workbook_path = Path(args.workbook)
    sync_table_headers(workbook_path)
    strip_worksheet_autofilters(workbook_path)
    validate_reference_dataset(workbook_path)
    print(f"reference dataset reparado com sucesso: {workbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
