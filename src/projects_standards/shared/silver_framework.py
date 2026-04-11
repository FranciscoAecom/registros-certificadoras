# Objetivo do modulo:
# Manter compatibilidade temporaria com imports legados enquanto a camada silver usa o pacote compartilhado.
# Processo:
# 1. Importar tudo de src.projects_standards.shared.silver via wildcard.
# 2. Manter compatibilidade com imports legados que referenciam silver_framework.py.
# 3. Servir como ponte durante migracao dos imports para o pacote compartilhado.


from src.projects_standards.shared.silver import *  # noqa: F401,F403
