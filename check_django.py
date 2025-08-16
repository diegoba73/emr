#!/usr/bin/env python
"""
Script simple para verificar Django
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')

try:
    import django
    django.setup()
    print("✅ Django configurado correctamente")
    
    # Verificar apps instaladas
    from django.apps import apps
    print(f"📱 Apps instaladas: {len(apps.get_app_configs())}")
    
    # Verificar configuración de usuario
    from django.conf import settings
    print(f"👤 AUTH_USER_MODEL: {getattr(settings, 'AUTH_USER_MODEL', 'No configurado')}")
    
    # Verificar si podemos importar nuestros modelos
    try:
        from usuarios.models import User
        print("✅ Modelo User importado correctamente")
    except Exception as e:
        print(f"❌ Error importando User: {e}")
    
    try:
        from pacientes.models import Paciente
        print("✅ Modelo Paciente importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Paciente: {e}")
    
    try:
        from medicos.models import Medico
        print("✅ Modelo Medico importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Medico: {e}")
    
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    import traceback
    traceback.print_exc()


