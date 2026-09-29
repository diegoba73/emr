from django.conf import settings
from django.db import models


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
