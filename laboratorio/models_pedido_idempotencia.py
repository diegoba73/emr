"""Idempotencia de POST /api/lab/pedidos-completos/."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class PedidoCompletoIdempotencia(models.Model):
    """Conserva la respuesta del primer éxito por Idempotency-Key + hash de payload."""

    key = models.CharField(max_length=128, unique=True, db_index=True)
    payload_hash = models.CharField(max_length=64)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    response_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Idempotencia pedido completo"
        verbose_name_plural = "Idempotencias pedido completo"

    def __str__(self) -> str:
        return f"{self.key} ({self.payload_hash[:8]})"
