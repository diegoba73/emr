#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.contrib.auth.models import Group
from usuarios.models import User

def asignar_grupos_usuarios():
    """Asignar grupos a usuarios existentes según su rol"""
    
    print("👥 ASIGNANDO GRUPOS A USUARIOS")
    print("=" * 40)
    
    # Crear grupos si no existen
    grupos = {
        'Pacientes': Group.objects.get_or_create(name='Pacientes')[0],
        'Médicos': Group.objects.get_or_create(name='Médicos')[0],
        'Secretarias': Group.objects.get_or_create(name='Secretarias')[0],
        'Laboratorio': Group.objects.get_or_create(name='Laboratorio')[0],
    }
    
    print("Grupos disponibles:")
    for nombre, grupo in grupos.items():
        print(f"  - {nombre}: {grupo}")
    
    # Asignar grupos según rol
    usuarios_actualizados = 0
    
    for user in User.objects.filter(is_active=True):
        print(f"\n👤 Procesando usuario: {user.username} (Rol: {user.rol})")
        
        # Limpiar grupos existentes
        user.groups.clear()
        
        # Asignar grupo según rol
        if user.rol == 'paciente':
            user.groups.add(grupos['Pacientes'])
            print(f"  ✅ Asignado grupo: Pacientes")
        elif user.rol == 'medico':
            user.groups.add(grupos['Médicos'])
            print(f"  ✅ Asignado grupo: Médicos")
        elif user.rol == 'secretaria':
            user.groups.add(grupos['Secretarias'])
            print(f"  ✅ Asignado grupo: Secretarias")
        elif user.rol == 'admin':
            # Los admins pueden tener acceso a todo
            user.groups.add(grupos['Pacientes'], grupos['Médicos'], grupos['Secretarias'])
            print(f"  ✅ Asignado grupos: Pacientes, Médicos, Secretarias")
        else:
            print(f"  ⚠️  Rol no reconocido: {user.rol}")
            continue
        
        usuarios_actualizados += 1
    
    print(f"\n🎉 Proceso completado!")
    print(f"✅ Usuarios actualizados: {usuarios_actualizados}")

def verificar_grupos():
    """Verificar que los grupos se asignaron correctamente"""
    
    print("\n🔍 VERIFICANDO ASIGNACIÓN DE GRUPOS")
    print("-" * 40)
    
    for user in User.objects.filter(is_active=True)[:10]:
        groups = list(user.groups.values_list('name', flat=True))
        print(f"👤 {user.username}")
        print(f"   Rol: {user.rol}")
        print(f"   Grupos: {groups}")
        print()

if __name__ == "__main__":
    asignar_grupos_usuarios()
    verificar_grupos()
