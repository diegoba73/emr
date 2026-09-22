"""Auditoría read-only Ticket A — no modifica datos."""
from django.db.models import Count

from laboratorio.models_inventario import ConsumoInsumoExamen, InsumoLab
from laboratorio.models_qc import EquipoAnalizador

print("=== EQUIPOS ===")
for e in EquipoAnalizador.objects.order_by("codigo"):
    print(f"{e.codigo}\t{e.nombre}\tactivo={e.activo}")

print("=== INSUMOS count by tipo ===")
for row in InsumoLab.objects.values("tipo").annotate(n=Count("id")).order_by("tipo"):
    print(row)

print("=== ALL REACTIVOS ===")
for i in InsumoLab.objects.filter(tipo="REACTIVO").select_related("equipo").order_by("codigo"):
    eq = i.equipo.codigo if i.equipo_id else None
    print(
        f"{i.codigo!r}\t{i.nombre[:70]}\tequipo={eq}\t"
        f"proveedor={(i.proveedor or '')[:40]!r}\tactivo={i.activo}"
    )

print("=== CONSUMOS count ===", ConsumoInsumoExamen.objects.count())
print("=== CONSUMOS activos (max 50) ===")
qs = ConsumoInsumoExamen.objects.select_related(
    "tipo_examen", "insumo", "insumo__equipo"
).order_by("tipo_examen__codigo")[:50]
for c in qs:
    print(
        f"{c.tipo_examen.codigo} -> {c.insumo.codigo} "
        f"qty={c.cantidad_por_determinacion} activo={c.activo}"
    )

print("=== CODIGOS REACTIVO que parecen REF Wiener/Finecare ===")
import re

pat = re.compile(r"^([0-9]{5,}|W[0-9]{2,}|[0-9]{5,}-[0-9]+)$")
for i in InsumoLab.objects.filter(tipo="REACTIVO").order_by("codigo"):
    if pat.match((i.codigo or "").strip()):
        print(i.codigo, i.nombre[:50])

print("=== DONE ===")
