"""Operadores LIMS: lectura de internación y contexto de revista (sin escritura clínica)."""
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from catalogos.models import DiagnosticoCIE10
from internacion.models import Sector, Cama, Internacion
from internacion.tests.helpers import unique_cie10_code, unique_suffix
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.origen_solicitud import INTERNACION_UCO
from pacientes.models import Paciente

User = get_user_model()


class LimsInternacionLecturaTestCase(APITestCase):
    def setUp(self):
        suffix = unique_suffix()
        self.laboratorio = User.objects.create_user(
            username=f'lab-int-{suffix}',
            password='x',
            email=f'lab-int-{suffix}@test.com',
            rol='laboratorio',
        )
        self.bioquimico = User.objects.create_user(
            username=f'bio-int-{suffix}',
            password='x',
            email=f'bio-int-{suffix}@test.com',
            rol='bioquimico',
        )
        self.paciente = Paciente.objects.create(
            nombre='Luis',
            apellido='Perez',
            dni=f'LAB-{suffix}',
        )
        self.sector = Sector.objects.create(nombre=f'UCO-lab-{suffix}')
        self.cama = Cama.objects.create(
            nombre=f'C-lab-{suffix}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        self.cie = DiagnosticoCIE10.objects.create(
            codigo=unique_cie10_code('I'),
            descripcion='Otras arritmias cardiacas especificadas',
            categoria='Cardiología',
            capitulo='IX',
            enfermedad='Arritmia',
        )
        self.internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=self.cama,
            diagnostico_cie=self.cie,
            diagnostico_ingreso='Arritmia',
            activo=True,
        )
        tipo_muestra = TipoMuestra.objects.create(
            codigo=f'TM{suffix}'[:20],
            nombre=f'Muestra {suffix}',
        )
        tipo_examen = TipoExamen.objects.create(
            codigo=f'TE{suffix}'[:20],
            nombre=f'Examen {suffix}',
            tipo_muestra_requerida=tipo_muestra,
            precio=10,
            activo=True,
        )
        self.solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud=INTERNACION_UCO,
            estado='FINALIZADO',
        )
        self.solicitud.tipos_examen.add(tipo_examen)

    def _assert_lectura_y_revista(self, user):
        self.client.force_authenticate(user=user)
        detalle = self.client.get(f'/api/internacion/internaciones/{self.internacion.id}/')
        self.assertEqual(detalle.status_code, status.HTTP_200_OK, detalle.data)
        self.assertEqual(detalle.data['id'], self.internacion.id)

        listado = self.client.get('/api/internacion/internaciones/')
        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        payload = listado.data['results'] if isinstance(listado.data, dict) else listado.data
        self.assertTrue(any(i['id'] == self.internacion.id for i in payload))

        revista = self.client.get(
            f'/api/internacion/internaciones/{self.internacion.id}/contexto-revista/'
        )
        self.assertEqual(revista.status_code, status.HTTP_200_OK, revista.data)
        labs = revista.data.get('laboratorio') or []
        self.assertTrue(any(lab['id'] == self.solicitud.id for lab in labs), labs)

        # Solo lectura: no pueden ingresar.
        cama_libre = Cama.objects.create(
            nombre=f'C-libre-{unique_suffix()}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        paciente_libre = Paciente.objects.create(
            nombre='Ana',
            apellido='Lopez',
            dni=f'LAB-IN-{unique_suffix()}',
        )
        crear = self.client.post(
            '/api/internacion/internaciones/',
            {
                'paciente': paciente_libre.id,
                'cama': cama_libre.id,
                'diagnostico_ingreso': 'Intento LIMS',
            },
            format='json',
        )
        self.assertEqual(crear.status_code, status.HTTP_403_FORBIDDEN)

    def test_laboratorio_ve_internacion_y_ordenes_revista(self):
        self._assert_lectura_y_revista(self.laboratorio)

    def test_bioquimico_ve_internacion_y_ordenes_revista(self):
        self._assert_lectura_y_revista(self.bioquimico)
