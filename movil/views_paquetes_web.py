"""CRUD web de paquetes lab móvil (catálogo institucional)."""

from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, viewsets

from api.permissions import LimsTipoExamenCatalogPermission
from auditoria.audit_service import log_create, log_update
from laboratorio.models import PanelExamen, TipoExamen

from .models import CONTEXTO_LAB_CHOICES, PaqueteLabContexto


class PaqueteLabContextoSerializer(serializers.ModelSerializer):
    paneles_ids = serializers.PrimaryKeyRelatedField(
        source='paneles',
        queryset=PanelExamen.objects.filter(activo=True),
        many=True,
        required=False,
    )
    examenes_ids = serializers.PrimaryKeyRelatedField(
        source='examenes',
        queryset=TipoExamen.objects.filter(activo=True),
        many=True,
        required=False,
    )
    paneles_detalle = serializers.SerializerMethodField()
    examenes_detalle = serializers.SerializerMethodField()
    contexto_display = serializers.SerializerMethodField()

    class Meta:
        model = PaqueteLabContexto
        fields = [
            'id',
            'codigo',
            'nombre',
            'contexto',
            'contexto_display',
            'descripcion',
            'activo',
            'orden',
            'paneles_ids',
            'examenes_ids',
            'paneles_detalle',
            'examenes_detalle',
        ]
        read_only_fields = ['id']

    def get_contexto_display(self, obj):
        return dict(CONTEXTO_LAB_CHOICES).get(obj.contexto, obj.contexto)

    def get_paneles_detalle(self, obj):
        return [
            {'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre}
            for p in obj.paneles.all()
        ]

    def get_examenes_detalle(self, obj):
        return [
            {'id': e.id, 'codigo': e.codigo, 'nombre': e.nombre}
            for e in obj.examenes.all()
        ]

    def validate_codigo(self, value):
        codigo = (value or '').strip().upper()
        if not codigo:
            raise serializers.ValidationError('El código es obligatorio.')
        qs = PaqueteLabContexto.objects.filter(codigo__iexact=codigo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un paquete con ese código.')
        return codigo

    def validate_nombre(self, value):
        nombre = (value or '').strip()
        if not nombre:
            raise serializers.ValidationError('El nombre es obligatorio.')
        return nombre

    def validate(self, attrs):
        paneles = attrs.get('paneles')
        examenes = attrs.get('examenes')
        if self.instance is None:
            if paneles is None:
                paneles = []
            if examenes is None:
                examenes = []
            if not paneles and not examenes:
                raise serializers.ValidationError(
                    'Agregá al menos un panel o un examen al paquete.'
                )
        elif paneles is not None or examenes is not None:
            p = paneles if paneles is not None else list(self.instance.paneles.all())
            e = examenes if examenes is not None else list(self.instance.examenes.all())
            if not p and not e and attrs.get('activo', self.instance.activo):
                raise serializers.ValidationError(
                    'Un paquete activo necesita al menos un panel o un examen.'
                )
        return attrs

    def create(self, validated_data):
        paneles = validated_data.pop('paneles', [])
        examenes = validated_data.pop('examenes', [])
        obj = PaqueteLabContexto.objects.create(**validated_data)
        if paneles:
            obj.paneles.set(paneles)
        if examenes:
            obj.examenes.set(examenes)
        return obj

    def update(self, instance, validated_data):
        paneles = validated_data.pop('paneles', None)
        examenes = validated_data.pop('examenes', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if paneles is not None:
            instance.paneles.set(paneles)
        if examenes is not None:
            instance.examenes.set(examenes)
        return instance


class PaqueteLabContextoViewSet(viewsets.ModelViewSet):
    """Paquetes por contexto para pedidos desde la app móvil."""

    queryset = (
        PaqueteLabContexto.objects.all()
        .prefetch_related('paneles', 'examenes')
        .order_by('contexto', 'orden', 'nombre')
    )
    serializer_class = PaqueteLabContextoSerializer
    permission_classes = [LimsTipoExamenCatalogPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'contexto']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering_fields = ['contexto', 'orden', 'nombre', 'codigo']
    ordering = ['contexto', 'orden', 'nombre']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            module='movil',
            metadata={'accion': 'crear_paquete_lab_movil', 'view': 'PaqueteLabContextoViewSet'},
        )

    def perform_update(self, serializer):
        before = {
            'codigo': serializer.instance.codigo,
            'activo': serializer.instance.activo,
            'contexto': serializer.instance.contexto,
        }
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            before=before,
            module='movil',
            metadata={'accion': 'editar_paquete_lab_movil', 'view': 'PaqueteLabContextoViewSet'},
        )
