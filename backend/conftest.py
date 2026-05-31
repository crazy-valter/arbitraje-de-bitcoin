"""
Configuración de pytest a nivel de proyecto.

Configura las variables de entorno necesarias para que los módulos
que usan _require_secret() no abortan durante los tests.
"""

import os

# Variables de entorno requeridas por jwt_manager y admin_seeder
# Se definen antes de que cualquier módulo del proyecto sea importado
os.environ.setdefault("ACCESS_TOKEN_SECRET", "test-access-secret-for-unit-tests")
os.environ.setdefault("REFRESH_TOKEN_SECRET", "test-refresh-secret-for-unit-tests")
os.environ.setdefault("ADMIN_EMAIL", "test@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "testpassword123")
