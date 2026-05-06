"""
Vistas de la app core.
Incluye endpoints de diagnóstico y health check.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status


class HealthCheckView(APIView):
    """
    Endpoint de health check para diagnóstico de conectividad.
    
    Permite verificar que el backend Django está funcionando correctamente
    sin requerir autenticación.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Retorna el estado del servicio.
        
        Returns:
            Response: JSON con status "ok" y nombre del servicio
        """
        return Response(
            {
                "status": "ok",
                "service": "EMR-API"
            },
            status=status.HTTP_200_OK
        )









