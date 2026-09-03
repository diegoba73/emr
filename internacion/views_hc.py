from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated

from api.permissions import IsInternacionStaff
from usuarios.roles import ROLES_HC_ENFERMERIA, ROLES_HC_KINESIOLOGIA, ROLES_HC_MEDICO

from .hc_access import internacion_para_usuario, puede_escribir_hc
from .hc_sync import sincronizar_medicacion_habitual_texto
from .models import (
    BalanceHidrico,
    ControlEnfermeria,
    IndicacionMedica,
    MedicacionHabitualInternacion,
    MedicacionInternacion,
    NotaEnfermeria,
    RegistroKinesiologia,
)
from .serializers_hc import (
    BalanceHidricoSerializer,
    ControlEnfermeriaSerializer,
    IndicacionMedicaSerializer,
    MedicacionHabitualInternacionSerializer,
    MedicacionInternacionSerializer,
    NotaEnfermeriaHcSerializer,
    RegistroKinesiologiaSerializer,
)


class HcNestedViewSet(viewsets.ModelViewSet):
    pagination_class = None
    permission_classes = [IsAuthenticated, IsInternacionStaff]
    write_roles = frozenset()
    internacion_kwarg = 'internacion_pk'

    def get_internacion(self):
        return internacion_para_usuario(self.request, self.kwargs[self.internacion_kwarg])

    def get_queryset(self):
        internacion = self.get_internacion()
        return super().get_queryset().filter(internacion=internacion)

    def _assert_write(self):
        if self.request.method in SAFE_METHODS:
            return
        if not puede_escribir_hc(self.request, self.write_roles):
            raise PermissionDenied(
                'No tenés permiso para cargar o editar este formulario de internación.'
            )

    def create(self, request, *args, **kwargs):
        self._assert_write()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._assert_write()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._assert_write()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._assert_write()
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(internacion=self.get_internacion(), registrado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class IndicacionMedicaViewSet(HcNestedViewSet):
    queryset = IndicacionMedica.objects.select_related('registrado_por').all()
    serializer_class = IndicacionMedicaSerializer
    write_roles = ROLES_HC_MEDICO


class MedicacionInternacionViewSet(HcNestedViewSet):
    queryset = MedicacionInternacion.objects.select_related('registrado_por').all()
    serializer_class = MedicacionInternacionSerializer
    write_roles = ROLES_HC_MEDICO


class ControlEnfermeriaViewSet(HcNestedViewSet):
    queryset = ControlEnfermeria.objects.select_related('registrado_por').all()
    serializer_class = ControlEnfermeriaSerializer
    write_roles = ROLES_HC_ENFERMERIA


class BalanceHidricoViewSet(HcNestedViewSet):
    queryset = BalanceHidrico.objects.select_related('registrado_por').all()
    serializer_class = BalanceHidricoSerializer
    write_roles = ROLES_HC_ENFERMERIA


class NotaEnfermeriaHcViewSet(HcNestedViewSet):
    queryset = NotaEnfermeria.objects.select_related('registrado_por').all()
    serializer_class = NotaEnfermeriaHcSerializer
    write_roles = ROLES_HC_ENFERMERIA


class RegistroKinesiologiaViewSet(HcNestedViewSet):
    queryset = RegistroKinesiologia.objects.select_related('registrado_por').all()
    serializer_class = RegistroKinesiologiaSerializer
    write_roles = ROLES_HC_KINESIOLOGIA


class MedicacionHabitualInternacionViewSet(HcNestedViewSet):
    queryset = MedicacionHabitualInternacion.objects.select_related('registrado_por').all()
    serializer_class = MedicacionHabitualInternacionSerializer
    write_roles = ROLES_HC_MEDICO

    def perform_create(self, serializer):
        super().perform_create(serializer)
        sincronizar_medicacion_habitual_texto(self.get_internacion())

    def perform_update(self, serializer):
        super().perform_update(serializer)
        sincronizar_medicacion_habitual_texto(self.get_internacion())

    def perform_destroy(self, instance):
        internacion = instance.internacion
        super().perform_destroy(instance)
        sincronizar_medicacion_habitual_texto(internacion)
