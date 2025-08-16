from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsSecretariaOrAdmin, IsMedicoOrAdmin, IsPacienteOrStaff, CanManageTurnos
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from usuarios.models import UserProfile

from .serializers import (
    PacienteSerializer, MedicoSerializer, EspecialidadSerializer,
    TipoExamenSerializer, PanelExamenSerializer, SolicitudExamenSerializer,
    ResultadoExamenSerializer, ConsultaSerializer, ConsultaCreateSerializer, DiagnosticoSerializer,
    PrescripcionSerializer, MedicamentoSerializer, DashboardStatsSerializer,
    PacienteSearchSerializer, ConsultaSearchSerializer, TurnoSerializer,
    TurnoCreateUpdateSerializer, InternacionSerializer
)

from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from laboratorio.models import TipoExamen, PanelExamen, SolicitudExamen, ResultadoExamen
from historias_clinicas.models import Consulta, Diagnostico, Prescripcion, HistoriaClinica, Internacion
from catalogos.models import Medicamento
from turnos.models import Turno


class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    permission_classes = [AllowAny]  # Temporal para desarrollo
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Búsqueda de pacientes por nombre, apellido o DNI"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'results': []})
        
        pacientes = Paciente.objects.filter(
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(dni__icontains=query)
        )[:10]
        
        serializer = PacienteSearchSerializer(pacientes, many=True)
        return Response({'results': serializer.data})


class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer
    permission_classes = [AllowAny]  # Cambiado para desarrollo


class EspecialidadViewSet(viewsets.ModelViewSet):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [AllowAny]  # Cambiado para desarrollo


class TipoExamenViewSet(viewsets.ModelViewSet):
    queryset = TipoExamen.objects.filter(activo=True)
    serializer_class = TipoExamenSerializer
    permission_classes = [IsAuthenticated]


class PanelExamenViewSet(viewsets.ModelViewSet):
    queryset = PanelExamen.objects.filter(activo=True)
    serializer_class = PanelExamenSerializer
    permission_classes = [IsAuthenticated]


class SolicitudExamenViewSet(viewsets.ModelViewSet):
    queryset = SolicitudExamen.objects.all()
    serializer_class = SolicitudExamenSerializer
    permission_classes = [IsSecretariaOrAdmin]  # Solo secretarias y admins pueden gestionar solicitudes
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de solicitudes de laboratorio"""
        hoy = timezone.now().date()
        
        stats = {
            'pendientes': SolicitudExamen.objects.filter(estado='PENDIENTE').count(),
            'en_proceso': SolicitudExamen.objects.filter(estado='EN_PROCESO').count(),
            'completadas_hoy': SolicitudExamen.objects.filter(
                estado='COMPLETADO',
                fecha_solicitud__date=hoy
            ).count(),
            'total_hoy': SolicitudExamen.objects.filter(fecha_solicitud__date=hoy).count(),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar el estado de una solicitud"""
        solicitud = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        if nuevo_estado in ['PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'CANCELADO']:
            solicitud.estado = nuevo_estado
            solicitud.save()
            serializer = self.get_serializer(solicitud)
            return Response(serializer.data)
        
        return Response(
            {'error': 'Estado inválido'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class ResultadoExamenViewSet(viewsets.ModelViewSet):
    queryset = ResultadoExamen.objects.all()
    serializer_class = ResultadoExamenSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def por_solicitud(self, request):
        """Obtener resultados por solicitud"""
        solicitud_id = request.query_params.get('solicitud_id')
        if solicitud_id:
            resultados = ResultadoExamen.objects.filter(solicitud_id=solicitud_id)
            serializer = self.get_serializer(resultados, many=True)
            return Response(serializer.data)
        return Response({'error': 'solicitud_id requerido'}, status=400)


class ConsultaViewSet(viewsets.ModelViewSet):
    queryset = Consulta.objects.all()
    serializer_class = ConsultaSerializer
    permission_classes = [AllowAny]  # Temporal para desarrollo
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs  # Para desarrollo, mostrar todas
        if getattr(user, 'is_superuser', False) or user.rol.upper() == 'ADMIN':
            return qs
        if user.rol.upper() == 'MEDICO':
            try:
                return qs.filter(medico=user.medico)
            except Exception:
                return qs.none()
        # Para desarrollo, mostrar todas las consultas
        return qs
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Búsqueda de consultas por paciente"""
        paciente_id = request.query_params.get('paciente_id')
        query = request.query_params.get('q', '')
        
        consultas = Consulta.objects.all()
        
        if paciente_id:
            consultas = consultas.filter(historia_clinica__paciente_id=paciente_id)
        
        if query:
            consultas = consultas.filter(
                Q(motivo_consulta_detalle__icontains=query) |
                Q(diagnostico_presuntivo__icontains=query) |
                Q(medico__nombre__icontains=query) |
                Q(medico__apellido__icontains=query)
            )
        
        consultas = consultas.order_by('-fecha_hora_consulta')[:10]
        serializer = ConsultaSearchSerializer(consultas, many=True)
        return Response({'results': serializer.data})


class DiagnosticoViewSet(viewsets.ModelViewSet):
    queryset = Diagnostico.objects.all()
    serializer_class = DiagnosticoSerializer
    permission_classes = [IsAuthenticated]


class PrescripcionViewSet(viewsets.ModelViewSet):
    queryset = Prescripcion.objects.all()
    serializer_class = PrescripcionSerializer
    permission_classes = [IsAuthenticated]


class MedicamentoViewSet(viewsets.ModelViewSet):
    queryset = Medicamento.objects.filter(activo=True)
    serializer_class = MedicamentoSerializer
    permission_classes = [IsAuthenticated]
    
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
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    permission_classes = [AllowAny]  # Temporal para desarrollo
    
    def get_queryset(self):
        """
        Filtrar turnos según el rol del usuario:
        - Secretarias y admins: ven todos los turnos
        - Médicos: solo ven sus propios turnos
        - Pacientes: solo ven sus propios turnos
        """
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            return queryset  # Para desarrollo, mostrar todos
        
        # Superusuarios ven todo
        if self.request.user.is_superuser:
            return queryset
        
        # Secretarias y admins ven todos los turnos
        if self.request.user.rol.upper() in ['SECRETARIA', 'ADMIN']:
            return queryset
        
        # Médicos ven solo sus turnos
        if self.request.user.rol.upper() == 'MEDICO':
            try:
                medico = self.request.user.medico
                return queryset.filter(medico=medico)
            except:
                return queryset.none()
        
        # Pacientes ven solo sus turnos
        if self.request.user.rol.upper() == 'PACIENTE':
            try:
                paciente = self.request.user.paciente
                return queryset.filter(paciente=paciente)
            except:
                return queryset.none()
        
        return queryset  # Para desarrollo, mostrar todos
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TurnoCreateUpdateSerializer
        return TurnoSerializer
    
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
        
        turnos = Turno.objects.all()
        
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
        
        turnos = Turno.objects.filter(
            fecha_hora__date=fecha_obj,
            estado='DISPONIBLE'
        )
        
        if especialidad_id:
            turnos = turnos.filter(especialidad_id=especialidad_id)
        
        turnos = turnos.order_by('fecha_hora')
        serializer = self.get_serializer(turnos, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reservar(self, request, pk=None):
        """Reservar un turno"""
        turno = self.get_object()
        paciente_id = request.data.get('paciente_id')
        
        if not paciente_id:
            return Response({'error': 'paciente_id requerido'}, status=400)
        
        if turno.estado != 'DISPONIBLE':
            return Response({'error': 'Turno no disponible'}, status=400)
        
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
        
        # Verificar que el turno esté confirmado o realizado
        if turno.estado not in ['CONFIRMADO', 'REALIZADO']:
            return Response({'error': 'Solo se pueden crear consultas para turnos confirmados o realizados'}, status=400)
        
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


# Vista especial para el dashboard
class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]  # Cambiado para desarrollo
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas generales del dashboard"""
        hoy = timezone.now().date()
        
        # Estadísticas básicas
        total_pacientes = Paciente.objects.count()
        consultas_hoy = Consulta.objects.filter(fecha_hora_consulta__date=hoy).count()
        solicitudes_pendientes = SolicitudExamen.objects.filter(estado='PENDIENTE').count()
        resultados_listos = ResultadoExamen.objects.filter(
            fecha_resultado__date=hoy,
            es_normal=False
        ).count()
        
        # Consultas por especialidad
        consultas_por_especialidad = Consulta.objects.filter(
            fecha_hora_consulta__date=hoy
        ).values('medico__especialidad__nombre').annotate(
            total=Count('id')
        )
        
        # Solicitudes por estado
        solicitudes_por_estado = SolicitudExamen.objects.values('estado').annotate(
            total=Count('id')
        )
        
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
    from usuarios.serializers import UserSerializer
    
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)

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
        
        # Crear paciente
        paciente_data = {
            'antecedentes_personales': data.get('antecedentes_personales'),
            'antecedentes_familiares': data.get('antecedentes_familiares'),
        }
        
        Paciente.objects.create(user=user, dni=data['dni'], **paciente_data)
        
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
    permission_classes = [IsMedicoOrAdmin]  # Solo médicos y admins pueden gestionar internaciones
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrar por rol del usuario
        if hasattr(user, 'rol'):
            if user.rol.upper() == 'MEDICO':
                # Médicos ven sus propias internaciones
                try:
                    queryset = queryset.filter(medico_responsable=user.medico)
                except:
                    queryset = queryset.none()
            elif user.rol.upper() == 'ADMIN':
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
