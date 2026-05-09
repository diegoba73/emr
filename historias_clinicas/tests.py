"""Placeholder de la suite legacy de ``historias_clinicas``.

La suite real ahora vive bajo ``historias_clinicas/tests/`` (paquete). Este
módulo se mantiene vacío deliberadamente para preservar el path histórico y
para que ``pytest`` pueda incluirlo en sus rutas sin recoger tests obsoletos
que asumían modelos o tablas que ya no se usan en este flujo (``Sintoma``
quedó dentro de ``historias_clinicas`` y se cubre desde el paquete nuevo).

No agregar tests aquí: usar el paquete ``historias_clinicas/tests/``.
"""
