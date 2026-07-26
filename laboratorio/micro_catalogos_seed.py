"""Catálogos de cultivo y muestra propios de microbiología clínica (no LIMS química)."""

TIPOS_CULTIVO_MICRO_SEED = [
    ("HEMOCULTIVO", "Hemocultivo", 10),
    ("CATETER", "Cultivo de catéter", 20),
    ("PUNTA_CATETER", "Cultivo de punta de catéter", 30),
    ("UROCULTIVO", "Urocultivo", 40),
    ("COPROCULTIVO", "Coprocultivo", 50),
    ("LCR", "Cultivo de líquido cefalorraquídeo — LCR", 60),
    ("NASOFARINGEO", "Cultivo nasofaríngeo", 70),
    ("ESPUTO", "Cultivo de esputo", 80),
    ("ASPIRADO_TRAQUEAL_BRONQUIAL", "Cultivo de aspirado traqueal/bronquial", 90),
    ("MINI_BAL", "Cultivo de lavado broncoalveolar — Mini BAL", 100),
    ("VAGINAL", "Cultivo vaginal", 110),
    ("URETRAL", "Cultivo uretral", 120),
    ("SGB", "Cultivo para Streptococcus agalactiae / SGB", 130),
    ("PIEL_PARTES_BLANDAS", "Cultivo de piel y partes blandas", 140),
    ("HERIDA_ABSCESO", "Cultivo de herida/absceso", 150),
    ("MATERIAL_QUIRURGICO", "Cultivo de material quirúrgico", 160),
    ("BIOPSIA", "Cultivo de biopsia", 170),
    ("TEJIDO", "Cultivo de tejido", 180),
    ("OSEO", "Cultivo óseo", 190),
    ("LIQUIDO_PERITONEAL", "Cultivo de líquido peritoneal / ascítico", 200),
    ("LIQUIDO_PLEURAL", "Cultivo de líquido pleural", 210),
    ("LIQUIDO_SINOVIAL", "Cultivo de líquido sinovial / articular", 220),
    ("LIQUIDO_PERICARDICO", "Cultivo de líquido pericárdico", 230),
    ("VIGILANCIA_EPIDEMIOLOGICA", "Cultivo de vigilancia epidemiológica", 240),
    ("AMBIENTAL", "Cultivo ambiental", 250),
]

TIPOS_MUESTRA_MICRO_SEED = [
    ("SANGRE", "Sangre", 10),
    ("ORINA", "Orina", 20),
    ("MATERIA_FECAL", "Materia fecal", 30),
    ("LCR", "LCR", 40),
    ("ESPUTO", "Esputo", 50),
    ("BAL", "BAL", 60),
    ("ASPIRADO", "Aspirados", 70),
    ("EXUDADO_FARINGEO", "Exudado faríngeo", 80),
    ("EXUDADO_NASAL", "Exudado nasal", 90),
    ("EXUDADO_OTICO", "Exudado ótico", 100),
    ("EXUDADO_OCULAR", "Exudado ocular", 110),
    ("EXUDADO_GENITAL", "Exudado genital", 120),
    ("LIQUIDO_ESTERIL", "Líquidos estériles", 130),
    ("PUS", "Pus", 140),
    ("TEJIDO", "Tejidos", 150),
    ("HUESO", "Hueso", 160),
    ("BIOPSIA", "Biopsias", 170),
    ("CATETER", "Catéteres", 180),
    ("PROTESIS", "Prótesis", 190),
    ("DISPOSITIVO", "Dispositivos", 200),
    ("HISOPADO_VIGILANCIA", "Hisopados de vigilancia", 210),
]


def seed_catalogos_microbiologia(*, update_existing: bool = True) -> dict[str, int]:
    """Idempotente: crea/actualiza tipos de cultivo y muestra micro.

    Desactiva cultivos cuyo código ya no está en el seed actual.
    """
    from laboratorio.models_microbiologia import (
        TipoCultivoMicrobiologia,
        TipoMuestraMicrobiologia,
    )

    created_c = updated_c = deactivated_c = 0
    codigos_cultivo = {c for c, _, _ in TIPOS_CULTIVO_MICRO_SEED}
    for codigo, nombre, orden in TIPOS_CULTIVO_MICRO_SEED:
        obj, created = TipoCultivoMicrobiologia.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "orden": orden, "activo": True},
        )
        if created:
            created_c += 1
        elif update_existing:
            changed = False
            if obj.nombre != nombre:
                obj.nombre = nombre
                changed = True
            if obj.orden != orden:
                obj.orden = orden
                changed = True
            if not obj.activo:
                obj.activo = True
                changed = True
            if changed:
                obj.save()
                updated_c += 1

    for obj in TipoCultivoMicrobiologia.objects.exclude(codigo__in=codigos_cultivo):
        if obj.activo:
            obj.activo = False
            obj.save(update_fields=["activo", "updated_at"])
            deactivated_c += 1

    created_m = updated_m = 0
    for codigo, nombre, orden in TIPOS_MUESTRA_MICRO_SEED:
        obj, created = TipoMuestraMicrobiologia.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "orden": orden, "activo": True},
        )
        if created:
            created_m += 1
        elif update_existing:
            changed = False
            if obj.nombre != nombre:
                obj.nombre = nombre
                changed = True
            if obj.orden != orden:
                obj.orden = orden
                changed = True
            if not obj.activo:
                obj.activo = True
                changed = True
            if changed:
                obj.save()
                updated_m += 1

    return {
        "cultivos_creados": created_c,
        "cultivos_actualizados": updated_c,
        "cultivos_desactivados": deactivated_c,
        "muestras_creadas": created_m,
        "muestras_actualizadas": updated_m,
    }
