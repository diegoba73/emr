import os
import django
from django.db.utils import IntegrityError

# --- Configuración del Entorno de Django ---
# Esto le dice al script dónde encontrar la configuración de tu proyecto Django.
# 'synesis' es el nombre de tu módulo de configuración principal (la carpeta donde está settings.py).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

# --- Importa tu Modelo TipoExamen ---
# Asegúrate de que la ruta sea correcta: 'laboratorio' es el nombre de tu app.
from laboratorio.models import TipoExamen

def load_tipos_examenes_from_file(file_path='tipos_examenes.txt'):
    """
    Carga tipos de exámenes desde un archivo de texto.
    Cada línea del archivo se considera el nombre de un examen.
    Si un examen ya existe, se omite.
    """
    try:
        # Obtiene la ruta absoluta del archivo para mayor robustez,
        # ya que el script se ejecuta desde la raíz del proyecto.
        script_dir = os.path.dirname(__file__)
        abs_file_path = os.path.join(script_dir, file_path)

        with open(abs_file_path, 'r', encoding='utf-8') as f:
            # Lee cada línea, elimina espacios en blanco al inicio/final y filtra líneas vacías.
            examenes_list = [line.strip() for line in f if line.strip()]

        print(f"\n--- INICIANDO CARGA MASIVA DE TIPOS DE EXÁMENES ---")
        print(f"Intentando cargar {len(examenes_list)} tipos de exámenes desde '{file_path}'...")
        print("-" * 50)

        examenes_creados = 0
        examenes_existentes = 0
        examenes_fallidos = 0

        for nombre_examen in examenes_list:
            try:
                # Intenta obtener el examen si ya existe, o crearlo si no.
                # 'defaults' permite establecer valores para campos si el objeto es creado.
                # Para este script simple, la unidad_medida y rangos quedan en blanco/nulo por defecto.
                # Puedes editarlos manualmente en el admin después para cada examen.
                examen, created = TipoExamen.objects.get_or_create(
                    nombre=nombre_examen,
                    defaults={'descripcion': f"Examen de laboratorio: {nombre_examen}"}
                )
                if created:
                    print(f"  ✅ Creado: '{examen.nombre}'")
                    examenes_creados += 1
                else:
                    print(f"  ℹ️ Ya existe: '{examen.nombre}'")
                    examenes_existentes += 1
            except IntegrityError:
                # Esto captura errores si hay problemas de unicidad no cubiertos por get_or_create
                print(f"  ❌ Error de integridad: '{nombre_examen}' (posible duplicado no manejado)")
                examenes_fallidos += 1
            except Exception as e:
                print(f"  ❌ Error inesperado al procesar '{nombre_examen}': {e}")
                examenes_fallidos += 1

        print("-" * 50)
        print(f"--- CARGA COMPLETADA ---")
        print(f"Resumen: Creados: {examenes_creados}, Ya Existentes: {examenes_existentes}, Fallidos: {examenes_fallidos}")
        print("-------------------------")

    except FileNotFoundError:
        print(f"\nError fatal: El archivo '{file_path}' no se encontró en '{abs_file_path}'.")
        print("Asegúrate de que 'tipos_examenes.txt' esté en el mismo directorio que 'manage.py'.")
    except Exception as e:
        print(f"\nOcurrió un error general durante la carga: {e}")
        print("Asegúrate de que tu entorno virtual esté activo y el proyecto Django configurado.")

if __name__ == '__main__':
    # Llama a la función principal para iniciar la carga
    load_tipos_examenes_from_file()