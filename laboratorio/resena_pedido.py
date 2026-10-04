"""
Reseña clínica que justifica exámenes fuera del listado básico del pedido papel.

- Motor de reglas (determinístico) siempre disponible.
- MedGemma/Ollama opcional para mejorar la redacción (docs_synesis/reglas/ia.md):
  solo sugerencia, el operador la revisa/edita antes de imprimir y el médico firma.
  El prompt no lleva datos identificatorios (nombre, DNI, OS).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from laboratorio.models import PanelExamen

# Códigos del formulario papel que NO requieren reseña (listado básico).
CODIGOS_SIN_RESENA: frozenset[str] = frozenset({
    "PAN_HEMO", "GLU", "UREA", "CREATI", "AU", "CA", "MG", "P", "FERR",
    "PAN_IONO", "CL", "CA_ION", "PAN_LIP", "PAN_HEP", "PROT_T", "ALB",
    "PAN_COAG", "INR", "VSG", "PCR_US", "AMIL", "LIP", "GGT", "LDH",
    "CPK", "CPK_MB", "TROP_I", "MIOG", "TROP_US", "PROBNP", "DDIM",
    "PAN_ORI", "PAN_CLEAR", "PAN_IONO_U24", "PAN_IONO_U", "PAN_PROT24",
    "PROT_U_AZ", "PAN_MALB24", "PAN_MALB_AZ", "PAN_EAB_ART", "PAN_EAB_VEN",
    "LACT",
})

# (clave de grupo, finalidad) por código. Exámenes del mismo grupo se redactan juntos.
_FINALIDAD: dict[str, tuple[str, str]] = {
    "HBA1C": ("glucemia", "evaluar el control metabólico de la glucemia"),
    "PAN_FERR": ("hierro", "evaluar el metabolismo del hierro"),
    "PAN_ELP": ("proteinas", "evaluar el perfil de proteínas séricas"),
    "LPA": ("riesgo_cv", "completar la estratificación del riesgo cardiovascular"),
    "PSA": ("prostata", "control prostático"),
    "TSH": ("tiroides", "evaluar la función tiroidea"),
    "T3": ("tiroides", "evaluar la función tiroidea"),
    "T4": ("tiroides", "evaluar la función tiroidea"),
    "T4L": ("tiroides", "evaluar la función tiroidea"),
    "B12": ("b12", "descartar déficit de vitamina B12"),
    "VITD": ("vitd", "evaluar los niveles de vitamina D"),
}
_FINALIDAD_DEFAULT = ("otros", "completar la evaluación diagnóstica")

# Ajustes de finalidad según el diagnóstico (palabras clave en minúscula, sin tildes).
_FINALIDAD_POR_DX: list[tuple[tuple[str, ...], str, str]] = [
    (("fibrilacion", "arritmia", "aleteo", "taquicardia", "insuficiencia cardiaca"),
     "tiroides", "descartar disfunción tiroidea como causa o factor desencadenante"),
    (("diabetes", "dbt", "dm2", "dm 2", "hiperglucemia"),
     "glucemia", "evaluar el control metabólico de la diabetes"),
    (("anemia",), "hierro", "caracterizar la anemia y evaluar el metabolismo del hierro"),
    (("anemia",), "b12", "descartar déficit de vitamina B12 como causa de anemia"),
]

MAX_ANTECEDENTES = 220
MEDGEMMA_PRESUPUESTO_SEG = 45


@dataclass
class ContextoResena:
    sexo: str = ""  # "M" | "F" | ""
    edad: int | None = None
    antecedentes: str = ""
    diagnostico: str = ""
    examenes: list[tuple[str, str]] = field(default_factory=list)  # (código o "", nombre)


def _sin_tildes(s: str) -> str:
    tabla = str.maketrans("áéíóúüÁÉÍÓÚÜ", "aeiouuAEIOUU")
    return (s or "").translate(tabla).lower()


def recortar_antecedentes(texto: str, max_len: int = MAX_ANTECEDENTES) -> str:
    t = " ".join((texto or "").split()).strip().rstrip(".")
    if len(t) <= max_len:
        return t
    corte = t[:max_len].rsplit(" ", 1)[0].rstrip(",;")
    return f"{corte}…"


def componentes_paneles_basicos() -> set[str]:
    cods: set[str] = set()
    for pan in PanelExamen.objects.filter(
        codigo__in=[c for c in CODIGOS_SIN_RESENA if c.startswith("PAN_")]
    ).prefetch_related("tipos_examen"):
        cods.update((te.codigo or "").upper() for te in pan.tipos_examen.all())
    return cods


def examenes_que_requieren_resena(sol, *, componentes_basicos: set[str] | None = None) -> list[tuple[str, str]]:
    """
    (código, nombre) de lo solicitado fuera del listado básico. Los componentes de un
    panel básico pedidos sueltos (p. ej. Sodio de Ionograma) no requieren reseña.
    """
    if componentes_basicos is None:
        componentes_basicos = componentes_paneles_basicos()
    paneles = list(sol.paneles.all())
    en_panel: set[int] = set()
    out: list[tuple[str, str]] = []
    for pan in sorted(paneles, key=lambda p: (p.nombre or "")):
        en_panel.update(te.pk for te in pan.tipos_examen.all())
        cod = (pan.codigo or "").upper()
        if cod not in CODIGOS_SIN_RESENA:
            out.append((cod, (pan.nombre or pan.codigo or "").strip()))
    for te in sorted(sol.tipos_examen.all(), key=lambda t: (t.nombre or "")):
        if te.pk in en_panel:
            continue
        cod = (te.codigo or "").upper()
        if cod in CODIGOS_SIN_RESENA or cod in componentes_basicos:
            continue
        out.append((cod, (te.nombre or te.codigo or "").strip()))
    return [(c, n) for c, n in out if n]


def _unir(nombres: list[str]) -> str:
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def construir_resena_reglas(ctx: ContextoResena) -> str:
    dx_norm = _sin_tildes(ctx.diagnostico)
    grupos: dict[str, tuple[str, list[str]]] = {}
    for cod, nombre in ctx.examenes:
        clave, finalidad = _FINALIDAD.get(cod, _FINALIDAD_DEFAULT)
        for claves_dx, clave_obj, texto in _FINALIDAD_POR_DX:
            if clave_obj == clave and any(k in dx_norm for k in claves_dx):
                finalidad = texto
                break
        if clave not in grupos:
            grupos[clave] = (finalidad, [])
        grupos[clave][1].append(nombre)

    if ctx.sexo == "F":
        sujeto = "Paciente femenina"
    elif ctx.sexo == "M":
        sujeto = "Paciente masculino"
    else:
        sujeto = "Paciente"
    if ctx.edad is not None and ctx.edad >= 0:
        sujeto += f" de {ctx.edad} años"
    antecedentes = recortar_antecedentes(ctx.antecedentes)
    if antecedentes:
        sujeto += f", con antecedentes de {antecedentes}"
    dx = " ".join((ctx.diagnostico or "").split()).rstrip(".")
    if dx:
        primera = f"{sujeto}, que cursa con diagnóstico de {dx}."
    else:
        primera = f"{sujeto}, en estudio clínico."

    partes = [f"{_unir(noms)} para {fin}" for fin, noms in grupos.values()]
    if not partes:
        return primera
    segunda = (
        f"Se solicita {'; '.join(partes)}, como parte de la evaluación clínica "
        "y para orientar la conducta terapéutica."
    )
    return f"{primera} {segunda}"


def _prompt_medgemma(ctx: ContextoResena, borrador: str) -> str:
    sexo = {"F": "femenino", "M": "masculino"}.get(ctx.sexo, "no informado")
    edad = f"{ctx.edad} años" if ctx.edad is not None else "no informada"
    return "\n".join([
        "Sos un asistente médico. Redactá en español una reseña clínica breve (2 a 4 oraciones)",
        "que justifique ante la obra social los estudios de laboratorio solicitados,",
        "en estilo de nota médica, sin inventar datos ni diagnósticos nuevos,",
        "sin nombre ni datos identificatorios del paciente.",
        "",
        f"Sexo: {sexo}",
        f"Edad: {edad}",
        f"Antecedentes: {recortar_antecedentes(ctx.antecedentes) or 'no informados'}",
        f"Diagnóstico: {ctx.diagnostico or 'en estudio'}",
        "Estudios a justificar: " + ", ".join(n for _, n in ctx.examenes),
        "",
        f"Borrador de referencia (podés mejorarlo): {borrador}",
        "",
        "Respondé solo con el texto de la reseña, sin títulos, sin markdown ni explicación.",
    ])


def sugerir_resenas(
    contextos: list[ContextoResena],
    *,
    prefer_medgemma: bool = True,
    presupuesto_seg: float = MEDGEMMA_PRESUPUESTO_SEG,
) -> list[dict]:
    """
    Una sugerencia por contexto: {"texto", "fuente"}. MedGemma se usa mientras
    quede presupuesto de tiempo; el resto cae a reglas.
    """
    from laboratorio.medgemma_client import intentar_generar_texto_medgemma, medgemma_habilitado

    usar_ia = prefer_medgemma and medgemma_habilitado()
    inicio = time.monotonic()
    out: list[dict] = []
    for ctx in contextos:
        borrador = construir_resena_reglas(ctx)
        sug = {"texto": borrador, "fuente": "reglas"}
        if usar_ia and (time.monotonic() - inicio) < presupuesto_seg:
            med = intentar_generar_texto_medgemma(_prompt_medgemma(ctx, borrador), multilinea=True)
            texto = " ".join(((med or {}).get("texto") or "").replace("*", "").split())
            if texto:
                sug = {"texto": texto, "fuente": "medgemma"}
            else:
                usar_ia = False
        out.append(sug)
    return out
