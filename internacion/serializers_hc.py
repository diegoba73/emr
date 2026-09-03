from rest_framework import serializers

from .models import (
    BalanceHidrico,
    ControlEnfermeria,
    IndicacionMedica,
    MedicacionHabitualInternacion,
    MedicacionInternacion,
    NotaEnfermeria,
    RegistroKinesiologia,
)


def _nombre_usuario(user):
    if not user:
        return None
    full = f'{user.last_name or ""}, {user.first_name or ""}'.strip(', ')
    return full or user.username


class IndicacionMedicaSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = IndicacionMedica
        fields = (
            'id',
            'internacion',
            'fecha',
            'registrado_por',
            'registrado_por_nombre',
            'hidratacion',
            'oxigenoterapia',
            'reposo',
            'controles',
            'precauciones',
            'indicaciones',
            'vigente',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)


class MedicacionInternacionSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MedicacionInternacion
        fields = (
            'id',
            'internacion',
            'fecha',
            'registrado_por',
            'registrado_por_nombre',
            'medicamento',
            'dosis',
            'via',
            'frecuencia',
            'horario',
            'activa',
            'observaciones',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)


class ControlEnfermeriaSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ControlEnfermeria
        fields = (
            'id',
            'internacion',
            'fecha',
            'turno',
            'registrado_por',
            'registrado_por_nombre',
            'tension_arterial',
            'frecuencia_cardiaca',
            'frecuencia_respiratoria',
            'temperatura',
            'saturacion_oxigeno',
            'dolor',
            'glucemia',
            'observaciones',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)


class BalanceHidricoSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = BalanceHidrico
        fields = (
            'id',
            'internacion',
            'fecha',
            'turno',
            'registrado_por',
            'registrado_por_nombre',
            'ingresos_vo_ml',
            'ingresos_ev_ml',
            'diuresis_ml',
            'otros_egresos_ml',
            'observaciones',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)


class NotaEnfermeriaHcSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = NotaEnfermeria
        fields = (
            'id',
            'internacion',
            'fecha',
            'registrado_por',
            'registrado_por_nombre',
            'observaciones',
            'curaciones',
            'dispositivos',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)


class RegistroKinesiologiaSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RegistroKinesiologia
        fields = (
            'id',
            'internacion',
            'fecha',
            'registrado_por',
            'registrado_por_nombre',
            'frecuencia_respiratoria',
            'saturacion_oxigeno',
            'oxigenoterapia',
            'secreciones',
            'tecnica',
            'movilizacion',
            'evolucion',
            'plan',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)


class MedicacionHabitualInternacionSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MedicacionHabitualInternacion
        fields = (
            'id',
            'internacion',
            'fecha',
            'registrado_por',
            'registrado_por_nombre',
            'medicamento',
            'dosis_mg_dia',
        )
        read_only_fields = ('internacion', 'fecha', 'registrado_por')

    def get_registrado_por_nombre(self, obj):
        return _nombre_usuario(obj.registrado_por)
