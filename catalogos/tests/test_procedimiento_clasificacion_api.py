"""API catálogo procedimientos — clasificacion_quirurgica (Etapa A1).

Fuera de laboratorio/: no toca LIMS.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalogos.models import ProcedimientoCatalogo

User = get_user_model()


@pytest.fixture
def admin_client(db):
    user = User.objects.create_user(
        username=f"proc_cls_{uuid.uuid4().hex[:12]}",
        password="test-pass-123",
        rol="admin",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestProcedimientoClasificacionAPI:
    def test_list_incluye_clasificacion_sin_asignar(self, admin_client):
        nombre = f"API Proc list {uuid.uuid4().hex[:10]}"
        ProcedimientoCatalogo.objects.create(nombre=nombre, activo=True)
        r = admin_client.get("/api/procedimientos-catalogo/")
        assert r.status_code == 200
        rows = r.data if isinstance(r.data, list) else r.data.get("results", [])
        match = next((x for x in rows if x.get("nombre") == nombre), None)
        assert match is not None
        assert match["clasificacion_quirurgica"] == "SIN_ASIGNAR"

    def test_create_y_patch_clasificacion(self, admin_client):
        nombre = f"API Proc create {uuid.uuid4().hex[:10]}"
        r = admin_client.post(
            "/api/procedimientos-catalogo/",
            {
                "nombre": nombre,
                "descripcion": "",
                "activo": True,
                "clasificacion_quirurgica": "NO_QUIRURGICO",
            },
            format="json",
        )
        assert r.status_code in (200, 201), r.data
        assert r.data["clasificacion_quirurgica"] == "NO_QUIRURGICO"
        pk = r.data["id"]
        r2 = admin_client.patch(
            f"/api/procedimientos-catalogo/{pk}/",
            {"clasificacion_quirurgica": "QUIRURGICO"},
            format="json",
        )
        assert r2.status_code == 200, r2.data
        assert r2.data["clasificacion_quirurgica"] == "QUIRURGICO"

    def test_create_sin_campo_usa_default(self, admin_client):
        nombre = f"API Proc default {uuid.uuid4().hex[:10]}"
        r = admin_client.post(
            "/api/procedimientos-catalogo/",
            {"nombre": nombre, "activo": True},
            format="json",
        )
        assert r.status_code in (200, 201), r.data
        assert r.data["clasificacion_quirurgica"] == "SIN_ASIGNAR"

    def test_filtra_por_clasificacion_quirurgica(self, admin_client):
        nq = f"NQ {uuid.uuid4().hex[:8]}"
        q = f"Q {uuid.uuid4().hex[:8]}"
        ProcedimientoCatalogo.objects.create(
            nombre=nq, activo=True, clasificacion_quirurgica="NO_QUIRURGICO"
        )
        ProcedimientoCatalogo.objects.create(
            nombre=q, activo=True, clasificacion_quirurgica="QUIRURGICO"
        )
        r = admin_client.get(
            "/api/procedimientos-catalogo/",
            {"clasificacion_quirurgica": "NO_QUIRURGICO", "activo": "true"},
        )
        assert r.status_code == 200
        rows = r.data if isinstance(r.data, list) else r.data.get("results", [])
        nombres = {x.get("nombre") for x in rows}
        assert nq in nombres
        assert q not in nombres


@pytest.mark.django_db
class TestProcedimientoCatalogoPermisosSecretaria:
    def test_secretaria_lee_y_no_escribe(self, db):
        sec = User.objects.create_user(
            username=f"proc_sec_{uuid.uuid4().hex[:10]}",
            password="test-pass-123",
            rol="secretaria",
        )
        client = APIClient()
        client.force_authenticate(user=sec)
        ProcedimientoCatalogo.objects.create(
            nombre=f"Sec read {uuid.uuid4().hex[:8]}",
            activo=True,
            clasificacion_quirurgica="NO_QUIRURGICO",
        )
        r = client.get("/api/procedimientos-catalogo/", {"activo": "true"})
        assert r.status_code == 200
        r_post = client.post(
            "/api/procedimientos-catalogo/",
            {"nombre": f"Sec write {uuid.uuid4().hex[:8]}", "activo": True},
            format="json",
        )
        assert r_post.status_code in (403, 401)
