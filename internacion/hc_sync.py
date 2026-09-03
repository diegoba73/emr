"""Sincroniza el texto legado de medicación habitual con las filas estructuradas."""


def sincronizar_medicacion_habitual_texto(internacion):
    filas = internacion.medicaciones_habituales.order_by('id')
    lineas = []
    for fila in filas:
        nombre = (fila.medicamento or '').strip()
        dosis = (fila.dosis_mg_dia or '').strip()
        if not nombre:
            continue
        if dosis:
            lineas.append(f'{nombre} {dosis} mg/día')
        else:
            lineas.append(nombre)
    from internacion.models import Internacion
    Internacion.objects.filter(pk=internacion.pk).update(medicacion_habitual='\n'.join(lineas))
