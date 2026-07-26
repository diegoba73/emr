"""
Borrador de informe de estudio complementario (nivel 1).

Plantilla por reglas + MedGemma opcional. No persiste: el médico debe crear el borrador.
Sin PHI identificatoria en el prompt (sin nombre/DNI); solo edad/sexo si están disponibles.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from estudios.models import EstudioComplementario, TipoEstudioComplementario

_MODALIDAD_LABEL = dict(TipoEstudioComplementario.Modalidad.choices)

_TECNICA_POR_MODALIDAD = {
    TipoEstudioComplementario.Modalidad.IMAGEN_RX: (
        'Radiografía. Técnica y proyecciones a completar según protocolo local.'
    ),
    TipoEstudioComplementario.Modalidad.IMAGEN_TC: (
        'Tomografía computada. Protocolo, contraste y reconstrucciones a completar.'
    ),
    TipoEstudioComplementario.Modalidad.IMAGEN_RM: (
        'Resonancia magnética. Secuencias y uso de contraste a completar.'
    ),
    TipoEstudioComplementario.Modalidad.IMAGEN_US: (
        'Ecografía. Equipo y ventana acústica a completar.'
    ),
    TipoEstudioComplementario.Modalidad.PDF_INFORME_EXTERNO: (
        'Informe externo / documentación adjunta. Sintetizar hallazgos relevantes.'
    ),
    TipoEstudioComplementario.Modalidad.OTRO: (
        'Técnica del procedimiento a completar.'
    ),
}


def _edad_anos(paciente) -> int | None:
    fn = getattr(paciente, 'fecha_nacimiento', None)
    if not fn:
        return None
    today = date.today()
    return today.year - fn.year - ((today.month, today.day) < (fn.month, fn.day))


def _contexto_estudio(estudio: EstudioComplementario) -> dict[str, Any]:
    tipo_nombre = ''
    if estudio.tipo_estudio_id:
        tipo_nombre = estudio.tipo_estudio.nombre or ''
    modalidad_label = _MODALIDAD_LABEL.get(estudio.modalidad, estudio.modalidad)
    paciente = estudio.paciente
    edad = _edad_anos(paciente)
    sexo = (getattr(paciente, 'sexo', None) or '').strip() or None
    return {
        'modalidad': estudio.modalidad,
        'modalidad_label': modalidad_label,
        'tipo_estudio': tipo_nombre,
        'descripcion_clinica': (estudio.descripcion_clinica or '').strip(),
        'centro': (estudio.centro_realizador or '').strip(),
        'edad': edad,
        'sexo': sexo,
        'tecnica_hint': _TECNICA_POR_MODALIDAD.get(
            estudio.modalidad,
            _TECNICA_POR_MODALIDAD[TipoEstudioComplementario.Modalidad.OTRO],
        ),
    }


def construir_informe_estudio_reglas(
    estudio: EstudioComplementario,
    *,
    notas_medico: str = '',
) -> dict[str, Any]:
    """Plantilla estructurada cuando no hay MedGemma o como fallback."""
    ctx = _contexto_estudio(estudio)
    notas = (notas_medico or '').strip()
    hallazgos = notas if notas else 'A completar según la imagen / material del estudio.'
    conclusion = (
        notas
        if notas
        else 'Impresión diagnóstica a completar tras revisión de la imagen.'
    )

    lineas = [
        'INFORME DE ESTUDIO COMPLEMENTARIO (borrador sugerido — revisar)',
        '',
        f'Modalidad: {ctx["modalidad_label"]}',
    ]
    if ctx['tipo_estudio']:
        lineas.append(f'Estudio: {ctx["tipo_estudio"]}')
    demografia = []
    if ctx['edad'] is not None:
        demografia.append(f'{ctx["edad"]} años')
    if ctx['sexo']:
        demografia.append(f'sexo {ctx["sexo"]}')
    if demografia:
        lineas.append(f'Paciente (sin identificar): {", ".join(demografia)}')
    if ctx['descripcion_clinica']:
        lineas.append(f'Indicación clínica: {ctx["descripcion_clinica"]}')
    if ctx['centro']:
        lineas.append(f'Centro realizador: {ctx["centro"]}')
    lineas.extend(
        [
            '',
            'Técnica:',
            ctx['tecnica_hint'],
            '',
            'Hallazgos:',
            hallazgos,
            '',
            'Impresión / conclusión:',
            conclusion,
            '',
            'Nota: sugerencia asistida; no constituye informe firmado ni diagnóstico definitivo.',
        ]
    )
    texto = '\n'.join(lineas)
    return {
        'texto': texto,
        'fuente': 'reglas',
        'marcado_sugerencia': True,
        'vacio': False,
        'detalle': {
            'modalidad': ctx['modalidad'],
            'con_notas_medico': bool(notas),
        },
    }


def _build_prompt_informe(estudio: EstudioComplementario, *, notas_medico: str, borrador_reglas: str) -> str:
    ctx = _contexto_estudio(estudio)
    lines = [
        'Sos un asistente de redacción de informes de estudios complementarios (imagenología u otros).',
        'Redactá un borrador de informe en español, estructurado en secciones: Técnica, Hallazgos, Impresión.',
        'No inventes hallazgos concretos que no estén en las notas del médico.',
        'Si faltan datos, indicá claramente «a completar».',
        'No menciones nombre, DNI ni datos identificatorios del paciente.',
        'No firmes el informe ni lo presentes como validado.',
        '',
        f'Modalidad: {ctx["modalidad_label"]}',
    ]
    if ctx['tipo_estudio']:
        lines.append(f'Tipo de estudio: {ctx["tipo_estudio"]}')
    if ctx['edad'] is not None:
        lines.append(f'Edad (años): {ctx["edad"]}')
    if ctx['sexo']:
        lines.append(f'Sexo: {ctx["sexo"]}')
    if ctx['descripcion_clinica']:
        lines.append(f'Indicación clínica: {ctx["descripcion_clinica"]}')
    if (notas_medico or '').strip():
        lines.append(f'Notas del médico (prioridad): {notas_medico.strip()}')
    if (borrador_reglas or '').strip():
        lines.append('')
        lines.append('Plantilla de referencia (podés mejorarla respetando las notas):')
        lines.append(borrador_reglas.strip()[:2500])
    lines.append('')
    lines.append('Respondé solo con el texto del informe, sin markdown ni preámbulo.')
    return '\n'.join(lines)


def sugerir_informe_estudio(
    estudio: EstudioComplementario,
    *,
    notas_medico: str = '',
    prefer_medgemma: bool = True,
) -> dict[str, Any]:
    """
    Orquesta MedGemma (si está habilitado) con fallback a plantilla por reglas.
    No persiste el informe.
    """
    from laboratorio.medgemma_client import intentar_generar_texto_medgemma

    reglas = construir_informe_estudio_reglas(estudio, notas_medico=notas_medico)
    if not prefer_medgemma:
        return reglas

    prompt = _build_prompt_informe(
        estudio,
        notas_medico=notas_medico,
        borrador_reglas=reglas.get('texto') or '',
    )
    med = intentar_generar_texto_medgemma(prompt, multilinea=True)
    if med and med.get('texto'):
        med = {
            **med,
            'detalle': {
                'modalidad': estudio.modalidad,
                'con_notas_medico': bool((notas_medico or '').strip()),
            },
        }
        return med
    return reglas
