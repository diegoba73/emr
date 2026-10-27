"""Reporte de solo lectura: DNI exactos o normalizados repetidos.

No escribe ni fusiona fichas. Pensado para medir volumen en producción.

Ejemplos::

    python manage.py reportar_dni_duplicados
    python manage.py reportar_dni_duplicados --limit 50
    python manage.py reportar_dni_duplicados --solo-exactos
"""
from __future__ import annotations

import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from pacientes.models import Paciente

_NO_ALNUM = re.compile(r"[^0-9A-Za-z]+")


def normalizar_dni(raw: str | None) -> str:
    """Quita espacios/puntos/guiones; mayúsculas. Vacío → ''."""
    if raw is None:
        return ""
    return _NO_ALNUM.sub("", str(raw).strip()).upper()


def normalizar_dni_digitos(raw: str | None) -> str:
    """Solo dígitos, sin ceros a la izquierda (DNI tipográfico).

    ``01234567`` y ``1234567`` colapsan al mismo valor. Si no queda ningún
    dígito, devuelve ``''``. Un documento que era solo ceros queda como ``'0'``.
    """
    digits = re.sub(r"\D+", "", str(raw or ""))
    if not digits:
        return ""
    stripped = digits.lstrip("0")
    return stripped if stripped else "0"


class Command(BaseCommand):
    help = (
        "Lista DNIs repetidos (exacto y/o normalizado). Solo lectura; "
        "no modifica la base."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=30,
            help="Máximo de grupos a imprimir por tipo (default 30). 0 = todos.",
        )
        parser.add_argument(
            "--solo-exactos",
            action="store_true",
            help="Solo GROUP BY dni exacto (suele ser 0 si hay unique en BD).",
        )
        parser.add_argument(
            "--solo-normalizados",
            action="store_true",
            help="Solo colisiones tras normalizar (quitar puntos/guiones/espacios).",
        )

    def handle(self, *args, **options):
        limit = max(0, int(options["limit"]))
        solo_exactos = bool(options["solo_exactos"])
        solo_normalizados = bool(options["solo_normalizados"])
        if solo_exactos and solo_normalizados:
            self.stderr.write("Usá solo uno de --solo-exactos / --solo-normalizados.")
            return

        total = Paciente.objects.count()
        self.stdout.write(f"Pacientes totales: {total}")
        self.stdout.write("Modo: solo lectura (no se escribe nada).\n")

        if not solo_normalizados:
            self._report_exactos(limit)
        if not solo_exactos:
            self._report_normalizados(limit)
            self._report_digitos_sin_ceros(limit)

    def _print_groups(self, titulo: str, grupos: list[tuple], limit: int) -> None:
        self.stdout.write(self.style.NOTICE(titulo))
        if not grupos:
            self.stdout.write("  (ninguno)\n")
            return

        fichas = sum(n for _k, n, _ids in grupos)
        self.stdout.write(
            f"  Grupos: {len(grupos)} | Fichas involucradas: {fichas}\n"
        )
        mostrar = grupos if limit == 0 else grupos[:limit]
        for key, n, ids in mostrar:
            ids_txt = ", ".join(str(i) for i in ids[:12])
            extra = f" … (+{len(ids) - 12})" if len(ids) > 12 else ""
            self.stdout.write(f"  [{key}] x{n} → ids: {ids_txt}{extra}")
        if limit and len(grupos) > limit:
            self.stdout.write(f"  … {len(grupos) - limit} grupos más (subí --limit o usá 0)")
        self.stdout.write("")

    def _report_exactos(self, limit: int) -> None:
        qs = (
            Paciente.objects.values("dni")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .order_by("-n", "dni")
        )
        grupos: list[tuple] = []
        for row in qs:
            dni = row["dni"]
            ids = list(
                Paciente.objects.filter(dni=dni)
                .order_by("id")
                .values_list("id", flat=True)
            )
            grupos.append((dni if dni not in (None, "") else "(vacío)", row["n"], ids))
        self._print_groups("1) DNI exacto repetido (mismo texto en BD)", grupos, limit)

    def _report_normalizados(self, limit: int) -> None:
        buckets: dict[str, list[tuple[int, str]]] = defaultdict(list)
        vacios = 0
        for pk, dni in Paciente.objects.values_list("id", "dni").iterator(chunk_size=2000):
            norm = normalizar_dni(dni)
            if not norm:
                vacios += 1
                continue
            buckets[norm].append((pk, dni or ""))

        grupos = []
        for norm, items in buckets.items():
            if len(items) < 2:
                continue
            # Solo interesa si hay más de un id; si el raw ya es idéntico,
            # el reporte exacto ya lo cubre — igual lo listamos acá.
            ids = [pk for pk, _raw in sorted(items, key=lambda t: t[0])]
            raws = sorted({raw for _pk, raw in items})
            label = norm if len(raws) == 1 else f"{norm} (raw: {' | '.join(raws[:5])})"
            grupos.append((label, len(items), ids))

        grupos.sort(key=lambda t: (-t[1], t[0]))
        self.stdout.write(f"DNI vacíos / no normalizables: {vacios}")
        self._print_groups(
            "2) Mismo DNI normalizado (puntos/guiones/espacios distintos)",
            grupos,
            limit,
        )

    def _report_digitos_sin_ceros(self, limit: int) -> None:
        buckets: dict[str, list[tuple[int, str]]] = defaultdict(list)
        con_cero_izq = 0
        no_digit = 0
        for pk, dni in Paciente.objects.values_list("id", "dni").iterator(chunk_size=2000):
            raw = dni or ""
            digits = re.sub(r"\D+", "", raw)
            if not digits:
                no_digit += 1
                continue
            if digits != digits.lstrip("0") and digits.lstrip("0"):
                con_cero_izq += 1
            key = normalizar_dni_digitos(raw)
            buckets[key].append((pk, raw))

        grupos = []
        for key, items in buckets.items():
            if len(items) < 2:
                continue
            ids = [pk for pk, _raw in sorted(items, key=lambda t: t[0])]
            raws = sorted({raw for _pk, raw in items})
            # Solo grupos donde hay textos distintos (p. ej. 0123 vs 123)
            if len(raws) < 2:
                continue
            label = f"{key} (raw: {' | '.join(raws[:6])})"
            grupos.append((label, len(items), ids))

        grupos.sort(key=lambda t: (-t[1], t[0]))
        self.stdout.write(f"Fichas con ceros a la izquierda (dígitos): {con_cero_izq}")
        self.stdout.write(f"Fichas sin dígitos en DNI: {no_digit}")
        self._print_groups(
            "3) Mismo DNI numérico (sin ceros a la izquierda)",
            grupos,
            limit,
        )
