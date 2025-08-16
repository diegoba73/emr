from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from historias_clinicas.models import Consulta, Paciente # Asegúrate de importar Paciente
from django.db.models import Q # Para búsquedas más complejas si es necesario

class ConsultaPorPacienteAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '')
        paciente_id_str = request.GET.get('paciente_id')

        results = []

        if not paciente_id_str:
            return JsonResponse({'results': [], 'error': 'Paciente ID no proporcionado'})

        try:
            paciente_id = int(paciente_id_str)
            # Asumiendo que tienes un modelo Paciente y Consulta.historia_clinica.paciente es la relación
            qs = Consulta.objects.filter(historia_clinica__paciente_id=paciente_id)

            if term:
                # Adapta este filtro según los campos de Consulta que quieras buscar
                qs = qs.filter(
                    Q(motivo_consulta_detalle__icontains=term) |
                    Q(diagnostico_presuntivo__icontains=term) |
                    Q(medico__nombre__icontains=term) | # Ejemplo: buscar por nombre del médico
                    Q(medico__apellido__icontains=term) # Ejemplo: buscar por apellido del médico
                )

            # Limita el número de resultados
            for item in qs.distinct()[:10]: 
                results.append({
                    'id': item.pk,
                    # Asegúrate que tu modelo Consulta tenga un __str__ útil
                    'text': str(item) 
                })
        except ValueError:
            return JsonResponse({'results': [], 'error': 'Paciente ID inválido'})
        except Paciente.DoesNotExist: # Si Paciente.objects.get(pk=paciente_id) fuera usado
            return JsonResponse({'results': [], 'error': 'Paciente no encontrado'})


        return JsonResponse({'results': results})