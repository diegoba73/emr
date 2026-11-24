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
    class Tipo(models.TextChoices):
        ASISTENCIA = 'ASISTENCIA', 'Confirmar asistencia'
        CONFIRMAR_TURNO = 'CONFIRMAR_TURNO', 'Confirmar turno'
        ESTOY_EN_SALA = 'ESTOY_EN_SALA', 'Aviso estoy en sala (1 h)'

    turno = models.ForeignKey('turnos.Turno', on_delete=models.CASCADE)
    dispositivo = models.ForeignKey(DispositivoPush, on_delete=models.CASCADE)
    fecha_turno = models.DateTimeField()
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.ASISTENCIA,
    )
    estado = models.CharField(max_length=15, default='PENDIENTE', choices=[
        ('PENDIENTE', 'Pendiente'), ('ACEPTADO', 'Aceptado por Expo'),
        ('ENTREGADO', 'Aceptado por FCM/APNs'), ('ERROR', 'Error'), ('OMITIDO', 'Omitido')])
    intentos = models.PositiveSmallIntegerField(default=0)
    proximo_intento = models.DateTimeField()
    ticket = models.CharField(max_length=128, blank=True)
    error_codigo = models.CharField(max_length=80, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['turno', 'dispositivo', 'fecha_turno', 'tipo'],
                name='recordatorio_turno_dispositivo_fecha_tipo',
            )
        ]


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


class PagoReservaTurno(models.Model):
    """Andamiaje de cobro/garantía para reserva desde la app (cobro apagado por flag)."""

    class Tipo(models.TextChoices):
        CONSULTA = 'CONSULTA', 'Pago de consulta (particular)'
        GARANTIA_OS = 'GARANTIA_OS', 'Garantía de asistencia (obra social)'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'
        ANULADO = 'ANULADO', 'Anulado'

    class Medio(models.TextChoices):
        MERCADOPAGO = 'MERCADOPAGO', 'Mercado Pago'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'
        OTRO = 'OTRO', 'Otro'

    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='pagos_reserva_movil',
    )
    turno = models.ForeignKey(
        'turnos.Turno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos_reserva_movil',
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )
    medio = models.CharField(
        max_length=20,
        choices=Medio.choices,
        blank=True,
        default='',
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    referencia = models.CharField(max_length=120, blank=True, default='')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en', '-id']
        verbose_name = 'Pago reserva turno (móvil)'
        verbose_name_plural = 'Pagos reserva turno (móvil)'

    def __str__(self):
        return f'{self.tipo} {self.estado} paciente={self.paciente_id}'
