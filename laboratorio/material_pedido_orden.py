"""
Material de pedido en órdenes clínicas / estudios micro.

- Mapeo tipo_muestra → material_pedido (catálogo).
- Inferencia sobre órdenes legacy (material_pedido NULL) sin mutar filas.
- Anti-duplicado: paciente + material + fecha_programada_toma.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import connection, transaction
from django.db.models import Q

from laboratorio.materiales_pedido_catalogo import MATERIALES_PEDIDO, as_api_list
from laboratorio.models import PanelExamen, SolicitudExamen, TipoExamen


ESTADOS_ORDEN_TERMINALES = frozenset({"FINALIZADO", "CANCELADO"})
ESTADOS_MICRO_TERMINALES = frozenset({"CANCELADO", "VALIDADO", "INFORMADO"})

MENSAJE_MATERIAL_ACTIVO = (
    "Ya existe una orden activa de {material} para ese día de extracción. "
    "Esperá a que el laboratorio la finalice, o programalo para otro día."
)

MENSAJE_MICRO_ACTIVO = (
    "Ya existe un pedido de microbiología activo para ese material/procedencia "
    "y día de extracción."
)

MENSAJE_MATERIAL_AMBIGUO = (
    "No se pudo determinar el material de pedido de una orden existente "
    "(solicitud {solicitud_id}, códigos sin mapeo: {codigos}). "
    "Revisá el catálogo antes de crear un pedido nuevo."
)


def _muestra_a_material() -> dict[str, str]:
    """codigo TipoMuestra (upper) → codigo material_pedido."""
    out: dict[str, str] = {}
    for row in as_api_list():
        mat = row["codigo"]
        for tm in row.get("tipo_muestra_codigos") or []:
            out[(tm or "").upper()] = mat
    return out


_MUESTRA_A_MATERIAL: dict[str, str] | None = None


def muestra_codigo_a_material(muestra_codigo: str | None) -> str | None:
    global _MUESTRA_A_MATERIAL
    if _MUESTRA_A_MATERIAL is None:
        _MUESTRA_A_MATERIAL = _muestra_a_material()
    if not muestra_codigo:
        return None
    return _MUESTRA_A_MATERIAL.get(muestra_codigo.upper().strip())


def material_pedido_valido(codigo: str | None) -> bool:
    if not codigo:
        return False
    c = codigo.upper().strip()
    return any(m.codigo == c for m in MATERIALES_PEDIDO)


def normalizar_material_pedido(codigo: str | None) -> str:
    return (codigo or "").upper().strip()


@dataclass
class InferenciaMateriales:
    materiales: frozenset[str]
    codigos_sin_mapeo: tuple[str, ...]
    ambiguo: bool


def inferir_materiales_de_solicitud(solicitud: SolicitudExamen) -> InferenciaMateriales:
    """
    Materiales representados por una orden (explícito o legacy).
    No muta la solicitud.
    """
    explicit = (getattr(solicitud, "material_pedido", None) or "").strip().upper()
    if explicit:
        return InferenciaMateriales(
            materiales=frozenset({explicit}),
            codigos_sin_mapeo=(),
            ambiguo=False,
        )

    mats: set[str] = set()
    sin: list[str] = []
    tipo_ids = set(solicitud.tipos_examen.values_list("id", flat=True))
    # Componentes de paneles vinculados
    for panel in solicitud.paneles.prefetch_related("tipos_examen").all():
        for te in panel.tipos_examen.all():
            tipo_ids.add(te.id)

    tipos = TipoExamen.objects.filter(pk__in=tipo_ids).select_related(
        "tipo_muestra_requerida"
    )
    for te in tipos:
        tm = getattr(te.tipo_muestra_requerida, "codigo", None) if te.tipo_muestra_requerida_id else None
        mat = muestra_codigo_a_material(tm)
        if mat:
            mats.add(mat)
        else:
            sin.append(te.codigo or str(te.pk))

    return InferenciaMateriales(
        materiales=frozenset(mats),
        codigos_sin_mapeo=tuple(sorted(set(sin))),
        ambiguo=bool(sin) and not mats,
    )


def tipo_examen_compatible_con_material(
    tipo: TipoExamen, material_codigo: str | None
) -> bool:
    """True si el examen mapea al material (o material vacío = legacy permisivo por muestra)."""
    mat = normalizar_material_pedido(material_codigo)
    tm = getattr(tipo.tipo_muestra_requerida, "codigo", None) if tipo.tipo_muestra_requerida_id else None
    mapped = muestra_codigo_a_material(tm)
    if not mat:
        # Legacy: compatible si mapea a algún material conocido o no tiene muestra
        return True
    if mapped is None:
        return False
    return mapped == mat


def componentes_panel_por_material(panel: PanelExamen) -> dict[str, list[int]]:
    """material_codigo → lista de tipo_examen_id del panel."""
    out: dict[str, list[int]] = {}
    for te in panel.tipos_examen.filter(activo=True).select_related(
        "tipo_muestra_requerida"
    ):
        tm = getattr(te.tipo_muestra_requerida, "codigo", None) if te.tipo_muestra_requerida_id else None
        mat = muestra_codigo_a_material(tm)
        if not mat:
            continue
        out.setdefault(mat, []).append(te.id)
    return out


def _lock_key(paciente_id: int, material: str, fecha) -> str:
    return f"lims_mat:{paciente_id}:{material}:{fecha.isoformat()}"


def adquirir_locks_materiales(paciente_id: int, materiales: set[str], fecha) -> None:
    """
    Lock advisory por (paciente, material, fecha) — PostgreSQL.
    En SQLite (tests) es no-op; la atomicidad de la transacción sigue aplicando.
    """
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        for mat in sorted(materiales):
            key = _lock_key(paciente_id, mat, fecha)
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [key])


def ordenes_activas_mismo_dia(paciente_id: int, fecha_programada_toma):
    return (
        SolicitudExamen.objects.filter(
            paciente_id=paciente_id,
            fecha_programada_toma=fecha_programada_toma,
        )
        .exclude(estado__in=ESTADOS_ORDEN_TERMINALES)
        .prefetch_related("tipos_examen__tipo_muestra_requerida", "paneles__tipos_examen__tipo_muestra_requerida")
    )


@dataclass
class ConflictoMaterial:
    material: str
    solicitud_id: int
    mensaje: str


def buscar_conflictos_materiales_clinicos(
    paciente_id: int,
    fecha_programada_toma,
    materiales: set[str],
    *,
    exclude_solicitud_id: int | None = None,
) -> list[ConflictoMaterial]:
    """Detecta órdenes activas que ya cubren alguno de los materiales pedidos."""
    conflictos: list[ConflictoMaterial] = []
    qs = ordenes_activas_mismo_dia(paciente_id, fecha_programada_toma)
    if exclude_solicitud_id:
        qs = qs.exclude(pk=exclude_solicitud_id)

    mats_needed = {normalizar_material_pedido(m) for m in materiales if m}
    for sol in qs:
        inf = inferir_materiales_de_solicitud(sol)
        if inf.ambiguo or (inf.codigos_sin_mapeo and not inf.materiales):
            conflictos.append(
                ConflictoMaterial(
                    material="?",
                    solicitud_id=sol.pk,
                    mensaje=MENSAJE_MATERIAL_AMBIGUO.format(
                        solicitud_id=sol.pk,
                        codigos=", ".join(inf.codigos_sin_mapeo) or "—",
                    ),
                )
            )
            continue
        overlap = mats_needed & set(inf.materiales)
        for mat in sorted(overlap):
            conflictos.append(
                ConflictoMaterial(
                    material=mat,
                    solicitud_id=sol.pk,
                    mensaje=MENSAJE_MATERIAL_ACTIVO.format(material=mat),
                )
            )
    return conflictos


def buscar_conflictos_micro(
    paciente_id: int,
    fecha_programada_toma,
    *,
    material_pedido: str,
    exclude_estudio_id: int | None = None,
) -> list[str]:
    """Anti-dup micro: paciente + material_pedido + fecha (cierra D4 ASPIRADO genérico)."""
    from laboratorio.models_microbiologia import EstudioMicrobiologia

    mat = normalizar_material_pedido(material_pedido)
    if not mat:
        return ["Indicá el material de pedido del estudio de microbiología."]

    qs = EstudioMicrobiologia.objects.filter(
        paciente_id=paciente_id,
        fecha_programada_toma=fecha_programada_toma,
        material_pedido=mat,
    ).exclude(estado__in=ESTADOS_MICRO_TERMINALES)
    if exclude_estudio_id:
        qs = qs.exclude(pk=exclude_estudio_id)
    if qs.exists():
        return [MENSAJE_MICRO_ACTIVO]
    return []
