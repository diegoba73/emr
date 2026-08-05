"""
Numeración y resolución de códigos LIMS (familia LAB).

Fuente única de verdad para:
- protocolo compartido LAB-YYYY-XXXXX (lab clínico + microbiología);
- códigos de tubo LAB-YYYY-XXXXX-nn;
- parse / resolve de escaneo (canónico + legacy MUE/MIC/MICB solo lectura).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from laboratorio.models import SolicitudExamen
    from laboratorio.models_catalog import Muestra
    from laboratorio.models_microbiologia import EstudioMicrobiologia

PROTOCOLO_PREFIX = "LAB"
PROTOCOLO_DIGITS = 5
TUBO_SUFFIX_DIGITS = 2

# LAB-2026-00042
RE_PROTOCOLO = re.compile(
    rf"^{PROTOCOLO_PREFIX}-(\d{{4}})-(\d{{{PROTOCOLO_DIGITS}}})$",
    re.IGNORECASE,
)
# LAB-2026-00042-01
RE_TUBO = re.compile(
    rf"^{PROTOCOLO_PREFIX}-(\d{{4}})-(\d{{{PROTOCOLO_DIGITS}}})-(\d{{{TUBO_SUFFIX_DIGITS}}})$",
    re.IGNORECASE,
)
RE_LEGACY_MUE = re.compile(r"^MUE-\d{4}-\d+$", re.IGNORECASE)
RE_LEGACY_MICB = re.compile(r"^MICB-\d{4}-\d+$", re.IGNORECASE)
RE_LEGACY_MIC = re.compile(r"^MIC-\d{4}-\d+$", re.IGNORECASE)


class CodigoKind(str, Enum):
    PROTOCOLO = "protocolo"
    TUBO = "tubo"
    LEGACY_MUE = "legacy_mue"
    LEGACY_MICB = "legacy_micb"
    LEGACY_MIC = "legacy_mic"
    INVALID = "invalid"


@dataclass(frozen=True)
class ParsedCodigo:
    raw: str
    kind: CodigoKind
    year: int | None = None
    seq: int | None = None
    tubo_n: int | None = None


ResolveTipo = Literal["tubo", "micro"]


class LabCodigoError(Exception):
    """Error de dominio al generar o resolver códigos LAB."""

    def __init__(self, message: str, *, code: str = "lab_codigo"):
        super().__init__(message)
        self.code = code


def normalize_codigo(codigo: str | None) -> str:
    return (codigo or "").strip()


def format_protocolo(year: int, n: int) -> str:
    return f"{PROTOCOLO_PREFIX}-{year}-{n:0{PROTOCOLO_DIGITS}d}"


def format_tubo(protocolo: str, tubo_n: int) -> str:
    proto = normalize_codigo(protocolo).upper()
    if not RE_PROTOCOLO.match(proto):
        raise LabCodigoError(f"Protocolo inválido para tubo: {protocolo!r}")
    return f"{proto}-{tubo_n:0{TUBO_SUFFIX_DIGITS}d}"


def parse_codigo(codigo: str | None) -> ParsedCodigo:
    raw = normalize_codigo(codigo)
    if not raw:
        return ParsedCodigo(raw="", kind=CodigoKind.INVALID)
    upper = raw.upper()

    m_tubo = RE_TUBO.match(upper)
    if m_tubo:
        return ParsedCodigo(
            raw=upper,
            kind=CodigoKind.TUBO,
            year=int(m_tubo.group(1)),
            seq=int(m_tubo.group(2)),
            tubo_n=int(m_tubo.group(3)),
        )

    m_proto = RE_PROTOCOLO.match(upper)
    if m_proto:
        return ParsedCodigo(
            raw=upper,
            kind=CodigoKind.PROTOCOLO,
            year=int(m_proto.group(1)),
            seq=int(m_proto.group(2)),
        )

    if RE_LEGACY_MICB.match(upper):
        return ParsedCodigo(raw=upper, kind=CodigoKind.LEGACY_MICB)
    if RE_LEGACY_MIC.match(upper):
        return ParsedCodigo(raw=upper, kind=CodigoKind.LEGACY_MIC)
    if RE_LEGACY_MUE.match(upper):
        return ParsedCodigo(raw=upper, kind=CodigoKind.LEGACY_MUE)

    return ParsedCodigo(raw=upper, kind=CodigoKind.INVALID)


def _max_seq_from_queryset(values: list[str], year: int) -> int:
    prefix = f"{PROTOCOLO_PREFIX}-{year}-"
    max_n = 0
    for value in values:
        if not value or not value.upper().startswith(prefix.upper()):
            continue
        # Solo protocolo puro (sin sufijo de tubo)
        parsed = parse_codigo(value)
        if parsed.kind == CodigoKind.PROTOCOLO and parsed.seq is not None:
            max_n = max(max_n, parsed.seq)
    return max_n


@transaction.atomic
def next_protocolo(*, year: int | None = None) -> str:
    """
    Asigna el siguiente LAB-YYYY-XXXXX de forma atómica (secuencia compartida).
    """
    from laboratorio.models_catalog import LabProtocoloCounter
    from laboratorio.models import SolicitudExamen
    from laboratorio.models_microbiologia import EstudioMicrobiologia

    y = year or timezone.now().year
    counter, created = LabProtocoloCounter.objects.select_for_update().get_or_create(
        year=y,
        defaults={"last_n": 0},
    )
    if created or counter.last_n == 0:
        # Alinear con máximos ya existentes (LAB- canónicos en ambas tablas).
        sols = list(
            SolicitudExamen.objects.filter(numero__startswith=f"{PROTOCOLO_PREFIX}-{y}-").values_list(
                "numero", flat=True
            )
        )
        ests = list(
            EstudioMicrobiologia.objects.filter(
                numero__startswith=f"{PROTOCOLO_PREFIX}-{y}-"
            ).values_list("numero", flat=True)
        )
        counter.last_n = max(
            counter.last_n,
            _max_seq_from_queryset(sols, y),
            _max_seq_from_queryset(ests, y),
        )

    counter.last_n += 1
    counter.save(update_fields=["last_n", "updated_at"])
    return format_protocolo(y, counter.last_n)


def asignar_protocolo_si_vacio(numero_actual: str | None) -> str:
    """Si ya hay número, lo normaliza; si no, asigna uno nuevo."""
    actual = normalize_codigo(numero_actual)
    if actual:
        return actual.upper() if actual.upper().startswith(f"{PROTOCOLO_PREFIX}-") else actual
    return next_protocolo()


def next_tubo_codigo(solicitud: "SolicitudExamen") -> str:
    """
    Siguiente código de tubo para la orden: LAB-YYYY-XXXXX-nn.
    Requiere que la solicitud ya tenga numero de protocolo.
    """
    from laboratorio.models_catalog import Muestra

    protocolo = normalize_codigo(getattr(solicitud, "numero", None)).upper()
    if not protocolo or parse_codigo(protocolo).kind != CodigoKind.PROTOCOLO:
        raise LabCodigoError(
            "La orden debe tener número de protocolo LAB-YYYY-XXXXX antes de crear tubos."
        )

    existing = list(
        Muestra.objects.filter(
            solicitud_id=solicitud.pk,
            codigo_barra__startswith=f"{protocolo}-",
        ).values_list("codigo_barra", flat=True)
    )
    max_n = 0
    for cb in existing:
        parsed = parse_codigo(cb)
        if parsed.kind == CodigoKind.TUBO and parsed.tubo_n is not None:
            max_n = max(max_n, parsed.tubo_n)
    return format_tubo(protocolo, max_n + 1)


@dataclass
class ResolveResult:
    tipo: ResolveTipo
    codigo: str
    muestra: "Muestra | None" = None
    estudio: "EstudioMicrobiologia | None" = None
    hint: str | None = None


def resolver_entidad(codigo: str | None) -> ResolveResult:
    """
    Resuelve un código escaneado a tubo (Muestra) o micro (EstudioMicrobiologia).

    Raises LabCodigoError con mensajes operativos (404-like / hint de tubo).
    """
    from django.db.models import Q

    from laboratorio.models import SolicitudExamen
    from laboratorio.models_catalog import Muestra
    from laboratorio.models_microbiologia import EstudioMicrobiologia

    parsed = parse_codigo(codigo)
    if parsed.kind == CodigoKind.INVALID:
        raise LabCodigoError("Código inválido o vacío.", code="invalid")

    raw = parsed.raw

    if parsed.kind in (CodigoKind.TUBO, CodigoKind.LEGACY_MUE):
        try:
            muestra = Muestra.objects.select_related(
                "solicitud", "paciente", "tipo_muestra", "tipo_contenedor"
            ).get(codigo_barra=raw)
        except Muestra.DoesNotExist:
            # Legacy may have mixed case stored; try original strip
            try:
                muestra = Muestra.objects.select_related(
                    "solicitud", "paciente", "tipo_muestra", "tipo_contenedor"
                ).get(codigo_barra__iexact=raw)
            except Muestra.DoesNotExist as exc:
                raise LabCodigoError("Muestra (tubo) no encontrada.", code="not_found") from exc
        return ResolveResult(tipo="tubo", codigo=raw, muestra=muestra)

    if parsed.kind in (CodigoKind.LEGACY_MICB, CodigoKind.LEGACY_MIC, CodigoKind.PROTOCOLO):
        estudio = (
            EstudioMicrobiologia.objects.select_related(
                "solicitud", "paciente", "tipo_cultivo", "tipo_muestra_micro"
            )
            .filter(Q(codigo_barra__iexact=raw) | Q(numero__iexact=raw))
            .first()
        )
        if estudio is not None:
            return ResolveResult(tipo="micro", codigo=raw, estudio=estudio)

        if parsed.kind == CodigoKind.PROTOCOLO:
            # Protocolo de lab clínico: no es escaneable para recepción sin sufijo de tubo.
            if SolicitudExamen.objects.filter(numero__iexact=raw).exists():
                raise LabCodigoError(
                    f"«{raw}» es un protocolo de lab clínico. Escaneá el tubo "
                    f"(p. ej. {raw}-01), no el número de orden.",
                    code="need_tubo_suffix",
                )
            raise LabCodigoError("Código no encontrado.", code="not_found")

        raise LabCodigoError(
            "Estudio de microbiología no encontrado.", code="not_found"
        )

    raise LabCodigoError("Código no encontrado.", code="not_found")


def serialize_resolve_payload(
    result: ResolveResult,
    *,
    request: Any = None,
    extra: dict | None = None,
) -> dict:
    """Arma el JSON unificado {tipo, codigo, muestra|estudio, ...}."""
    from laboratorio.serializers_muestras import MuestraLookupSerializer
    from laboratorio.serializers_microbiologia import EstudioMicrobiologiaSerializer

    ctx = {"request": request} if request is not None else {}
    payload: dict[str, Any] = {
        "tipo": result.tipo,
        "codigo": result.codigo,
    }
    if result.hint:
        payload["hint"] = result.hint
    if result.tipo == "tubo" and result.muestra is not None:
        payload["muestra"] = MuestraLookupSerializer(result.muestra, context=ctx).data
    if result.tipo == "micro" and result.estudio is not None:
        payload["estudio"] = EstudioMicrobiologiaSerializer(result.estudio, context=ctx).data
    if extra:
        payload.update(extra)
    return payload
