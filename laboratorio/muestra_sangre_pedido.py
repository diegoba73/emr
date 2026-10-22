"""
Criterio de «material Sangre» para pedido / catálogo.

Incluye cualquier tipo de muestra de sangre/suero/plasma (EDTA, citrato,
heparina, papel filtro, etc.), sin exigir el código canónico exacto.
Excluye otros materiales (orina, LCR, médula, seminal, …).
"""
from __future__ import annotations


def es_tipo_muestra_sangre_pedido(
    codigo: str | None,
    nombre: str | None = None,
) -> bool:
    """
    True si el material clínico pertenece a la familia sangre del pedido.

    El ``nombre`` es opcional (reserva para reglas futuras); hoy alcanza el código.
    """
    del nombre  # API estable; hoy no se usa
    c = (codigo or "").strip().upper()
    if not c:
        return False
    # No-sangre explícitos aunque digan plasma/EDTA en el código.
    if c == "PLASMA_SEMINAL" or c.startswith("PLASMA_SEMINAL"):
        return False
    if c.startswith("MEDULA"):
        return False
    if c.startswith("SANGRE"):
        return True
    if c.startswith("SUERO"):
        return True
    if c.startswith("PLASMA"):
        return True
    return False


def codigos_tipo_muestra_sangre_en_db(*, solo_activos: bool = True) -> list[str]:
    """Códigos de TipoMuestra en BD que califican como Sangre para el pedido."""
    from laboratorio.models import TipoMuestra

    qs = TipoMuestra.objects.all()
    if solo_activos:
        qs = qs.filter(activo=True)
    out: set[str] = set()
    for codigo, nombre in qs.values_list("codigo", "nombre"):
        if es_tipo_muestra_sangre_pedido(codigo, nombre):
            out.add((codigo or "").strip().upper())
    return sorted(out)
