"""Fixtures compartidas para tests de solicitudes."""

import pytest
from django.contrib.auth import get_user_model

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.fixture
def esp_cardiologia(db):
    esp, _ = Especialidad.objects.get_or_create(
        nombre='Cardiología',
        defaults={'descripcion': 'Test solicitudes'},
    )
    return esp


@pytest.fixture
def esp_neurologia(db):
    esp, _ = Especialidad.objects.get_or_create(
        nombre='Neurología',
        defaults={'descripcion': 'Test solicitudes'},
    )
    return esp


@pytest.fixture
def paciente_a(db):
    return Paciente.objects.create(dni='SOL-P-001', nombre='Ana', apellido='Test')


@pytest.fixture
def paciente_b(db):
    return Paciente.objects.create(dni='SOL-P-002', nombre='Bruno', apellido='Test')


@pytest.fixture
def medico_profile(db, esp_cardiologia):
    user = User.objects.create_user(
        username='med_sol_perm',
        email='med-sol@test.com',
        password='x',
        rol='medico',
    )
    medico = Medico.objects.create(
        user=user,
        matricula='SOL-M-001',
        nombre='Dr',
        apellido='Vinculado',
        especialidad=esp_cardiologia,
    )
    return medico


@pytest.fixture
def medico_otro(db, esp_cardiologia):
    user = User.objects.create_user(
        username='med_sol_otro',
        email='med-otro@test.com',
        password='x',
        rol='medico',
    )
    return Medico.objects.create(
        user=user,
        matricula='SOL-M-002',
        nombre='Dr',
        apellido='Ajeno',
        especialidad=esp_cardiologia,
    )
