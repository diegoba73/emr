"""Siembra FRASCO_ORINA y asigna tipo_contenedor a todos los TipoExamen."""

from django.db import migrations

CONTENEDORES = (
    ("EDTA", "Tubo EDTA", "Morado", "EDTA K2"),
    ("CITRATO", "Tubo Citrato", "Celeste", "Citrato de sodio"),
    ("HEPARINA", "Tubo Heparina", "Verde", "Heparina de litio"),
    ("SUERO", "Tubo Suero", "Rojo", "Sin anticoagulante / gel"),
    ("FRASCO_ORINA", "Frasco de orina", "Ámbar", "Sin aditivo"),
)

_EDTA = frozenset(
    {
        "HEMATIES", "HTO", "HGB", "RDW", "LEU", "NEUT_CAY", "NEUT_SEG",
        "EOS", "BAS", "LINF", "MONO", "PLAQ", "HBA1C", "VSG",
    }
)
_CITRATO = frozenset({"TP", "PP", "INR", "KPTT", "DDIM"})
_HEPARINA = frozenset({"EAB_ART", "EAB_VEN", "LACT", "CA_ION"})
_FRASCO = frozenset(
    {
        "ORI_COLOR", "ORI_ASP", "ORI_DENS", "ORI_PH", "ORI_BIL", "ORI_NIT",
        "ORI_CET", "ORI_CEL", "ORI_LEU", "ORI_HEM", "ORI_PIO", "ORI_MUC",
        "ORI_CRIS", "ORI_CONC", "NA_U", "K_U", "CL_U", "CREA_U", "DIUR",
        "CLEAR_CREA", "MICROALB", "PROT_U_24", "PROT_U_AZ",
    }
)


def _tubo(codigo: str, muestra_codigo: str | None) -> str:
    c = (codigo or "").upper().strip()
    if c in _EDTA:
        return "EDTA"
    if c in _CITRATO:
        return "CITRATO"
    if c in _HEPARINA:
        return "HEPARINA"
    if c in _FRASCO or c.startswith("ORI_"):
        return "FRASCO_ORINA"
    m = (muestra_codigo or "").upper().strip()
    if m == "ORINA":
        return "FRASCO_ORINA"
    return "SUERO"


def asignar_tubos(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoContenedor = apps.get_model("laboratorio", "TipoContenedor")
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")

    for codigo, nombre, color, aditivo in CONTENEDORES:
        TipoContenedor.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "color": color,
                "aditivo": aditivo,
                "activo": True,
                "descripcion": "",
            },
        )

    by_codigo = {tc.codigo: tc for tc in TipoContenedor.objects.all()}
    muestras = {tm.pk: tm.codigo for tm in TipoMuestra.objects.all()}

    for ex in TipoExamen.objects.all().iterator():
        muestra_codigo = muestras.get(ex.tipo_muestra_requerida_id) if ex.tipo_muestra_requerida_id else None
        tubo = _tubo(ex.codigo, muestra_codigo)
        tc = by_codigo.get(tubo)
        if tc is None:
            continue
        if ex.tipo_contenedor_id != tc.pk:
            TipoExamen.objects.filter(pk=ex.pk).update(tipo_contenedor_id=tc.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0024_alter_solicitudexamen_origen_solicitud"),
    ]

    operations = [
        migrations.RunPython(asignar_tubos, migrations.RunPython.noop),
    ]
