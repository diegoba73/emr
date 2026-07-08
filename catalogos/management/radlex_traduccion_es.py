"""
Traducción de nombres RadLex Playbook al español clínico (Argentina/España).

RadLex Playbook no publica traducción oficial; este módulo aplica un glosario
estructurado sobre los patrones repetitivos del nomenclador (modalidad, región
anatómica, contraste, procedimientos intervencionistas).
"""
from __future__ import annotations

import re

# Sufijos de contraste / guía (orden: más largo primero)
_CONTRAST_PHRASES: tuple[tuple[str, str], ...] = (
    (' w and wo IV Contrast', ' con y sin contraste IV'),
    (' wo and w IV Contrast', ' sin y con contraste IV'),
    (' w and wo Contrast', ' con y sin contraste'),
    (' wo IV Contrast', ' sin contraste IV'),
    (' w IV Contrast', ' con contraste IV'),
    (' without IV Contrast', ' sin contraste IV'),
    (' with IV Contrast', ' con contraste IV'),
    (' without Contrast', ' sin contraste'),
    (' with Contrast', ' con contraste'),
    (' with Imaging Guidance', ' con guía por imagen'),
    (' without Imaging Guidance', ' sin guía por imagen'),
    (' with Guidance', ' con guía'),
)

# Modalidades al inicio del nombre
_MODALITY_PREFIXES: tuple[tuple[str, str], ...] = (
    ('PT/CT ', 'PET/TC '),
    ('FL/XR ', 'Fluoroscopia/Radiografía '),
    ('NM/CT ', 'Medicina nuclear/TC '),
    ('Mammo ', 'Mamografía '),
    ('CT ', 'TC '),
    ('MR ', 'RM '),
    ('US ', 'Ecografía '),
    ('XR ', 'Radiografía '),
    ('NM ', 'Medicina nuclear '),
    ('FL ', 'Fluoroscopia '),
    ('XA ', 'Angiografía '),
    ('PT ', 'PET '),
    ('DXA ', 'Densitometría ósea '),
    ('RF ', 'Radioscopia '),
    ('RP ', ''),  # procedimiento intervencionista; el resto del nombre ya describe la acción
)

# Frases compuestas (región / procedimiento)
_PHRASES: tuple[tuple[str, str], ...] = (
    ('Lower Extremity', 'miembros inferiores'),
    ('Upper Extremity', 'miembros superiores'),
    ('Cervical Spine', 'columna cervical'),
    ('Thoracic Spine', 'columna torácica'),
    ('Lumbar Spine', 'columna lumbar'),
    ('Sacrum and Coccyx', 'sacro y coxis'),
    ('Temporal Bone', 'hueso temporal'),
    ('Soft Tissue', 'tejidos blandos'),
    ('Major Joint', 'articulación mayor'),
    ('Small Joint', 'articulación menor'),
    ('Imaging Guidance', 'guía por imagen'),
    ('IV Contrast', 'contraste IV'),
    ('Oral Contrast', 'contraste oral'),
    ('Rectal Contrast', 'contraste rectal'),
    ('Barium Enema', 'enema baritado'),
    ('Barium Swallow', 'tránsito esofágico baritado'),
    ('Chest PA and Lateral', 'tórax PA y lateral'),
    ('PA and Lateral', 'PA y lateral'),
    ('Anteroposterior', 'anteroposterior'),
    ('Posteroanterior', 'posteroanterior'),
    ('Arteriovenous Fistula', 'fístula arteriovenosa'),
    ('Whole Body', 'cuerpo entero'),
    ('Bone Age', 'edad ósea'),
    ('Bone Scan', 'gammagrafía ósea'),
    ('Cardiac Stress', 'estrés cardíaco'),
    ('Stress Test', 'prueba de estrés'),
    ('Rest and Stress', 'reposo y estrés'),
    ('Rest Only', 'solo reposo'),
    ('Sleep Study', 'estudio del sueño'),
    ('Fine Needle', 'aguja fina'),
    ('Core Needle', 'aguja core'),
    ('Joint Injection', 'infiltración articular'),
    ('Joint Aspiration', 'aspiración articular'),
    ('Knee Aspiration', 'aspiración de rodilla'),
    ('Liver Biopsy', 'biopsia hepática'),
    ('Kidney Biopsy', 'biopsia renal'),
    ('Lung Biopsy', 'biopsia pulmonar'),
    ('Bone Biopsy', 'biopsia ósea'),
    ('Thyroid Biopsy', 'biopsia tiroidea'),
    ('Prostate Biopsy', 'biopsia prostática'),
    ('Muscle Biopsy', 'biopsia muscular'),
    ('Soft Tissue Biopsy', 'biopsia de tejidos blandos'),
    ('Pleural Biopsy', 'biopsia pleural'),
    ('Pancreas Biopsy', 'biopsia pancreática'),
    ('Mediastinal Biopsy', 'biopsia mediastínica'),
    ('Abdomen Biopsy', 'biopsia abdominal'),
    ('Spinal Tap', 'punción lumbar'),
    ('Lumbar Puncture', 'punción lumbar'),
    ('Chest Tube', 'tubo pleural'),
    ('Central Line', 'vía central'),
    ('Port Placement', 'colocación de port'),
    ('Feeding Tube', 'sonda de alimentación'),
    ('Foreign Body', 'cuerpo extraño'),
    ('Renal Transplant', 'trasplante renal'),
    ('Liver Transplant', 'trasplante hepático'),
    ('Heart Transplant', 'trasplante cardíaco'),
)

# Palabras sueltas (después de frases compuestas)
_WORDS: dict[str, str] = {
    'Abdomen': 'abdomen',
    'Abdominal': 'abdominal',
    'Angio': 'angiografía',
    'Angiography': 'angiografía',
    'Angioplasty': 'angioplastia',
    'Ankle': 'tobillo',
    'Aorta': 'aorta',
    'Aortic': 'aórtico',
    'Appendix': 'apéndice',
    'Arm': 'brazo',
    'Artery': 'arteria',
    'Arterial': 'arterial',
    'Arthrocentesis': 'artrocentesis',
    'Arthrogram': 'artrograma',
    'Arthrography': 'artrografía',
    'Aspiration': 'aspiración',
    'Axilla': 'axila',
    'Back': 'espalda',
    'Biopsy': 'biopsia',
    'Bladder': 'vejiga',
    'Bone': 'hueso',
    'Both': 'ambos',
    'Brain': 'cerebro',
    'Breast': 'mama',
    'Bronchoscopy': 'broncoscopia',
    'Cardiac': 'cardíaco',
    'Chest': 'tórax',
    'Colon': 'colon',
    'Contrast': 'contraste',
    'Coronary': 'coronario',
    'Cyst': 'quiste',
    'Drainage': 'drenaje',
    'Elbow': 'codo',
    'Embolization': 'embolización',
    'Esophagus': 'esófago',
    'Extremity': 'extremidad',
    'Eye': 'ojo',
    'Facial': 'facial',
    'Fallopian': 'trompa de Falopio',
    'Fetal': 'fetal',
    'Finger': 'dedo',
    'Foot': 'pie',
    'Gallbladder': 'vesícula biliar',
    'Guidance': 'guía',
    'Hand': 'mano',
    'Head': 'cráneo',
    'Heart': 'corazón',
    'Hip': 'cadera',
    'Hysterosalpingography': 'histerosalpingografía',
    'Injection': 'inyección',
    'Intraoperative': 'intraoperatorio',
    'Joint': 'articulación',
    'Kidney': 'riñón',
    'Knee': 'rodilla',
    'Larynx': 'laringe',
    'Left': 'izquierdo',
    'Leg': 'pierna',
    'Liver': 'hígado',
    'Lung': 'pulmón',
    'Lymph': 'linfático',
    'Mandible': 'mandíbula',
    'Maxillofacial': 'maxilofacial',
    'Mediastinal': 'mediastino',
    'Mediastinum': 'mediastino',
    'Muscle': 'músculo',
    'Neck': 'cuello',
    'Needle': 'aguja',
    'Oblique': 'oblicua',
    'Orbits': 'órbitas',
    'Ovary': 'ovario',
    'Pancreas': 'páncreas',
    'Pelvis': 'pelvis',
    'Pelvic': 'pélvico',
    'Placement': 'colocación',
    'Pleural': 'pleural',
    'Prostate': 'próstata',
    'Pulmonary': 'pulmonar',
    'Renal': 'renal',
    'Right': 'derecho',
    'Sacrum': 'sacro',
    'Scan': 'estudio',
    'Scrotum': 'escroto',
    'Shoulder': 'hombro',
    'Sinuses': 'senos paranasales',
    'Skull': 'cráneo',
    'Spine': 'columna',
    'Spleen': 'bazo',
    'Stent': 'stent',
    'Stomach': 'estómago',
    'Testicle': 'testículo',
    'Thigh': 'muslo',
    'Thorax': 'tórax',
    'Thyroid': 'tiroides',
    'Toe': 'dedo del pie',
    'Transplant': 'trasplante',
    'Tube': 'tubo',
    'Tumor': 'tumor',
    'Uterus': 'útero',
    'Vein': 'vena',
    'Venous': 'venoso',
    'Views': 'proyecciones',
    'Wrist': 'muñeca',
    'and': 'y',
    'with': 'con',
    'without': 'sin',
    'w': 'con',
    'wo': 'sin',
    'of': 'de',
    'the': '',
    'for': 'para',
    'in': 'en',
    'on': 'en',
}


def _title_es(text: str) -> str:
    """Capitaliza la primera letra; mantiene siglas (TC, RM, IV, PA)."""
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return text
    parts = text.split(' ')
    out: list[str] = []
    for i, p in enumerate(parts):
        if p.upper() in {'TC', 'RM', 'IV', 'PA', 'PET', 'NM', 'MR', 'CT', 'US', 'XR', 'FL', 'XA'}:
            out.append(p.upper())
        elif i == 0:
            out.append(p[:1].upper() + p[1:])
        else:
            out.append(p)
    return ' '.join(out)


def traducir_estudio_radlex(name: str) -> str:
    """Traduce un nombre RadLex Playbook al español clínico."""
    if not name or not name.strip():
        return name

    result = name.strip()

    for en, es in _CONTRAST_PHRASES:
        if en in result:
            result = result.replace(en, es)

    for en, es in _MODALITY_PREFIXES:
        if result.startswith(en):
            result = es + result[len(en) :]
            break

    for en, es in _PHRASES:
        result = re.sub(re.escape(en), es, result, flags=re.IGNORECASE)

    def replace_word(match: re.Match[str]) -> str:
        word = match.group(0)
        key = word if word in _WORDS else word.capitalize() if word.capitalize() in _WORDS else None
        if key is None:
            lower = word.lower()
            for k, v in _WORDS.items():
                if k.lower() == lower:
                    return v if word.islower() else (v.capitalize() if word[0].isupper() else v)
            return word
        translated = _WORDS[key if key in _WORDS else word.capitalize()]
        if not translated:
            return ''
        if word.isupper():
            return translated.upper()
        if word[0].isupper():
            return translated.capitalize() if translated else ''
        return translated

    result = re.sub(r'[A-Za-z]+', replace_word, result)
    result = re.sub(r'\s+', ' ', result).strip()
    result = re.sub(r'\s+,', ',', result)
    return _title_es(result)
