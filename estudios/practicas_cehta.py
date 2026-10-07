"""Catálogo de prácticas CEHTA + códigos legacy (ex-modalidad)."""

from __future__ import annotations

import re
import unicodedata


# Valores históricos de modalidad (siguen válidos en estudios existentes).
LEGACY_PRACTICA_CHOICES: list[tuple[str, str]] = [
    ('IMAGEN_RX', 'Imagen — Rayos X'),
    ('IMAGEN_TC', 'Imagen — Tomografía'),
    ('IMAGEN_RM', 'Imagen — Resonancia'),
    ('IMAGEN_US', 'Imagen — Ultrasonido'),
    ('PDF_INFORME_EXTERNO', 'PDF / informe externo'),
    ('OTRO', 'Otro'),
]

# Solapa PRACTICAS del Excel CEHTA (deduplicada).
CEHTA_PRACTICA_NOMBRES: list[str] = [
    'Cardiografía por impedancia',
    'Colocación de Dispositivo intrauterino',
    'Colpocitología',
    'Colposcopía',
    'Consulta especialista en cardiología',
    'Consulta especialista en cirugía',
    'Consulta especialista en diabetología',
    'Consulta especialista en ginecología',
    'Consulta especialista en nefrología',
    'Consulta especialista en neumonología',
    'Consulta especialista en nutrición',
    'Consulta especialista en traumatología',
    'Consulta especialista en urología',
    'Consulta médica',
    'Control de marcapasos',
    'Doppler arterial miembros inf.',
    'Doppler arterial miembros sup.',
    'Doppler arterio-venoso de miembros inferiores',
    'Doppler arterio-venoso de miembros superiores',
    'Doppler cardíaco',
    'Doppler de aorta abdominal',
    'Doppler de Riñón',
    'Doppler de testículos',
    'Doppler de tiroides',
    'Doppler de vasos de cuello',
    'Doppler transesofágico',
    'Doppler transvaginal',
    'Doppler venoso miembros inf.',
    'Doppler venoso miembros sup.',
    'Ecocardiograma de estrés',
    'Ecodoppler aorto ilíaco',
    'Ecodoppler arterial y/o venoso de otras regiones',
    'Ecodoppler circulación portal',
    'Ecografía completa de abdomen',
    'Ecografía de aorta abdominal',
    'Ecografía de partes blandas',
    'Ecografía de testículos',
    'Ecografía de tiroides',
    'Ecografía ginecológica',
    'Ecografía hepatica / vias biliares',
    'Ecografía mamaria',
    'Ecografía pancreática o suprarenal',
    'Ecografía Renal',
    'Ecografía transvaginal',
    'Ecografía vesical / prostática',
    'Electrocardiograma',
    'Ergoespirometría',
    'Ergometría de 12 derivaciones',
    'Escisión local, electrocoagulación, Biopsia (cuello, vulva, vagina)',
    'Espirometría',
    'Himenotomía',
    'Holter 3 canales',
    'MAPA',
    'Presurometria Segmentaria',
    'Punción biopsia mamaria con aguja fina',
    'Rehabilitación Cardiopulmonar',
    'Test de marcha o caminata',
]


def slug_practica(nombre: str) -> str:
    text = (nombre or '').strip()
    if not text:
        return 'OTRO'
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r'[^A-Za-z0-9]+', '_', ascii_text.upper()).strip('_')
    # Alineado a TipoEstudioComplementario.codigo (max_length=50).
    return (slug[:50] or 'OTRO')


CEHTA_PRACTICA_CHOICES: list[tuple[str, str]] = [
    (slug_practica(n), n) for n in CEHTA_PRACTICA_NOMBRES
]

# Choices unificados: legacy primero, luego CEHTA (sin pisar códigos legacy).
_seen: set[str] = set()
PRACTICA_CHOICES: list[tuple[str, str]] = []
for code, label in [*LEGACY_PRACTICA_CHOICES, *CEHTA_PRACTICA_CHOICES]:
    if code in _seen:
        continue
    _seen.add(code)
    PRACTICA_CHOICES.append((code, label))

PRACTICA_LABELS: dict[str, str] = dict(PRACTICA_CHOICES)
