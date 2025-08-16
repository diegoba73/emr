#!/usr/bin/env python
"""
Script para probar las APIs de autenticación
"""
import requests
import json

# ============================================================================
# CONFIGURACIÓN - EDITA ESTOS VALORES CON TUS USUARIOS REALES
# ============================================================================

# Usuarios reales creados en Django Admin
TEST_USERS = [
    {
        'username': 'medico_prueba',
        'password': '1234@asd',
        'description': 'Médico'
    },
    {
        'username': 'secretaria_prueba',
        'password': '1234@asd',
        'description': 'Secretaria'
    },
    {
        'username': 'paciente_prueba',
        'password': '1234@asd',
        'description': 'Paciente'
    },
    {
        'username': 'labo_prueba',
        'password': '1234@asd',
        'description': 'Laboratorio'
    }
]

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'
SESSION = requests.Session()

def test_login(username, password, description):
    """Probar login con credenciales específicas"""
    print(f"\n🔐 Probando login con {description} ({username})...")
    
    login_data = {
        'username': username,
        'password': password
    }
    
    try:
        response = SESSION.post(f'{BASE_URL}/auth/login/', json=login_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login exitoso!")
            print(f"Usuario: {data['user']['username']}")
            print(f"Grupos: {data['user']['groups']}")
            print(f"Staff: {data['user']['is_staff']}")
            return True
        else:
            print(f"❌ Login falló: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_current_user():
    """Probar obtener usuario actual"""
    print("\n👤 Probando obtener usuario actual...")
    
    try:
        response = SESSION.get(f'{BASE_URL}/auth/current-user/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Usuario actual obtenido!")
            print(f"Usuario: {data['username']}")
            print(f"Grupos: {data['groups']}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_users():
    """Probar listar usuarios (solo para staff)"""
    print("\n👥 Probando listar usuarios...")
    
    try:
        response = SESSION.get(f'{BASE_URL}/auth/users/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Usuarios obtenidos!")
            print(f"Total usuarios: {len(data)}")
            for user in data[:5]:  # Mostrar solo los primeros 5
                print(f"  - {user['username']} ({', '.join(user['groups'])}) - Staff: {user['is_staff']}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_groups():
    """Probar listar grupos"""
    print("\n🏷️  Probando listar grupos...")
    
    try:
        response = SESSION.get(f'{BASE_URL}/auth/groups/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Grupos obtenidos!")
            for group in data:
                print(f"  - {group['name']} ({group['user_count']} usuarios)")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_logout():
    """Probar logout"""
    print("\n🚪 Probando logout...")
    
    try:
        response = SESSION.post(f'{BASE_URL}/auth/logout/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Logout exitoso!")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Probando APIs de autenticación...")
    print("=" * 50)
    
    # Probar login con cada usuario
    for user in TEST_USERS:
        if test_login(user['username'], user['password'], user['description']):
            # Si el login es exitoso, probar otras APIs
            test_current_user()
            test_list_users()
            test_list_groups()
            test_logout()
            break
    else:
        print("\n❌ No se pudo hacer login con ningún usuario.")
        print("💡 Verifica que:")
        print("   1. El servidor Django esté corriendo en http://127.0.0.1:8000")
        print("   2. Las credenciales en TEST_USERS sean correctas")
        print("   3. Los usuarios existan en Django Admin")
    
    print("\n🎉 Pruebas completadas!")

if __name__ == '__main__':
    main()
