"""Consultas pasadas para la app: resumen seguro, sin notas clínicas."""

from __future__ import annotations

from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from pacientes.services import ensure_paciente_linked_to_user
from turnos.models import Atencion
from usuarios.roles import normalize_rol

from .authentication import AutenticacionMovil, RolMovil


def _rol(user) -> str:
    return normalize_rol(user)


class ConsultasMovil(APIView):
    """
    Paciente: solo sus atenciones FINALIZADAS (fecha, médico, tipo).
    No expone observaciones ni diagnósticos cargados por el médico.
    Médico: no usa este listado (trabaja en EMR web); 403.
    """

    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def get(self, request):
        rol = _rol(request.user)
        if rol != 'paciente':
            raise PermissionDenied(
                'Las consultas clínicas pasadas en la app son solo para el paciente. '
                'El médico las consulta en el EMR.'
            )
        paciente = ensure_paciente_linked_to_user(request.user)
        if not paciente:
            return Response({'results': []})

        qs = (
            Atencion.objects.filter(
                paciente=paciente,
                estado_clinico=Atencion.EstadoClinico.FINALIZADA,
            )
            .select_related('medico_principal')
            .order_by('-fecha_cierre', '-fecha_admision', '-id')[:100]
        )
        results = []
        for a in qs:
            medico = a.medico_principal
            medico_nombre = ''
            if medico:
                medico_nombre = (
                    getattr(medico, 'nombre_completo', None)
                    or f'{medico.apellido or ""}, {medico.nombre or ""}'.strip(', ')
                )
            fecha = a.fecha_cierre or a.fecha_admision
            results.append(
                {
                    'id': a.pk,
                    'fecha': fecha.isoformat() if fecha else None,
                    'medico_nombre': medico_nombre,
                    'tipo_intervencion': a.tipo_intervencion,
                    'tipo_intervencion_display': a.get_tipo_intervencion_display(),
                    'contexto_atencion': a.contexto_atencion,
                    'contexto_display': a.get_contexto_atencion_display(),
                    'estado_clinico': a.estado_clinico,
                }
            )
        return Response({'results': results})
