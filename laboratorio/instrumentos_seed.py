"""Asegura interfaces CM260 / Sysmex y mapeos de analito."""
from __future__ import annotations

from laboratorio.equipos_lab import EQUIPOS_LAB, codigo_equipo_canonico
from laboratorio.instrumentos_catalogo import MAPEO_POR_DRIVER
from laboratorio.models import TipoExamen
from laboratorio.models_instrumentos import InterfazInstrumento, MapeoAnalitoInstrumento
from laboratorio.models_qc import EquipoAnalizador


def asegurar_equipo(codigo: str) -> EquipoAnalizador:
    canon = codigo_equipo_canonico(codigo)
    meta = EQUIPOS_LAB.get(canon, {"nombre": canon, "marca_modelo": canon})
    eq, _ = EquipoAnalizador.objects.get_or_create(
        codigo=canon,
        defaults={
            "nombre": meta.get("nombre") or canon,
            "marca_modelo": meta.get("marca_modelo") or "",
            "activo": True,
        },
    )
    return eq


def asegurar_interfaz(driver: str) -> InterfazInstrumento:
    eq = asegurar_equipo(driver)
    interfaz, created = InterfazInstrumento.objects.get_or_create(
        driver=driver,
        equipo=eq,
        defaults={
            "nombre": f"{eq.nombre} (ASTM)",
            "transporte": InterfazInstrumento.Transporte.SIMULADOR,
            "activo": True,
        },
    )
    if not created and interfaz.equipo_id != eq.id:
        interfaz.equipo = eq
        interfaz.save(update_fields=["equipo", "updated_at"])
    return interfaz


def seed_mapeos_interfaz(interfaz: InterfazInstrumento) -> tuple[int, int]:
    """Crea mapeos faltantes. Retorna (creados, omitidos_sin_examen)."""
    tabla = MAPEO_POR_DRIVER.get(interfaz.driver, {})
    creados = 0
    omitidos = 0
    for codigo_inst, codigo_ex in tabla.items():
        te = TipoExamen.objects.filter(codigo=codigo_ex, activo=True).first()
        if te is None:
            omitidos += 1
            continue
        _, was = MapeoAnalitoInstrumento.objects.get_or_create(
            interfaz=interfaz,
            codigo_instrumento=codigo_inst.strip().upper(),
            defaults={"tipo_examen": te, "activo": True},
        )
        if was:
            creados += 1
    return creados, omitidos


def seed_instrumentos_default() -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for driver in (InterfazInstrumento.Driver.CM260, InterfazInstrumento.Driver.SYSMEX_XP300):
        interfaz = asegurar_interfaz(driver)
        out[driver] = seed_mapeos_interfaz(interfaz)
    return out
