#!/usr/bin/env python3
"""
Script para corregir los grupos del usuario admin
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.contrib.auth.models import Group
from usuarios.models import User

def corregir_grupos_admin():
    """Corrige los grupos del usuario admin"""
    
    print("🔧 Corrigiendo grupos del usuario admin...")
    print("=" * 50)
    
    try:
        # Obtener el usuario admin
        admin_user = User.objects.get(username='admin')
        print(f"👤 Usuario admin encontrado: {admin_user.username}")
        print(f"🏆 Es superusuario: {admin_user.is_superuser}")
        print(f"👑 Es staff: {admin_user.is_staff}")
        
        # Mostrar grupos actuales
        grupos_actuales = list(admin_user.groups.all())
        print(f"👥 Grupos actuales: {[g.name for g in grupos_actuales]}")
        
        # Limpiar todos los grupos
        admin_user.groups.clear()
        print("🧹 Grupos limpiados")
        
        # Opción 1: No asignar ningún grupo (solo superusuario)
        print("✅ Admin configurado como superusuario sin grupos específicos")
        print("   Esto hará que aparezca como 'Administrador' en el sistema")
        
        # Opción 2: Asignar solo el grupo de administradores (si existe)
        try:
            grupo_admin = Group.objects.get(name='Administradores')
            admin_user.groups.add(grupo_admin)
            print(f"✅ Agregado al grupo: {grupo_admin.name}")
        except Group.DoesNotExist:
            print("ℹ️  No existe el grupo 'Administradores'")
        
        # Guardar cambios
        admin_user.save()
        
        # Verificar resultado
        grupos_finales = list(admin_user.groups.all())
        print(f"👥 Grupos finales: {[g.name for g in grupos_finales]}")
        
        print("\n🎉 Usuario admin corregido exitosamente!")
        print("   Ahora aparecerá como 'Administrador' en el sistema")
        
    except User.DoesNotExist:
        print("❌ Usuario admin no encontrado")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    corregir_grupos_admin()



