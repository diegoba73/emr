"""Reglas de correccion del catalogo microbiologico LabWin."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CorreccionEstado = Literal["NINGUNA", "ORTOGRAFIA_AUTO", "PENDIENTE_REVISION"]


@dataclass(frozen=True)
class CorreccionResultado:
    nombre_mostrar: str
    correccion_estado: CorreccionEstado
    requiere_revision: bool
    motivo_revision: str
    activo: bool = True
    tipo_registro: str = ""
    categoria: str = ""


_ANTIB_ORTO = {
    "AS": "Ampicilina/sulbactam",
    "TS": "Trimetoprima/sulfametoxazol",
}
_ANTIB_INACTIVOS = frozenset({"TTT"})
_ANTIB_PENDIENTE = {
    "NI": "Nombre LabWin ambiguo (NITROFURANOS); revisar si es nitrofurantoina u otro.",
    "TA": "Nombre LabWin incompleto (TAZOBACTAMA); revisar combinacion clinica.",
}
_BACTE_ORTO: dict[str, tuple[str, str]] = {}
# ENTC vive en NEMOTEC (no fusionar con BACTE).
_FRASE_ORTO = {
    "ENTC": ("Enterococcus faecalis", "HALLAZGO"),
}
_FRASE_FENOTIPO = frozenset({"CONT", "col", "stha", "KLEBBLEE"})
_FRASE_UMBRAL = frozenset({"gr1", "gr2", "gr3", "gr4", "gr5", "uf+"})


def corregir_antibiotico(codigo: str, nombre_original: str) -> CorreccionResultado:
    code = (codigo or "").strip()
    original = (nombre_original or "").strip() or code
    if code in _ANTIB_INACTIVOS:
        return CorreccionResultado(
            nombre_mostrar=original,
            correccion_estado="NINGUNA",
            requiere_revision=False,
            motivo_revision="Registro de prueba LabWin; importado inactivo.",
            activo=False,
        )
    if code in _ANTIB_ORTO:
        return CorreccionResultado(
            nombre_mostrar=_ANTIB_ORTO[code],
            correccion_estado="ORTOGRAFIA_AUTO",
            requiere_revision=False,
            motivo_revision=f"Ortografia inequívoca desde '{original}'.",
            activo=True,
        )
    if code in _ANTIB_PENDIENTE:
        return CorreccionResultado(
            nombre_mostrar=original,
            correccion_estado="PENDIENTE_REVISION",
            requiere_revision=True,
            motivo_revision=_ANTIB_PENDIENTE[code],
            activo=True,
        )
    return CorreccionResultado(
        nombre_mostrar=original,
        correccion_estado="NINGUNA",
        requiere_revision=False,
        motivo_revision="",
        activo=True,
    )


def corregir_microorganismo(codigo: str, nombre_original: str) -> CorreccionResultado:
    code = (codigo or "").strip()
    original = (nombre_original or "").strip() or code
    if code in _BACTE_ORTO:
        nombre, tipo = _BACTE_ORTO[code]
        return CorreccionResultado(
            nombre_mostrar=nombre,
            correccion_estado="ORTOGRAFIA_AUTO",
            requiere_revision=False,
            motivo_revision=f"Ortografia inequívoca desde '{original}'.",
            activo=True,
            tipo_registro=tipo,
        )
    return CorreccionResultado(
        nombre_mostrar=original,
        correccion_estado="NINGUNA",
        requiere_revision=False,
        motivo_revision="",
        activo=True,
        tipo_registro="MICROORGANISMO",
    )


def corregir_frase(abreviatura: str, texto_original: str) -> CorreccionResultado:
    abrev = (abreviatura or "").strip()
    original = (texto_original or "").strip() or abrev
    if abrev in _FRASE_ORTO:
        texto, cat = _FRASE_ORTO[abrev]
        return CorreccionResultado(
            nombre_mostrar=texto,
            correccion_estado="ORTOGRAFIA_AUTO",
            requiere_revision=False,
            motivo_revision=f"Ortografia inequívoca desde '{original}'.",
            activo=True,
            categoria=cat,
        )
    if abrev in _FRASE_FENOTIPO:
        return CorreccionResultado(
            nombre_mostrar=original,
            correccion_estado="NINGUNA",
            requiere_revision=False,
            motivo_revision="Frase de fenotipo / interpretacion clinica.",
            activo=True,
            categoria="FENOTIPO",
        )
    if abrev in _FRASE_UMBRAL:
        return CorreccionResultado(
            nombre_mostrar=original,
            correccion_estado="PENDIENTE_REVISION",
            requiere_revision=True,
            motivo_revision="Umbral cuantitativo historico LabWin; validar antes de uso rutinario.",
            activo=True,
            categoria="UMBRAL",
        )
    return CorreccionResultado(
        nombre_mostrar=original,
        correccion_estado="NINGUNA",
        requiere_revision=False,
        motivo_revision="",
        activo=True,
        categoria="GENERAL",
    )


def filas_reporte_revision_conocidas() -> list[dict[str, str]]:
    """Filas estables para stdout/docs: origen, codigo, original, propuesta, motivo."""
    # Originales tipicos de la exportacion LabWin (fixtures / export real).
    antib_original = {
        "AS": "AMPINICILINA-SULBACTAMA",
        "TS": "TRIMETOP.+SULFAMETOXAZOL",
        "TTT": "Esto es de prueba",
        "NI": "NITROFURANOS",
        "TA": "TAZOBACTAMA",
    }
    bacte_original: dict[str, str] = {}
    frase_original = {
        "ENTC": "Enteroccocus faecalis.",
        "CONT": "Crecimiento mixto de flora bacteriana sin predominio",
        "col": "Colistina: ver nota fenotipica",
        "stha": "Staphylococcus aureus (fenotipo)",
        "KLEBBLEE": "Klebsiella spp. con fenotipo BLEE",
        "gr1": "Se obtuvo desarrollo de menos de 10.000 UFC/ml",
        "gr2": "Umbral cuantitativo historico LabWin",
        "gr3": "Umbral cuantitativo historico LabWin",
        "gr4": "Umbral cuantitativo historico LabWin",
        "gr5": "Umbral cuantitativo historico LabWin",
        "uf+": "Se observo desarrollo de mas de 150 000 UFC por ml",
    }

    rows: list[dict[str, str]] = []

    for code, propuesta in _ANTIB_ORTO.items():
        original = antib_original.get(code, "")
        rows.append(
            {
                "origen": "ANTIB",
                "codigo": code,
                "original": original,
                "propuesta": propuesta,
                "motivo": f"Ortografia inequivoca desde '{original}'.",
            }
        )
    for code in sorted(_ANTIB_INACTIVOS):
        original = antib_original.get(code, "")
        rows.append(
            {
                "origen": "ANTIB",
                "codigo": code,
                "original": original,
                "propuesta": original,
                "motivo": "Registro de prueba LabWin; importado inactivo.",
            }
        )
    for code, motivo in _ANTIB_PENDIENTE.items():
        original = antib_original.get(code, "")
        rows.append(
            {
                "origen": "ANTIB",
                "codigo": code,
                "original": original,
                "propuesta": original,
                "motivo": motivo,
            }
        )
    for code, (nombre, _) in _BACTE_ORTO.items():
        original = bacte_original.get(code, "")
        rows.append(
            {
                "origen": "BACTE",
                "codigo": code,
                "original": original,
                "propuesta": nombre,
                "motivo": f"Ortografia inequivoca desde '{original}'.",
            }
        )
    for abrev, (texto, cat) in _FRASE_ORTO.items():
        original = frase_original.get(abrev, "")
        rows.append(
            {
                "origen": "NEMOTEC",
                "codigo": abrev,
                "original": original,
                "propuesta": texto,
                "motivo": f"Ortografia inequivoca [{cat}] desde '{original}'.",
            }
        )
    for abrev in sorted(_FRASE_FENOTIPO, key=str.lower):
        original = frase_original.get(abrev, "")
        rows.append(
            {
                "origen": "NEMOTEC",
                "codigo": abrev,
                "original": original,
                "propuesta": original,
                "motivo": "Frase de fenotipo / interpretacion clinica.",
            }
        )
    for abrev in sorted(_FRASE_UMBRAL, key=str.lower):
        original = frase_original.get(abrev, "")
        rows.append(
            {
                "origen": "NEMOTEC",
                "codigo": abrev,
                "original": original,
                "propuesta": original,
                "motivo": "Umbral cuantitativo historico LabWin; validar antes de uso rutinario.",
            }
        )
    return rows
