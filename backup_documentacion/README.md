# EMR (Electronic Medical Record)

Sistema de Historia Clínica Electrónica desarrollado en Django.

## Características principales
- Gestión de pacientes, médicos, turnos, historias clínicas y laboratorio.
- Estructura modular y escalable.
- Preparado para integración con IA y catálogos internacionales (CIE-10, SNOMED, etc.).
- Scripts de carga masiva de datos.

## Instalación

1. Clona el repositorio y entra al directorio del proyecto.
2. Crea y activa un entorno virtual:
   ```bash
   python3 -m venv emr_ev
   source emr_ev/bin/activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Copia `.env.example` a `.env` y configura tus variables de entorno.
5. Realiza las migraciones:
   ```bash
   python manage.py migrate
   ```
6. Crea un superusuario:
   ```bash
   python manage.py createsuperuser
   ```
7. Ejecuta el servidor:
   ```bash
   python manage.py runserver
   ```

## Estructura del proyecto
- **historias_clinicas/**: Modelos y lógica de historias clínicas, consultas, síntomas, diagnósticos y tratamientos.
- **laboratorio/**: Gestión de tipos de exámenes, paneles, solicitudes y resultados de laboratorio.
- **medicos/**: Modelos de médicos y especialidades.
- **pacientes/**: Modelos de pacientes y antecedentes.
- **turnos/**: Gestión de turnos médicos.
- **synesis/**: Configuración principal de Django.
- **templates/**: Plantillas HTML para el admin y vistas.
- **static/**: Archivos estáticos (JS, CSS).

## Buenas prácticas
- Usa variables de entorno para datos sensibles.
- Mantén DEBUG=False en producción.
- Personaliza el admin para facilitar la gestión.
- Agrega y ejecuta tests automáticos:
  ```bash
  python manage.py test
  ```

## Scripts útiles
- `load_examenes.py`: Carga masiva de tipos de exámenes desde archivo.
- `load_sintomas.py`: Carga masiva de síntomas desde archivo.

## Licencia
MIT 