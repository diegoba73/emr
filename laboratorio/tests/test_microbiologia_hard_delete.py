"""
Tests API — hard delete en cascada de registros clínicos de microbiología.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    Microorganismo,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)
from laboratorio.tests.test_microbiologia_api import _setup_estudio_con_lectura

User = get_user_model()


@pytest.mark.django_db
class TestMicrobiologiaHardDeleteAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_hd_{self.suf}",
            email=f"lhd{self.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.bio = User.objects.create_user(
            username=f"bio_hd_{self.suf}",
            email=f"bhd{self.suf}@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_hd_{self.suf}",
            email=f"mhd{self.suf}@t.com",
            password="x",
            rol="medico",
        )
        self.ctx = _setup_estudio_con_lectura(self.suf, self.lab, self.med_user)
        self.micro = Microorganismo.objects.create(
            codigo=f"EC{self.suf}",
            nombre="E. coli",
            genero="Escherichia",
            especie="coli",
            activo=True,
        )
        self.antibiotico = Antibiotico.objects.create(
            codigo=f"AMP{self.suf}",
            nombre="Ampicilina",
            activo=True,
        )
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def _build_cadena(self):
        aislado = AisladoMicrobiologico.objects.create(
            estudio=self.ctx["estudio"],
            lectura_origen=self.ctx["lectura"],
            microorganismo=self.micro,
            estado="IDENTIFICADO",
            requiere_antibiograma=True,
        )
        ident = IdentificacionMicroorganismo.objects.create(
            aislado=aislado,
            microorganismo=self.micro,
            metodo="MALDI",
            resultado="E. coli",
        )
        ab = Antibiograma.objects.create(aislado=aislado, estado="EN_PROCESO")
        res = ResultadoAntibiotico.objects.create(
            antibiograma=ab,
            antibiotico=self.antibiotico,
            interpretacion="S",
        )
        return {
            "aislado": aislado,
            "ident": ident,
            "ab": ab,
            "res": res,
            "siembra": self.ctx["siembra"],
            "lectura": self.ctx["lectura"],
        }

    def test_delete_siembra_cascada_y_audita(self):
        cadena = self._build_cadena()
        sid = cadena["siembra"].pk
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.delete(f"/api/lab/microbiologia/siembras/{sid}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, r.content)
        self.assertFalse(SiembraMicrobiologia.objects.filter(pk=sid).exists())
        self.assertFalse(LecturaCultivo.objects.filter(pk=cadena["lectura"].pk).exists())
        self.assertFalse(AisladoMicrobiologico.objects.filter(pk=cadena["aislado"].pk).exists())
        self.assertFalse(IdentificacionMicroorganismo.objects.filter(pk=cadena["ident"].pk).exists())
        self.assertFalse(Antibiograma.objects.filter(pk=cadena["ab"].pk).exists())
        self.assertFalse(ResultadoAntibiotico.objects.filter(pk=cadena["res"].pk).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=SiembraMicrobiologia._meta.label,
                entity_id=str(sid),
                action="DELETE",
                metadata__accion="eliminar_siembra",
            ).exists()
        )

    def test_delete_aislado_cascada_parcial(self):
        cadena = self._build_cadena()
        aid = cadena["aislado"].pk
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.delete(f"/api/lab/microbiologia/aislados/{aid}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AisladoMicrobiologico.objects.filter(pk=aid).exists())
        self.assertFalse(Antibiograma.objects.filter(pk=cadena["ab"].pk).exists())
        self.assertFalse(ResultadoAntibiotico.objects.filter(pk=cadena["res"].pk).exists())
        # Siembra/lectura permanecen
        self.assertTrue(SiembraMicrobiologia.objects.filter(pk=cadena["siembra"].pk).exists())
        self.assertTrue(LecturaCultivo.objects.filter(pk=cadena["lectura"].pk).exists())

    def test_delete_antibiograma_con_resultados(self):
        cadena = self._build_cadena()
        abid = cadena["ab"].pk
        r = self.client.delete(f"/api/lab/microbiologia/antibiogramas/{abid}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Antibiograma.objects.filter(pk=abid).exists())
        self.assertFalse(ResultadoAntibiotico.objects.filter(pk=cadena["res"].pk).exists())
        self.assertTrue(AisladoMicrobiologico.objects.filter(pk=cadena["aislado"].pk).exists())

    def test_delete_bloqueado_estudio_validado(self):
        cadena = self._build_cadena()
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="VALIDADO")
        r = self.client.delete(f"/api/lab/microbiologia/siembras/{cadena['siembra'].pk}/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SiembraMicrobiologia.objects.filter(pk=cadena["siembra"].pk).exists())

    def test_delete_bloqueado_estudio_informado(self):
        cadena = self._build_cadena()
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="INFORMADO")
        r = self.client.delete(f"/api/lab/microbiologia/aislados/{cadena['aislado'].pk}/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_informe_borrador_y_emitido(self):
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        self.client.force_authenticate(self.bio)
        r = self.client.post(
            "/api/lab/microbiologia/informes/",
            {
                "estudio_id": self.ctx["estudio"].pk,
                "tipo": "PRELIMINAR",
                "texto": "borrador",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        iid = r.json()["id"]
        with self.captureOnCommitCallbacks(execute=True):
            r_del = self.client.delete(f"/api/lab/microbiologia/informes/{iid}/")
        self.assertEqual(r_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformeMicrobiologia.objects.filter(pk=iid).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=InformeMicrobiologia._meta.label,
                entity_id=str(iid),
                action="DELETE",
                metadata__accion="eliminar_informe",
            ).exists()
        )

        r2 = self.client.post(
            "/api/lab/microbiologia/informes/",
            {
                "estudio_id": self.ctx["estudio"].pk,
                "tipo": "PRELIMINAR",
                "texto": "otro",
            },
            format="json",
        )
        iid2 = r2.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid2}/emitir/",
            {"texto": "Emitido para borrar."},
            format="json",
        )
        r_del2 = self.client.delete(f"/api/lab/microbiologia/informes/{iid2}/")
        self.assertEqual(r_del2.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformeMicrobiologia.objects.filter(pk=iid2).exists())

    def test_anular_informe_sigue_disponible(self):
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        self.client.force_authenticate(self.bio)
        r = self.client.post(
            "/api/lab/microbiologia/informes/",
            {
                "estudio_id": self.ctx["estudio"].pk,
                "tipo": "PRELIMINAR",
                "texto": "x",
            },
            format="json",
        )
        iid = r.json()["id"]
        r2 = self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/anular/",
            {"motivo": "error de tipeo"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.assertEqual(r2.json()["estado"], "ANULADO")
        # Luego se puede hard-delete el anulado
        r3 = self.client.delete(f"/api/lab/microbiologia/informes/{iid}/")
        self.assertEqual(r3.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformeMicrobiologia.objects.filter(pk=iid).exists())

    def test_delete_resultado_antibiotico(self):
        cadena = self._build_cadena()
        rid = cadena["res"].pk
        r = self.client.delete(f"/api/lab/microbiologia/resultados-antibiotico/{rid}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResultadoAntibiotico.objects.filter(pk=rid).exists())
        self.assertTrue(Antibiograma.objects.filter(pk=cadena["ab"].pk).exists())

    def test_delete_identificacion(self):
        cadena = self._build_cadena()
        iid = cadena["ident"].pk
        r = self.client.delete(f"/api/lab/microbiologia/identificaciones/{iid}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(IdentificacionMicroorganismo.objects.filter(pk=iid).exists())
        self.assertTrue(AisladoMicrobiologico.objects.filter(pk=cadena["aislado"].pk).exists())
