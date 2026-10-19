"""
Pedido LIMS atómico: N órdenes clínicas + M estudios micro en una transacción.

Único camino de confirmación médica (consulta / guardia / internación / mostrador médico).
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from laboratorio.material_pedido_orden import (
    MATERIALES_UNIFICABLES_AMBULATORIO,
    adquirir_locks_materiales,
    buscar_conflictos_materiales_clinicos,
    buscar_conflictos_micro,
    componentes_panel_por_material,
    material_pedido_valido,
    muestra_codigo_a_material,
    normalizar_material_pedido,
    tipo_examen_compatible_con_material,
)
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.models_pedido_idempotencia import PedidoCompletoIdempotencia
from laboratorio.origen_solicitud import (
    es_origen_ambulatorio,
    inferir_origen_solicitud,
    normalizar_origen_solicitud,
)
from laboratorio.panel_componentes_orden import ordenar_queryset_panel

logger = logging.getLogger(__name__)


def hash_payload_pedido(payload: dict) -> str:
    """Hash canónico del body (sin Idempotency-Key)."""
    canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolver_tipos_para_material(
    examenes_ids: list[int],
    paneles_ids: list[int],
    material: str,
) -> tuple[set[int], set[int], list[str]]:
    """
    Tipos a crear en la orden de este material + paneles a vincular.
    Fail-closed si un componente pedido no mapea al material.
    """
    mat = normalizar_material_pedido(material)
    errores: list[str] = []
    tipos: set[int] = set()
    paneles_ok: set[int] = set()

    for tid in examenes_ids or []:
        try:
            te = TipoExamen.objects.select_related("tipo_muestra_requerida").get(pk=int(tid))
        except (TipoExamen.DoesNotExist, TypeError, ValueError):
            errores.append(f"Examen inexistente: {tid}")
            continue
        if not tipo_examen_compatible_con_material(te, mat):
            errores.append(
                f"El examen {te.codigo or te.pk} no corresponde al material {mat}."
            )
            continue
        tipos.add(te.id)

    for pid in paneles_ids or []:
        try:
            panel = PanelExamen.objects.prefetch_related(
                "tipos_examen__tipo_muestra_requerida"
            ).get(pk=int(pid))
        except (PanelExamen.DoesNotExist, TypeError, ValueError):
            errores.append(f"Panel inexistente: {pid}")
            continue
        por_mat = componentes_panel_por_material(panel)
        if mat not in por_mat and por_mat:
            # Panel multi-material sin componentes de este material: no vincular.
            continue
        comps = por_mat.get(mat) or []
        if not comps and not por_mat:
            # Panel sin mapeo de muestra → fail-closed
            errores.append(
                f"El panel {panel.codigo or panel.pk} tiene componentes sin material mapeado."
            )
            continue
        if not comps:
            continue
        paneles_ok.add(panel.id)
        tipos.update(comps)

    # Insumos de calculados (mismo criterio que create granular, acotado a tipos ya elegidos)
    if tipos:
        from laboratorio.calculos_derivados import INSUMOS_POR_CODIGO_CALCULADO
        from laboratorio.catalogo_solicitud_papel import LEGACY_EXAMEN_A_PANEL

        por_id = {
            tid: (c or "").strip().upper()
            for tid, c in TipoExamen.objects.filter(pk__in=tipos).values_list("id", "codigo")
        }
        for codigo_legacy, panel_codigo in list(LEGACY_EXAMEN_A_PANEL.items()):
            if codigo_legacy not in por_id.values():
                continue
            try:
                panel = PanelExamen.objects.get(codigo=panel_codigo, activo=True)
            except PanelExamen.DoesNotExist:
                continue
            por_mat = componentes_panel_por_material(panel)
            comps = por_mat.get(mat) or []
            if comps:
                paneles_ok.add(panel.pk)
                tipos.update(comps)
            for tid, codigo in list(por_id.items()):
                if codigo == codigo_legacy:
                    tipos.discard(tid)

        codigos = {
            (c or "").strip().upper()
            for c in TipoExamen.objects.filter(pk__in=tipos).values_list("codigo", flat=True)
        }
        # Insumos de calculados: siempre (aunque sean de otro material).
        # Ej.: CLEAR_CREA en orden ORINA exige CREATI (suero) para calcular e informar.
        for codigo in list(codigos):
            for insumo in INSUMOS_POR_CODIGO_CALCULADO.get(codigo, ()):
                code = (insumo or "").strip().upper()
                if not code or code in codigos:
                    continue
                te = TipoExamen.objects.filter(codigo=code, activo=True).first()
                if te:
                    tipos.add(te.id)
                    codigos.add(code)

    return tipos, paneles_ok, errores


def _resolver_tipos_materiales_permitidos(
    examenes_ids: list[int],
    paneles_ids: list[int],
    materiales: set[str],
) -> tuple[set[int], set[int], list[str]]:
    """
    Tipos/paneles para una orden que cubre varios materiales (bucket ambulatorio).
    Solo acepta componentes cuyo material mapeado está en ``materiales``.
    """
    mats = {normalizar_material_pedido(m) for m in materiales if m}
    errores: list[str] = []
    tipos: set[int] = set()
    paneles_ok: set[int] = set()

    for tid in examenes_ids or []:
        try:
            te = TipoExamen.objects.select_related("tipo_muestra_requerida").get(pk=int(tid))
        except (TipoExamen.DoesNotExist, TypeError, ValueError):
            errores.append(f"Examen inexistente: {tid}")
            continue
        tm = (
            getattr(te.tipo_muestra_requerida, "codigo", None)
            if te.tipo_muestra_requerida_id
            else None
        )
        mapped = muestra_codigo_a_material(tm)
        if mapped not in mats:
            errores.append(
                f"El examen {te.codigo or te.pk} no corresponde a los materiales "
                f"{', '.join(sorted(mats))}."
            )
            continue
        tipos.add(te.id)

    for pid in paneles_ids or []:
        try:
            panel = PanelExamen.objects.prefetch_related(
                "tipos_examen__tipo_muestra_requerida"
            ).get(pk=int(pid))
        except (PanelExamen.DoesNotExist, TypeError, ValueError):
            errores.append(f"Panel inexistente: {pid}")
            continue
        por_mat = componentes_panel_por_material(panel)
        comps: list[int] = []
        for mat in mats:
            comps.extend(por_mat.get(mat) or [])
        if not comps and por_mat:
            continue
        if not comps and not por_mat:
            errores.append(
                f"El panel {panel.codigo or panel.pk} tiene componentes sin material mapeado."
            )
            continue
        if not comps:
            continue
        paneles_ok.add(panel.id)
        tipos.update(comps)

    if tipos:
        from laboratorio.calculos_derivados import INSUMOS_POR_CODIGO_CALCULADO
        from laboratorio.catalogo_solicitud_papel import LEGACY_EXAMEN_A_PANEL

        por_id = {
            tid: (c or "").strip().upper()
            for tid, c in TipoExamen.objects.filter(pk__in=tipos).values_list("id", "codigo")
        }
        for codigo_legacy, panel_codigo in list(LEGACY_EXAMEN_A_PANEL.items()):
            if codigo_legacy not in por_id.values():
                continue
            try:
                panel = PanelExamen.objects.get(codigo=panel_codigo, activo=True)
            except PanelExamen.DoesNotExist:
                continue
            por_mat = componentes_panel_por_material(panel)
            comps = []
            for mat in mats:
                comps.extend(por_mat.get(mat) or [])
            if comps:
                paneles_ok.add(panel.pk)
                tipos.update(comps)
            for tid, codigo in list(por_id.items()):
                if codigo == codigo_legacy:
                    tipos.discard(tid)

        codigos = {
            (c or "").strip().upper()
            for c in TipoExamen.objects.filter(pk__in=tipos).values_list("codigo", flat=True)
        }
        for codigo in list(codigos):
            for insumo in INSUMOS_POR_CODIGO_CALCULADO.get(codigo, ()):
                code = (insumo or "").strip().upper()
                if not code or code in codigos:
                    continue
                te = TipoExamen.objects.filter(codigo=code, activo=True).first()
                if te:
                    tipos.add(te.id)
                    codigos.add(code)

    return tipos, paneles_ok, errores


def colapsar_solicitudes_lab_ambulatorio(
    solicitudes_lab: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Une grupos SANGRE/ORINA/MATERIA_FECAL en un solo ítem si hay ≥2 materiales.
    Otros materiales (LCR, etc.) quedan aparte. Un solo material del bucket: sin cambio.
    """
    uni: list[dict[str, Any]] = []
    resto: list[dict[str, Any]] = []
    for g in solicitudes_lab or []:
        mat = normalizar_material_pedido(g.get("material_pedido"))
        if mat in MATERIALES_UNIFICABLES_AMBULATORIO:
            uni.append(g)
        else:
            resto.append(g)

    mats_uni = {
        normalizar_material_pedido(g.get("material_pedido"))
        for g in uni
        if normalizar_material_pedido(g.get("material_pedido"))
    }
    if len(mats_uni) < 2:
        return list(solicitudes_lab or [])

    examenes_ids: list[int] = []
    paneles_ids: list[int] = []
    obs_parts: list[str] = []
    for g in uni:
        examenes_ids.extend(int(x) for x in (g.get("examenes_ids") or []))
        paneles_ids.extend(int(x) for x in (g.get("paneles_ids") or []))
        o = (g.get("observaciones") or "").strip()
        if o and o not in obs_parts:
            obs_parts.append(o)

    # Dedup preservando orden
    seen_e: set[int] = set()
    examenes_dedup: list[int] = []
    for tid in examenes_ids:
        if tid not in seen_e:
            seen_e.add(tid)
            examenes_dedup.append(tid)
    seen_p: set[int] = set()
    paneles_dedup: list[int] = []
    for pid in paneles_ids:
        if pid not in seen_p:
            seen_p.add(pid)
            paneles_dedup.append(pid)

    merged: dict[str, Any] = {
        "material_pedido": "",
        "examenes_ids": examenes_dedup,
        "paneles_ids": paneles_dedup,
        "observaciones": " | ".join(obs_parts),
        "_materiales_unificados": sorted(mats_uni),
    }
    return [merged] + resto


def _crear_solicitud_material(
    *,
    paciente,
    medico_interno,
    medico_externo_nombre: str,
    origen_solicitud: str,
    consulta_hc,
    fecha_programada_toma,
    observaciones: str,
    material_pedido: str,
    examenes_ids: list[int],
    paneles_ids: list[int],
    obra_social_orden: str = "",
    afiliado_orden: str = "",
) -> SolicitudExamen:
    from laboratorio.derivacion_service import defaults_derivacion_para_tipo
    from laboratorio.examen_orina_micro import valor_inicial_resultado
    from laboratorio.restricciones_frecuencia import (
        RestriccionFrecuenciaError,
        assert_puede_agregar_ensayos,
    )

    mat = normalizar_material_pedido(material_pedido)
    if not material_pedido_valido(mat):
        raise ValidationError({"material_pedido": f"Material de pedido inválido: {material_pedido}"})

    tipos, paneles_ok, errores = _resolver_tipos_para_material(
        examenes_ids, paneles_ids, mat
    )
    if errores:
        raise ValidationError({"detail": errores[0], "errores": errores})
    if not tipos and not paneles_ok:
        raise ValidationError(
            {"detail": f"No hay exámenes para el material {mat} en este pedido."}
        )

    try:
        assert_puede_agregar_ensayos(
            None,
            paciente.pk,
            tipos,
            origen_solicitud=origen_solicitud or "",
        )
    except RestriccionFrecuenciaError as exc:
        raise ValidationError(str(exc)) from exc

    solicitud = SolicitudExamen.objects.create(
        paciente=paciente,
        medico_interno=medico_interno,
        medico_externo_nombre=(medico_externo_nombre or "").strip(),
        origen_solicitud=origen_solicitud or "",
        consulta_hc=consulta_hc,
        fecha_programada_toma=fecha_programada_toma,
        observaciones=observaciones or "",
        material_pedido=mat,
        obra_social_orden=obra_social_orden or "",
        afiliado_orden=afiliado_orden or "",
        estado="PENDIENTE",
    )
    if paneles_ok:
        solicitud.paneles.set(list(paneles_ok))

    tipos_creados: set[int] = set()
    for tid in sorted(tipos):
        try:
            te = TipoExamen.objects.select_related("laboratorio_derivacion").get(pk=tid)
        except TipoExamen.DoesNotExist:
            continue
        ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=te,
            valor_obtenido=valor_inicial_resultado(te),
            es_patologico=False,
            **defaults_derivacion_para_tipo(te),
        )
        tipos_creados.add(tid)

    if tipos_creados:
        solicitud.tipos_examen.set(list(tipos_creados))
    return solicitud


def _crear_solicitud_multi_material(
    *,
    paciente,
    medico_interno,
    medico_externo_nombre: str,
    origen_solicitud: str,
    consulta_hc,
    fecha_programada_toma,
    observaciones: str,
    materiales: set[str],
    examenes_ids: list[int],
    paneles_ids: list[int],
    obra_social_orden: str = "",
    afiliado_orden: str = "",
) -> SolicitudExamen:
    """Orden ambulatoria unificada: material_pedido vacío; anti-dup por inferencia."""
    from laboratorio.derivacion_service import defaults_derivacion_para_tipo
    from laboratorio.examen_orina_micro import valor_inicial_resultado
    from laboratorio.restricciones_frecuencia import (
        RestriccionFrecuenciaError,
        assert_puede_agregar_ensayos,
    )

    mats = {normalizar_material_pedido(m) for m in materiales if m}
    if not mats:
        raise ValidationError({"material_pedido": "Materiales unificados vacíos."})
    if not mats.issubset(MATERIALES_UNIFICABLES_AMBULATORIO):
        raise ValidationError(
            {
                "material_pedido": (
                    "Solo SANGRE, ORINA y MATERIA_FECAL se unifican en ambulatorio."
                )
            }
        )

    tipos, paneles_ok, errores = _resolver_tipos_materiales_permitidos(
        examenes_ids, paneles_ids, mats
    )
    if errores:
        raise ValidationError({"detail": errores[0], "errores": errores})
    if not tipos and not paneles_ok:
        raise ValidationError(
            {"detail": "No hay exámenes para los materiales unificados en este pedido."}
        )

    try:
        assert_puede_agregar_ensayos(
            None,
            paciente.pk,
            tipos,
            origen_solicitud=origen_solicitud or "",
        )
    except RestriccionFrecuenciaError as exc:
        raise ValidationError(str(exc)) from exc

    solicitud = SolicitudExamen.objects.create(
        paciente=paciente,
        medico_interno=medico_interno,
        medico_externo_nombre=(medico_externo_nombre or "").strip(),
        origen_solicitud=origen_solicitud or "",
        consulta_hc=consulta_hc,
        fecha_programada_toma=fecha_programada_toma,
        observaciones=observaciones or "",
        material_pedido="",
        obra_social_orden=obra_social_orden or "",
        afiliado_orden=afiliado_orden or "",
        estado="PENDIENTE",
    )
    if paneles_ok:
        solicitud.paneles.set(list(paneles_ok))

    tipos_creados: set[int] = set()
    for tid in sorted(tipos):
        try:
            te = TipoExamen.objects.select_related("laboratorio_derivacion").get(pk=tid)
        except TipoExamen.DoesNotExist:
            continue
        ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=te,
            valor_obtenido=valor_inicial_resultado(te),
            es_patologico=False,
            **defaults_derivacion_para_tipo(te),
        )
        tipos_creados.add(tid)

    if tipos_creados:
        solicitud.tipos_examen.set(list(tipos_creados))
    return solicitud


def _materiales_de_grupo_lab(g: dict[str, Any]) -> set[str]:
    """Materiales clínicos que cubre un ítem de solicitudes_lab (incl. unificado)."""
    uni = g.get("_materiales_unificados") or g.get("materiales_unificados")
    if uni:
        return {normalizar_material_pedido(m) for m in uni if m}
    mat = normalizar_material_pedido(g.get("material_pedido"))
    return {mat} if mat else set()


@transaction.atomic
def crear_pedido_completo(
    *,
    user,
    paciente_id: int,
    fecha_programada_toma,
    solicitudes_lab: list[dict[str, Any]],
    estudios_micro: list[dict[str, Any]],
    medico_id: int | None = None,
    medico_externo_nombre: str = "",
    consulta_hc_id: int | None = None,
    origen_solicitud: str = "",
    observaciones: str = "",
    observaciones_micro: str = "",
    obra_social: str = "",
    numero_afiliado: str = "",
    afiliacion_id: int | None = None,
    idempotency_key: str | None = None,
    payload_for_hash: dict | None = None,
) -> dict:
    """
    Crea N clínicas + M micros. Rollback total si algo falla.
    Idempotencia: misma key + mismo hash → misma respuesta; key + hash distinto → 409.
    """
    from pacientes.models import Paciente
    from medicos.models import Medico
    from historias_clinicas.models import Consulta
    from laboratorio.microbiologia_estado import (
        MicrobiologiaAccionError,
        crear_estudio_desde_pedido,
    )
    from pacientes.afiliaciones import normalizar_snapshot_os, upsert_afiliacion
    from pacientes.models import PacienteAfiliacion

    if not solicitudes_lab and not estudios_micro:
        raise ValidationError({"detail": "Indicá al menos un pedido clínico o de microbiología."})

    payload_hash = hash_payload_pedido(payload_for_hash or {})
    if idempotency_key:
        existing = (
            PedidoCompletoIdempotencia.objects.select_for_update()
            .filter(key=idempotency_key)
            .first()
        )
        if existing is not None:
            if existing.payload_hash != payload_hash:
                raise ValidationError(
                    {
                        "detail": (
                            "Idempotency-Key ya usada con otro pedido. "
                            "Usá una clave nueva o reintentá con el mismo payload."
                        ),
                        "code": "idempotency_conflict",
                    }
                )
            return existing.response_json

    try:
        paciente = Paciente.objects.get(pk=int(paciente_id))
    except (Paciente.DoesNotExist, TypeError, ValueError) as exc:
        raise ValidationError({"paciente_id": "Paciente inexistente."}) from exc

    medico = None
    if medico_id is not None:
        try:
            medico = Medico.objects.get(pk=int(medico_id))
        except (Medico.DoesNotExist, TypeError, ValueError) as exc:
            raise ValidationError({"medico_id": "Médico inexistente."}) from exc

    consulta_hc = None
    if consulta_hc_id is not None:
        try:
            consulta_hc = Consulta.objects.get(pk=int(consulta_hc_id))
        except (Consulta.DoesNotExist, TypeError, ValueError) as exc:
            raise ValidationError({"consulta_hc_id": "Consulta inexistente."}) from exc

    if fecha_programada_toma is None:
        fecha_programada_toma = timezone.localdate()
    elif isinstance(fecha_programada_toma, str):
        from datetime import date as date_cls

        try:
            fecha_programada_toma = date_cls.fromisoformat(fecha_programada_toma[:10])
        except ValueError as exc:
            raise ValidationError(
                {"fecha_programada_toma": "Fecha de extracción inválida (YYYY-MM-DD)."}
            ) from exc

    origen = normalizar_origen_solicitud(origen_solicitud) or (origen_solicitud or "")
    if not origen:
        origen = (
            inferir_origen_solicitud(
                paciente_id=paciente.pk,
                consulta_hc=consulta_hc,
            )
            or ""
        )

    snap_os, snap_afil = "", ""
    if afiliacion_id is not None:
        try:
            afil = PacienteAfiliacion.objects.get(
                pk=afiliacion_id, paciente_id=paciente.pk, activo=True
            )
        except PacienteAfiliacion.DoesNotExist as exc:
            raise ValidationError(
                {"afiliacion_id": "Afiliación inexistente para este paciente."}
            ) from exc
        snap_os, snap_afil = afil.obra_social, afil.numero_afiliado or ""
        upsert_afiliacion(
            paciente, obra_social=snap_os, numero_afiliado=snap_afil, marcar_principal=True
        )
    elif obra_social or numero_afiliado:
        snap_os, snap_afil = normalizar_snapshot_os(obra_social, numero_afiliado)
        if snap_os:
            upsert_afiliacion(
                paciente, obra_social=snap_os, numero_afiliado=snap_afil, marcar_principal=True
            )

    # Ambulatorio: colapsar SANGRE+ORINA+MATERIA_FECAL en un solo grupo clínico.
    if es_origen_ambulatorio(origen):
        solicitudes_lab = colapsar_solicitudes_lab_ambulatorio(list(solicitudes_lab or []))

    # Validar y lockear todos los materiales clínicos + micro antes de crear.
    mats_clinicos: set[str] = set()
    for g in solicitudes_lab:
        mats_g = _materiales_de_grupo_lab(g)
        if not mats_g:
            mat = normalizar_material_pedido(g.get("material_pedido"))
            if not material_pedido_valido(mat):
                raise ValidationError(
                    {
                        "material_pedido": (
                            "Material de pedido obligatorio/válido en cada grupo clínico."
                        )
                    }
                )
            mats_g = {mat}
        for mat in mats_g:
            if not material_pedido_valido(mat):
                raise ValidationError(
                    {
                        "material_pedido": (
                            "Material de pedido obligatorio/válido en cada grupo clínico."
                        )
                    }
                )
            mats_clinicos.add(mat)

    mats_micro: set[str] = set()
    for g in estudios_micro:
        mat = normalizar_material_pedido(g.get("material_pedido"))
        if not material_pedido_valido(mat):
            raise ValidationError(
                {
                    "material_pedido": (
                        "Material de pedido obligatorio en cada estudio de microbiología."
                    )
                }
            )
        mats_micro.add(mat)

    adquirir_locks_materiales(paciente.pk, mats_clinicos | mats_micro, fecha_programada_toma)

    for mat in mats_micro:
        msgs = buscar_conflictos_micro(
            paciente.pk, fecha_programada_toma, material_pedido=mat
        )
        if msgs:
            raise ValidationError({"detail": msgs[0], "material": mat})

    from laboratorio.solicitud_orden_abierta import (
        agregar_examenes_a_solicitud,
        orden_esta_abierta,
    )

    creadas_lab: list[SolicitudExamen] = []
    for g in solicitudes_lab:
        mats_g = _materiales_de_grupo_lab(g)
        mat = normalizar_material_pedido(g.get("material_pedido"))
        if not mats_g and mat:
            mats_g = {mat}
        conflictos = buscar_conflictos_materiales_clinicos(
            paciente.pk, fecha_programada_toma, mats_g
        )
        if conflictos:
            c0 = conflictos[0]
            sol_exist = (
                SolicitudExamen.objects.select_for_update()
                .prefetch_related("muestras")
                .get(pk=c0.solicitud_id)
            )
            # Mismo material + PENDIENTE sin etiquetas → agregar a esa orden.
            # Otro estado (con etiquetas / en proceso) → no crear orden duplicada.
            if orden_esta_abierta(sol_exist):
                agregar_examenes_a_solicitud(
                    sol_exist,
                    examenes_ids=list(g.get("examenes_ids") or []),
                    paneles_ids=list(g.get("paneles_ids") or []),
                    user=user,
                )
                if (g.get("observaciones") or observaciones) and not (
                    sol_exist.observaciones or ""
                ).strip():
                    sol_exist.observaciones = (
                        g.get("observaciones") or observaciones or ""
                    ).strip()
                    sol_exist.save(update_fields=["observaciones"])
                creadas_lab.append(sol_exist)
            else:
                mat_label = c0.material or mat or ",".join(sorted(mats_g))
                raise ValidationError(
                    {
                        "detail": (
                            f"Ya existe una orden de {mat_label} para ese día "
                            f"({sol_exist.numero or sol_exist.pk}) con etiquetas o en proceso. "
                            "Un pedido médico no puede crear otra ni agregar exámenes; "
                            "el laboratorio puede agregarlos a la orden existente, "
                            "o programalo para otro día."
                        ),
                        "solicitud_id": sol_exist.pk,
                        "material": mat_label,
                    }
                )
            continue

        if (
            g.get("_materiales_unificados")
            or g.get("materiales_unificados")
            or (not mat and len(mats_g) > 1)
        ):
            sol = _crear_solicitud_multi_material(
                paciente=paciente,
                medico_interno=medico,
                medico_externo_nombre=medico_externo_nombre,
                origen_solicitud=origen,
                consulta_hc=consulta_hc,
                fecha_programada_toma=fecha_programada_toma,
                observaciones=g.get("observaciones") or observaciones or "",
                materiales=mats_g,
                examenes_ids=list(g.get("examenes_ids") or []),
                paneles_ids=list(g.get("paneles_ids") or []),
                obra_social_orden=snap_os,
                afiliado_orden=snap_afil,
            )
        else:
            sol = _crear_solicitud_material(
                paciente=paciente,
                medico_interno=medico,
                medico_externo_nombre=medico_externo_nombre,
                origen_solicitud=origen,
                consulta_hc=consulta_hc,
                fecha_programada_toma=fecha_programada_toma,
                observaciones=g.get("observaciones") or observaciones or "",
                material_pedido=g["material_pedido"],
                examenes_ids=list(g.get("examenes_ids") or []),
                paneles_ids=list(g.get("paneles_ids") or []),
                obra_social_orden=snap_os,
                afiliado_orden=snap_afil,
            )
        creadas_lab.append(sol)

    creados_micro = []
    for g in estudios_micro:
        try:
            est = crear_estudio_desde_pedido(
                paciente=paciente,
                tipo_cultivo_id=int(g["tipo_cultivo_id"]),
                tipo_muestra_micro_id=int(g["tipo_muestra_micro_id"]),
                medico_interno=medico,
                medico_externo_nombre=medico_externo_nombre,
                observaciones=g.get("observaciones") or observaciones_micro or "",
                actor=user,
                view="pedidos_completos",
                origen_solicitud=origen,
                consulta_hc=consulta_hc,
                fecha_programada_toma=fecha_programada_toma,
                obra_social_orden=snap_os,
                afiliado_orden=snap_afil,
                material_pedido=normalizar_material_pedido(g.get("material_pedido")),
            )
        except MicrobiologiaAccionError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        creados_micro.append(est)

    # Únicos: merge al mismo id no debe duplicar en la respuesta.
    sol_ids: list[int] = []
    for s in creadas_lab:
        if s.pk not in sol_ids:
            sol_ids.append(s.pk)
    micro_ids = [e.pk for e in creados_micro]
    pedidos = [{"tipo": "LAB_CLINICO", "id": sid} for sid in sol_ids] + [
        {"tipo": "MICROBIOLOGIA", "id": mid} for mid in micro_ids
    ]
    response = {
        "pedidos": pedidos,
        "solicitudes_ids": sol_ids,
        "estudios_micro_ids": micro_ids,
        "fecha_programada_toma": fecha_programada_toma.isoformat()
        if hasattr(fecha_programada_toma, "isoformat")
        else str(fecha_programada_toma),
    }

    if idempotency_key:
        PedidoCompletoIdempotencia.objects.create(
            key=idempotency_key,
            payload_hash=payload_hash,
            user=user,
            response_json=response,
        )

    return response


# Silencia import unused en type checkers
_ = (muestra_codigo_a_material, ordenar_queryset_panel, serializers)
