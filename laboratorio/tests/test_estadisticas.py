"""Tests API Estadísticas LIMS (agregados, sin PHI)."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente

User = get_user_model()

BASE = '/api/lab/estadisticas'


class TestEstadisticasLimsApi(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='adm_est', password='x', rol='admin')
        self.bio = User.objects.create_user(username='bio_est', password='x', rol='bioquimico')
        self.sec_lab = User.objects.create_user(
            username='seclab_est', password='x', rol='secretaria_lab'
        )
        self.sec = User.objects.create_user(username='sec_est', password='x', rol='secretaria')
        self.lab = User.objects.create_user(username='lab_est', password='x', rol='laboratorio')
        self.med = User.objects.create_user(username='med_est', password='x', rol='medico')

        self.pac = Paciente.objects.create(
            dni='EST001',
            nombre='E',
            apellido='Stats',
            obra_social='osde',
        )
        self.tm = TipoMuestra.objects.create(codigo='SANGRE_EST', nombre='Sangre', activo=True)
        self.te = TipoExamen.objects.create(
            codigo='GLU',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )

        aware = timezone.is_aware(timezone.now())
        f1 = datetime(2026, 10, 10, 10, 0, 0)
        if aware:
            f1 = timezone.make_aware(f1)

        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac,
            origen_solicitud='GUARDIA',
            estado='EN_PROCESO',
            numero='EST-2026-0001',
            obra_social_orden='OSDE',
        )
        ResultadoExamen.objects.create(
            solicitud=self.sol,
            tipo_examen=self.te,
            valor_obtenido='90',
        )
        SolicitudExamen.objects.filter(pk=self.sol.pk).update(
            fecha_solicitud=f1,
            estado='FINALIZADO',
        )
        self.sol.refresh_from_db()
        self.client = APIClient()
        self.params = {'desde': '2026-10-01', 'hasta': '2026-10-31'}

    def test_resumen_ok_roles_permitidos(self):
        for user in (self.admin, self.bio, self.sec_lab):
            self.client.force_authenticate(user=user)
            r = self.client.get(f'{BASE}/resumen/', self.params)
            self.assertEqual(r.status_code, 200, user.rol)
            self.assertEqual(r.data['total_ordenes'], 1)
            self.assertEqual(r.data['total_examenes'], 1)
            self.assertGreaterEqual(len(r.data['top_examenes']), 1)
            self.assertNotIn('paciente', str(r.data).lower())

    def test_resumen_forbidden_otros_roles(self):
        for user in (self.sec, self.lab, self.med):
            self.client.force_authenticate(user=user)
            r = self.client.get(f'{BASE}/resumen/', self.params)
            self.assertEqual(r.status_code, 403, user.rol)

    def test_series_y_desgloses(self):
        self.client.force_authenticate(user=self.bio)
        r = self.client.get(f'{BASE}/series/', {**self.params, 'granularidad': 'mes'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['granularidad'], 'mes')
        self.assertTrue(any(p['ordenes'] >= 1 for p in r.data['puntos']))

        for path in ('por-examen', 'por-obra-social', 'por-origen', 'por-estado'):
            rr = self.client.get(f'{BASE}/{path}/', self.params)
            self.assertEqual(rr.status_code, 200, path)
            self.assertGreaterEqual(rr.data['total'], 1)
            self.assertTrue(rr.data['items'])

    def test_export_csv(self):
        self.client.force_authenticate(user=self.sec_lab)
        r = self.client.get(f'{BASE}/export.csv', {**self.params, 'dimension': 'examen'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        body = r.content.decode('utf-8')
        self.assertIn('codigo', body)
        self.assertIn('GLU', body)
