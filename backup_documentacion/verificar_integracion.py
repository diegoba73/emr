#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from usuarios.models import User, Secretaria
from medicos.models import Medico
from pacientes.models import Paciente

def verificar_integracion():
    print("🔍 VERIFICACIÓN DE INTEGRACIÓN DE USUARIOS")
    print("=" * 50)
    
    # 1. Verificar usuarios por rol
    print("\n📊 USUARIOS POR ROL:")
    print("-" * 30)
    total_users = User.objects.count()
    users_medico = User.objects.filter(rol='medico').count()
    users_paciente = User.objects.filter(rol='paciente').count()
    users_secretaria = User.objects.filter(rol='secretaria').count()
    users_admin = User.objects.filter(rol='admin').count()
    
    print(f"Total de usuarios: {total_users}")
    print(f"Usuarios con rol 'médico': {users_medico}")
    print(f"Usuarios con rol 'paciente': {users_paciente}")
    print(f"Usuarios con rol 'secretaria': {users_secretaria}")
    print(f"Usuarios con rol 'admin': {users_admin}")
    
    # 2. Verificar modelos específicos
    print("\n🏥 MODELOS ESPECÍFICOS:")
    print("-" * 30)
    total_medicos = Medico.objects.count()
    total_pacientes = Paciente.objects.count()
    total_secretarias = Secretaria.objects.count()
    
    print(f"Total de médicos: {total_medicos}")
    print(f"Total de pacientes: {total_pacientes}")
    print(f"Total de secretarias: {total_secretarias}")
    
    # 3. Verificar relaciones
    print("\n🔗 VERIFICACIÓN DE RELACIONES:")
    print("-" * 30)
    
    # Médicos
    medicos_con_user = 0
    for medico in Medico.objects.all():
        if hasattr(medico, 'user') and medico.user:
            medicos_con_user += 1
    
    # Pacientes
    pacientes_con_user = 0
    for paciente in Paciente.objects.all():
        if hasattr(paciente, 'user') and paciente.user:
            pacientes_con_user += 1
    
    # Secretarias
    secretarias_con_user = 0
    for secretaria in Secretaria.objects.all():
        if hasattr(secretaria, 'user') and secretaria.user:
            secretarias_con_user += 1
    
    print(f"Médicos con User: {medicos_con_user}/{total_medicos}")
    print(f"Pacientes con User: {pacientes_con_user}/{total_pacientes}")
    print(f"Secretarias con User: {secretarias_con_user}/{total_secretarias}")
    
    # 4. Detalle de usuarios
    print("\n👥 DETALLE DE USUARIOS:")
    print("-" * 30)
    for user in User.objects.all():
        print(f"- {user.username}: {user.first_name} {user.last_name} (Rol: {user.rol})")
    
    # 5. Detalle de médicos
    print("\n👨‍⚕️ DETALLE DE MÉDICOS:")
    print("-" * 30)
    for medico in Medico.objects.all():
        print(f"- {medico.user.username}: {medico.user.first_name} {medico.user.last_name} (Matrícula: {medico.matricula})")
    
    # 6. Análisis de integración
    print("\n✅ ANÁLISIS DE INTEGRACIÓN:")
    print("-" * 30)
    
    # Verificar si hay usuarios con rol médico pero sin modelo Medico
    users_medico_sin_modelo = 0
    for user in User.objects.filter(rol='medico'):
        if not hasattr(user, 'medico'):
            users_medico_sin_modelo += 1
    
    # Verificar si hay usuarios con rol paciente pero sin modelo Paciente
    users_paciente_sin_modelo = 0
    for user in User.objects.filter(rol='paciente'):
        if not hasattr(user, 'paciente'):
            users_paciente_sin_modelo += 1
    
    # Verificar si hay usuarios con rol secretaria pero sin modelo Secretaria
    users_secretaria_sin_modelo = 0
    for user in User.objects.filter(rol='secretaria'):
        if not hasattr(user, 'secretaria'):
            users_secretaria_sin_modelo += 1
    
    print(f"Usuarios 'médico' sin modelo Medico: {users_medico_sin_modelo}")
    print(f"Usuarios 'paciente' sin modelo Paciente: {users_paciente_sin_modelo}")
    print(f"Usuarios 'secretaria' sin modelo Secretaria: {users_secretaria_sin_modelo}")
    
    # 7. Resumen final
    print("\n🎯 RESUMEN FINAL:")
    print("-" * 30)
    
    integracion_completa = True
    problemas = []
    
    if users_medico_sin_modelo > 0:
        integracion_completa = False
        problemas.append(f"{users_medico_sin_modelo} usuarios médicos sin modelo Medico")
    
    if users_paciente_sin_modelo > 0:
        integracion_completa = False
        problemas.append(f"{users_paciente_sin_modelo} usuarios pacientes sin modelo Paciente")
    
    if users_secretaria_sin_modelo > 0:
        integracion_completa = False
        problemas.append(f"{users_secretaria_sin_modelo} usuarios secretarias sin modelo Secretaria")
    
    if total_medicos != users_medico:
        integracion_completa = False
        problemas.append("Discrepancia entre usuarios médicos y modelos Medico")
    
    if total_pacientes != users_paciente:
        integracion_completa = False
        problemas.append("Discrepancia entre usuarios pacientes y modelos Paciente")
    
    if total_secretarias != users_secretaria:
        integracion_completa = False
        problemas.append("Discrepancia entre usuarios secretarias y modelos Secretaria")
    
    if integracion_completa:
        print("✅ INTEGRACIÓN COMPLETA: Todos los usuarios están correctamente integrados")
    else:
        print("❌ INTEGRACIÓN INCOMPLETA: Se encontraron los siguientes problemas:")
        for problema in problemas:
            print(f"   - {problema}")
    
    return integracion_completa

if __name__ == "__main__":
    verificar_integracion()
