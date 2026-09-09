"""
Render ZPL para etiquetas de muestra 40×23 mm (perfil 3nStar LDT114).

Separado del ViewSet y del transporte de red.

Estrategia de sizing (conservadora, sin validación física aún)
-------------------------------------------------------------
Fuente ZPL ``^A0N,h,w``: se modela el ancho ocupado como

    estimated_width_dots = len(texto) * w

(modelo monospace de celda ``w``; deliberadamente conservador frente a glifos
anchos). El texto debe cumplir:

    estimated_width_dots <= MAX_CONTENT_WIDTH_DOTS

con ``MAX_CONTENT_WIDTH_DOTS = PW - 2 * MARGIN_X`` (320 − 24 = 296).

1. Código (línea 1): **nunca se trunca**. Se elige el mayor ``w`` ≤ preferido
   tal que ``len * w ≤ MAX``. Si hace falta, ``w`` puede bajar del mínimo
   “ideal” de jerarquía (sigue siendo el mayor entero que cabe).
2. Paciente (línea 2): **apellido completo siempre** (nunca se trunca). Si no
   cabe con el ``w`` mínimo deseado, se omite solo la inicial del nombre; el
   sizing baja ``w`` para conservar apellido + DNI íntegros. DNI no se trunca.
3. Lugar / fecha|tipo: se reduce el fragmento abreviable (lugar / tipo; **no**
   fecha), hasta que quepa; luego se sube ``w`` lo más posible.
4. Altura ``h`` sigue la jerarquía visual (código > resto) y se apila en Y
   con márgenes/gaps sin superar ``LL=184``.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from laboratorio.label_profiles import LabelPrinterProfile, PROFILE_3NSTAR_LDT114_203_40X23

# --- Geometría 40×23 @ 203 dpi -------------------------------------------------
MARGIN_X = 12
MARGIN_Y_TOP = 8
MARGIN_Y_BOTTOM = 8
LINE_GAP = 4
MAX_CONTENT_WIDTH_DOTS = PROFILE_3NSTAR_LDT114_203_40X23.width_dots - (2 * MARGIN_X)  # 296

# Preferidos / mínimos legibles (dots). El código puede bajar del mínimo ideal.
LINE1_H_PREF, LINE1_W_PREF, LINE1_W_MIN_IDEAL = 28, 28, 14
LINE2_H_PREF, LINE2_W_PREF, LINE2_W_MIN = 18, 18, 11
LINE3_H_PREF, LINE3_W_PREF, LINE3_W_MIN = 16, 16, 11
LINE4_H_PREF, LINE4_W_PREF, LINE4_W_MIN = 16, 16, 11

# Controles C0 + DEL, incluyendo TAB/CR/LF (no imprimibles de forma fiel en ^FD).
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_CODIGO_ZPL_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f^~\\]")


class CodigoBarraZplError(ValueError):
    """El código de barras no puede representarse fielmente en ZPL ^FD."""


def prepare_codigo_barra_for_zpl(codigo_barra: str) -> str:
    """
    Identidad de muestra para ZPL: exacta, sin transformar.

    Valida el string ORIGINAL (sin strip). Cualquier control, ^, ~, \\ o
    whitespace de borde que implicaría transformación → rechazo.
    """
    if codigo_barra is None:
        raise CodigoBarraZplError("La muestra no tiene código de barras asignado.")
    codigo = codigo_barra
    if codigo == "":
        raise CodigoBarraZplError("La muestra no tiene código de barras asignado.")
    # Rechazar si strip/sanitización cambiaría la identidad.
    if codigo != codigo.strip(" \t\r\n"):
        raise CodigoBarraZplError(
            "El código de barras contiene caracteres no representables de forma "
            "fiel en ZPL; no se puede previsualizar ni imprimir."
        )
    if _CODIGO_ZPL_UNSAFE_RE.search(codigo):
        raise CodigoBarraZplError(
            "El código de barras contiene caracteres no representables de forma "
            "fiel en ZPL; no se puede previsualizar ni imprimir."
        )
    return codigo


def escape_zpl_fd(value: str) -> str:
    """
    Sanitiza texto NO identitario para campos ^FD (paciente, lugar, tipo).

    - Elimina controles (incl. tab/CR/LF).
    - Neutraliza ^, ~ y \\ para evitar inyección.
    - Conserva letras españolas (Ñ, tildes) — el perfil usa ^CI28 UTF-8.
    No usar para codigo_barra (ver ``prepare_codigo_barra_for_zpl``).
    """
    text = unicodedata.normalize("NFC", value or "")
    text = _CTRL_RE.sub("", text)
    text = text.replace("^", " ").replace("~", " ").replace("\\", "/")
    text = re.sub(r" +", " ", text).strip()
    return text


def normalize_lugar_extraccion(value: str) -> str:
    """Normaliza espacios y mayúsculas; no reinterpretar el contenido."""
    text = re.sub(r"\s+", " ", (value or "").strip())
    return text.upper()


def format_paciente_abreviado(apellido: str | None, nombre: str | None) -> str:
    """APELLIDO I. — apellido + inicial del primer nombre."""
    ap = escape_zpl_fd(re.sub(r"\s+", " ", (apellido or "").strip()).upper())
    nom = escape_zpl_fd(re.sub(r"\s+", " ", (nombre or "").strip()))
    if not ap:
        return ""
    inicial = ""
    if nom:
        for ch in nom.split(" ", 1)[0]:
            if ch.isalpha():
                inicial = ch.upper()
                break
    if inicial:
        return f"{ap} {inicial}."
    return ap


def format_fecha_toma_label(dt) -> str:
    """DD/MM HH:MM en zona local Django."""
    from django.utils import timezone

    if dt is None:
        return ""
    local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    return local.strftime("%d/%m %H:%M")


def estimated_text_width_dots(text: str, char_width: int) -> int:
    """Modelo conservador: celda monospace de ancho ``char_width`` por carácter."""
    return max(0, len(text)) * max(0, int(char_width))


def max_font_width_for_text(
    text: str,
    *,
    preferred: int,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
) -> int:
    """Mayor ``w`` ≤ preferred tal que ``len(text)*w ≤ max_content_width`` (mínimo 1)."""
    n = max(1, len(text or ""))
    return max(1, min(int(preferred), max_content_width // n))


def text_fits(text: str, char_width: int, max_content_width: int = MAX_CONTENT_WIDTH_DOTS) -> bool:
    return estimated_text_width_dots(text, char_width) <= max_content_width


def _apellido_token(apellido: str | None) -> str:
    return escape_zpl_fd(re.sub(r"\s+", " ", (apellido or "").strip()).upper())


def _nombre_inicial(nombre: str | None) -> str:
    nom = escape_zpl_fd(re.sub(r"\s+", " ", (nombre or "").strip()))
    if not nom:
        return ""
    for ch in nom.split(" ", 1)[0]:
        if ch.isalpha():
            return ch.upper()
    return ""


def format_line_paciente(
    apellido: str | None,
    nombre: str | None,
    dni: str | None,
    *,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
    min_char_width: int = LINE2_W_MIN,
) -> str:
    """
    Línea 2: APELLIDO I. | DNI NNNNNNNN

    **Apellido completo siempre** (nunca se trunca). Tampoco se trunca el DNI.
    Si la línea no cabe con ``min_char_width``, se omite la inicial del nombre;
    el render bajará ``w`` para que apellido+DNI quepan enteros.
    """
    dni_clean = escape_zpl_fd(re.sub(r"\s+", "", (dni or "").strip()))
    suffix = f" | DNI {dni_clean}"
    inicial = _nombre_inicial(nombre)
    ap = _apellido_token(apellido)

    def compose(*, with_inicial: bool) -> str:
        if not ap and not (with_inicial and inicial):
            return f"DNI {dni_clean}" if dni_clean else ""
        if with_inicial and inicial:
            return f"{ap} {inicial}.{suffix}" if ap else f"{inicial}.{suffix}"
        return f"{ap}{suffix}" if ap else f"DNI {dni_clean}"

    # Preferir apellido completo + inicial; si no cabe al mínimo, solo apellido+DNI.
    full = compose(with_inicial=True)
    if text_fits(full, min_char_width, max_content_width):
        return full
    without_inicial = compose(with_inicial=False)
    return without_inicial


def format_line_lugar(
    lugar_extraccion: str,
    *,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
    min_char_width: int = LINE3_W_MIN,
) -> str:
    lugar = escape_zpl_fd(normalize_lugar_extraccion(lugar_extraccion))
    while lugar and not text_fits(lugar, min_char_width, max_content_width):
        lugar = lugar[:-1]
    return lugar


def format_line_fecha_tipo(
    fecha_toma,
    tipo_operacional: str,
    *,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
    min_char_width: int = LINE4_W_MIN,
) -> str:
    fecha_part = escape_zpl_fd(format_fecha_toma_label(fecha_toma))
    tipo = escape_zpl_fd(re.sub(r"\s+", " ", (tipo_operacional or "").strip()).upper())
    while True:
        line = f"{fecha_part} | {tipo}" if tipo else fecha_part
        if text_fits(line, min_char_width, max_content_width):
            return line
        if not tipo:
            return fecha_part  # fecha completa; sizing bajará w si hace falta
        tipo = tipo[:-1]


@dataclass(frozen=True)
class LabelLines:
    codigo: str
    paciente_dni: str
    lugar: str
    fecha_tipo: str

    def as_list(self) -> list[str]:
        return [self.codigo, self.paciente_dni, self.lugar, self.fecha_tipo]


@dataclass(frozen=True)
class LineLayout:
    text: str
    height: int
    width: int
    x: int
    y: int

    @property
    def estimated_width_dots(self) -> int:
        return estimated_text_width_dots(self.text, self.width)


@dataclass(frozen=True)
class RenderedLabel:
    lines: LabelLines
    layouts: tuple[LineLayout, LineLayout, LineLayout, LineLayout]
    zpl: str

    def all_fit_width(self, max_content_width: int = MAX_CONTENT_WIDTH_DOTS) -> bool:
        return all(lay.estimated_width_dots <= max_content_width for lay in self.layouts)


def build_label_lines(
    *,
    codigo_barra: str,
    apellido: str | None,
    nombre: str | None,
    dni: str | None,
    lugar_extraccion: str,
    fecha_toma,
    tipo_operacional: str,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
) -> LabelLines:
    # Identidad: exacta o error. Campos display: ya sanitizados en format_line_*.
    codigo = prepare_codigo_barra_for_zpl(codigo_barra)
    return LabelLines(
        codigo=codigo,
        paciente_dni=format_line_paciente(
            apellido, nombre, dni, max_content_width=max_content_width
        ),
        lugar=format_line_lugar(lugar_extraccion, max_content_width=max_content_width),
        fecha_tipo=format_line_fecha_tipo(
            fecha_toma, tipo_operacional, max_content_width=max_content_width
        ),
    )


def _layout_line(
    text: str,
    *,
    y: int,
    h_pref: int,
    w_pref: int,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
    identity: bool = False,
) -> LineLayout:
    # identity=True: codigo_barra ya validado, sin transformar.
    # Resto: texto ya sanitizado en format_*; escape idempotente como defensa.
    fd_text = text if identity else escape_zpl_fd(text)
    w = max_font_width_for_text(fd_text, preferred=w_pref, max_content_width=max_content_width)
    # Altura no mayor que el ancho preferido de jerarquía; si w bajó mucho, bajar h un poco.
    h = min(h_pref, max(w, min(h_pref, w + 4)))
    return LineLayout(text=fd_text, height=h, width=w, x=MARGIN_X, y=y)


def render_zpl_40x23(
    lines: LabelLines,
    profile: LabelPrinterProfile | None = None,
    *,
    max_content_width: int = MAX_CONTENT_WIDTH_DOTS,
) -> RenderedLabel:
    """
    ZPL mínimo compatible: ^PW/^LL + 4 campos ^FD escapados.
    Cada línea elige ``w`` para que ``len*w ≤ max_content_width``.
    """
    profile = profile or PROFILE_3NSTAR_LDT114_203_40X23
    y = MARGIN_Y_TOP
    specs = (
        (lines.codigo, LINE1_H_PREF, LINE1_W_PREF),
        (lines.paciente_dni, LINE2_H_PREF, LINE2_W_PREF),
        (lines.lugar, LINE3_H_PREF, LINE3_W_PREF),
        (lines.fecha_tipo, LINE4_H_PREF, LINE4_W_PREF),
    )
    layouts_list: list[LineLayout] = []
    for idx, (text, h_pref, w_pref) in enumerate(specs):
        lay = _layout_line(
            text,
            y=y,
            h_pref=h_pref,
            w_pref=w_pref,
            max_content_width=max_content_width,
            identity=(idx == 0),
        )
        layouts_list.append(lay)
        y = lay.y + lay.height + LINE_GAP

    # Si el apilado vertical se pasa, comprimir alturas proporcionalmente (ancho intacto).
    max_y = profile.height_dots - MARGIN_Y_BOTTOM
    used_bottom = layouts_list[-1].y + layouts_list[-1].height
    if used_bottom > max_y and used_bottom > 0:
        scale = max_y / used_bottom
        new_layouts: list[LineLayout] = []
        y = MARGIN_Y_TOP
        for lay in layouts_list:
            h = max(10, int(lay.height * scale))
            new_layouts.append(
                LineLayout(text=lay.text, height=h, width=lay.width, x=lay.x, y=y)
            )
            y = y + h + max(2, int(LINE_GAP * scale))
        layouts_list = new_layouts

    layouts = (
        layouts_list[0],
        layouts_list[1],
        layouts_list[2],
        layouts_list[3],
    )

    parts = [
        "^XA",
        profile.encoding_cmd,
        f"^PW{profile.width_dots}",
        f"^LL{profile.height_dots}",
        "^LH0,0",
    ]
    for lay in layouts:
        parts.append(f"^FO{lay.x},{lay.y}^A0N,{lay.height},{lay.width}^FD{lay.text}^FS")
    parts.append("^XZ")
    zpl = "\n".join(parts)

    rendered = RenderedLabel(lines=lines, layouts=layouts, zpl=zpl)
    if not rendered.all_fit_width(max_content_width):
        # Invariante de construcción: no debería ocurrir.
        raise ValueError("Layout ZPL excede MAX_CONTENT_WIDTH_DOTS")
    return rendered
