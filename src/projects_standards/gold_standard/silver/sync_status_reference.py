# Objetivo do script:
# Sincronizar a tabela de referencia de status da certificadora a partir do dataset silver.
# Processo:
# 1. Definir configuracao da certificadora (nome, slug bronze, referencia).
# 2. Definir funcao coletora de status delegando ao coletor padrao compartilhado.
# 3. Delegar ao framework compartilhado run_status_sync(CONFIG) que:
#    a. Carrega o dataset silver mais recente da certificadora.
#    b. Coleta formas observadas de status por projeto.
#    c. Atualiza a aba standards_status do reference_dataset.xlsx.
# 4. Retornar codigo de saida.


import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import collect_default_status_rows, run_status_sync, sync_status_reference_projects  # noqa: E402


DISPLAY_NAME = "Gold Standard"
BRONZE_SLUG = "gold_standard"
REFERENCE_NAME = "Gold Standard"


# Coleta os status observados no projeto segundo a regra padrao atual da certificadora.
def collect_status_rows(project: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    return collect_default_status_rows(project)


# Sincroniza a referencia de status a partir dos projetos ja carregados em memoria.
def sync_status_reference_for_projects(*, records: list[dict[str, Any]], **_: Any) -> int:
    return sync_status_reference_projects(
        reference_name=REFERENCE_NAME,
        projects=records,
        collector=collect_status_rows,
    )


CONFIG = {
    "display_name": DISPLAY_NAME,
    "bronze_slug": BRONZE_SLUG,
    "reference_name": REFERENCE_NAME,
    "status_collector": collect_status_rows,
}


if __name__ == "__main__":
    raise SystemExit(run_status_sync(CONFIG))
