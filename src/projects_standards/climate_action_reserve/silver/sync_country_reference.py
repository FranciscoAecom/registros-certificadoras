# Objetivo do script:
# Sincronizar a tabela de referencia de paises observados na certificadora a partir do dataset silver.
# Processo:
# 1. Definir configuracao da certificadora (nome, slug bronze, referencia).
# 2. Definir funcao coletora de paises delegando ao coletor padrao compartilhado.
# 3. Delegar ao framework compartilhado run_country_sync(CONFIG) que:
#    a. Carrega o dataset silver mais recente da certificadora.
#    b. Coleta formas observadas de pais por projeto.
#    c. Atualiza a aba countries_observed_mapping do reference_dataset.xlsx.
# 4. Retornar codigo de saida.


import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.projects_standards.shared.silver import collect_default_country_rows, run_country_sync, sync_country_reference_projects  # noqa: E402


DISPLAY_NAME = "Climate Action Reserve"
BRONZE_SLUG = "climate_action_reserve"
REFERENCE_NAME = "Climate Action Reserve"


# Coleta os paises observados no projeto segundo a regra padrao atual da certificadora.
def collect_country_rows(project: dict[str, Any]) -> list[str]:
    return collect_default_country_rows(project)


# Sincroniza a referencia de paises a partir dos projetos ja carregados em memoria.
def sync_country_reference_for_projects(*, records: list[dict[str, Any]], **_: Any) -> int:
    return sync_country_reference_projects(
        reference_name=REFERENCE_NAME,
        projects=records,
        collector=collect_country_rows,
    )


CONFIG = {
    "display_name": DISPLAY_NAME,
    "bronze_slug": BRONZE_SLUG,
    "reference_name": REFERENCE_NAME,
    "country_collector": collect_country_rows,
}


if __name__ == "__main__":
    raise SystemExit(run_country_sync(CONFIG))
