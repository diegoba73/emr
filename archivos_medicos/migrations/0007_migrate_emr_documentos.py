"""Migra emr.Documento al repositorio unificado ArchivoMedico."""

from django.db import migrations


TIPO_DOCUMENTO_A_ARCHIVO = {
    'INFORME': 'PDF',
    'ESTUDIO': 'OTRO',
    'ANALISIS': 'PDF',
    'DIAGNOSTICO': 'PDF',
    'IMAGEN': 'FOTO_CLINICA',
    'CONSENTIMIENTO': 'PDF',
    'OTRO': 'OTRO',
}


def migrar_documentos_emr_a_archivos(apps, schema_editor):
    Documento = apps.get_model('emr', 'Documento')
    ArchivoMedico = apps.get_model('archivos_medicos', 'ArchivoMedico')

    for doc in Documento.objects.select_related('atencion').iterator():
        atencion = doc.atencion
        if not atencion or not atencion.paciente_id:
            continue
        if ArchivoMedico.objects.filter(atencion_id=atencion.id, archivo=doc.archivo).exists():
            continue
        titulo = (doc.descripcion or '').strip() or str(doc.tipo_documento or 'Archivo')
        ArchivoMedico.objects.create(
            titulo=titulo[:200],
            descripcion=doc.descripcion,
            tipo_archivo=TIPO_DOCUMENTO_A_ARCHIVO.get(doc.tipo_documento, 'OTRO'),
            archivo=doc.archivo,
            paciente_id=atencion.paciente_id,
            atencion_id=atencion.id,
            subido_por_id=doc.usuario_cargador_id,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('emr', '0001_initial'),
        ('archivos_medicos', '0006_archivomedico_atencion'),
    ]

    operations = [
        migrations.RunPython(migrar_documentos_emr_a_archivos, noop_reverse),
    ]
