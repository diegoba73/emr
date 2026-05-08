"""
Tests de API (ViewSets) para catalogos — sin depender del URLconf global.
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from catalogos.views import (
    AreaInternacionViewSet,
    CamaInternacionViewSet,
    CentroFisicoViewSet,
    ProcedimientoViewSet,
    TipoAtencionViewSet,
)

User = get_user_model()


@pytest.fixture
def api_rf():
    return APIRequestFactory()


@pytest.fixture
def authenticated_user(db):
    return User.objects.create_user(
        username=f"cat_api_{uuid.uuid4().hex[:16]}",
        password="test-pass-123",
    )


@pytest.mark.django_db
class TestCatalogosViewSetsAuthenticated:
    def test_centros_fisicos_list_200(self, api_rf, authenticated_user):
        request = api_rf.get("/fake/")
        force_authenticate(request, user=authenticated_user)
        view = CentroFisicoViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code == 200

    def test_tipos_atencion_list_200(self, api_rf, authenticated_user):
        request = api_rf.get("/fake/")
        force_authenticate(request, user=authenticated_user)
        view = TipoAtencionViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code == 200

    def test_areas_internacion_list_200(self, api_rf, authenticated_user):
        request = api_rf.get("/fake/")
        force_authenticate(request, user=authenticated_user)
        view = AreaInternacionViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code == 200

    def test_camas_internacion_list_200(self, api_rf, authenticated_user):
        request = api_rf.get("/fake/")
        force_authenticate(request, user=authenticated_user)
        view = CamaInternacionViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code == 200

    def test_procedimientos_list_200_when_authenticated(self, api_rf, authenticated_user):
        request = api_rf.get("/fake/")
        force_authenticate(request, user=authenticated_user)
        view = ProcedimientoViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestProcedimientoViewSetUnauthenticated:
    def test_procedimientos_list_not_200_without_auth(self, api_rf):
        request = api_rf.get("/fake/")
        view = ProcedimientoViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code != 200
        assert response.status_code in (401, 403)
