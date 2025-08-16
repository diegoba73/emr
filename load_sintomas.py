import os
import django

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

# Importa tu modelo Sintoma
from historias_clinicas.models import Sintoma

def load_sintomas_from_file(file_path='sintomas.txt'):
    """Carga síntomas desde un archivo de texto."""
    try:
        # Ruta absoluta al archivo de síntomas para mayor robustez
        script_dir = os.path.dirname(__file__)
        abs_file_path = os.path.join(script_dir, file_path)

        with open(abs_file_path, 'r', encoding='utf-8') as f:
            sintomas_list = [line.strip() for line in f if line.strip()]

        print(f"Intentando cargar {len(sintomas_list)} síntomas desde {abs_file_path}...")
        sintomas_creados = 0
        sintomas_existentes = 0

        for nombre_sintoma in sintomas_list:
            try:
                sintoma, created = Sintoma.objects.get_or_create(
                    nombre=nombre_sintoma,
                    defaults={'descripcion': f"Síntoma: {nombre_sintoma}"}
                )
                if created:
                    print(f"  Creado: '{sintoma.nombre}'")
                    sintomas_creados += 1
                else:
                    print(f"  Ya existe: '{sintoma.nombre}'")
                    sintomas_existentes += 1
            except Exception as e:
                print(f"  Error al procesar '{nombre_sintoma}': {e}")
        print(f"\nCarga completada. Creados: {sintomas_creados}, Existentes: {sintomas_existentes}")

    except FileNotFoundError:
        print(f"Error: El archivo '{abs_file_path}' no se encontró. Asegúrate de que esté en el mismo directorio que 'manage.py'.")
    except Exception as e:
        print(f"Ocurrió un error general: {e}")

if __name__ == '__main__':
    load_sintomas_from_file()