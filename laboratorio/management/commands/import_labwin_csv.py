"""
Importa historial LabWin: pacientes únicos por DNI y una orden LIMS por fila con resultados.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from laboratorio.labwin_csv import (
    LabwinOrder,
    LabwinPatient,
    load_labwin_csv,
    parse_valor_numerico,
)
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.origen_solicitud import EXTERNO_ICPL
from laboratorio.resultados_clinicos import (
    aplicar_snapshots_desde_tipo_examen,
    calcular_es_critico,
    calcular_es_patologico,
)
from pacientes.models import Paciente
from pacientes.texto import aplicar_mayusculas_paciente


def _aware(d) -> datetime:
    dt = datetime.combine(d, time(12, 0))
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def _empty(val: str | None) -> bool:
    return not (val or "").strip()


def _fill_empty_fields(obj: Paciente, row: LabwinPatient) -> list[str]:
    """Campos CSV que completarían vacíos. No muta el objeto."""
    dirty: list[str] = []
    if _empty(obj.nombre) and row.nombre:
        dirty.append("nombre")
    if _empty(obj.apellido) and row.apellido:
        dirty.append("apellido")
    if _empty(obj.telefono) and row.telefono:
        dirty.append("telefono")
    if _empty(obj.direccion) and row.direccion:
        dirty.append("direccion")
    return dirty


def _apply_fill(obj: Paciente, row: LabwinPatient) -> list[str]:
    dirty = _fill_empty_fields(obj, row)
    for campo in dirty:
        setattr(obj, campo, getattr(row, campo))
    return dirty


class Command(BaseCommand):
    help = (
        "Importa pacientes y órdenes históricas desde todo_labwin.csv. "
        "Paciente único por DNI (solo completa campos vacíos). "
        "Cada fila con resultados = una orden FINALIZADA (protocolo LW-YYYY-NNNNN)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            nargs="?",
            default="data/icpl/todo_labwin.csv",
            help="Ruta al CSV LabWin. Por defecto: data/icpl/todo_labwin.csv",
        )
        parser.add_argument("--encoding", default="utf-8-sig")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analiza y contrasta con la BD sin escribir.",
        )
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo no existe: {csv_path}")

        patients, orders, stats = load_labwin_csv(csv_path, encoding=options["encoding"])
        self.stdout.write(f"Archivo: {csv_path}")
        self.stdout.write(f"  Filas leídas: {stats.lines_read}")
        self.stdout.write(f"  DNI vacíos: {stats.dni_vacios}")
        self.stdout.write(f"  DNI inválidos: {stats.dni_invalidos}")
        self.stdout.write(f"  DNI omitidos (revisión): {stats.dni_omitidos_revision}")
        self.stdout.write(f"  Filas sin resultado mapeado: {stats.rows_sin_resultado}")
        self.stdout.write(f"  Pacientes únicos: {stats.unique_patients}")
        self.stdout.write(f"  Órdenes con resultados: {stats.orders}")
        self.stdout.write(f"  EAB arterial (layout coherente): {stats.eab_art}")
        self.stdout.write(f"  EAB venoso (layout coherente): {stats.eab_ven}")
        self.stdout.write(
            f"  EAB omitido (export 2022-2025 columnas corridas): {stats.eab_omitido_layout_viejo}"
        )

        exam_codes = {c for o in orders for c in o.resultados}
        tipos = {
            te.codigo: te
            for te in TipoExamen.objects.filter(codigo__in=exam_codes, activo=True)
        }
        missing_codes = sorted(exam_codes - set(tipos))
        if missing_codes:
            self.stdout.write(
                self.style.WARNING(
                    f"  Códigos LIMS ausentes en catálogo (se omiten): {', '.join(missing_codes)}"
                )
            )

        existing_pac = {
            p.dni: p
            for p in Paciente.objects.filter(dni__in=list(patients.keys()))
        }
        to_create_p = [dni for dni in patients if dni not in existing_pac]
        to_fill = 0
        for dni, row in patients.items():
            obj = existing_pac.get(dni)
            if obj is not None and _fill_empty_fields(obj, row):
                to_fill += 1

        existing_numeros = set(
            SolicitudExamen.objects.filter(
                numero__in=[o.protocolo for o in orders]
            ).values_list("numero", flat=True)
        )
        new_orders = [o for o in orders if o.protocolo not in existing_numeros]
        skipped_orders = len(orders) - len(new_orders)

        proto_dups = _duplicate_protocolos(new_orders)
        if proto_dups:
            self.stdout.write(
                self.style.WARNING(
                    f"  Protocolos duplicados en CSV (se importa la primera): {len(proto_dups)}"
                )
            )

        eab_prefijos = ("PH_", "PO2_", "PCO2_", "SAT_O2_", "HCO3_", "BE_")
        existing_eab_orders = [
            o
            for o in orders
            if o.protocolo in existing_numeros
            and any(c.startswith(eab_prefijos) for c in o.resultados)
        ]
        self.stdout.write(f"  Pacientes nuevos: {len(to_create_p)}")
        self.stdout.write(f"  Pacientes existentes a completar (campos vacíos): {to_fill}")
        self.stdout.write(f"  Órdenes nuevas: {len(new_orders)}")
        self.stdout.write(f"  Órdenes ya existentes (no se duplican): {skipped_orders}")
        self.stdout.write(
            f"  Órdenes existentes a completar EAB: {len(existing_eab_orders)}"
        )

        if stats.warnings:
            self.stdout.write(self.style.WARNING("Advertencias (muestra):"))
            for w in stats.warnings[:25]:
                self.stdout.write(f"  - {w}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run: no se modificó la base."))
            return

        batch = max(1, options["batch_size"])
        created_p, filled_p, created_o, created_r = self._write(
            patients=patients,
            orders=new_orders,
            tipos=tipos,
            batch=batch,
        )
        added_eab = self._add_missing_resultados(
            orders=orders,
            existing_numeros=existing_numeros,
            tipos=tipos,
            batch=batch,
        )
        self.stdout.write(self.style.SUCCESS("Importación LabWin completada."))
        self.stdout.write(f"  Pacientes creados: {created_p}")
        self.stdout.write(f"  Pacientes completados: {filled_p}")
        self.stdout.write(f"  Órdenes creadas: {created_o}")
        self.stdout.write(f"  Resultados creados: {created_r}")
        self.stdout.write(f"  Resultados EAB agregados a órdenes existentes: {added_eab}")

    def _write(
        self,
        *,
        patients: dict[str, LabwinPatient],
        orders: list[LabwinOrder],
        tipos: dict[str, TipoExamen],
        batch: int,
    ) -> tuple[int, int, int, int]:
        created_p = 0
        filled_p = 0
        with transaction.atomic():
            existing = {
                p.dni: p
                for p in Paciente.objects.filter(dni__in=list(patients.keys()))
            }
            nuevos: list[Paciente] = []
            for dni, row in patients.items():
                obj = existing.get(dni)
                if obj is None:
                    p = Paciente(
                        dni=dni,
                        nombre=row.nombre or "Sin nombre",
                        apellido=row.apellido or "Sin apellido",
                        telefono=row.telefono or None,
                        direccion=row.direccion or None,
                    )
                    aplicar_mayusculas_paciente(p)
                    nuevos.append(p)
                    continue
                dirty = _apply_fill(obj, row)
                if dirty:
                    obj.save(update_fields=dirty)
                    filled_p += 1
            for i in range(0, len(nuevos), batch):
                Paciente.objects.bulk_create(nuevos[i : i + batch], ignore_conflicts=True)
                created_p += len(nuevos[i : i + batch])

        dni_to_id = dict(
            Paciente.objects.filter(dni__in=list(patients.keys())).values_list("dni", "id")
        )
        seen_proto: set[str] = set()
        created_o = 0
        created_r = 0

        for i in range(0, len(orders), batch):
            chunk = orders[i : i + batch]
            with transaction.atomic():
                sol_objs: list[SolicitudExamen] = []
                chunk_ok: list[LabwinOrder] = []
                for order in chunk:
                    if order.protocolo in seen_proto:
                        continue
                    paciente_id = dni_to_id.get(order.dni)
                    if not paciente_id:
                        continue
                    resultados = {
                        c: v for c, v in order.resultados.items() if c in tipos
                    }
                    if not resultados:
                        continue
                    seen_proto.add(order.protocolo)
                    order.resultados = resultados
                    chunk_ok.append(order)
                    sol_objs.append(
                        SolicitudExamen(
                            numero=order.protocolo,
                            paciente_id=paciente_id,
                            origen_solicitud=EXTERNO_ICPL,
                            estado="PENDIENTE",
                            observaciones=f"Importado LabWin {order.numero_labwin}",
                        )
                    )
                if not sol_objs:
                    continue
                created = SolicitudExamen.objects.bulk_create(sol_objs)
                created_o += len(created)
                proto_to_sol = {
                    s.numero: s
                    for s in SolicitudExamen.objects.filter(
                        numero__in=[o.protocolo for o in chunk_ok]
                    )
                }
                res_objs: list[ResultadoExamen] = []
                m2m_exam: list[tuple[int, int]] = []
                fecha_by_id: dict[int, datetime] = {}
                for order in chunk_ok:
                    sol = proto_to_sol.get(order.protocolo)
                    if sol is None:
                        continue
                    fecha_by_id[sol.id] = _aware(order.fecha)
                    for codigo, valor in order.resultados.items():
                        te = tipos[codigo]
                        m2m_exam.append((sol.id, te.id))
                        res_objs.append(_make_resultado(sol, te, valor))
                if m2m_exam:
                    through = SolicitudExamen.tipos_examen.through
                    through.objects.bulk_create(
                        [
                            through(solicitudexamen_id=sid, tipoexamen_id=tid)
                            for sid, tid in m2m_exam
                        ],
                        ignore_conflicts=True,
                    )
                _attach_paneles(chunk_ok, proto_to_sol)
                if res_objs:
                    ResultadoExamen.objects.bulk_create(res_objs, batch_size=500)
                    created_r += len(res_objs)
                for sol_id, fecha in fecha_by_id.items():
                    SolicitudExamen.objects.filter(pk=sol_id).update(
                        estado="FINALIZADO",
                        fecha_solicitud=fecha,
                    )

        return created_p, filled_p, created_o, created_r

    def _add_missing_resultados(
        self,
        *,
        orders: list[LabwinOrder],
        existing_numeros: set[str],
        tipos: dict[str, TipoExamen],
        batch: int,
    ) -> int:
        pending = [o for o in orders if o.protocolo in existing_numeros]
        if not pending:
            return 0
        added = 0
        for i in range(0, len(pending), batch):
            chunk = pending[i : i + batch]
            numeros = [o.protocolo for o in chunk]
            proto_to_sol = {
                s.numero: s
                for s in SolicitudExamen.objects.filter(numero__in=numeros)
            }
            ya = set(
                ResultadoExamen.objects.filter(
                    solicitud__numero__in=numeros
                ).values_list("solicitud__numero", "tipo_examen__codigo")
            )
            res_objs: list[ResultadoExamen] = []
            m2m_exam: list[tuple[int, int]] = []
            with transaction.atomic():
                for order in chunk:
                    sol = proto_to_sol.get(order.protocolo)
                    if sol is None:
                        continue
                    for codigo, valor in order.resultados.items():
                        te = tipos.get(codigo)
                        if te is None:
                            continue
                        if (order.protocolo, codigo) in ya:
                            continue
                        m2m_exam.append((sol.id, te.id))
                        res_objs.append(_make_resultado(sol, te, valor))
                        ya.add((order.protocolo, codigo))
                if m2m_exam:
                    through = SolicitudExamen.tipos_examen.through
                    through.objects.bulk_create(
                        [
                            through(solicitudexamen_id=sid, tipoexamen_id=tid)
                            for sid, tid in m2m_exam
                        ],
                        ignore_conflicts=True,
                    )
                _attach_paneles(chunk, proto_to_sol)
                if res_objs:
                    ResultadoExamen.objects.bulk_create(res_objs, batch_size=500)
                    added += len(res_objs)
        return added


def _make_resultado(sol: SolicitudExamen, te: TipoExamen, valor: str) -> ResultadoExamen:
    res = ResultadoExamen(
        solicitud=sol,
        tipo_examen=te,
        valor_obtenido=valor[:255],
        valor_numerico=parse_valor_numerico(valor),
        unidad=te.unidad_default or "",
    )
    aplicar_snapshots_desde_tipo_examen(res, te)
    pat = calcular_es_patologico(
        res.valor_numerico,
        res.rango_min_snapshot,
        res.rango_max_snapshot,
    )
    if pat is not None:
        res.es_patologico = pat
    crit = calcular_es_critico(
        res.valor_numerico,
        res.valor_critico_min_snapshot,
        res.valor_critico_max_snapshot,
    )
    if crit is not None:
        res.es_critico = crit
    return res


def _attach_paneles(orders: list[LabwinOrder], proto_to_sol: dict[str, SolicitudExamen]) -> None:
    codigos = {p for o in orders for p in o.paneles}
    if not codigos:
        return
    paneles = {p.codigo: p for p in PanelExamen.objects.filter(codigo__in=codigos, activo=True)}
    through = SolicitudExamen.paneles.through
    rows = []
    for order in orders:
        sol = proto_to_sol.get(order.protocolo)
        if sol is None:
            continue
        for codigo in order.paneles:
            panel = paneles.get(codigo)
            if panel is None:
                continue
            rows.append(through(solicitudexamen_id=sol.id, panelexamen_id=panel.id))
    if rows:
        through.objects.bulk_create(rows, ignore_conflicts=True)


def _duplicate_protocolos(orders: list[LabwinOrder]) -> set[str]:
    counts = Counter(o.protocolo for o in orders)
    return {p for p, n in counts.items() if n > 1}
