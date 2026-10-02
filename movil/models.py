from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

CONTEXTO_LAB_CHOICES = [
    ('GUARDIA', 'Guardia'),
    ('AMBULATORIO', 'Ambulatorio'),
    ('INTERNACION', 'Internación'),
]


class SesionMovil(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    revocada = models.BooleanField(default=False)


class DispositivoPush(models.Model):
    sesion = models.ForeignKey(SesionMovil, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    plataforma = models.CharField(max_length=10, choices=[('android', 'Android'), ('ios', 'iOS')])
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)


class RecordatorioTurno(models.Model):
    turno = models.ForeignKey('turnos.Turno', on_delete=models.CASCADE)
    dispositivo = models.ForeignKey(DispositivoPush, on_delete=models.CASCADE)
    fecha_turno = models.DateTimeField()
    estado = models.CharField(max_length=15, default='PENDIENTE', choices=[
        ('PENDIENTE', 'Pendiente'), ('ACEPTADO', 'Aceptado por Expo'),
        ('ENTREGADO', 'Aceptado por FCM/APNs'), ('ERROR', 'Error'), ('OMITIDO', 'Omitido')])
    intentos = models.PositiveSmallIntegerField(default=0)
    proximo_intento = models.DateTimeField()
    ticket = models.CharField(max_length=128, blank=True)
    error_codigo = models.CharField(max_length=80, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['turno', 'dispositivo', 'fecha_turno'], name='recordatorio_turno_dispositivo_fecha')]


class PaqueteLabContexto(models.Model):
    """Paquetes de pedidos LIMS por contexto clínico (configurables en admin)."""

    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120)
    contexto = models.CharField(max_length=20, choices=CONTEXTO_LAB_CHOICES, db_index=True)
    descripcion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    paneles = models.ManyToManyField(
        'laboratorio.PanelExamen',
        blank=True,
        related_name='paquetes_lab_movil',
    )
    examenes = models.ManyToManyField(
        'laboratorio.TipoExamen',
        blank=True,
        related_name='paquetes_lab_movil',
    )

    class Meta:
        ordering = ['contexto', 'orden', 'nombre']
        verbose_name = 'Paquete lab móvil'
        verbose_name_plural = 'Paquetes lab móvil'

    def __str__(self):
        return f'{self.contexto}: {self.nombre}'


class FavoritoLabMedico(models.Model):
    """Favoritos de paneles/exámenes por médico para pedidos desde la app."""

    medico = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.CASCADE,
        related_name='favoritos_lab_movil',
    )
    tipo_examen = models.ForeignKey(
        'laboratorio.TipoExamen',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='favoritos_lab_movil',
    )
    panel = models.ForeignKey(
        'laboratorio.PanelExamen',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='favoritos_lab_movil',
    )
    orden = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['medico', 'tipo_examen'],
                condition=models.Q(tipo_examen__isnull=False),
                name='favorito_lab_medico_examen_uniq',
            ),
            models.UniqueConstraint(
                fields=['medico', 'panel'],
                condition=models.Q(panel__isnull=False),
                name='favorito_lab_medico_panel_uniq',
            ),
        ]
        verbose_name = 'Favorito lab médico'
        verbose_name_plural = 'Favoritos lab médico'

    def clean(self):
        tiene_examen = self.tipo_examen_id is not None
        tiene_panel = self.panel_id is not None
        if tiene_examen == tiene_panel:
            raise ValidationError('Indicá exactamente un examen o un panel.')

    def __str__(self):
        dest = self.panel or self.tipo_examen
        return f'{self.medico_id}: {dest}'
