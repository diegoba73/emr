"""Carga catálogo de reactivos por equipo (Ticket B).

Por defecto: dry-run (no escribe BD, no stock, no ConsumoInsumoExamen).
--apply: crea/actualiza solo InsumoLab no ambiguos (requiere autorización explícita).

No toca QC. No modifica CRE/GLU Pharmacorp.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.models_inventario import InsumoLab
from laboratorio.models_qc import EquipoAnalizador
from laboratorio.reactivos_matriz_catalogo import (
    REACTIVOS_CATALOGO_CONFIRMADOS,
    REACTIVOS_CATALOGO_PENDIENTES,
    SKU_LEGACY_NO_TOCAR,
)


def _planificar() -> dict:
    equipos = {e.codigo: e for e in EquipoAnalizador.objects.filter(activo=True)}
    existentes = list(
        InsumoLab.objects.filter(tipo=InsumoLab.Tipo.REACTIVO).select_related("equipo")
    )
    by_codigo = {i.codigo: i for i in existentes}

    nuevos: list[dict] = []
    reutilizar: list[dict] = []
    actualizar: list[dict] = []
    conflictos: list[dict] = []
    omitidos_legacy: list[dict] = []

    for row in REACTIVOS_CATALOGO_CONFIRMADOS:
        sku = row["codigo"]
        if sku in SKU_LEGACY_NO_TOCAR:
            omitidos_legacy.append(
                {
                    "codigo": sku,
                    "motivo": "SKU legacy protegido",
                    "ref": row["ref_comercial"],
                }
            )
            continue

        eq = equipos.get(row["equipo_codigo"])
        if eq is None:
            conflictos.append(
                {
                    "codigo": sku,
                    "ref": row["ref_comercial"],
                    "problema": f"Equipo {row['equipo_codigo']} ausente o inactivo",
                }
            )
            continue

        # Identidad primaria: codigo SKU exacto (no REF sola).
        hit = by_codigo.get(sku)
        if hit is None:
            # Conflicto: misma REF + mismo equipo + distinto SKU ya existente.
            mismos_ref = [
                i
                for i in existentes
                if (i.ref_comercial or "").strip() == row["ref_comercial"]
                and i.equipo_id
                and i.equipo.codigo == row["equipo_codigo"]
                and i.codigo != sku
            ]
            if mismos_ref:
                conflictos.append(
                    {
                        "codigo": sku,
                        "ref": row["ref_comercial"],
                        "problema": (
                            "REF+equipo ya en otro SKU: "
                            + ", ".join(x.codigo for x in mismos_ref)
                            + " — no crear/actualizar por ambigüedad"
                        ),
                    }
                )
                continue
            nuevos.append(
                {
                    "codigo": sku,
                    "nombre": row["nombre"],
                    "ref_comercial": row["ref_comercial"],
                    "equipo": row["equipo_codigo"],
                    "proveedor": row["proveedor"],
                    "unidad": row["unidad"],
                    "lis": ",".join(row["lis_codigos"]),
                    "equipo_id": eq.id,
                    "row": row,
                }
            )
            continue

        # Reutilizar por SKU exacto. Actualizar solo si campos claros y sin ambigüedad.
        cambios: dict[str, str] = {}
        if (hit.ref_comercial or "") != row["ref_comercial"]:
            if hit.ref_comercial:
                conflictos.append(
                    {
                        "codigo": sku,
                        "ref": row["ref_comercial"],
                        "problema": (
                            f"SKU existe con REF distinta '{hit.ref_comercial}' "
                            f"vs propuesta '{row['ref_comercial']}' — no sobrescribir"
                        ),
                    }
                )
                continue
            cambios["ref_comercial"] = row["ref_comercial"]
        if hit.equipo_id != eq.id:
            if hit.equipo_id is not None:
                conflictos.append(
                    {
                        "codigo": sku,
                        "ref": row["ref_comercial"],
                        "problema": (
                            f"SKU existe con otro equipo "
                            f"(id={hit.equipo_id}) vs {row['equipo_codigo']} — no sobrescribir"
                        ),
                    }
                )
                continue
            cambios["equipo_id"] = eq.id
        if (hit.proveedor or "") != row["proveedor"] and not (hit.proveedor or "").strip():
            cambios["proveedor"] = row["proveedor"]
        if hit.nombre != row["nombre"] and not cambios and not hit.ref_comercial:
            # Nombre distinto sin otros cambios: reutilizar sin forzar rename ambiguo
            pass

        entry = {
            "codigo": sku,
            "id": hit.id,
            "nombre": hit.nombre,
            "ref_comercial": hit.ref_comercial or "",
            "equipo": hit.equipo.codigo if hit.equipo_id else None,
            "lis": ",".join(row["lis_codigos"]),
            "cambios": cambios,
            "row": row,
            "obj": hit,
            "equipo_obj": eq,
        }
        if cambios:
            actualizar.append(entry)
        else:
            reutilizar.append(entry)

    return {
        "nuevos": nuevos,
        "reutilizar": reutilizar,
        "actualizar": actualizar,
        "conflictos": conflictos,
        "omitidos_legacy": omitidos_legacy,
        "pendientes": list(REACTIVOS_CATALOGO_PENDIENTES),
        "equipos": equipos,
    }


class Command(BaseCommand):
    help = (
        "Catálogo reactivos por equipo (Ticket B). Default dry-run. "
        "No crea ConsumoInsumoExamen ni toca QC/stock."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Escribe InsumoLab (requiere autorización). Sin esto solo dry-run.",
        )

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        plan = _planificar()

        self.stdout.write("=== Ticket B — catálogo reactivos (dry-run)" if not apply else "=== Ticket B — APPLY ===")
        self.stdout.write(f"Propuestos confirmados: {len(REACTIVOS_CATALOGO_CONFIRMADOS)}")
        self.stdout.write(f"Nuevos: {len(plan['nuevos'])}")
        self.stdout.write(f"Reutilizar (sin cambios): {len(plan['reutilizar'])}")
        self.stdout.write(f"Actualizar campos vacíos: {len(plan['actualizar'])}")
        self.stdout.write(f"Conflictos: {len(plan['conflictos'])}")
        self.stdout.write(f"Pendientes (no carga): {len(plan['pendientes'])}")

        self.stdout.write("\n-- NUEVOS --")
        for n in plan["nuevos"]:
            self.stdout.write(
                f"  + {n['codigo']} | REF={n['ref_comercial']} | "
                f"{n['equipo']} | {n['nombre'][:50]} | LIS={n['lis']}"
            )

        self.stdout.write("\n-- REUTILIZAR --")
        for r in plan["reutilizar"]:
            self.stdout.write(
                f"  = {r['codigo']} id={r['id']} | REF={r['ref_comercial'] or '∅'} | "
                f"equipo={r['equipo']}"
            )

        self.stdout.write("\n-- ACTUALIZAR (solo campos vacíos/seguros) --")
        for a in plan["actualizar"]:
            self.stdout.write(f"  ~ {a['codigo']} id={a['id']} cambios={a['cambios']}")

        self.stdout.write("\n-- CONFLICTOS --")
        for c in plan["conflictos"]:
            self.stdout.write(f"  ! {c['codigo']} REF={c['ref']}: {c['problema']}")

        self.stdout.write("\n-- PENDIENTES (no escribir) --")
        for p in plan["pendientes"]:
            self.stdout.write(
                f"  ? {p['lis']} | {p['nombre']} | {p['motivo']} | equipo={p['equipo_codigo']}"
            )

        self.stdout.write("\n-- LEGACY PROTEGIDO --")
        for o in plan["omitidos_legacy"]:
            self.stdout.write(f"  # {o}")

        self.stdout.write(
            "\nNOTA: lis_codigos documentados; NO se crea ConsumoInsumoExamen "
            "(evita descuento de stock)."
        )

        if not apply:
            self.stdout.write(self.style.WARNING("\nDry-run: cero escrituras."))
            return

        with transaction.atomic():
            for n in plan["nuevos"]:
                InsumoLab.objects.create(
                    codigo=n["codigo"],
                    nombre=n["nombre"],
                    tipo=InsumoLab.Tipo.REACTIVO,
                    ref_comercial=n["ref_comercial"],
                    equipo_id=n["equipo_id"],
                    proveedor=n["proveedor"],
                    unidad=n["unidad"],
                    activo=True,
                )
            for a in plan["actualizar"]:
                obj = a["obj"]
                for k, v in a["cambios"].items():
                    setattr(obj, k, v)
                obj.save(update_fields=[*a["cambios"].keys(), "updated_at"])

        self.stdout.write(self.style.SUCCESS("APPLY OK (solo InsumoLab; sin consumos/stock/QC)."))
