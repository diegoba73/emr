"""Placeholder de la suite legacy de ``turnos``.

La suite real ahora vive bajo ``turnos/tests/`` (paquete). Este módulo se
mantiene vacío deliberadamente para preservar el path histórico y para que
``pytest`` pueda incluirlo en sus rutas sin recoger tests obsoletos que
referenciaban campos eliminados (``especialidad_turno`` y otros) durante el
rediseño del modelo ``Turno``.

No agregar tests aquí: usar el paquete ``turnos/tests/``.
"""
