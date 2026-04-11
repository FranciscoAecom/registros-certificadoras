# Objetivo do script:
# Sincronizar a tabela de referencia de metodologias da certificadora a partir do dataset silver.
# Processo:
# 1. Definir configuracao da certificadora (nome, slug bronze, referencia).
# 2. Definir funcao coletora de metodologias delegando ao coletor padrao compartilhado.
# 3. Delegar ao framework compartilhado run_methodology_sync(CONFIG) que:
#    a. Carrega o dataset silver mais recente da certificadora.
#    b. Coleta formas observadas de metodologia por projeto.
#    c. Atualiza a aba methodologies do reference_dataset.xlsx.
# 4. Retornar codigo de saida.


import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import collect_default_methodology_rows, run_methodology_sync, sync_methodology_reference_projects  # noqa: E402


DISPLAY_NAME = "Social Carbon"
BRONZE_SLUG = "social_carbon"
REFERENCE_NAME = "Social Carbon"


# Sincroniza a referencia de metodologias a partir dos projetos ja carregados em memoria.
def sync_methodology_reference_for_projects(*, records: list[dict[str, Any]], **_: Any) -> int:
    return sync_methodology_reference_projects(
        reference_name=REFERENCE_NAME,
        projects=records,
        collector=collect_default_methodology_rows,
    )


CONFIG = {
    "display_name": DISPLAY_NAME,
    "bronze_slug": BRONZE_SLUG,
    "reference_name": REFERENCE_NAME,
    "methodology_collector": collect_default_methodology_rows,
}


if __name__ == "__main__":
    raise SystemExit(run_methodology_sync(CONFIG))
