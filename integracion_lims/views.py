from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests
import json

@api_view(['POST'])
def recibir_resultados_lims(request):
    """Endpoint para recibir webhooks de resultados desde el LIMS."""
    # Aquí iría la lógica para procesar el JSON del LIMS
    # y crear o actualizar un ResultadoExamenLims
    data = request.data
    print(f"Recibido webhook de LIMS con datos: {data}")

    return Response({"status": "recibido"}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([])  # Permitir acceso sin autenticación para integración
@csrf_exempt
def obtener_analisis_paciente(request, paciente_id):
    """Obtener todos los análisis de laboratorio de un paciente específico desde el LIMS."""
    try:
        # Hacer petición al LIMS para obtener solicitudes del paciente
        lims_url = f"http://localhost:8001/api/laboratorio/solicitudes/?paciente_id={paciente_id}"
        
        response = requests.get(lims_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Procesar los datos para incluir información detallada
        analisis_procesados = []
        for solicitud in data.get('results', data):
            # Extraer información de paneles
            paneles_info = []
            for panel in solicitud.get('paneles_detalle', []):
                paneles_info.append(f"{panel.get('codigo', '')} - {panel.get('nombre', '')}")
            
            # Extraer información de exámenes individuales  
            examenes_info = []
            for examen in solicitud.get('tipos_examen_detalle', []):
                examenes_info.append(f"{examen.get('codigo', '')} - {examen.get('nombre', '')}")
            
            # Combinar toda la información de estudios
            estudios_realizados = []
            if paneles_info:
                estudios_realizados.extend([f"📋 {panel}" for panel in paneles_info])
            if examenes_info:
                estudios_realizados.extend([f"🔬 {examen}" for examen in examenes_info])
            
            analisis_procesados.append({
                'id': solicitud.get('id'),
                'numero': solicitud.get('numero'),
                'fecha_solicitud': solicitud.get('fecha_solicitud'),
                'estado': solicitud.get('estado', 'PENDIENTE'),
                'medico_nombre': solicitud.get('medico_nombre', 'N/A'),
                'observaciones': solicitud.get('observaciones', 'Sin observaciones'),
                'prioridad': solicitud.get('prioridad', 'NORMAL'),
                'estudios_realizados': ', '.join(estudios_realizados) if estudios_realizados else 'Sin estudios especificados',
                'paneles_detalle': solicitud.get('paneles_detalle', []),
                'tipos_examen_detalle': solicitud.get('tipos_examen_detalle', []),
                'tiene_resultados': solicitud.get('estado') in ['COMPLETADA', 'PARCIAL_COMPLETADA']
            })
        
        return Response({
            'paciente_id': paciente_id,
            'total_analisis': len(analisis_procesados),
            'analisis': analisis_procesados
        })
        
    except requests.exceptions.RequestException as e:
        # Devolver 200 con mensaje informativo en lugar de 502 para evitar errores en consola
        # cuando el LIMS no está disponible (situación esperada si no está corriendo)
        return Response({
            'paciente_id': paciente_id,
            'total_analisis': 0,
            'analisis': [],
            'lims_disponible': False,
            'mensaje': 'El servidor LIMS no está disponible en este momento'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)