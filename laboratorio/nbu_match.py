"""Empareja exámenes del catálogo LIMS con códigos del Nomenclador Bioquímico Único (NBU).

El campo interno TipoExamen.codigo (IACA) NO se modifica. Este módulo solo propone codigo_nbu.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

DEFAULT_NBU_CSV = Path(__file__).resolve().parent / "data" / "nbu_2012.csv"

STOP = {
    "de", "del", "la", "el", "los", "las", "en", "con", "para", "por", "un", "una",
    "o", "u", "y", "e", "al", "a", "the", "of", "and", "c", "cu", "x",
    "determinacion", "determinaciones", "dosaje", "dosajes", "cuantitativo",
    "cuantitativa", "cualitativo", "cualitativa", "total", "totales",
    "ag", "anti", "ac", "anticuerpo", "anticuerpos",
}

SPECIMEN_WORDS = {
    "suero", "serico", "serica", "serum", "orina", "urinario", "urinaria",
    "urinarias", "sangre", "sanguineo", "sanguinea", "plasma", "plasmatico",
    "plasmatica", "lcr", "cefalorraquideo", "cefaloraquideo", "saliva", "pelo",
    "semen", "seminal", "heces", "fecal", "pleural", "ascitico", "ascitis",
    "pericardico", "sinovial", "eritrocitario", "eritrocitaria", "neonatal",
    "neonatales",
}

# Token canónico → grupo de muestra. None = genérico (compatible con cualquiera).
SPECIMEN_GROUP_RE = (
    (re.compile(r"\b(papel filtro|neonatal|neo)\b"), "neonatal"),
    (re.compile(r"\b(materia fecal|heces|fecal)\b"), "mf"),
    (re.compile(r"\b(lcr|cefalorraquid\w*|cefaloraquid\w*|liquido cefalo)\b"), "lcr"),
    (re.compile(r"\bpleural\b"), "pleural"),
    (re.compile(r"\basciti\w*\b"), "ascitis"),
    (re.compile(r"\bpericard\w*\b"), "pericardico"),
    (re.compile(r"\bsinovial\b"), "sinovial"),
    (re.compile(r"\bsaliva\b"), "saliva"),
    (re.compile(r"\bpelo\b"), "pelo"),
    (re.compile(r"\b(semen|seminal)\b"), "semen"),
    (re.compile(r"\beritrocit\w*\b"), "eritrocito"),
    (re.compile(r"\b(orina|urinar\w*)\b"), "orina"),
    (re.compile(r"\b(suero|seric[oa]|serum|plasma\w*|sangre|sanguin\w*|edta|heparina)\b"), "sangre"),
)

TIME_NOISE_RE = re.compile(
    r"\b(\d+\s*(minutos?|min|hs?|horas?)|al azar|posprandial|postprandial|"
    r"con extraccion|domicilio|gestacional)\b",
)

# Sufijo de nomenclador: -emia = sangre, -uria = orina.
EMIA_RE = re.compile(r"\b[a-z]{2,}emia\b")
URIA_RE = re.compile(r"\b[a-z]{2,}uria\b")

EMIA_STEM = {
    "glucemia": "glucosa",
    "uremia": "urea",
    "albuminemia": "albumina",
    "calcemia": "calcio",
    "ferremia": "hierro",
    "fosfatemia": "fosforo",
    "natremia": "sodio",
    "potasemia": "potasio",
    "cloremia": "cloro",
    "amonemia": "amonio",
    "fluoremia": "fluor",
    "bilirrubinemia": "bilirrubina",
    "cetonemia": "cetona",
    "uricemia": "urico",
    "magnesemia": "magnesio",
    "lipemia": "lipidos",
    "proteinemia": "proteina",
    "alcoholemia": "etanol",
    "galactosemia": "galactosa",
    "parasitemia": "parasito",
}

URIA_STEM = {
    "glucosuria": "glucosa",
    "acetonuria": "acetona",
    "proteinuria": "proteina",
    "fosfaturia": "fosforo",
    "calciuria": "calcio",
    "fluoruria": "fluor",
    "bilirrubinuria": "bilirrubina",
    "alcoluria": "etanol",
    "aminoaciduria": "aminoacidos",
    "hematuria": "sangre",
}

STRONG_MODIFIERS = {
    "libre", "complejado", "neonatal", "sobrecarga", "tolerancia", "curva",
    "clearance", "clearence", "mutacion", "isoenzimas", "electroforesis",
    "panel", "confirmatorio", "screening", "rapido", "estimulo", "filiacion",
    "receptor", "indice", "genotipo", "mutaciones", "ultrasensible",
}

SYNONYM_TOKEN = {
    "glucosa": "glucemia",
    "tgo": "got",
    "tgp": "gpt",
    "alt": "gpt",
    "ast": "got",
    "fal": "fosfatasa",
    "hb": "hemoglobina",
    "hba1c": "glicosilada",
    "a1c": "glicosilada",
    "uremia": "urea",
    "albuminemia": "albumina",
    "psat": "psa",
    "psa": "psa",
    "ft4": "t4l",
    "t4libre": "t4l",
    "had": "vasopresina",
    "avp": "vasopresina",
    "adh": "vasopresina",
}

# Nombres cortos del catálogo → código NBU inequívoco.
EXPLICIT_ALIASES = {
    "tsh": "660865",
    "tirotrofina": "660865",
    "t4": "660866",
    "t4l": "660867",
    "t4 libre": "660867",
    "ft4": "660867",
    "t3": "660878",
    "t3l": "669661",
    "got": "660873",
    "gpt": "660874",
    "psa": "661000",
    "hemograma": "660475",
    "hematocrito": "660466",
    "glucemia": "660412",
    "pcr": "660761",  # proteína C reactiva; no PCR molecular
    "proteina c reactiva": "660761",
    "ferritina": "661062",
    "transferrina": "660875",
    "hdl": "661035",
    "ldl": "661040",
    "trigliceridos": "660876",
    "colesterol": "660174",
    "urea": "660902",
    "uremia": "660902",
    "albumina": "660015",
    "albuminemia": "660015",
    "afp": "660020",
    "fsh": "660370",
    "lh": "660612",
    "prl": "660759",
    "prolactina": "660759",
    "pth": "660739",
    "parathormona": "660739",
    "acth": "660006",
    "hba1c": "661070",
    "hemoglobina glicosilada": "661070",
    "acra": "662025",
    "potasio": "660753",
    "potasemia": "660753",
    "sodio": "660839",
    "natremia": "660839",
    "cloro": "660168",
    "cloremia": "660168",
}


@dataclass(frozen=True)
class NbuPractica:
    codigo_nbu: str
    nombre: str
    frecuencia: str = ""
    ub: str = ""


@dataclass(frozen=True)
class ExamRow:
    exam_id: int | None
    codigo: str
    nombre: str
    muestra: str = ""
    activo: bool = True


@dataclass(frozen=True)
class MatchResult:
    exam: ExamRow
    practica: NbuPractica | None
    score: float
    rule: str
    second_score: float = 0.0
    second_codigo: str = ""
    second_nombre: str = ""

    @property
    def auto(self) -> bool:
        return self.practica is not None and self.rule.startswith("auto")


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn"
    )


def _split_compounds(s: str) -> str:
    s = s.replace("hidroxiprogesterona", "hidroxi progesterona")
    s = s.replace("hidroxivitamina", "hidroxi vitamina")
    return s


def norm_text(s: str) -> str:
    s = strip_accents(s).lower()
    s = s.replace("ß", "b").replace("β", "b")
    s = TIME_NOISE_RE.sub(" ", s)
    s = _split_compounds(s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def specimen_group(nombre: str, muestra: str = "") -> str | None:
    blob = norm_text(f"{nombre} {muestra}")
    if re.search(r"\bseric\w*\s+o\s+urinar\w*", blob) or re.search(
        r"\bsangre\s+u\s+orina\b", blob
    ):
        return None
    for rx, group in SPECIMEN_GROUP_RE:
        if rx.search(blob):
            return group
    # Convención del nomenclador: *emia = sangre, *uria = orina.
    nombre_n = norm_text(nombre)
    if URIA_RE.search(nombre_n) and not EMIA_RE.search(nombre_n):
        return "orina"
    if EMIA_RE.search(nombre_n):
        return "sangre"
    return None


def _canonicalize(toks: list[str], spec: str | None) -> list[str]:
    out: list[str] = []
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if t == "glucosa" and nxt in {"6", "g6p", "6p"}:
            out.append("glucosa")
            continue
        if t == "glucosa":
            out.append("glucemia" if spec in (None, "sangre") else "glucosa")
            continue
        stem_uria = URIA_STEM.get(t)
        if stem_uria:
            out.append(stem_uria)
            continue
        stem_emia = EMIA_STEM.get(t)
        if stem_emia:
            out.append(t)
            out.append(stem_emia)
            continue
        out.append(SYNONYM_TOKEN.get(t, t))
    return out


def content_tokens(nombre: str, muestra: str = "") -> list[str]:
    spec = specimen_group(nombre, muestra)
    raw = [t for t in norm_text(nombre).split() if t and t not in STOP]
    raw = _canonicalize(raw, spec)
    return [t for t in raw if t not in SPECIMEN_WORDS]


def extract_aliases(nombre: str) -> set[str]:
    aliases: set[str] = set()
    n = strip_accents(nombre)
    for chunk in re.findall(r"\(([^)]{1,40})\)", n):
        for part in re.split(r"[/,]| o ", chunk):
            a = norm_text(part)
            if 1 <= len(a) <= 12:
                aliases.add(a.replace(" ", ""))
                aliases.update(a.split())
    tail = re.search(r"[-–]\s*([A-Za-z0-9][A-Za-z0-9/ ]{0,18})\s*$", n)
    if tail:
        a = norm_text(tail.group(1))
        if 2 <= len(a) <= 12:
            aliases.add(a.replace(" ", ""))
            aliases.update(x for x in a.split() if len(x) >= 2)
    return {SYNONYM_TOKEN.get(x, x) for x in aliases if x and x not in STOP}


def specimen_compatible(exam_spec: str | None, nbu_spec: str | None) -> bool:
    if not exam_spec or not nbu_spec:
        return True
    return exam_spec == nbu_spec


def _seq_ratio(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    return 100.0 * SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return 100.0 * len(a & b) / len(a | b)


def _coverage(a: set[str], b: set[str]) -> float:
    if not a:
        return 0.0
    return 100.0 * len(a & b) / len(a)


def score_pair(exam: ExamRow, practica: NbuPractica) -> tuple[float, str]:
    exam_spec = specimen_group(exam.nombre, exam.muestra)
    nbu_spec = specimen_group(practica.nombre)
    if not specimen_compatible(exam_spec, nbu_spec):
        return 0.0, "spec_mismatch"

    et = content_tokens(exam.nombre, exam.muestra)
    nt = content_tokens(practica.nombre)
    se, sn = set(et), set(nt)
    if not se or not sn:
        return 0.0, "empty"

    weak = STOP | STRONG_MODIFIERS
    exam_aliases = (extract_aliases(exam.nombre) | set(et)) - weak
    nbu_aliases = (extract_aliases(practica.nombre) | set(nt)) - weak
    alias_hit = bool(exam_aliases & nbu_aliases)

    jacc = _jaccard(se, sn)
    cov = _coverage(se, sn)
    seq = _seq_ratio(et, nt)
    score = max(jacc, cov * 0.92, seq)

    if se == sn:
        score = 100.0
        rule = "exact_tokens"
    elif se <= sn and len(se) >= 2:
        score = max(score, 94.0)
        rule = "subset"
    elif se <= sn and len(se) == 1 and alias_hit:
        score = max(score, 96.0)
        rule = "alias"
    elif alias_hit and cov >= 50:
        score = max(score, 90.0)
        rule = "alias"
    else:
        rule = "fuzzy"

    extra = sn - se - STOP
    nums_e = {t for t in se if t.isdigit()}
    nums_n = {t for t in sn if t.isdigit()}
    if nums_e and nums_n and nums_e.isdisjoint(nums_n):
        return 0.0, "num_mismatch"
    if {"1", "25"} <= nums_n and "1" not in nums_e:
        score -= 18.0
    if {"d2", "d3"} <= se and not ({"d2", "d3"} & sn):
        score -= 20.0
    if extra & STRONG_MODIFIERS:
        # El NBU agrega un modificador que el examen no tiene (libre, neonatal, panel…).
        if not (extra & se) and not (extra & exam_aliases):
            score -= 22.0
            rule = "modifier_penalty"

    if exam_spec and nbu_spec and exam_spec == nbu_spec:
        score = min(100.0, score + 2.0)

    return max(0.0, score), rule


def _prefer_pmo(rows: list[NbuPractica]) -> list[NbuPractica]:
    """Si el mismo nombre apunta a dos códigos, deja PMO / código más bajo.

    Conserva alias (varios nombres para el mismo código NBU).
    """
    by_norm: dict[str, list[NbuPractica]] = {}
    for r in rows:
        by_norm.setdefault(norm_text(r.nombre), []).append(r)
    out: list[NbuPractica] = []
    seen: set[tuple[str, str]] = set()
    for group in by_norm.values():
        if len(group) == 1:
            chosen = group
        else:
            pmo = [g for g in group if (g.frecuencia or "").upper() == "PMO"]
            pool = pmo or group
            pool = sorted(pool, key=lambda g: g.codigo_nbu)
            chosen = [pool[0]]
        for g in chosen:
            key = (g.codigo_nbu, norm_text(g.nombre))
            if key not in seen:
                out.append(g)
                seen.add(key)
    return out


def load_nbu_catalog(path: Path | None = None) -> list[NbuPractica]:
    csv_path = path or DEFAULT_NBU_CSV
    rows: list[NbuPractica] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            code = (r.get("codigo_nbu") or "").strip()
            nombre = (r.get("nombre") or "").strip()
            if not code or not nombre:
                continue
            rows.append(
                NbuPractica(
                    codigo_nbu=code,
                    nombre=nombre,
                    frecuencia=(r.get("frecuencia") or "").strip(),
                    ub=(r.get("ub") or "").strip(),
                )
            )
    return _prefer_pmo(rows)


def ub_map(catalog: list[NbuPractica] | None = None) -> dict[str, str]:
    """codigo_nbu → U.B. (string decimal)."""
    cat = catalog if catalog is not None else load_nbu_catalog()
    out: dict[str, str] = {}
    for p in cat:
        if p.codigo_nbu and p.ub:
            out[p.codigo_nbu] = p.ub
    return out


def _explicit_match(exam: ExamRow, catalog: list[NbuPractica]) -> NbuPractica | None:
    key = " ".join(content_tokens(exam.nombre, exam.muestra))
    short = content_tokens(exam.nombre, exam.muestra)
    code = None
    if key in EXPLICIT_ALIASES:
        code = EXPLICIT_ALIASES[key]
    elif len(short) == 1 and short[0] in EXPLICIT_ALIASES:
        code = EXPLICIT_ALIASES[short[0]]
    elif short and short[0] in EXPLICIT_ALIASES and len(short[0]) >= 4:
        code = EXPLICIT_ALIASES[short[0]]
    if not code:
        return None
    found = next((p for p in catalog if p.codigo_nbu == code), None)
    if not found:
        return None
    exam_spec = specimen_group(exam.nombre, exam.muestra)
    nbu_spec = specimen_group(found.nombre)
    if not specimen_compatible(exam_spec, nbu_spec):
        return None
    # Alias genéricos (glucemia, urea sérica, TSH) no se aplican a orina/LCR/etc.
    if exam_spec and exam_spec != "sangre" and nbu_spec is None:
        return None
    return found


def match_exam(
    exam: ExamRow,
    catalog: list[NbuPractica],
    *,
    min_score: float = 94.0,
    min_margin: float = 4.0,
    index: "CatalogIndex | None" = None,
) -> MatchResult:
    explicit = _explicit_match(exam, catalog)
    candidates = catalog
    if index is not None:
        candidates = index.candidates_for(exam)
        if explicit and explicit not in candidates:
            candidates = list(candidates) + [explicit]

    scored: list[tuple[float, str, NbuPractica]] = []
    for p in candidates:
        sc, rule = score_pair(exam, p)
        if explicit and p.codigo_nbu == explicit.codigo_nbu:
            sc = max(sc, 97.0)
            rule = "auto_alias"
        if sc <= 0:
            continue
        scored.append((sc, rule, p))

    if not scored:
        return MatchResult(exam=exam, practica=None, score=0.0, rule="unmatched")

    def rank(item: tuple[float, str, NbuPractica]) -> tuple:
        sc, _rule, p = item
        exam_spec = specimen_group(exam.nombre, exam.muestra)
        nbu_spec = specimen_group(p.nombre)
        spec_rank = 2 if exam_spec and nbu_spec == exam_spec else (1 if nbu_spec is None else 0)
        pmo = 1 if (p.frecuencia or "").upper() == "PMO" else 0
        return (sc, spec_rank, pmo, -int(p.codigo_nbu or "0"))

    scored.sort(key=rank, reverse=True)
    best_sc, best_rule, best_p = scored[0]
    best_spec = specimen_group(exam.nombre, exam.muestra)
    best_nbu_spec = specimen_group(best_p.nombre)
    best_spec_rank = 2 if best_spec and best_nbu_spec == best_spec else (
        1 if best_nbu_spec is None else 0
    )

    def _spec_rank(p: NbuPractica) -> int:
        nbu_spec = specimen_group(p.nombre)
        if best_spec and nbu_spec == best_spec:
            return 2
        if nbu_spec is None:
            return 1
        return 0

    peers = [
        item
        for item in scored[1:]
        if item[2].codigo_nbu != best_p.codigo_nbu
        and _spec_rank(item[2]) >= best_spec_rank
    ]
    second_sc = peers[0][0] if peers else 0.0
    second_p = peers[0][2] if peers else None

    auto_rule = best_rule if best_rule.startswith("auto") else f"auto_{best_rule}"
    if best_sc >= min_score and (best_sc - second_sc) >= min_margin:
        return MatchResult(
            exam=exam,
            practica=best_p,
            score=best_sc,
            rule=auto_rule,
            second_score=second_sc,
            second_codigo=second_p.codigo_nbu if second_p else "",
            second_nombre=second_p.nombre if second_p else "",
        )
    if best_sc >= 75:
        return MatchResult(
            exam=exam,
            practica=best_p,
            score=best_sc,
            rule="review",
            second_score=second_sc,
            second_codigo=second_p.codigo_nbu if second_p else "",
            second_nombre=second_p.nombre if second_p else "",
        )
    return MatchResult(
        exam=exam,
        practica=None,
        score=best_sc,
        rule="unmatched",
        second_score=second_sc,
        second_codigo=second_p.codigo_nbu if second_p else "",
        second_nombre=second_p.nombre if second_p else "",
    )


class CatalogIndex:
    """Índice token → prácticas para no comparar contra todo el nomenclador."""

    def __init__(self, catalog: list[NbuPractica]):
        self.catalog = catalog
        self._by_token: dict[str, list[NbuPractica]] = defaultdict(list)
        self._by_code = {p.codigo_nbu: p for p in catalog}
        for p in catalog:
            toks = set(content_tokens(p.nombre)) | extract_aliases(p.nombre)
            for t in toks:
                if t and t not in STOP:
                    self._by_token[t].append(p)

    def candidates_for(self, exam: ExamRow) -> list[NbuPractica]:
        toks = set(content_tokens(exam.nombre, exam.muestra)) | extract_aliases(exam.nombre)
        found: dict[str, NbuPractica] = {}
        for t in toks:
            if t in STOP:
                continue
            for p in self._by_token.get(t, ()):
                found[p.codigo_nbu] = p
        return list(found.values()) or self.catalog


def match_catalog(
    exams: list[ExamRow],
    catalog: list[NbuPractica] | None = None,
    **kwargs,
) -> list[MatchResult]:
    cat = catalog if catalog is not None else load_nbu_catalog()
    index = CatalogIndex(cat)
    return [match_exam(ex, cat, index=index, **kwargs) for ex in exams]
