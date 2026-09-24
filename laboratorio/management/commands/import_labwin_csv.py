"""
Importa historial LabWin: pacientes únicos por DNI y una orden LIMS por fila con resultados.
"""
from __future__ import annotations

import hashlib
import uuid
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

# Hook interno de tests: callable(chunk_index: int) -> None.
# Permite simular Kill tras commit de un lote de órdenes y antes del cierre.
_labwin_order_chunk_hook = None


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
        parser.add_argument(
            "--allow-new-patients",
            action="store_true",
            help=(
                "Permite crear pacientes nuevos. Por defecto (R1) exige que todos "
                "los DNI con orden ya existan en BD."
            ),
        )
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo no existe: {csv_path}")

        patients, orders, stats = load_labwin_csv(csv_path, encoding=options["encoding"])
        # Política R1: no crear/actualizar fichas sin ninguna orden con resultados.
        dnis_con_orden = {o.dni for o in orders}
        patients_sin_orden = len(patients) - len(dnis_con_orden)
        patients = {dni: row for dni, row in patients.items() if dni in dnis_con_orden}
        stats.unique_patients = len(patients)

        file_sha256 = _sha256_file(csv_path)
        self.stdout.write(f"Archivo: {csv_path}")
        self.stdout.write(f"  SHA-256: {file_sha256}")
        self.stdout.write(f"  Filas leídas: {stats.lines_read}")
        self.stdout.write(f"  DNI vacíos: {stats.dni_vacios}")
        self.stdout.write(f"  DNI inválidos: {stats.dni_invalidos}")
        self.stdout.write(f"  DNI omitidos (revisión): {stats.dni_omitidos_revision}")
        self.stdout.write(f"  Filas sin resultado mapeado: {stats.rows_sin_resultado}")
        self.stdout.write(f"  Pacientes solo ficha (omitidos, sin orden): {patients_sin_orden}")
        self.stdout.write(f"  Pacientes con orden (en alcance): {stats.unique_patients}")
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

        # Conteo exacto de resultados que se crearían (códigos presentes en catálogo).
        seen_proto_plan: set[str] = set()
        results_planned = 0
        for order in new_orders:
            if order.protocolo in seen_proto_plan:
                continue
            seen_proto_plan.add(order.protocolo)
            results_planned += sum(1 for c in order.resultados if c in tipos)
        self.stdout.write(f"  Resultados nuevos (planificados): {results_planned}")
        self.stdout.write(f"  Códigos catálogo ausentes: {len(missing_codes)}")

        identity_ok = len(to_create_p) == 0
        allow_new = bool(options.get("allow_new_patients"))
        if not identity_ok:
            self.stdout.write(
                self.style.ERROR(
                    f"  Identidad: BLOQUEO — {len(to_create_p)} DNI del CSV sin paciente local. "
                    "Apply no autorizado hasta resolver (o usar --allow-new-patients)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Identidad: OK — {len(patients)} DNI del CSV mapean 1:1 a pacientes locales."
                )
            )

        if stats.warnings:
            self.stdout.write(self.style.WARNING("Advertencias (muestra, sin PHI):"))
            for w in stats.warnings[:25]:
                self.stdout.write(f"  - {w}")

        if options["dry_run"]:
            # Dry-run: cero escrituras clínicas y cero AuditEvent.
            self.stdout.write(self.style.SUCCESS("Dry-run: no se modificó la base."))
            return

        if not identity_ok and not allow_new:
            raise CommandError(
                "Apply bloqueado: hay DNI del CSV sin paciente local inequívoco."
            )

        batch_id = str(uuid.uuid4())
        batch = max(1, options["batch_size"])
        # Contadores mutables: sobreviven a interrupción a mitad de _write.
        progress = {
            "created_p": 0,
            "filled_p": 0,
            "created_o": 0,
            "created_r": 0,
            "created_protos": [],
            "created_dnis": [],
            "added_eab": 0,
        }

        # Inicio durable: fuera de atomic → log_event persiste de inmediato
        # (no hay atomicidad datos↔auditoría; ver chunk_committed post-commit).
        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha256,
            success=True,
            metadata={
                "status": "started",
                "patients_in_scope": len(patients),
                "patients_sin_orden_omitidos": patients_sin_orden,
                "orders_planned": len(new_orders),
                "results_planned": results_planned,
                "orders_skipped_existing": skipped_orders,
                "missing_catalog_codes": len(missing_codes),
            },
        )

        try:
            self._write(
                patients=patients,
                orders=new_orders,
                tipos=tipos,
                batch=batch,
                batch_id=batch_id,
                file_sha256=file_sha256,
                progress=progress,
            )
            progress["added_eab"] = self._add_missing_resultados(
                orders=orders,
                existing_numeros=existing_numeros,
                tipos=tipos,
                batch=batch,
                batch_id=batch_id,
                file_sha256=file_sha256,
            )
        except Exception as exc:
            _audit_labwin_batch(
                batch_id=batch_id,
                file_sha256=file_sha256,
                success=False,
                error_message=type(exc).__name__,
                metadata={
                    "patients_in_scope": len(patients),
                    "patients_sin_orden_omitidos": patients_sin_orden,
                    "orders_planned": len(new_orders),
                    "results_planned": results_planned,
                    "patients_created_confirmed": progress["created_p"],
                    "orders_created_confirmed": progress["created_o"],
                    "results_created_confirmed": progress["created_r"],
                    "orders_created_set_sha256": _set_digest(progress["created_protos"]),
                    "patients_created_hmac_set_sha256": _set_digest(
                        [_hmac_token("dni", d) for d in progress["created_dnis"]]
                    ),
                    "status": (
                        "failed_partial"
                        if (progress["created_o"] or progress["created_p"])
                        else "failed"
                    ),
                },
            )
            raise

        created_p = progress["created_p"]
        filled_p = progress["filled_p"]
        created_o = progress["created_o"]
        created_r = progress["created_r"]
        added_eab = progress["added_eab"]
        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha256,
            success=True,
            metadata={
                "patients_created": created_p,
                "patients_filled": filled_p,
                "patients_sin_orden_omitidos": patients_sin_orden,
                "orders_created": created_o,
                "results_created": created_r,
                "eab_added": added_eab,
                "orders_skipped_existing": skipped_orders,
                "missing_catalog_codes": len(missing_codes),
                "results_planned": results_planned,
                "orders_created_set_sha256": _set_digest(progress["created_protos"]),
                "patients_touched_hmac_set_sha256": _set_digest(
                    [_hmac_token("dni", d) for d in progress["created_dnis"]]
                    + [_hmac_token("dni", d) for d in patients]
                ),
                "status": "applied",
            },
        )
        self.stdout.write(self.style.SUCCESS("Importación LabWin completada."))
        self.stdout.write(f"  Lote: {batch_id}")
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
        batch_id: str,
        file_sha256: str,
        progress: dict,
    ) -> None:
        created_p = 0
        filled_p = 0
        created_dnis: list[str] = progress["created_dnis"]
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
                    created_dnis.append(dni)
                    continue
                dirty = _apply_fill(obj, row)
                if dirty:
                    obj.save(update_fields=dirty)
                    filled_p += 1
            for i in range(0, len(nuevos), batch):
                Paciente.objects.bulk_create(nuevos[i : i + batch], ignore_conflicts=True)
                created_p += len(nuevos[i : i + batch])

        progress["created_p"] = created_p
        progress["filled_p"] = filled_p

        # Post-commit del bloque pacientes (fuera de atomic → AuditEvent inmediato).
        if created_p or filled_p:
            _audit_labwin_batch(
                batch_id=batch_id,
                file_sha256=file_sha256,
                success=True,
                metadata={
                    "status": "patients_committed",
                    "patients_created": created_p,
                    "patients_filled": filled_p,
                    "patients_created_hmac_set_sha256": _set_digest(
                        [_hmac_token("dni", d) for d in created_dnis]
                    ),
                },
            )

        dni_to_id = dict(
            Paciente.objects.filter(dni__in=list(patients.keys())).values_list("dni", "id")
        )
        seen_proto: set[str] = set()
        created_o = 0
        created_r = 0
        created_protos: list[str] = progress["created_protos"]
        order_chunk_index = 0

        for i in range(0, len(orders), batch):
            chunk = orders[i : i + batch]
            chunk_protos: list[str] = []
            chunk_r = 0
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
                chunk_protos = [o.protocolo for o in chunk_ok]
                created_protos.extend(chunk_protos)
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
                    chunk_r = len(res_objs)
                    created_r += chunk_r
                for sol_id, fecha in fecha_by_id.items():
                    SolicitudExamen.objects.filter(pk=sol_id).update(
                        estado="FINALIZADO",
                        fecha_solicitud=fecha,
                    )

            progress["created_o"] = created_o
            progress["created_r"] = created_r

            # Tras commit del lote: trazabilidad durable (no atómica con el lote).
            if chunk_protos:
                order_chunk_index += 1
                _audit_labwin_batch(
                    batch_id=batch_id,
                    file_sha256=file_sha256,
                    success=True,
                    metadata={
                        "status": "chunk_committed",
                        "phase": "orders",
                        "chunk_index": order_chunk_index,
                        "orders_in_chunk": len(chunk_protos),
                        "results_in_chunk": chunk_r,
                        "orders_created_cumulative": created_o,
                        "results_created_cumulative": created_r,
                        "orders_created_set_sha256": _set_digest(chunk_protos),
                    },
                )
                hook = _labwin_order_chunk_hook
                if hook is not None:
                    hook(order_chunk_index)

    def _add_missing_resultados(
        self,
        *,
        orders: list[LabwinOrder],
        existing_numeros: set[str],
        tipos: dict[str, TipoExamen],
        batch: int,
        batch_id: str,
        file_sha256: str,
    ) -> int:
        """
        Solo completa códigos faltantes en órdenes NO finalizadas.
        Órdenes FINALIZADO quedan en cuarentena (no se mutan vía bulk_create).
        """
        pending = [o for o in orders if o.protocolo in existing_numeros]
        if not pending:
            return 0
        numeros_all = [o.protocolo for o in pending]
        estado_by_numero = dict(
            SolicitudExamen.objects.filter(numero__in=numeros_all).values_list(
                "numero", "estado"
            )
        )
        open_orders = [
            o for o in pending if estado_by_numero.get(o.protocolo) not in ("FINALIZADO",)
        ]
        quarantined = len(pending) - len(open_orders)
        if quarantined:
            self.stdout.write(
                self.style.WARNING(
                    f"  Cuarentena: {quarantined} órdenes existentes FINALIZADO "
                    "con posibles determinaciones faltantes (no se modifican)."
                )
            )
        if not open_orders:
            return 0

        added = 0
        eab_chunk_index = 0
        for i in range(0, len(open_orders), batch):
            chunk = open_orders[i : i + batch]
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
                    if sol.estado == "FINALIZADO":
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
            if res_objs:
                eab_chunk_index += 1
                _audit_labwin_batch(
                    batch_id=batch_id,
                    file_sha256=file_sha256,
                    success=True,
                    metadata={
                        "status": "chunk_committed",
                        "phase": "eab",
                        "chunk_index": eab_chunk_index,
                        "results_in_chunk": len(res_objs),
                        "eab_added_cumulative": added,
                        "orders_touched_set_sha256": _set_digest(numeros),
                    },
                )
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _set_digest(values: list[str] | set[str]) -> str:
    digest = hashlib.sha256()
    for item in sorted(values):
        digest.update(item.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _hmac_token(kind: str, value: str) -> str:
    """Clave de procedencia acotada (no reversible sin secreto)."""
    import hmac

    from django.conf import settings

    secret = (
        getattr(settings, "LABWIN_PROVENANCE_HMAC_KEY", None)
        or getattr(settings, "SECRET_KEY", "dev")
    )
    raw = hmac.new(
        str(secret).encode("utf-8"),
        f"{kind}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return raw[:32]


def _audit_labwin_batch(
    *,
    batch_id: str,
    file_sha256: str,
    success: bool,
    metadata: dict,
    error_message: str | None = None,
) -> None:
    """Registra AuditEvent de lote sin PHI. Usa request_id=batch_id para correlación."""
    from auditoria.audit_service import log_event
    from auditoria.context import request_id_var

    token = request_id_var.set(batch_id)
    try:
        meta = {
            "file_sha256": file_sha256,
            "batch_id": batch_id,
            **metadata,
        }
        log_event(
            action="IMPORT_LABWIN_BATCH",
            entity_type="laboratorio.LabwinImportBatch",
            entity_id=batch_id,
            entity_repr=f"labwin-batch:{batch_id[:8]}",
            metadata=meta,
            module="laboratorio.import_labwin_csv",
            success=success,
            error_message=(error_message or "")[:500] or None,
        )
    finally:
        request_id_var.reset(token)
