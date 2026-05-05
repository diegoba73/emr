from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .permissions import (
    IsSecretariaOrAdmin,
    IsMedicoOrAdmin,
    IsPacienteOrStaff,
    CanManageTurnos,
    IsMedicoOrSecretariaOrAdmin,
    IsEMRClinicianOrReadOnly,
    IsEMRClinician,
    IsMedicoOrEnfermeriaOrAdmin,
)
from django.db.models import Count, Q
from django.utils import timezone
from django.http import Http404
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
import logging
from usuarios.models import UserProfile

logger = logging.getLogger(__name__)

from .serializers import (
    PacienteSerializer, MedicoSerializer, EspecialidadSerializer,
    DisponibilidadMedicoSerializer, ExcepcionMedicoSerializer,
    # TipoExamenSerializer, PanelExamenSerializer, SolicitudExamenSerializer,
    # ResultadoExamenSerializer, 
    ConsultaSerializer, ConsultaCreateSerializer, DiagnosticoSerializer,
    PrescripcionSerializer, MedicamentoSerializer, DashboardStatsSerializer,
    PacienteSearchSerializer, MedicoSearchSerializer, ConsultaSearchSerializer, TurnoSerializer,
    TurnoCreateUpdateSerializer, InternacionSerializer, DiagnosticoCIE10Serializer,
    RecursoSerializer, AtencionSerializer, AtencionCreateSerializer,
    ConsultaAmbulatoriaSerializer, RegistroProcedimientoSerializer,
    RegistroQuirurgicoSerializer, EstudioDiagnosticoSerializer,
    ProcedimientoCatalogoSerializer, DocumentoSerializer,
    SignosVitalesSerializer, AtencionUpdateSerializer
)

from pacientes.models import Paciente
from medicos.models import Medico, Especialidad, DisponibilidadMedico, ExcepcionMedico
# from laboratorio.models import TipoExamen, PanelExamen, SolicitudExamen, ResultadoExamen
from historias_clinicas.models import Consulta, Diagnostico, Prescripcion, HistoriaClinica, Internacion
from catalogos.models import Medicamento, DiagnosticoCIE10
from turnos.models import Turno, Recurso, Atencion, ConsultaAmbulatoria, RegistroProcedimiento, RegistroQuirurgico
from turnos.services import AtencionService, BusinessLogicError, resolve_tipo_intervencion_from_recurso
from catalogos.models import EstudioDiagnostico, ProcedimientoCatalogo
from emr.models import Documento, SignosVitales


# La función resolve_tipo_intervencion_from_recurso fue movida a turnos/services.py
# para evitar importaciones circulares. Se importa desde allí (línea 50).
class DisponibilidadMedicoViewSet(viewsets.ModelViewSet):
    queryset = DisponibilidadMedico.objects.select_related('medico').all()
    serializer_class = DisponibilidadMedicoSerializer
    permission_classes = [IsMedicoOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if hasattr(user, 'medico') and not user.is_superuser and str(getattr(user, 'rol', '')).lower() == 'medico':
            return qs.filter(medico=user.medico)
        return qs


class ExcepcionMedicoViewSet(viewsets.ModelViewSet):
    queryset = ExcepcionMedico.objects.select_related('medico').all()
    serializer_class = ExcepcionMedicoSerializer
    permission_classes = [IsMedicoOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if hasattr(user, 'medico') and not user.is_superuser and str(getattr(user, 'rol', '')).lower() == 'medico':
            return qs.filter(medico=user.medico)
        return qs


class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    permission_classes = [IsAuthenticated]  # Usuarios autenticados pueden acceder
    
    def get_permissions(self):
        """
        Instanciar y retornar la lista de permisos que requiere esta vista.
        Para actualizaciones, usar permisos personalizados que permitan a médicos
        actualizar datos demográficos de cualquier paciente.
        """
        if self.action in ['update', 'partial_update']:
            from .permissions import CanUpdatePacienteDemographics
            return [CanUpdatePacienteDemographics()]
        return [permission() for permission in self.permission_classes]
    
    def get_queryset(self):
        """
        Filtrar pacientes según el rol del usuario con soporte para búsqueda eficiente:
        - ADMIN/SECRETARIA/ENFERMERIA: ven todos los pacientes
        - MEDICO: ven solo pacientes que han tenido consultas con ellos (o todos si ?all=true)
        - PACIENTE: ven solo su propio perfil
        
        Parámetros de query:
        - search: texto de búsqueda (mínimo 2 caracteres) - busca en nombre, apellido, DNI
        - all: para médicos, permite ver todos los pacientes (solo en contextos explícitos)
        - Límite automático: 20 resultados cuando hay búsqueda
        """
        queryset = Paciente.objects.select_related('user').all()
        user = self.request.user
        
        # Normalizar rol a minúsculas para comparación
        user_rol = (user.rol or '').lower()
        
        # Aplicar búsqueda si existe (mínimo 2 caracteres)
        search = self.request.query_params.get('search', '').strip()
        if search and len(search) >= 2:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(dni__icontains=search)
            )
        
        # Aplicar filtros por rol según DOC_REGLAS_NEGOCIO.md
        # Admin, Secretaria y Enfermería ven todos los pacientes
        if user_rol in ['admin', 'secretaria', 'enfermeria'] or user.is_superuser:
            # No aplicar filtros adicionales, ya se aplicó búsqueda si existe
            pass
        
        # Médico: si viene el parámetro ?all=true, ver todos. Sino, solo pacientes con turnos/consultas
        elif user_rol == 'medico':
            # Verificar si se solicita ver todos (para modales de turnos)
            all_patients = self.request.query_params.get('all', 'false').lower() == 'true'
            
            if not all_patients:
                # Filtrado normal: solo pacientes con turnos o consultas con este médico
                try:
                    medico = user.medico
                    
                    # Obtener IDs de pacientes que tienen turnos con este médico
                    pacientes_con_turnos = Turno.objects.filter(
                        medico=medico
                    ).exclude(paciente__isnull=True).values_list('paciente_id', flat=True).distinct()
                    
                    # Obtener IDs de pacientes que han tenido consultas con este médico
                    pacientes_con_consultas = Consulta.objects.filter(
                        medico=medico
                    ).exclude(historia_clinica__paciente__isnull=True).values_list('historia_clinica__paciente_id', flat=True).distinct()
                    
                    # Combinar ambas listas (turnos y consultas)
                    pacientes_ids = set(list(pacientes_con_turnos) + list(pacientes_con_consultas))
                    
                    if pacientes_ids:
                        queryset = queryset.filter(id__in=pacientes_ids)
                    else:
                        queryset = queryset.none()
                except Exception as e:
                    queryset = queryset.none()
        
        # Paciente ve solo su propio perfil
        elif user_rol == 'paciente':
            try:
                queryset = queryset.filter(user=user)
            except Exception as e:
                logger.exception("Error filtrando PacienteViewSet por paciente: %s", e)
                queryset = queryset.none()
        else:
            queryset = queryset.none()
        
        # Aplicar límite de 20 resultados cuando hay búsqueda (optimización de performance)
        if search and len(search) >= 2:
            queryset = queryset[:20]
        
        return queryset
    
    def get_object(self):
        """
        Sobrescribir get_object para permitir que los médicos puedan actualizar
        pacientes que no están en su queryset filtrado, pero que tienen permisos
        según perform_update.
        """
        # Para operaciones de actualización, usar el queryset completo
        # y dejar que perform_update valide los permisos
        if self.request.method in ['PUT', 'PATCH']:
            # Obtener el ID del objeto desde la URL (por defecto es 'pk')
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            lookup_value = self.kwargs.get(lookup_url_kwarg)
            
            if lookup_value is None:
                raise Http404('No se encontró el ID del paciente en la URL.')
            
            # Usar el queryset base sin filtros para obtener el objeto
            try:
                obj = Paciente.objects.get(pk=lookup_value)
            except Paciente.DoesNotExist:
                raise Http404('No se encontró el paciente con el ID especificado.')
            
            # NO verificar permisos aquí - dejar que perform_update lo haga
            # Esto evita el 403 cuando el paciente no está en el queryset filtrado
            # pero tiene permisos según perform_update
            return obj
        
        # Para otras operaciones (GET, DELETE), usar el queryset filtrado normal
        return super().get_object()
    
    def check_object_permissions(self, request, obj):
        """
        Sobrescribir check_object_permissions para permitir que perform_update
        maneje los permisos en lugar de bloquear aquí.
        Solo verificar permisos para operaciones que NO sean PUT/PATCH.
        """
        # Para operaciones de actualización, no verificar permisos aquí
        # Dejar que perform_update lo haga
        if request.method in ['PUT', 'PATCH']:
            return
        
        # Para otras operaciones (GET, DELETE), verificar permisos normalmente
        super().check_object_permissions(request, obj)
    
    def update(self, request, *args, **kwargs):
        """
        Sobrescribir update para manejar permisos correctamente.
        No verificar permisos en get_object, dejar que perform_update lo haga.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_update(serializer)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response(getattr(e, 'detail', {'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error interno actualizando paciente: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    def perform_update(self, serializer):
        """
        Restricciones para actualizar pacientes (datos demográficos):
        - ADMIN/SECRETARIA: pueden actualizar cualquier paciente
        - MEDICO: pueden actualizar datos demográficos de CUALQUIER paciente
                  (necesario para actualizar información antes de la primera consulta)
        - PACIENTE: solo pueden actualizar su propio perfil
        """
        user = self.request.user
        paciente = serializer.instance
        
        # Admin y Secretaria pueden actualizar cualquier paciente
        if user.rol in ['admin', 'secretaria'] or user.is_superuser:
            serializer.save()
            return
        
        # Médico puede actualizar datos demográficos de CUALQUIER paciente
        # Esto permite actualizar información antes de la primera consulta
        if user.rol == 'medico':
            serializer.save()
            return
        
        # Paciente solo puede actualizar su propio perfil
        elif user.rol == 'paciente':
            try:
                if paciente.user == user:
                    serializer.save()
                else:
                    raise PermissionDenied("Solo puede actualizar su propio perfil")
            except Exception as e:
                raise ValidationError({'error': f'No se pudo actualizar el paciente: {str(e)}'})
        
        else:
            raise PermissionDenied("No tiene permisos para actualizar pacientes")
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Búsqueda rápida y eficiente de pacientes por apellido o DNI.
        - Si la búsqueda contiene solo números: busca en DNI
        - Si la búsqueda contiene letras: busca en apellido
        Busca en TODOS los registros disponibles según permisos del usuario.
        Prioriza coincidencias exactas y que empiezan con el término.
        Límite aumentado a 200 para búsquedas más completas."""
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})
        
        # Obtener queryset base con permisos aplicados
        queryset = self.get_queryset()
        
        # Determinar si la búsqueda es numérica o alfanumérica
        es_numerica = query.isdigit()
        
        # Normalizar query para búsqueda
        query_upper = query.upper()
        
        # Búsqueda según el tipo de query
        if es_numerica:
            # Búsqueda numérica: solo en DNI
            pacientes_todos = queryset.filter(
                Q(dni__exact=query) |        # DNI exacto (más relevante)
                Q(dni__startswith=query)      # DNI que empieza con el término
            ).distinct()
        else:
            # Búsqueda alfanumérica: solo en apellido
            pacientes_todos = queryset.filter(
                Q(apellido__istartswith=query) |  # Apellidos que empiezan con el término (más relevante)
                Q(apellido__icontains=query)     # Apellidos que contienen el término
            ).distinct()
        
        # Clasificar por relevancia usando un diccionario para evitar duplicados
        pacientes_por_id = {}  # id -> (prioridad, paciente)
        
        for paciente in pacientes_todos:
            paciente_id = paciente.id
            # Si ya está en el diccionario, mantener la prioridad más alta
            if paciente_id in pacientes_por_id:
                prioridad_actual, _ = pacientes_por_id[paciente_id]
            else:
                prioridad_actual = 999
            
            if es_numerica:
                # Búsqueda numérica: priorizar DNI exacto, luego DNI que empieza
                dni = (paciente.dni or '').strip()
                if dni == query:
                    nueva_prioridad = 1  # DNI exacto
                elif dni.startswith(query):
                    nueva_prioridad = 2  # DNI que empieza con el término
                else:
                    nueva_prioridad = 999
            else:
                # Búsqueda alfanumérica: priorizar apellido exacto, luego que empieza, luego contiene
                apellido_upper = (paciente.apellido or '').upper().strip()
                if apellido_upper == query_upper:
                    nueva_prioridad = 1  # Apellido exacto
                elif apellido_upper.startswith(query_upper):
                    nueva_prioridad = 2  # Apellido que empieza con el término
                elif query_upper in apellido_upper:
                    nueva_prioridad = 3  # Apellido contiene el término
                else:
                    nueva_prioridad = 999
            
            # Solo actualizar si la nueva prioridad es mejor (menor)
            if nueva_prioridad < prioridad_actual:
                pacientes_por_id[paciente_id] = (nueva_prioridad, paciente)
            elif paciente_id not in pacientes_por_id:
                pacientes_por_id[paciente_id] = (nueva_prioridad, paciente)
        
        # Convertir a lista y ordenar por prioridad, luego por apellido, nombre
        pacientes_lista = list(pacientes_por_id.values())
        pacientes_lista.sort(key=lambda x: (
            x[0],  # Prioridad
            (x[1].apellido or '').upper(),  # Apellido
            (x[1].nombre or '').upper()  # Nombre
        ))
        
        # Extraer solo los pacientes y limitar
        pacientes_finales = [p for _, p in pacientes_lista][:200]
        
        serializer = PacienteSearchSerializer(pacientes_finales, many=True)
        return Response({'results': serializer.data})


class MedicoViewSet(viewsets.ModelViewSet):
    """ViewSet para médicos - solo admin puede editar"""
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer
    permission_classes = [IsAuthenticated]  # Todos pueden ver, pero solo admin puede editar
    pagination_class = None  # Deshabilitar paginación - SIEMPRE cargar TODOS los médicos
    
    def get_permissions(self):
        """Solo admin puede crear/editar/eliminar médicos"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from .permissions import IsSecretariaOrAdmin
            return [IsSecretariaOrAdmin()]
        return [permission() for permission in self.permission_classes]
    
    def get_queryset(self):
        """
        Filtrar médicos según el rol del usuario:
        - ADMIN: ven todos los médicos
        - SECRETARIA: ven todos los médicos (para asignar turnos)
        - MEDICO: ven solo su propio perfil
        - PACIENTE: ven todos los médicos (para elegir en turnos)
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Normalizar rol a minúsculas para comparación
        user_rol = (user.rol or '').lower()
        
        # Debug logging
        print(f"🔍 MedicoViewSet - Usuario: {user.username}, Rol original: '{user.rol}', Rol normalizado: '{user_rol}', is_superuser: {user.is_superuser}")
        print(f"📊 Total médicos en BD: {queryset.count()}")
        
        # Admin, Secretaria y Enfermería ven todos los médicos
        if user_rol in ['admin', 'secretaria', 'enfermeria'] or user.is_superuser:
            print(f"✅ Usuario {user.username} tiene acceso a TODOS los médicos")
            return queryset
        
        # Médico ve solo su propio perfil
        if user_rol == 'medico':
            try:
                return queryset.filter(user=user)
            except Exception as e:
                logger.exception("Error filtrando MedicoViewSet por médico: %s", e)
                return queryset.none()
        
        # Paciente ve todos los médicos (para elegir en turnos)
        if user_rol == 'paciente':
            return queryset
        
        return queryset.none()

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Búsqueda rápida y eficiente de médicos por apellido o matrícula.
        - Si la búsqueda contiene solo números: busca en matrícula
        - Si la búsqueda contiene letras: busca en apellido
        Busca en TODOS los registros disponibles según permisos del usuario.
        Prioriza coincidencias exactas y que empiezan con el término.
        Límite aumentado a 200 para búsquedas más completas."""
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})

        # Obtener queryset base con permisos aplicados
        queryset = self.get_queryset()
        
        # Determinar si la búsqueda es numérica o alfanumérica
        es_numerica = query.isdigit()
        
        # Normalizar query para búsqueda
        query_upper = query.upper()
        
        # Búsqueda según el tipo de query
        if es_numerica:
            # Búsqueda numérica: solo en matrícula
            medicos_todos = queryset.select_related('especialidad').filter(
                Q(matricula__exact=query) |        # Matrícula exacta (más relevante)
                Q(matricula__startswith=query)      # Matrícula que empieza con el término
            ).distinct()
        else:
            # Búsqueda alfanumérica: solo en apellido
            medicos_todos = queryset.select_related('especialidad').filter(
                Q(apellido__istartswith=query) |  # Apellidos que empiezan con el término (más relevante)
                Q(apellido__icontains=query)      # Apellidos que contienen el término
            ).distinct()
        
        # Clasificar por relevancia usando un diccionario para evitar duplicados
        medicos_por_id = {}  # id -> (prioridad, medico)
        
        for medico in medicos_todos:
            medico_id = medico.id
            # Si ya está en el diccionario, mantener la prioridad más alta
            if medico_id in medicos_por_id:
                prioridad_actual, _ = medicos_por_id[medico_id]
            else:
                prioridad_actual = 999
            
            if es_numerica:
                # Búsqueda numérica: priorizar matrícula exacta, luego matrícula que empieza
                matricula = (medico.matricula or '').strip()
                if matricula == query:
                    nueva_prioridad = 1  # Matrícula exacta
                elif matricula.startswith(query):
                    nueva_prioridad = 2  # Matrícula que empieza con el término
                else:
                    nueva_prioridad = 999
            else:
                # Búsqueda alfanumérica: priorizar apellido exacto, luego que empieza, luego contiene
                apellido_upper = (medico.apellido or '').upper().strip()
                if apellido_upper == query_upper:
                    nueva_prioridad = 1  # Apellido exacto
                elif apellido_upper.startswith(query_upper):
                    nueva_prioridad = 2  # Apellido que empieza con el término
                elif query_upper in apellido_upper:
                    nueva_prioridad = 3  # Apellido contiene el término
                else:
                    nueva_prioridad = 999
            
            # Solo actualizar si la nueva prioridad es mejor (menor)
            if nueva_prioridad < prioridad_actual:
                medicos_por_id[medico_id] = (nueva_prioridad, medico)
            elif medico_id not in medicos_por_id:
                medicos_por_id[medico_id] = (nueva_prioridad, medico)
        
        # Convertir a lista y ordenar por prioridad, luego por apellido, nombre
        medicos_lista = list(medicos_por_id.values())
        medicos_lista.sort(key=lambda x: (
            x[0],  # Prioridad
            (x[1].apellido or '').upper(),  # Apellido
            (x[1].nombre or '').upper()  # Nombre
        ))
        
        # Extraer solo los médicos y limitar
        medicos_finales = [m for _, m in medicos_lista][:200]

        serializer = MedicoSearchSerializer(medicos_finales, many=True)
        return Response({'results': serializer.data})

    @action(detail=True, methods=['get'])
    def slots(self, request, pk=None):
        """Devolver slots disponibles para un médico y una fecha (YYYY-MM-DD)."""
        try:
            medico = self.get_object()
        except Exception:
            return Response({'error': 'Médico no encontrado'}, status=404)
        fecha_str = request.query_params.get('fecha')
        if not fecha_str:
            return Response({'error': 'Parámetro fecha requerido (YYYY-MM-DD)'}, status=400)
        try:
            target_date = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Formato de fecha inválido'}, status=400)

        day_of_week = target_date.weekday()
        disponibilidades = DisponibilidadMedico.objects.filter(medico=medico, activo=True, dia_semana=day_of_week).order_by('hora_inicio')
        excepciones = ExcepcionMedico.objects.filter(medico=medico, fecha=target_date)
        # Turnos existentes del día
        turnos_ocupados = Turno.objects.filter(medico=medico, fecha_hora_inicio__date=target_date)

        # Asegurar comparaciones entre datetimes conscientes de zona horaria
        tz = timezone.get_current_timezone()

        def overlaps(start_a, end_a, start_b, end_b):
            return start_a < end_b and start_b < end_a

        slots = []
        for disp in disponibilidades:
            slot_len = max(5, disp.duracion_slot_min)
            current_dt = timezone.make_aware(datetime.combine(target_date, disp.hora_inicio), tz)
            end_dt = timezone.make_aware(datetime.combine(target_date, disp.hora_fin), tz)
            while current_dt + timedelta(minutes=slot_len) <= end_dt:
                slot_start = current_dt
                slot_end = current_dt + timedelta(minutes=slot_len)
                # Excepciones
                blocked = False
                for ex in excepciones:
                    if ex.tipo == 'BLOQUEO':
                        blocked = True
                        break
                    if ex.tipo == 'AJUSTE' and ex.hora_inicio and ex.hora_fin:
                        ex_start = timezone.make_aware(datetime.combine(target_date, ex.hora_inicio), tz)
                        ex_end = timezone.make_aware(datetime.combine(target_date, ex.hora_fin), tz)
                        if overlaps(slot_start, slot_end, ex_start, ex_end):
                            blocked = True
                            break
                if blocked:
                    current_dt += timedelta(minutes=slot_len)
                    continue
                # Turnos ocupados (cualquier estado distinto de CANCELADO bloquea)
                ocupado = False
                for t in turnos_ocupados:
                    t_start = timezone.localtime(t.fecha_hora_inicio, tz)
                    t_end = timezone.localtime(t.fecha_hora_fin, tz) if t.fecha_hora_fin else (t_start + timedelta(minutes=slot_len))
                    if t.estado != 'CANCELADO' and overlaps(slot_start, slot_end, t_start, t_end):
                        ocupado = True
                        break
                if not ocupado:
                    slots.append({
                        'inicio': slot_start.strftime('%Y-%m-%dT%H:%M:%S'),
                        'fin': slot_end.strftime('%Y-%m-%dT%H:%M:%S'),
                        'duracion_min': slot_len,
                    })
                current_dt += timedelta(minutes=slot_len)

        return Response({'fecha': fecha_str, 'medico_id': medico.id, 'slots': slots})


class EspecialidadViewSet(viewsets.ModelViewSet):
    """ViewSet para especialidades - médicos, enfermería y admin pueden editar"""
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [IsMedicoOrEnfermeriaOrAdmin]  # Médicos, enfermería y admin pueden editar
    pagination_class = None  # Deshabilitar paginación - SIEMPRE cargar TODAS las especialidades


# class TipoExamenViewSet(viewsets.ModelViewSet):
#     queryset = TipoExamen.objects.filter(activo=True)
#     serializer_class = TipoExamenSerializer
#     permission_classes = [IsAuthenticated]


# class PanelExamenViewSet(viewsets.ModelViewSet):
#     queryset = PanelExamen.objects.filter(activo=True)
#     serializer_class = PanelExamenSerializer
#     permission_classes = [IsAuthenticated]


# class SolicitudExamenViewSet(viewsets.ModelViewSet):
#     queryset = SolicitudExamen.objects.all()
#     serializer_class = SolicitudExamenSerializer
#     permission_classes = [IsSecretariaOrAdmin]  # Solo secretarias y admins pueden gestionar solicitudes
    
#     @action(detail=False, methods=['get'])
#     def estadisticas(self, request):
#         """Estadísticas de solicitudes de laboratorio"""
#         hoy = timezone.now().date()
        
#         stats = {
#             'pendientes': SolicitudExamen.objects.filter(estado='PENDIENTE').count(),
#             'en_proceso': SolicitudExamen.objects.filter(estado='EN_PROCESO').count(),
#             'completadas_hoy': SolicitudExamen.objects.filter(
#                 estado='COMPLETADO',
#                 fecha_solicitud__date=hoy
#             ).count(),
#             'total_hoy': SolicitudExamen.objects.filter(fecha_solicitud__date=hoy).count(),
#         }
        
#         return Response(stats)
    
#     @action(detail=True, methods=['post'])
#     def cambiar_estado(self, request, pk=None):
#         """Cambiar el estado de una solicitud"""
#         solicitud = self.get_object()
#         nuevo_estado = request.data.get('estado')
        
#         if nuevo_estado in ['PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'CANCELADO']:
#             solicitud.estado = nuevo_estado
#             solicitud.save()
#             serializer = self.get_serializer(solicitud)
#             return Response(serializer.data)
        
#         return Response(
#             {'error': 'Estado inválido'}, 
#             status=status.HTTP_400_BAD_REQUEST
#         )


# class ResultadoExamenViewSet(viewsets.ModelViewSet):
#     queryset = ResultadoExamen.objects.all()
#     serializer_class = ResultadoExamenSerializer
#     permission_classes = [IsAuthenticated]
    
#     @action(detail=False, methods=['get'])
#     def por_solicitud(self, request):
#         """Obtener resultados por solicitud"""
#         solicitud_id = request.query_params.get('solicitud_id')
#         if solicitud_id:
#             resultados = ResultadoExamen.objects.filter(solicitud_id=solicitud_id)
#             serializer = self.get_serializer(resultados, many=True)
#             return Response(serializer.data)
#         return Response({'error': 'solicitud_id requerido'}, status=400)


class ConsultaViewSet(viewsets.ModelViewSet):
    queryset = Consulta.objects.all()
    serializer_class = ConsultaSerializer
    permission_classes = [IsMedicoOrSecretariaOrAdmin]  # Médicos, secretarias y admins pueden gestionar consultas
    
    def get_queryset(self):
        """
        Filtrar consultas según el rol del usuario con optimización de queries:
        - ADMIN: ven todas las consultas
        - SECRETARIA: ven todas las consultas
        - ENFERMERIA: ven todas las consultas
        - MEDICO: ven solo sus consultas (consultas donde es el médico)
        - PACIENTE: ven solo sus consultas (según DOC_REGLAS_NEGOCIO.md)
        
        Optimizaciones:
        - select_related para historia_clinica__paciente y medico (evita N+1 queries)
        - Ordenamiento por fecha descendente
        """
        # Optimizar queries con select_related para evitar N+1 queries
        queryset = Consulta.objects.select_related(
            'historia_clinica__paciente',
            'medico',
            'medico__especialidad',
            'turno'
        ).order_by('-fecha_hora_consulta')
        
        user = self.request.user
        
        # Normalizar rol a minúsculas
        user_rol = (user.rol or '').lower() if hasattr(user, 'rol') else ''
        
        # Admin, Secretaria y Enfermería ven todas las consultas
        if user_rol in ['admin', 'secretaria', 'enfermeria'] or user.is_superuser:
            return queryset
        
        # Médico ve solo sus consultas (donde es el médico responsable)
        if user_rol == 'medico':
            try:
                return queryset.filter(medico=user.medico)
            except Exception:
                return queryset.none()
        
        # Paciente ve solo sus consultas (según DOC_REGLAS_NEGOCIO.md)
        if user_rol == 'paciente':
            try:
                return queryset.filter(historia_clinica__paciente__user=user)
            except Exception:
                return queryset.none()
        
        # Otros roles no tienen acceso a consultas
        return queryset.none()
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """
        Búsqueda de consultas por paciente o texto.
        Usa el queryset optimizado de get_queryset() que ya incluye select_related.
        """
        paciente_id = request.query_params.get('paciente_id')
        query = request.query_params.get('q', '').strip()
        
        # Aplicar el mismo filtrado que get_queryset (ya optimizado con select_related)
        consultas = self.get_queryset()
        
        if paciente_id:
            try:
                consultas = consultas.filter(historia_clinica__paciente_id=int(paciente_id))
            except (ValueError, TypeError):
                return Response({'results': []})
        
        if query and len(query) >= 2:
            consultas = consultas.filter(
                Q(motivo_consulta_detalle__icontains=query) |
                Q(diagnostico_presuntivo__icontains=query) |
                Q(medico__nombre__icontains=query) |
                Q(medico__apellido__icontains=query) |
                Q(historia_clinica__paciente__nombre__icontains=query) |
                Q(historia_clinica__paciente__apellido__icontains=query) |
                Q(historia_clinica__paciente__dni__icontains=query)
            )
        
        # Limitar a 20 resultados para performance
        consultas = consultas[:20]
        serializer = ConsultaSearchSerializer(consultas, many=True)
        return Response({'results': serializer.data})


class DiagnosticoViewSet(viewsets.ModelViewSet):
    queryset = Diagnostico.objects.all()
    serializer_class = DiagnosticoSerializer
    permission_classes = [IsAuthenticated]


class DiagnosticoCIE10ViewSet(viewsets.ModelViewSet):
    """ViewSet para diagnósticos CIE-10 - médicos, enfermería y admin pueden editar"""
    queryset = DiagnosticoCIE10.objects.all()
    serializer_class = DiagnosticoCIE10Serializer
    permission_classes = [IsMedicoOrEnfermeriaOrAdmin]  # Médicos, enfermería y admin pueden editar
    pagination_class = None  # Deshabilitar paginación - SIEMPRE cargar TODOS los diagnósticos
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['capitulo', 'enfermedad', 'categoria', 'activo']
    search_fields = ['codigo', 'descripcion', 'enfermedad', 'capitulo']
    ordering_fields = ['codigo', 'descripcion']
    ordering = ['codigo']

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Búsqueda rápida y eficiente de diagnósticos CIE-10 por código o descripción.
        - Si la búsqueda contiene solo letras/números al inicio: busca en código
        - Si la búsqueda contiene letras: busca en descripción y enfermedad
        Prioriza coincidencias exactas y que empiezan con el término.
        Límite aumentado a 200 para búsquedas más completas."""
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})
        
        # Normalizar query para búsqueda
        query_upper = query.upper()
        query_lower = query.lower()
        
        # Determinar si la búsqueda parece ser un código (empieza con letras seguidas de números)
        es_codigo = bool(query and (query[0].isalpha() and any(c.isdigit() for c in query)))
        
        # Obtener queryset base (solo activos)
        queryset = DiagnosticoCIE10.objects.filter(activo=True)
        
        # Búsqueda según el tipo de query
        if es_codigo:
            # Búsqueda por código: priorizar código exacto, luego que empieza, luego contiene
            diagnosticos_todos = queryset.filter(
                Q(codigo__iexact=query) |           # Código exacto (más relevante)
                Q(codigo__istartswith=query) |      # Código que empieza con el término
                Q(codigo__icontains=query)          # Código que contiene el término
            ).distinct()
        else:
            # Búsqueda por descripción/enfermedad: priorizar que empieza, luego contiene
            diagnosticos_todos = queryset.filter(
                Q(descripcion__istartswith=query) |  # Descripción que empieza con el término (más relevante)
                Q(descripcion__icontains=query) |     # Descripción que contiene el término
                Q(enfermedad__istartswith=query) |   # Enfermedad que empieza con el término
                Q(enfermedad__icontains=query) |     # Enfermedad que contiene el término
                Q(codigo__icontains=query)           # También buscar en código como fallback
            ).distinct()
        
        # Clasificar por relevancia usando un diccionario para evitar duplicados
        diagnosticos_por_id = {}  # id -> (prioridad, diagnostico)
        
        for diagnostico in diagnosticos_todos:
            diagnostico_id = diagnostico.id
            # Si ya está en el diccionario, mantener la prioridad más alta
            if diagnostico_id in diagnosticos_por_id:
                prioridad_actual, _ = diagnosticos_por_id[diagnostico_id]
            else:
                prioridad_actual = 999
            
            if es_codigo:
                # Búsqueda por código: priorizar código exacto, luego que empieza, luego contiene
                codigo_upper = (diagnostico.codigo or '').upper().strip()
                if codigo_upper == query_upper:
                    nueva_prioridad = 1  # Código exacto
                elif codigo_upper.startswith(query_upper):
                    nueva_prioridad = 2  # Código que empieza con el término
                elif query_upper in codigo_upper:
                    nueva_prioridad = 3  # Código contiene el término
                else:
                    nueva_prioridad = 999
            else:
                # Búsqueda por descripción/enfermedad: priorizar que empieza, luego contiene
                descripcion_lower = (diagnostico.descripcion or '').lower().strip()
                enfermedad_lower = (diagnostico.enfermedad or '').lower().strip()
                codigo_upper = (diagnostico.codigo or '').upper().strip()
                
                if descripcion_lower.startswith(query_lower):
                    nueva_prioridad = 1  # Descripción que empieza con el término
                elif enfermedad_lower.startswith(query_lower):
                    nueva_prioridad = 2  # Enfermedad que empieza con el término
                elif query_lower in descripcion_lower:
                    nueva_prioridad = 3  # Descripción contiene el término
                elif query_lower in enfermedad_lower:
                    nueva_prioridad = 4  # Enfermedad contiene el término
                elif query_upper in codigo_upper:
                    nueva_prioridad = 5  # Código contiene el término (fallback)
                else:
                    nueva_prioridad = 999
            
            # Solo actualizar si la nueva prioridad es mejor (menor)
            if nueva_prioridad < prioridad_actual:
                diagnosticos_por_id[diagnostico_id] = (nueva_prioridad, diagnostico)
            elif diagnostico_id not in diagnosticos_por_id:
                diagnosticos_por_id[diagnostico_id] = (nueva_prioridad, diagnostico)
        
        # Convertir a lista y ordenar por prioridad, luego por código, descripción
        diagnosticos_lista = list(diagnosticos_por_id.values())
        diagnosticos_lista.sort(key=lambda x: (
            x[0],  # Prioridad
            (x[1].codigo or '').upper(),  # Código
            (x[1].descripcion or '').upper()  # Descripción
        ))
        
        # Extraer solo los diagnósticos y limitar
        diagnosticos_finales = [d for _, d in diagnosticos_lista][:200]
        
        serializer = self.get_serializer(diagnosticos_finales, many=True)
        return Response({'results': serializer.data})


class PrescripcionViewSet(viewsets.ModelViewSet):
    queryset = Prescripcion.objects.all()
    serializer_class = PrescripcionSerializer
    permission_classes = [IsAuthenticated]


class MedicamentoViewSet(viewsets.ModelViewSet):
    """ViewSet para medicamentos - médicos y admin pueden editar"""
    queryset = Medicamento.objects.all()
    serializer_class = MedicamentoSerializer
    permission_classes = [IsMedicoOrAdmin]  # Médicos y admin pueden editar
    pagination_class = None  # Deshabilitar paginación - SIEMPRE cargar TODOS los medicamentos
    
    def get_queryset(self):
        """Filtrar por activo si se solicita, o mostrar todos para admin"""
        queryset = super().get_queryset()
        if self.request.query_params.get('activo') == 'true':
            return queryset.filter(activo=True)
        return queryset
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Búsqueda de medicamentos"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'results': []})
        
        medicamentos = Medicamento.objects.filter(
            Q(nombre__icontains=query) |
            Q(principio_activo__icontains=query)
        )[:10]
        
        serializer = self.get_serializer(medicamentos, many=True)
        return Response({'results': serializer.data})


class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.select_related('paciente', 'medico', 'recurso').prefetch_related('atencion', 'atencion__consulta_ambulatoria', 'atencion__registro_procedimiento', 'atencion__registro_quirurgico')
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated]  # Usuarios autenticados pueden acceder
    
    def get_queryset(self):
        """
        Filtrar turnos según el rol del usuario:
        - ADMIN/SECRETARIA: ven todos los turnos
        - MEDICO: solo ven sus propios turnos
        - PACIENTE: solo ven sus propios turnos
        """
        # Asegurar que el queryset base mantenga las relaciones
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()
        
        # Admin y Secretaria ven todos los turnos
        if role in ['admin', 'secretaria'] or user.is_superuser:
            return queryset
        
        # Médico ve SOLO sus propios turnos
        if role == 'medico':
            try:
                medico = user.medico
                return queryset.filter(medico=medico)
            except Exception:
                return queryset.none()
        
        # Paciente ve solo sus turnos
        if role == 'paciente':
            try:
                paciente = user.paciente
                return queryset.filter(paciente=paciente)
            except Exception as e:
                logger.exception("Error filtrando TurnoViewSet por paciente: %s", e)
                return queryset.none()
        
        return queryset.none()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TurnoCreateUpdateSerializer
        return TurnoSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            # Recargar el turno con todas sus relaciones para asegurar que se serialicen correctamente
            instance = serializer.instance
            if instance:
                instance = (
                    Turno.objects
                    .select_related('paciente', 'medico', 'recurso')
                    .prefetch_related('atencion')
                    .get(pk=instance.pk)
                )
                # Usar TurnoSerializer para la respuesta (no TurnoCreateUpdateSerializer)
                response_serializer = TurnoSerializer(instance)
                headers = self.get_success_headers(response_serializer.data)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response(getattr(e, 'detail', {'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error interno creando turno: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_update(serializer)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response(getattr(e, 'detail', {'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error interno actualizando turno: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """
        Restricciones para crear turnos:
        - PACIENTE: solo puede crear turnos para sí mismo
        - MEDICO: puede crear turnos solo asociados a sí mismo como médico
        - ADMIN/SECRETARIA: pueden crear turnos para cualquier paciente
        """
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()
        
        # Validación de disponibilidad si hay médico y fecha definidos
        try:
            data = serializer.validated_data
            medico = data.get('medico')
            start = data.get('fecha_hora_inicio')
            end = data.get('fecha_hora_fin') or (start + timedelta(minutes=60)) if start else None
            # Normalizar awareness
            tz = timezone.get_current_timezone()
            if start and timezone.is_naive(start):
                start = timezone.make_aware(start, tz)
            if end and timezone.is_naive(end):
                end = timezone.make_aware(end, tz)
            if medico and start and end:
                start_local = timezone.localtime(start, tz)
                end_local = timezone.localtime(end, tz)
                # Chequear disponibilidad del día
                day_of_week = start_local.weekday()
                all_dispon = DisponibilidadMedico.objects.filter(medico=medico, activo=True)
                dispones = all_dispon.filter(dia_semana=day_of_week)
                # Si el médico tiene disponibilidades cargadas y el día no está entre ellas, rechazar
                if all_dispon.exists() and not dispones.exists():
                    raise PermissionDenied('El médico no atiende ese día')
                # Si hay disponibilidad para ese día, debe caer dentro de alguna franja horaria
                inside_any = any(
                    timezone.make_aware(datetime.combine(start_local.date(), d.hora_inicio), tz) <= start_local and
                    end_local <= timezone.make_aware(datetime.combine(start_local.date(), d.hora_fin), tz)
                    for d in dispones
                )
                if dispones.exists() and not inside_any:
                    raise PermissionDenied('Fuera del horario de atención del médico')
                # Excepciones
                excepciones = ExcepcionMedico.objects.filter(medico=medico, fecha=start_local.date())
                for ex in excepciones:
                    if ex.tipo == 'BLOQUEO':
                        raise PermissionDenied('El médico no atiende en esa fecha')
                    if ex.tipo == 'AJUSTE' and ex.hora_inicio and ex.hora_fin:
                        ex_start = timezone.make_aware(datetime.combine(start_local.date(), ex.hora_inicio), tz)
                        ex_end = timezone.make_aware(datetime.combine(start_local.date(), ex.hora_fin), tz)
                        if not (end_local <= ex_start or start_local >= ex_end):
                            raise PermissionDenied('Horario bloqueado por ajuste del médico')
                # Solapamiento con turnos existentes
                conflictos = Turno.objects.filter(medico=medico, fecha_hora_inicio__date=start_local.date()).exclude(estado='CANCELADO')
                for t in conflictos:
                    t_start = timezone.localtime(t.fecha_hora_inicio, tz)
                    t_end = timezone.localtime(t.fecha_hora_fin, tz) if t.fecha_hora_fin else (t_start + timedelta(minutes=60))
                    if not (end_local <= t_start or start_local >= t_end):
                        raise PermissionDenied('Solapa con otro turno del médico')
        except PermissionDenied:
            raise
        except Exception:
            # No bloquear si falta info o algún error inesperado
            pass

        # Guardar el turno según el rol del usuario
        try:
            if role == 'paciente' and hasattr(user, 'paciente'):
                serializer.save(paciente=user.paciente)
            elif role == 'medico' and hasattr(user, 'medico'):
                serializer.save(medico=user.medico)
            elif role in ['admin', 'secretaria'] or user.is_superuser:
                serializer.save()
            else:
                raise PermissionDenied("No tiene permisos para crear turnos")
        except PermissionDenied:
            raise
        except Exception as e:
            raise ValidationError({ 'error': f'No se pudo crear el turno: {str(e)}' })

    def perform_update(self, serializer):
        """
        Validaciones de disponibilidad, solapamiento y permisos al actualizar.
        También crea Atencion automáticamente cuando el estado cambia a CONFIRMADO o REALIZADO.
        """
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()
        turno_original = serializer.instance
        
        # Validaciones de permisos
        try:
            if role == 'paciente':
                if turno_original.paciente != user.paciente:
                    raise PermissionDenied("Solo puede actualizar sus propios turnos")
            elif role == 'medico':
                if turno_original.medico != user.medico:
                    raise PermissionDenied("No puede actualizar turnos de otros médicos")
            elif role not in ['admin', 'secretaria'] and not user.is_superuser:
                raise PermissionDenied("No tiene permisos para actualizar turnos")
        except PermissionDenied:
            raise
        except Exception:
            pass
        
        # Validaciones de disponibilidad y solapamiento
        try:
            data = serializer.validated_data
            medico = data.get('medico') or turno_original.medico
            start = data.get('fecha_hora_inicio') or turno_original.fecha_hora_inicio
            end = data.get('fecha_hora_fin') or turno_original.fecha_hora_fin or (start + timedelta(minutes=60))
            tz = timezone.get_current_timezone()
            if start and timezone.is_naive(start):
                start = timezone.make_aware(start, tz)
            if end and timezone.is_naive(end):
                end = timezone.make_aware(end, tz)
            if medico and start and end:
                start_local = timezone.localtime(start, tz)
                end_local = timezone.localtime(end, tz)
                day_of_week = start_local.weekday()
                all_dispon = DisponibilidadMedico.objects.filter(medico=medico, activo=True)
                dispones = all_dispon.filter(dia_semana=day_of_week)
                if all_dispon.exists() and not dispones.exists():
                    raise PermissionDenied('El médico no atiende ese día')
                inside_any = any(
                    timezone.make_aware(datetime.combine(start_local.date(), d.hora_inicio), tz) <= start_local and
                    end_local <= timezone.make_aware(datetime.combine(start_local.date(), d.hora_fin), tz)
                    for d in dispones
                )
                if dispones.exists() and not inside_any:
                    raise PermissionDenied('Fuera del horario de atención del médico')
                # Solapamiento
                conflictos = Turno.objects.filter(medico=medico, fecha_hora_inicio__date=start_local.date()).exclude(id=turno_original.id).exclude(estado='CANCELADO')
                for t in conflictos:
                    t_start = timezone.localtime(t.fecha_hora_inicio, tz)
                    t_end = timezone.localtime(t.fecha_hora_fin, tz) if t.fecha_hora_fin else (t_start + timedelta(minutes=60))
                    if not (end_local <= t_start or start_local >= t_end):
                        raise PermissionDenied('Solapa con otro turno del médico')
        except PermissionDenied:
            raise
        except Exception:
            pass

        # Guardar el turno
        estado_anterior = turno_original.estado
        recurso_anterior = turno_original.recurso
        turno = serializer.save()
        estado_nuevo = turno.estado
        recurso_nuevo = turno.recurso
        
        # Verificar si cambió el recurso
        recurso_cambio = recurso_anterior != recurso_nuevo
        
        # Si el estado cambió a CONFIRMADO o REALIZADO, crear Atencion si no existe
        if estado_nuevo in ['CONFIRMADO', 'REALIZADO'] and estado_anterior != estado_nuevo:
            # Verificar que el turno tenga paciente, médico y recurso
            if turno.paciente and turno.medico and turno.recurso:
                # Verificar si ya existe una atención para este turno
                try:
                    atencion = turno.atencion
                    # Si cambió el recurso, actualizar tipo_atencion y tipo_intervencion
                    if recurso_cambio:
                        tipo_atencion = turno.recurso.tipo_recurso
                        tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)
                        atencion.tipo_atencion = tipo_atencion
                        atencion.tipo_intervencion = tipo_intervencion
                        atencion.save(update_fields=['tipo_atencion', 'tipo_intervencion', 'updated_at'])
                    elif not atencion.tipo_intervencion:
                        # Si no tiene tipo_intervencion, calcularlo
                        tipo_intervencion = resolve_tipo_intervencion_from_recurso(atencion.tipo_atencion)
                        atencion.tipo_intervencion = tipo_intervencion
                        atencion.save(update_fields=['tipo_intervencion', 'updated_at'])
                except Atencion.DoesNotExist:
                    # Determinar el tipo de atención según el tipo de recurso
                    tipo_atencion = turno.recurso.tipo_recurso
                    tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)
                    # Crear la atención
                    Atencion.objects.create(
                        turno=turno,
                        paciente=turno.paciente,
                        medico_principal=turno.medico,
                        tipo_atencion=tipo_atencion,
                        tipo_intervencion=tipo_intervencion,
                        estado_clinico=Atencion.EstadoClinico.ABIERTA,
                    )
        # Si el recurso cambió y ya existe una atención, actualizar tipo_intervencion
        elif recurso_cambio and turno.paciente and turno.medico and turno.recurso:
            try:
                atencion = turno.atencion
                tipo_atencion = turno.recurso.tipo_recurso
                tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)
                atencion.tipo_atencion = tipo_atencion
                atencion.tipo_intervencion = tipo_intervencion
                atencion.save(update_fields=['tipo_atencion', 'tipo_intervencion', 'updated_at'])
            except Atencion.DoesNotExist:
                # Si no existe atención y el estado no es CONFIRMADO/REALIZADO, no hacer nada
                pass
    
    def perform_destroy(self, instance):
        """
        Restricciones para eliminar turnos:
        - PACIENTE: no puede eliminar turnos
        - MEDICO: no puede eliminar turnos de otros médicos
        - ADMIN/SECRETARIA: pueden eliminar cualquier turno
        """
        user = self.request.user
        
        if user.rol == 'paciente':
            raise PermissionDenied("Los pacientes no pueden eliminar turnos")
        elif user.rol == 'medico':
            # Médico solo puede eliminar sus propios turnos
            if instance.medico != user.medico:
                raise PermissionDenied("No puede eliminar turnos de otros médicos")
        elif user.rol in ['admin', 'secretaria']:
            # Admin y Secretaria pueden eliminar cualquier turno
            pass
        
        instance.delete()
    
    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            print("Error en update:", str(e))
            raise
    
    @action(detail=False, methods=['get'])
    def por_fecha(self, request):
        """Obtener turnos por fecha"""
        fecha = request.query_params.get('fecha')
        medico_id = request.query_params.get('medico_id')
        
        # Aplicar el mismo filtrado que get_queryset
        turnos = self.get_queryset()
        
        if fecha:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                turnos = turnos.filter(fecha_hora__date=fecha_obj)
            except ValueError:
                return Response({'error': 'Formato de fecha inválido'}, status=400)
        
        if medico_id:
            turnos = turnos.filter(medico_id=medico_id)
        
        turnos = turnos.order_by('fecha_hora')
        serializer = self.get_serializer(turnos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """Obtener turnos disponibles"""
        fecha = request.query_params.get('fecha')
        especialidad_id = request.query_params.get('especialidad_id')
        
        if not fecha:
            return Response({'error': 'Fecha requerida'}, status=400)
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Formato de fecha inválido'}, status=400)
        
        # Aplicar el mismo filtrado que get_queryset
        turnos = self.get_queryset().filter(
            fecha_hora_inicio__date=fecha_obj,
            estado='RESERVADO'
        )
        
        # Filtrar por recurso si se especifica
        recurso_id = request.query_params.get('recurso_id')
        if recurso_id:
            turnos = turnos.filter(recurso_id=recurso_id)
        
        turnos = turnos.order_by('fecha_hora_inicio')
        serializer = self.get_serializer(turnos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def mis_pacientes(self, request):
        """
        Para médicos: retorna sus pacientes asociados con sus turnos.
        Para secretarias: retorna todos los pacientes con sus turnos.
        """
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()
        
        if role == 'medico':
            try:
                medico = user.medico
                # Obtener pacientes que tienen turnos con este médico
                pacientes_ids = Turno.objects.filter(
                    medico=medico
                ).exclude(paciente__isnull=True).values_list('paciente_id', flat=True).distinct()
                
                pacientes = Paciente.objects.filter(id__in=pacientes_ids)
                
                # Construir respuesta con pacientes y sus turnos
                resultado = []
                for paciente in pacientes:
                    turnos_paciente = Turno.objects.filter(medico=medico, paciente=paciente).order_by('-fecha_hora_inicio')
                    turnos_data = TurnoSerializer(turnos_paciente, many=True).data
                    
                    resultado.append({
                        'paciente': PacienteSerializer(paciente).data,
                        'paciente_id': paciente.id,
                        'turnos': turnos_data,
                        'total_turnos': turnos_paciente.count()
                    })
                
                return Response({
                    'medico_id': medico.id,
                    'medico_nombre': medico.nombre_completo,
                    'pacientes': resultado,
                    'total_pacientes': len(resultado)
                })
            except Exception as e:
                return Response({'error': f'Error obteniendo pacientes: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        elif role in ['admin', 'secretaria'] or user.is_superuser:
            # Secretaria/Admin ve todos los pacientes con sus turnos
            pacientes = Paciente.objects.all()[:100]  # Limitar para no sobrecargar
            
            resultado = []
            for paciente in pacientes:
                turnos_paciente = Turno.objects.filter(paciente=paciente).order_by('-fecha_hora_inicio')
                turnos_data = TurnoSerializer(turnos_paciente, many=True).data
                
                resultado.append({
                    'paciente': PacienteSerializer(paciente).data,
                    'paciente_id': paciente.id,
                    'turnos': turnos_data,
                    'total_turnos': turnos_paciente.count()
                })
            
            return Response({
                'pacientes': resultado,
                'total_pacientes': len(resultado)
            })
        
        return Response({'error': 'No tiene permisos para acceder a esta información'}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['post'])
    def reservar(self, request, pk=None):
        """Reservar un turno"""
        turno = self.get_object()
        paciente_id = request.data.get('paciente_id')
        
        if not paciente_id:
            return Response({'error': 'paciente_id requerido'}, status=400)
        
        if turno.estado not in ['RESERVADO', 'CONFIRMADO']:
            return Response({'error': 'Turno no disponible'}, status=400)
        
        # Verificar permisos para reservar
        user = self.request.user
        
        if user.rol == 'paciente':
            # Paciente solo puede reservar para sí mismo
            if str(turno.paciente_id) != str(paciente_id):
                return Response({'error': 'Solo puede reservar turnos para sí mismo'}, status=403)
        elif user.rol not in ['admin', 'secretaria']:
            return Response({'error': 'No tiene permisos para reservar turnos'}, status=403)
        
        turno.paciente_id = paciente_id
        turno.estado = 'RESERVADO'
        turno.save()
        
        serializer = self.get_serializer(turno)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def crear_consulta(self, request, pk=None):
        """Crear una consulta desde un turno (solo para médicos)"""
        turno = self.get_object()
        
        # Verificar que el usuario sea médico
        if not hasattr(request.user, 'medico'):
            return Response({'error': 'Solo los médicos pueden crear consultas'}, status=403)
        
        # Verificar que el turno pertenezca al médico
        if turno.medico != request.user.medico:
            return Response({'error': 'Solo puede crear consultas para sus propios turnos'}, status=403)
        
        # Verificar que el turno esté en un estado válido para crear consulta
        if turno.estado not in ['RESERVADO', 'CONFIRMADO', 'REALIZADO']:
            return Response({'error': 'Solo se pueden crear consultas para turnos reservados, confirmados o realizados'}, status=400)
        
        # Verificar que no exista ya una consulta para este turno
        if hasattr(turno, 'consulta'):
            return Response({'error': 'Ya existe una consulta para este turno'}, status=400)
        
        # Obtener o crear la historia clínica del paciente
        try:
            historia_clinica, _ = HistoriaClinica.objects.get_or_create(paciente=turno.paciente)
        except Exception as e:
            return Response({'error': f'No se pudo obtener/crear la historia clínica: {str(e)}'}, status=400)
        
        # Crear la consulta
        consulta_data = {
            'historia_clinica_id': historia_clinica.pk,
            'medico_id': request.user.medico.id,
            'turno_id': turno.id,
            'fecha_hora_consulta': turno.fecha_hora_inicio,
            'motivo_consulta_detalle': turno.motivo_consulta or 'Consulta médica',
            'anamnesis': request.data.get('anamnesis', ''),
            'examen_fisico': request.data.get('examen_fisico', ''),
            'diagnostico_presuntivo': request.data.get('diagnostico_presuntivo', ''),
            'plan_manejo': request.data.get('plan_manejo', ''),
            'notas_medicas': request.data.get('notas_medicas', '')
        }
        
        serializer = ConsultaCreateSerializer(data=consulta_data)
        if serializer.is_valid():
            consulta = serializer.save()
            
            # Actualizar el estado del turno a REALIZADO
            turno.estado = 'REALIZADO'
            turno.save()
            
            return Response({
                'message': 'Consulta creada exitosamente',
                'consulta': serializer.data
            }, status=201)
        else:
            return Response(serializer.errors, status=400)

    @action(detail=True, methods=['get'])
    def consulta_info(self, request, pk=None):
        """Obtener información de la consulta asociada al turno"""
        turno = self.get_object()
        
        if hasattr(turno, 'consulta'):
            serializer = ConsultaSerializer(turno.consulta)
            return Response(serializer.data)
        else:
            return Response({'message': 'No hay consulta asociada a este turno'}, status=404)

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Confirmar un turno (solo para médicos)"""
        turno = self.get_object()
        
        # Verificar que el usuario sea médico
        if not hasattr(request.user, 'medico'):
            return Response({'error': 'Solo los médicos pueden confirmar turnos'}, status=403)
        
        # Verificar que el turno pertenezca al médico
        if turno.medico != request.user.medico:
            return Response({'error': 'Solo puede confirmar sus propios turnos'}, status=403)
        
        # Verificar que el turno esté reservado
        if turno.estado != 'RESERVADO':
            return Response({'error': 'Solo se pueden confirmar turnos reservados'}, status=400)
        
        # Confirmar el turno
        turno.estado = 'CONFIRMADO'
        turno.save()
        
        serializer = self.get_serializer(turno)
        return Response({
            'message': 'Turno confirmado exitosamente',
            'turno': serializer.data
        })

    @action(detail=True, methods=['post'])
    def iniciar_atencion(self, request, pk=None):
        """
        Iniciar una atención médica desde un turno.
        
        Esta acción delega toda la lógica al AtencionService para garantizar
        transiciones atómicas y seguras de Turno a Atención.
        
        Permite crear automáticamente:
        - ConsultaAmbulatoria (para CONSULTORIO)
        - RegistroProcedimiento (para SALA_PROCEDIMIENTO)
        - RegistroQuirurgico (para QUIROFANO/SALA_HEMODINAMIA)
        """
        turno = self.get_object()
        
        try:
            # Delegar toda la lógica al servicio
            outcome = AtencionService.iniciar_atencion_desde_turno(
                turno_id=turno.id,
                usuario_solicitante=request.user,
            )
            atencion = outcome.atencion
            turno.refresh_from_db()
            
            # Serializar la atención creada
            from .serializers import AtencionSerializer
            atencion_serializer = AtencionSerializer(atencion)
            
            return Response({
                'message': 'Atención iniciada exitosamente',
                'atencion': atencion_serializer.data,
                'turno_id': turno.id,
                'estado_turno': turno.estado
            }, status=status.HTTP_201_CREATED)
            
        except BusinessLogicError as e:
            # Errores de lógica de negocio retornan 400 Bad Request
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Turno.DoesNotExist:
            return Response({
                'error': 'El turno especificado no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            # Errores inesperados retornan 500 Internal Server Error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Error inesperado al iniciar atención desde turno {turno.id}: {str(e)}",
                exc_info=True
            )
            return Response({
                'error': 'Error interno del servidor al iniciar la atención'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Vista especial para el panel
class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]  # Cambiado para desarrollo
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas generales del panel"""
        hoy = timezone.now().date()
        
        # Estadísticas básicas
        total_pacientes = Paciente.objects.count()
        consultas_hoy = Consulta.objects.filter(fecha_hora_consulta__date=hoy).count()
        # solicitudes_pendientes = SolicitudExamen.objects.filter(estado='PENDIENTE').count()
        # resultados_listos = ResultadoExamen.objects.filter(
        #     fecha_resultado__date=hoy,
        #     es_normal=False
        # ).count()
        solicitudes_pendientes = 0  # Temporalmente en 0 hasta implementar solicitudes
        resultados_listos = 0  # Temporalmente en 0 hasta implementar resultados
        
        # Consultas por especialidad
        consultas_por_especialidad = Consulta.objects.filter(
            fecha_hora_consulta__date=hoy
        ).values('medico__especialidad__nombre').annotate(
            total=Count('id')
        )
        
        # Solicitudes por estado
        # solicitudes_por_estado = SolicitudExamen.objects.values('estado').annotate(
        #     total=Count('id')
        # )
        solicitudes_por_estado = []  # Temporalmente vacío hasta implementar solicitudes
        
        stats = {
            'total_pacientes': total_pacientes,
            'consultas_hoy': consultas_hoy,
            'solicitudes_pendientes': solicitudes_pendientes,
            'resultados_listos': resultados_listos,
            'consultas_por_especialidad': {
                item['medico__especialidad__nombre'] or 'Sin Especialidad': item['total']
                for item in consultas_por_especialidad
            },
            'solicitudes_por_estado': {
                item['estado']: item['total']
                for item in solicitudes_por_estado
            }
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)

# ============================================================================
# VISTAS DE AUTENTICACIÓN
# ============================================================================

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from usuarios.models import UserProfile

@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token_view(request):
    """Endpoint público para obtener el token CSRF"""
    from django.middleware.csrf import get_token
    token = get_token(request)
    return Response({'csrftoken': token})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Vista para login de usuarios"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Username y password son requeridos'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response({
            'error': 'Credenciales inválidas'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({
            'error': 'Usuario inactivo'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    login(request, user)
    
    # Obtener información del usuario
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'rol': user.rol.upper(),  # Convertir a mayúsculas para consistencia
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'groups': list(user.groups.values_list('name', flat=True)),
    }
    
    # Agregar información del perfil si existe
    try:
        profile = user.profile
        user_data['profile'] = {
            'fecha_nacimiento': profile.fecha_nacimiento,
            'genero': profile.genero,
            'direccion': profile.direccion,
            'ciudad': profile.ciudad,
            'codigo_postal': profile.codigo_postal,
            'grupo_sanguineo': profile.grupo_sanguineo,
            'alergias': profile.alergias,
            'medicamentos_actuales': profile.medicamentos_actuales,
            'contacto_emergencia_nombre': profile.contacto_emergencia_nombre,
            'contacto_emergencia_telefono': profile.contacto_emergencia_telefono,
            'contacto_emergencia_relacion': profile.contacto_emergencia_relacion,
            'edad': profile.get_edad(),
        }
    except UserProfile.DoesNotExist:
        user_data['profile'] = None
    
    return Response({
        'message': 'Login exitoso',
        'user': user_data
    })

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Vista para logout de usuarios"""
    logout(request)
    return Response({'message': 'Logout exitoso'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Obtener información del usuario actual"""
    user = request.user
    
    # Construir respuesta básica del usuario
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'rol': user.rol,
        'telefono': user.telefono,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined,
        'last_login': user.last_login
    }
    
    # Agregar información específica según el rol
    if user.rol == 'medico':
        try:
            from medicos.models import Medico
            medico = Medico.objects.get(user=user)
            user_data['medico'] = {
                'id': medico.id,
                'nombre': medico.nombre,
                'apellido': medico.apellido,
                'email': medico.email,
                'matricula': medico.matricula,
                'especialidad': {
                    'id': medico.especialidad.id,
                    'nombre': medico.especialidad.nombre
                } if medico.especialidad else None
            }
        except Medico.DoesNotExist:
            user_data['medico'] = None
    elif user.rol == 'paciente':
        from pacientes.services import ensure_paciente_linked_to_user

        paciente = ensure_paciente_linked_to_user(user)
        if paciente:
            user_data['paciente'] = {
                'id': paciente.id,
                'nombre': paciente.nombre,
                'apellido': paciente.apellido,
                'dni': paciente.dni,
                'email': paciente.email
            }
        else:
            user_data['paciente'] = None
    
    return Response(user_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """Listar usuarios (solo para staff)"""
    if not request.user.is_staff:
        return Response({
            'error': 'Acceso denegado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    users = User.objects.all().select_related('profile')
    user_list = []
    
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'groups': list(user.groups.values_list('name', flat=True)),
        }
        
        # Agregar información del perfil si existe
        try:
            profile = user.profile
            user_data['profile'] = {
                'fecha_nacimiento': profile.fecha_nacimiento,
                'genero': profile.genero,
                'ciudad': profile.ciudad,
                'edad': profile.get_edad(),
            }
        except UserProfile.DoesNotExist:
            user_data['profile'] = None
        
        user_list.append(user_data)
    
    return Response(user_list)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_groups(request):
    """Listar grupos disponibles"""
    if not request.user.is_staff:
        return Response({
            'error': 'Acceso denegado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    groups = Group.objects.all()
    group_list = []
    
    for group in groups:
        group_data = {
            'id': group.id,
            'name': group.name,
            'user_count': group.user_set.count(),
        }
        group_list.append(group_data)
    
    return Response(group_list)

# ============================================================================
# VISTAS DE REGISTRO DE USUARIOS
# ============================================================================

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from usuarios.models import User, UserProfile
from pacientes.models import Paciente
from medicos.models import Medico
from usuarios.models import Secretaria

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_patient(request):
    """Registro de pacientes (público)"""
    try:
        data = request.data
        
        # Validar campos requeridos
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'dni']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'El campo {field} es requerido'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el username no exista
        if User.objects.filter(username=data['username']).exists():
            return Response({
                'error': 'El nombre de usuario ya existe'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el email no exista
        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'El email ya está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el DNI no exista
        if Paciente.objects.filter(dni=data['dni']).exists():
            return Response({
                'error': 'El DNI ya está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar contraseña
        try:
            validate_password(data['password'])
        except ValidationError as e:
            return Response({
                'error': 'Contraseña inválida: ' + ', '.join(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear usuario
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            telefono=data.get('telefono', ''),
            rol='paciente'
        )
        
        # Crear perfil de usuario
        profile_data = {
            'fecha_nacimiento': data.get('fecha_nacimiento'),
            'genero': data.get('genero'),
            'direccion': data.get('direccion'),
            'ciudad': data.get('ciudad'),
            'codigo_postal': data.get('codigo_postal'),
            'grupo_sanguineo': data.get('grupo_sanguineo'),
            'alergias': data.get('alergias'),
            'medicamentos_actuales': data.get('medicamentos_actuales'),
            'contacto_emergencia_nombre': data.get('contacto_emergencia_nombre'),
            'contacto_emergencia_telefono': data.get('contacto_emergencia_telefono'),
            'contacto_emergencia_relacion': data.get('contacto_emergencia_relacion'),
        }
        
        UserProfile.objects.create(user=user, **profile_data)
        
        # Crear paciente - Solo campos específicos de paciente (no duplicados)
        paciente_data = {
            'user': user,  # Relación obligatoria
            'dni': data['dni'],
            'obra_social': data.get('obra_social'),
            'numero_afiliado': data.get('numero_afiliado'),
            'antecedentes_personales': data.get('antecedentes_personales'),
            'antecedentes_familiares': data.get('antecedentes_familiares'),
            'observaciones': data.get('observaciones'),
        }
        
        Paciente.objects.create(**paciente_data)
        
        # Asignar al grupo Pacientes
        try:
            pacientes_group = Group.objects.get(name='Pacientes')
            user.groups.add(pacientes_group)
        except Group.DoesNotExist:
            pass  # El grupo no existe, pero no es crítico
        
        return Response({
            'message': 'Paciente registrado exitosamente',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Error en el registro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsSecretariaOrAdmin])
def register_doctor(request):
    """Registro de médicos (solo secretarias y admins)"""
    try:
        data = request.data
        
        # Validar campos requeridos
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'matricula', 'especialidad_id']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'El campo {field} es requerido'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el username no exista
        if User.objects.filter(username=data['username']).exists():
            return Response({
                'error': 'El nombre de usuario ya existe'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el email no exista
        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'El email ya está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que la matrícula no exista
        if Medico.objects.filter(matricula=data['matricula']).exists():
            return Response({
                'error': 'La matrícula ya está registrada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar contraseña
        try:
            validate_password(data['password'])
        except ValidationError as e:
            return Response({
                'error': 'Contraseña inválida: ' + ', '.join(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear usuario
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            telefono=data.get('telefono', ''),
            rol='medico'
        )
        
        # Crear perfil de usuario
        profile_data = {
            'fecha_nacimiento': data.get('fecha_nacimiento'),
            'genero': data.get('genero'),
            'direccion': data.get('direccion'),
            'ciudad': data.get('ciudad'),
            'codigo_postal': data.get('codigo_postal'),
        }
        
        UserProfile.objects.create(user=user, **profile_data)
        
        # Crear médico
        medico_data = {
            'especialidad_id': data['especialidad_id'],
            'areas_interes_ia': data.get('areas_interes_ia'),
        }
        
        Medico.objects.create(user=user, matricula=data['matricula'], **medico_data)
        
        # Asignar al grupo Médicos
        try:
            medicos_group = Group.objects.get(name='Médicos')
            user.groups.add(medicos_group)
        except Group.DoesNotExist:
            pass
        
        return Response({
            'message': 'Médico registrado exitosamente',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Error en el registro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsSecretariaOrAdmin])
def register_secretary(request):
    """Registro de secretarias (solo admins)"""
    try:
        data = request.data
        
        # Validar campos requeridos
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'legajo']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'El campo {field} es requerido'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el username no exista
        if User.objects.filter(username=data['username']).exists():
            return Response({
                'error': 'El nombre de usuario ya existe'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el email no exista
        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'El email ya está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el legajo no exista
        if Secretaria.objects.filter(legajo=data['legajo']).exists():
            return Response({
                'error': 'El legajo ya está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar contraseña
        try:
            validate_password(data['password'])
        except ValidationError as e:
            return Response({
                'error': 'Contraseña inválida: ' + ', '.join(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear usuario
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            telefono=data.get('telefono', ''),
            rol='secretaria'
        )
        
        # Crear perfil de usuario
        profile_data = {
            'fecha_nacimiento': data.get('fecha_nacimiento'),
            'genero': data.get('genero'),
            'direccion': data.get('direccion'),
            'ciudad': data.get('ciudad'),
            'codigo_postal': data.get('codigo_postal'),
        }
        
        UserProfile.objects.create(user=user, **profile_data)
        
        # Crear secretaria
        secretaria_data = {
            'sector': data.get('sector'),
        }
        
        Secretaria.objects.create(user=user, legajo=data['legajo'], **secretaria_data)
        
        # Asignar al grupo Secretarias
        try:
            secretarias_group = Group.objects.get(name='Secretarias')
            user.groups.add(secretarias_group)
        except Group.DoesNotExist:
            pass
        
        return Response({
            'message': 'Secretaria registrada exitosamente',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Error en el registro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# NUEVO: ViewSet para Internaciones
class InternacionViewSet(viewsets.ModelViewSet):
    queryset = Internacion.objects.all()
    serializer_class = InternacionSerializer
    permission_classes = [IsMedicoOrEnfermeriaOrAdmin]  # Médicos, enfermería y admins pueden gestionar internaciones
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrar por rol del usuario
        if hasattr(user, 'rol'):
            rol_upper = user.rol.upper()
            if rol_upper == 'MEDICO':
                # Médicos ven sus propias internaciones
                try:
                    queryset = queryset.filter(medico_responsable=user.medico)
                except Exception as e:
                    logger.exception("Error filtrando InternacionViewSet por médico: %s", e)
                    queryset = queryset.none()
            elif rol_upper == 'ENFERMERIA':
                # Enfermería puede ver todas las internaciones activas
                queryset = queryset.filter(activo=True)
            elif rol_upper == 'ADMIN':
                # Admins ven todas
                pass
            else:
                # Otros roles no ven internaciones
                queryset = queryset.none()
        
        # Filtros adicionales
        estado = self.request.query_params.get('estado', None)
        centro_fisico = self.request.query_params.get('centro_fisico', None)
        area = self.request.query_params.get('area', None)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if centro_fisico:
            queryset = queryset.filter(cama__area__centro_fisico__codigo=centro_fisico)
        if area:
            queryset = queryset.filter(cama__area__codigo=area)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def dar_alta(self, request, pk=None):
        """Dar alta a una internación"""
        internacion = self.get_object()
        
        if internacion.estado != 'ACTIVA':
            return Response(
                {'error': 'Solo se puede dar alta a internaciones activas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar estado y fecha de alta
        internacion.estado = 'ALTA_MEDICA'
        internacion.fecha_alta = request.data.get('fecha_alta')
        internacion.observaciones = request.data.get('observaciones', '')
        internacion.save()
        
        # Liberar la cama
        cama = internacion.cama
        cama.estado = 'DISPONIBLE'
        cama.save()
        
        serializer = self.get_serializer(internacion)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas de internaciones"""
        queryset = self.get_queryset()
        
        # Estadísticas por estado
        activas = queryset.filter(estado='ACTIVA').count()
        altas_medicas = queryset.filter(estado='ALTA_MEDICA').count()
        altas_voluntarias = queryset.filter(estado='ALTA_VOLUNTARIA').count()
        
        # Estadísticas por centro
        cehta = queryset.filter(cama__area__centro_fisico__codigo='CEHTA').count()
        icpl = queryset.filter(cama__area__centro_fisico__codigo='ICPL').count()
        
        return Response({
            'por_estado': {
                'activas': activas,
                'altas_medicas': altas_medicas,
                'altas_voluntarias': altas_voluntarias
            },
            'por_centro': {
                'cehta': cehta,
                'icpl': icpl
            },
            'total': queryset.count()
        })


# ViewSets para Recursos
class RecursoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar recursos físicos agendables"""
    queryset = Recurso.objects.filter(activo=True)
    serializer_class = RecursoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo_recurso', 'ubicacion', 'activo']
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'tipo_recurso']
    ordering = ['nombre']


# ViewSets para Atencion y modelos relacionados
class AtencionViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar atenciones clínicas"""
    queryset = (
        Atencion.objects
        .select_related('paciente', 'medico_principal', 'turno', 'turno__recurso', 'consulta_ambulatoria', 'registro_procedimiento', 'registro_quirurgico')
        .prefetch_related('documentos')
    )
    permission_classes = [IsEMRClinicianOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo_intervencion', 'estado_clinico', 'paciente', 'medico_principal', 'turno', 'turno__recurso__tipo_recurso']
    search_fields = [
        'paciente__nombre',
        'paciente__apellido',
        'medico_principal__nombre',
        'medico_principal__apellido',
        'observaciones_generales',
    ]
    ordering_fields = ['fecha_admision', 'fecha_cierre', 'updated_at']
    ordering = ['-fecha_admision']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AtencionCreateSerializer
        if self.action in ['update', 'partial_update']:
            return AtencionUpdateSerializer
        return AtencionSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Sobrescribir retrieve para asegurar carga completa de relaciones"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Sobrescribir create para manejar correctamente cuando se retorna una atención existente"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Verificar si ya existe una atención para este turno antes de crear
            turno_id = serializer.validated_data.get('turno_id')
            paciente_id = serializer.validated_data.get('paciente_id')
            medico_principal_id = serializer.validated_data.get('medico_principal_id')
            
            print(f"🔍 Verificando atención existente - turno_id: {turno_id}, paciente_id: {paciente_id}, medico_principal_id: {medico_principal_id}")
            
            if turno_id:
                try:
                    # Cargar la atención con todas sus relaciones
                    atencion_existente = (
                        Atencion.objects
                        .select_related('paciente', 'medico_principal', 'turno', 'turno__recurso', 'consulta_ambulatoria', 'registro_procedimiento', 'registro_quirurgico')
                        .prefetch_related('documentos')
                        .get(turno_id=turno_id)
                    )
                    print(f"✅ Atención existente encontrada: {atencion_existente.id}")
                    print(f"   - paciente: {atencion_existente.paciente_id}, medico_principal: {atencion_existente.medico_principal_id}")
                    # Si existe, retornar usando el serializer completo
                    response_serializer = AtencionSerializer(atencion_existente)
                    response_data = response_serializer.data
                    print(f"   - paciente en respuesta: {'paciente' in response_data}")
                    return Response(response_data, status=status.HTTP_200_OK)
                except Atencion.DoesNotExist:
                    print(f"ℹ️ No existe atención para turno {turno_id}, creando nueva")
                    pass
            
            # Si no existe, crear normalmente
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            
            # Recargar la instancia con todas sus relaciones para la respuesta
            instance = serializer.instance
            if not instance:
                return Response(
                    {'error': 'No se pudo crear la atención'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Verificar que la instancia tenga paciente y medico_principal
            if not instance.paciente_id or not instance.medico_principal_id:
                return Response(
                    {'error': 'La atención debe tener paciente y médico principal asignados'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Recargar con todas las relaciones
            try:
                instance = (
                    Atencion.objects
                    .select_related('paciente', 'medico_principal', 'turno', 'turno__recurso', 'consulta_ambulatoria', 'registro_procedimiento', 'registro_quirurgico')
                    .prefetch_related('documentos')
                    .get(pk=instance.pk)
                )
                
                # Verificar que las relaciones estén cargadas
                print(f"✅ Atencion {instance.id} creada - paciente_id: {instance.paciente_id}, medico_principal_id: {instance.medico_principal_id}")
                print(f"   - paciente cargado: {hasattr(instance, 'paciente') and instance.paciente is not None}")
                print(f"   - medico_principal cargado: {hasattr(instance, 'medico_principal') and instance.medico_principal is not None}")
                
            except Atencion.DoesNotExist:
                return Response(
                    {'error': 'No se pudo encontrar la atención creada'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except Exception as reload_error:
                print(f"❌ Error recargando Atencion {instance.pk if instance else 'None'}: {reload_error}")
                import traceback
                print(traceback.format_exc())
                return Response(
                    {'error': f'Error al recargar la atención: {str(reload_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Usar el serializer completo para la respuesta
            try:
                response_serializer = AtencionSerializer(instance)
                response_data = response_serializer.data
                print(f"✅ Serialización exitosa - paciente en respuesta: {'paciente' in response_data}")
                return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            except Exception as serialize_error:
                print(f"❌ Error serializando respuesta: {serialize_error}")
                import traceback
                print(traceback.format_exc())
                return Response(
                    {'error': f'Error al serializar la respuesta: {str(serialize_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            import traceback
            error_detail = str(e)
            traceback_str = traceback.format_exc()
            print(f"Error en AtencionViewSet.create: {error_detail}")
            print(traceback_str)
            return Response(
                {'error': f'Error al crear la atención: {error_detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        """
        Filtrar atenciones según el rol del usuario.
        El queryset base ya incluye select_related para optimizar queries.
        """
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()
        
        if user.is_superuser or role in ['admin', 'secretaria']:
            return queryset
        
        if role == 'medico':
            try:
                medico = user.medico
                return queryset.filter(medico_principal=medico)
            except Exception:
                return queryset.none()
        
        if role == 'paciente':
            try:
                paciente = user.paciente
                return queryset.filter(paciente=paciente)
            except Exception:
                return queryset.none()
        
        return queryset.none()

    def perform_create(self, serializer):
        validated = serializer.validated_data
        tipo_intervencion = validated.get('tipo_intervencion')
        if not tipo_intervencion:
            tipo_atencion = validated.get('tipo_atencion')
            if isinstance(tipo_atencion, str):
                tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)
        
        # El serializer ya maneja la lógica de verificar si existe una atención para el turno
        # y retornar la existente si es el caso
        serializer.save(
            tipo_intervencion=tipo_intervencion or Atencion.TipoIntervencion.CONSULTA,
            estado_clinico=validated.get('estado_clinico') or Atencion.EstadoClinico.ABIERTA,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        if not instance.tipo_intervencion:
            instance.tipo_intervencion = resolve_tipo_intervencion_from_recurso(instance.tipo_atencion)
            instance.save(update_fields=['tipo_intervencion', 'updated_at'])
    
    @action(detail=True, methods=['post'])
    def cerrar_atencion(self, request, pk=None):
        """Cerrar una atención"""
        atencion = self.get_object()
        
        if atencion.fecha_cierre:
            return Response(
                {'error': 'La atención ya está cerrada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        atencion.fecha_cierre = timezone.now()
        atencion.estado_clinico = Atencion.EstadoClinico.FINALIZADA
        atencion.save(update_fields=['fecha_cierre', 'estado_clinico', 'updated_at'])
        
        serializer = self.get_serializer(atencion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def crear_registro_ambulatorio(self, request, pk=None):
        """Crear registro de consulta ambulatoria para una atención"""
        atencion = self.get_object()
        
        if atencion.tipo_intervencion != Atencion.TipoIntervencion.CONSULTA:
            return Response(
                {'error': 'Este tipo de atención no corresponde a consulta ambulatoria'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if hasattr(atencion, 'consulta_ambulatoria'):
            return Response(
                {'error': 'Ya existe un registro de consulta ambulatoria para esta atención'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ConsultaAmbulatoriaSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(atencion=atencion)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def crear_registro_procedimiento(self, request, pk=None):
        """Crear registro de procedimiento/estudio para una atención"""
        atencion = self.get_object()
        
        if atencion.tipo_intervencion not in [
            Atencion.TipoIntervencion.ESTUDIO,
            Atencion.TipoIntervencion.PROCEDIMIENTO,
        ]:
            return Response(
                {'error': 'Este tipo de atención no corresponde a un estudio/procedimiento'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if hasattr(atencion, 'registro_procedimiento'):
            return Response(
                {'error': 'Ya existe un registro de procedimiento para esta atención'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RegistroProcedimientoSerializer(
            data=request.data,
            context={'request': request, 'atencion': atencion}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(atencion=atencion)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def crear_registro_quirurgico(self, request, pk=None):
        """Crear registro quirúrgico para una atención"""
        atencion = self.get_object()
        
        if atencion.tipo_intervencion != Atencion.TipoIntervencion.CIRUGIA:
            return Response(
                {'error': 'Este tipo de atención no corresponde a un acto quirúrgico'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if hasattr(atencion, 'registro_quirurgico'):
            return Response(
                {'error': 'Ya existe un registro quirúrgico para esta atención'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RegistroQuirurgicoSerializer(
            data=request.data,
            context={'request': request, 'atencion': atencion}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(atencion=atencion)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConsultaAmbulatoriaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar consultas ambulatorias"""
    queryset = ConsultaAmbulatoria.objects.select_related('atencion', 'atencion__paciente', 'atencion__medico_principal')
    serializer_class = ConsultaAmbulatoriaSerializer
    permission_classes = [IsEMRClinicianOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['atencion__paciente__nombre', 'atencion__paciente__apellido']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()

        if user.is_superuser or role in ['admin', 'secretaria']:
            return queryset
        if role == 'medico':
            try:
                return queryset.filter(atencion__medico_principal=user.medico)
            except Exception:
                return queryset.none()
        if role == 'paciente':
            try:
                return queryset.filter(atencion__paciente=user.paciente)
            except Exception:
                return queryset.none()
        return queryset.none()


class RegistroProcedimientoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar registros de procedimientos"""
    queryset = RegistroProcedimiento.objects.select_related('atencion', 'atencion__paciente', 'atencion__medico_principal', 'procedimiento', 'profesional_asistente')
    serializer_class = RegistroProcedimientoSerializer
    permission_classes = [IsEMRClinicianOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['atencion__paciente__nombre', 'atencion__paciente__apellido', 'descripcion_procedimiento']
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()

        if user.is_superuser or role in ['admin', 'secretaria']:
            return queryset
        if role == 'medico':
            try:
                medico = user.medico
                return queryset.filter(
                    Q(atencion__medico_principal=medico) |
                    Q(profesional_asistente=medico)
                )
            except Exception:
                return queryset.none()
        if role == 'paciente':
            try:
                return queryset.filter(atencion__paciente=user.paciente)
            except Exception:
                return queryset.none()
        return queryset.none()


class RegistroQuirurgicoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar registros quirúrgicos"""
    queryset = RegistroQuirurgico.objects.select_related('atencion', 'atencion__paciente', 'atencion__medico_principal', 'procedimiento', 'anestesista')
    serializer_class = RegistroQuirurgicoSerializer
    permission_classes = [IsEMRClinicianOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['atencion__paciente__nombre', 'atencion__paciente__apellido']
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()

        if user.is_superuser or role in ['admin', 'secretaria']:
            return queryset
        if role == 'medico':
            try:
                medico = user.medico
                return queryset.filter(
                    Q(atencion__medico_principal=medico) |
                    Q(anestesista=medico) |
                    Q(documentos_adjuntos__usuario_cargador=user)
                ).distinct()
            except Exception:
                return queryset.none()
        if role == 'paciente':
            try:
                return queryset.filter(atencion__paciente=user.paciente)
            except Exception:
                return queryset.none()
        return queryset.none()


class DocumentoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar documentos clínicos"""
    queryset = Documento.objects.select_related('atencion', 'atencion__paciente', 'atencion__medico_principal', 'usuario_cargador')
    serializer_class = DocumentoSerializer
    permission_classes = [IsEMRClinicianOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo_documento', 'atencion']
    search_fields = [
        'descripcion',
        'atencion__paciente__nombre',
        'atencion__paciente__apellido',
        'usuario_cargador__first_name',
        'usuario_cargador__last_name',
    ]
    ordering_fields = ['fecha_subida', 'created_at']
    ordering = ['-fecha_subida']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()

        if user.is_superuser or role in ['admin', 'secretaria']:
            pass
        elif role == 'medico':
            try:
                medico = user.medico
                queryset = queryset.filter(
                    Q(atencion__medico_principal=medico) |
                    Q(usuario_cargador=user)
                )
            except Exception:
                return queryset.none()
        elif role == 'paciente':
            try:
                queryset = queryset.filter(atencion__paciente=user.paciente)
            except Exception:
                return queryset.none()
        else:
            return queryset.none()

        atencion_param = self.request.query_params.get('atencion')
        if atencion_param:
            queryset = queryset.filter(atencion_id=atencion_param)
        tipo_documento = self.request.query_params.get('tipo_documento')
        if tipo_documento:
            queryset = queryset.filter(tipo_documento=tipo_documento)
        return queryset

    def perform_create(self, serializer):
        usuario = self.request.user if self.request.user.is_authenticated else None
        serializer.save(usuario_cargador=usuario)

    def perform_update(self, serializer):
        instance = serializer.save()
        if not instance.usuario_cargador and self.request.user.is_authenticated:
            instance.usuario_cargador = self.request.user
            instance.save(update_fields=['usuario_cargador', 'updated_at'])
    
    @action(detail=False, methods=['get'])
    def tipos(self, request):
        """
        Endpoint para obtener los tipos de documento disponibles.
        Retorna lista de opciones para usar en frontend.
        """
        tipos = [
            {'value': 'INFORME', 'label': 'Informe'},
            {'value': 'ESTUDIO', 'label': 'Estudio'},
            {'value': 'ANALISIS', 'label': 'Análisis'},
            {'value': 'DIAGNOSTICO', 'label': 'Diagnóstico'},
            {'value': 'IMAGEN', 'label': 'Imagen'},
            {'value': 'CONSENTIMIENTO', 'label': 'Consentimiento informado'},
            {'value': 'OTRO', 'label': 'Otro'},
        ]
        return Response(tipos)


class SignosVitalesViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar registros de signos vitales"""
    queryset = SignosVitales.objects.select_related('atencion', 'atencion__paciente', 'atencion__medico_principal', 'registrado_por')
    serializer_class = SignosVitalesSerializer
    permission_classes = [IsEMRClinicianOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['atencion', 'rol_registrador']
    ordering_fields = ['fecha_registro', 'created_at']
    ordering = ['-fecha_registro']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = str(getattr(user, 'rol', '') or '').lower()

        if user.is_superuser or role in ['admin', 'secretaria']:
            pass
        elif role == 'medico':
            try:
                queryset = queryset.filter(atencion__medico_principal=user.medico)
            except Exception:
                return queryset.none()
        elif role == 'paciente':
            try:
                queryset = queryset.filter(atencion__paciente=user.paciente)
            except Exception:
                return queryset.none()
        else:
            return queryset.none()

        atencion_param = self.request.query_params.get('atencion')
        if atencion_param:
            queryset = queryset.filter(atencion_id=atencion_param)
        return queryset

    def create(self, request, *args, **kwargs):
        """Sobrescribir create para logging detallado y mejor manejo de errores"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        
        logger.error(f"🔍 SignosVitalesViewSet.create - request.data: {request.data}")
        logger.error(f"🔍 SignosVitalesViewSet.create - request.user: {request.user}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"❌ SignosVitalesViewSet.create - Errores de validación: {serializer.errors}")
            # Devolver los errores de validación de forma clara
            return Response(
                {
                    'error': 'Error de validación',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            logger.error(f"✅ SignosVitalesViewSet.create - Creado exitosamente: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"❌ SignosVitalesViewSet.create - Error al guardar: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return Response(
                {
                    'error': 'Error al guardar el registro',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        usuario = self.request.user if self.request.user.is_authenticated else None
        serializer.save(registrado_por=usuario)

# ViewSets para catálogos
class EstudioDiagnosticoViewSet(viewsets.ModelViewSet):
    """ViewSet para catálogo de estudios diagnósticos - médicos y admin pueden editar"""
    queryset = EstudioDiagnostico.objects.all()
    serializer_class = EstudioDiagnosticoSerializer
    permission_classes = [IsMedicoOrAdmin]  # Médicos y admin pueden editar
    pagination_class = None  # Deshabilitar paginación - SIEMPRE cargar TODOS los estudios
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre']
    ordering = ['nombre']
    
    def get_queryset(self):
        """Filtrar por activo si se solicita, o mostrar todos para admin"""
        queryset = super().get_queryset()
        if self.request.query_params.get('activo') == 'true':
            return queryset.filter(activo=True)
        return queryset


class ProcedimientoCatalogoViewSet(viewsets.ModelViewSet):
    """ViewSet para catálogo de procedimientos - médicos y admin pueden editar"""
    queryset = ProcedimientoCatalogo.objects.all()
    serializer_class = ProcedimientoCatalogoSerializer
    permission_classes = [IsMedicoOrAdmin]  # Médicos y admin pueden editar
    pagination_class = None  # Deshabilitar paginación - SIEMPRE cargar TODOS los procedimientos
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre']
    ordering = ['nombre']
    
    def get_queryset(self):
        """Filtrar por activo si se solicita, o mostrar todos para admin"""
        queryset = super().get_queryset()
        if self.request.query_params.get('activo') == 'true':
            return queryset.filter(activo=True)
        return queryset
