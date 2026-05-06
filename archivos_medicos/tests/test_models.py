"""
Tests para los modelos de la app archivos_medicos.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from archivos_medicos.models import ArchivoMedico
from archivos_medicos.validators import validar_tamanio_archivo, validar_extension_archivo
from pacientes.models import Paciente
from historias_clinicas.models import HistoriaClinica, Consulta
from medicos.models import Medico, Especialidad
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestArchivoMedicoModel:
    """Tests para el modelo ArchivoMedico."""
    
    def test_upload_exitoso_archivo_pequeno(self):
        """
        Test Upload Exitoso: Sube un archivo .txt pequeño vinculado a un paciente.
        Verifica que se guarde correctamente.
        """
        # Crear paciente
        paciente = Paciente.objects.create(
            dni='11111111',
            nombre='Juan',
            apellido='Pérez'
        )
        
        # Crear archivo simulado pequeño (UTF-8: no usar literals b'' con no-ASCII)
        contenido = 'Contenido de prueba del archivo médico'.encode('utf-8')
        archivo = SimpleUploadedFile(
            name='documento_medico.txt',
            content=contenido,
            content_type='text/plain'
        )
        
        # Crear archivo médico
        archivo_medico = ArchivoMedico.objects.create(
            titulo='Documento de Prueba',
            descripcion='Archivo de prueba para test',
            tipo_archivo='PDF',
            archivo=archivo,
            paciente=paciente,
            es_urgente=False
        )
        
        # Verificar que se guardó correctamente
        assert archivo_medico.titulo == 'Documento de Prueba'
        assert archivo_medico.paciente == paciente
        assert archivo_medico.tipo_archivo == 'PDF'
        assert archivo_medico.archivo.name is not None
        assert archivo_medico.fecha_subida is not None
        assert archivo_medico.es_urgente is False
    
    def test_validacion_tamanio_archivo_muy_grande(self):
        """
        Test Validación Tamaño: Intenta subir un archivo simulado > 10MB.
        Debe lanzar ValidationError.
        """
        # Crear paciente
        paciente = Paciente.objects.create(
            dni='22222222',
            nombre='María',
            apellido='González'
        )
        
        # Crear archivo simulado > 10MB (11MB)
        TAMANIO_11MB = 11 * 1024 * 1024  # 11MB en bytes
        contenido = b'x' * TAMANIO_11MB
        archivo = SimpleUploadedFile(
            name='archivo_grande.pdf',
            content=contenido,
            content_type='application/pdf'
        )
        
        # Crear instancia del modelo
        archivo_medico = ArchivoMedico(
            titulo='Archivo Grande',
            tipo_archivo='PDF',
            archivo=archivo,
            paciente=paciente
        )
        
        # Verificar que lanza ValidationError al validar
        with pytest.raises(ValidationError) as exc_info:
            archivo_medico.full_clean()
        
        # Verificar que el error es sobre el tamaño
        assert 'demasiado grande' in str(exc_info.value).lower() or 'tamaño' in str(exc_info.value).lower()
    
    def test_validacion_extension_archivo_no_permitida(self):
        """
        Test Validación Extensión: Intenta subir un archivo .exe o .bat.
        Debe lanzar ValidationError (Seguridad crítica).
        """
        # Crear paciente
        paciente = Paciente.objects.create(
            dni='33333333',
            nombre='Carlos',
            apellido='López'
        )
        
        # Test con archivo .exe
        contenido_exe = b'MZ\x90\x00'  # Header de archivo ejecutable
        archivo_exe = SimpleUploadedFile(
            name='malware.exe',
            content=contenido_exe,
            content_type='application/x-msdownload'
        )
        
        archivo_medico_exe = ArchivoMedico(
            titulo='Archivo Ejecutable',
            tipo_archivo='OTRO',
            archivo=archivo_exe,
            paciente=paciente
        )
        
        # Verificar que lanza ValidationError
        with pytest.raises(ValidationError) as exc_info:
            archivo_medico_exe.full_clean()
        
        # Verificar que el error es sobre la extensión
        assert 'extensión' in str(exc_info.value).lower() or 'permitida' in str(exc_info.value).lower()
        
        # Test con archivo .bat
        contenido_bat = b'@echo off\n'
        archivo_bat = SimpleUploadedFile(
            name='script.bat',
            content=contenido_bat,
            content_type='application/x-msdos-program'
        )
        
        archivo_medico_bat = ArchivoMedico(
            titulo='Script Batch',
            tipo_archivo='OTRO',
            archivo=archivo_bat,
            paciente=paciente
        )
        
        # Verificar que también lanza ValidationError
        with pytest.raises(ValidationError):
            archivo_medico_bat.full_clean()
    
    def test_validacion_extension_archivo_permitida(self):
        """Test que las extensiones permitidas pasan la validación."""
        # Crear paciente
        paciente = Paciente.objects.create(
            dni='44444444',
            nombre='Ana',
            apellido='Martínez'
        )
        
        # Test con diferentes extensiones permitidas
        extensiones_permitidas = [
            ('archivo.dcm', 'DICOM'),
            ('archivo.nii', 'NIFTI'),
            ('archivo.nii.gz', 'NIFTI'),
            ('archivo.jpg', 'FOTO_CLINICA'),
            ('archivo.png', 'FOTO_CLINICA'),
            ('archivo.pdf', 'PDF'),
            ('archivo.txt', 'OTRO'),
        ]
        
        for nombre_archivo, tipo_archivo in extensiones_permitidas:
            contenido = b'Contenido de prueba'
            archivo = SimpleUploadedFile(
                name=nombre_archivo,
                content=contenido,
                content_type='application/octet-stream'
            )
            
            archivo_medico = ArchivoMedico(
                titulo=f'Archivo {nombre_archivo}',
                tipo_archivo=tipo_archivo,
                archivo=archivo,
                paciente=paciente
            )
            
            # No debe lanzar error
            try:
                archivo_medico.full_clean()
            except ValidationError as e:
                pytest.fail(f"La extensión {nombre_archivo} debería ser permitida, pero lanzó: {e}")
    
    def test_relaciones_archivo_medico(self):
        """
        Test Relaciones: Verifica que se pueda vincular (o no) a una consulta específica.
        """
        # Crear paciente
        paciente = Paciente.objects.create(
            dni='55555555',
            nombre='Pedro',
            apellido='Sánchez'
        )
        
        # Crear historia clínica y consulta
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        
        especialidad = Especialidad.objects.create(
            nombre='Cardiología Test Archivos Relaciones',
            descripcion='Test archivos_medicos relaciones'
        )
        medico = Medico.objects.create(
            matricula='MAT-014',
            nombre='Dr. Roberto',
            apellido='Díaz',
            especialidad=especialidad
        )
        
        consulta = Consulta.objects.create(
            historia_clinica=historia_clinica,
            medico=medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control cardíaco'
        )
        
        # Crear usuario
        usuario = User.objects.create_user(
            username='medico_test',
            email='medico@test.com',
            password='testpass123',
            rol='medico'
        )
        
        # Crear archivo médico sin consulta
        contenido = b'Contenido de prueba'
        archivo = SimpleUploadedFile(
            name='documento.pdf',
            content=contenido,
            content_type='application/pdf'
        )
        
        archivo_medico_sin_consulta = ArchivoMedico.objects.create(
            titulo='Archivo sin consulta',
            tipo_archivo='PDF',
            archivo=archivo,
            paciente=paciente,
            subido_por=usuario
        )
        
        assert archivo_medico_sin_consulta.consulta is None
        assert archivo_medico_sin_consulta.paciente == paciente
        assert archivo_medico_sin_consulta.subido_por == usuario
        
        # Crear archivo médico con consulta
        archivo2 = SimpleUploadedFile(
            name='documento2.pdf',
            content=contenido,
            content_type='application/pdf'
        )
        
        archivo_medico_con_consulta = ArchivoMedico.objects.create(
            titulo='Archivo con consulta',
            tipo_archivo='PDF',
            archivo=archivo2,
            paciente=paciente,
            consulta=consulta,
            subido_por=usuario
        )
        
        assert archivo_medico_con_consulta.consulta == consulta
        assert archivo_medico_con_consulta.paciente == paciente
        assert archivo_medico_con_consulta.subido_por == usuario
    
    def test_archivo_medico_cascade_al_borrar_paciente(self):
        """
        Test Integridad: Verifica que al borrar un Paciente,
        sus archivos médicos también se borren (CASCADE).
        """
        # Crear paciente
        paciente = Paciente.objects.create(
            dni='66666666',
            nombre='Laura',
            apellido='Gómez'
        )
        
        # Crear archivo médico
        contenido = b'Contenido de prueba'
        archivo = SimpleUploadedFile(
            name='documento.pdf',
            content=contenido,
            content_type='application/pdf'
        )
        
        archivo_medico = ArchivoMedico.objects.create(
            titulo='Archivo de prueba',
            tipo_archivo='PDF',
            archivo=archivo,
            paciente=paciente
        )
        
        archivo_id = archivo_medico.id
        
        # Borrar el paciente
        paciente.delete()
        
        # Verificar que el archivo médico también se borró (CASCADE)
        assert not ArchivoMedico.objects.filter(id=archivo_id).exists()
    
    def test_archivo_medico_set_null_al_borrar_consulta(self):
        """
        Test Integridad: Verifica que al borrar una Consulta,
        el campo consulta del archivo médico pase a NULL (SET_NULL).
        """
        # Crear paciente y consulta
        paciente = Paciente.objects.create(
            dni='77777777',
            nombre='Miguel',
            apellido='Torres'
        )
        
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        
        especialidad = Especialidad.objects.create(
            nombre='Neurología Test Archivos Set Null',
            descripcion='Test archivos_medicos set null consulta'
        )
        medico = Medico.objects.create(
            matricula='MAT-015',
            nombre='Dr. Elena',
            apellido='Vargas',
            especialidad=especialidad
        )
        
        consulta = Consulta.objects.create(
            historia_clinica=historia_clinica,
            medico=medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control neurológico'
        )
        
        # Crear archivo médico vinculado a consulta
        contenido = b'Contenido de prueba'
        archivo = SimpleUploadedFile(
            name='documento.pdf',
            content=contenido,
            content_type='application/pdf'
        )
        
        archivo_medico = ArchivoMedico.objects.create(
            titulo='Archivo vinculado',
            tipo_archivo='PDF',
            archivo=archivo,
            paciente=paciente,
            consulta=consulta
        )
        
        assert archivo_medico.consulta == consulta
        
        # Borrar la consulta
        consulta.delete()
        
        # Refrescar el archivo médico
        archivo_medico.refresh_from_db()
        
        # Verificar que el campo consulta es NULL
        assert archivo_medico.consulta is None
        # Verificar que el archivo médico sigue existiendo
        assert ArchivoMedico.objects.filter(id=archivo_medico.id).exists()


@pytest.mark.django_db
class TestValidators:
    """Tests para los validadores aislados."""
    
    def test_validar_tamanio_archivo_pequeno(self):
        """Test que un archivo pequeño pasa la validación."""
        contenido = 'Contenido pequeño'.encode('utf-8')
        archivo = SimpleUploadedFile(
            name='pequeno.txt',
            content=contenido,
            content_type='text/plain'
        )
        
        # No debe lanzar error
        try:
            validar_tamanio_archivo(archivo)
        except ValidationError:
            pytest.fail("Un archivo pequeño no debería lanzar ValidationError")
    
    def test_validar_tamanio_archivo_grande(self):
        """Test que un archivo grande lanza ValidationError."""
        TAMANIO_11MB = 11 * 1024 * 1024
        contenido = b'x' * TAMANIO_11MB
        archivo = SimpleUploadedFile(
            name='grande.pdf',
            content=contenido,
            content_type='application/pdf'
        )
        
        # Debe lanzar ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validar_tamanio_archivo(archivo)
        
        assert 'demasiado grande' in str(exc_info.value).lower() or '10' in str(exc_info.value)
    
    def test_validar_extension_permitida(self):
        """Test que extensiones permitidas pasan la validación."""
        extensiones_permitidas = ['.dcm', '.nii', '.jpg', '.png', '.pdf', '.txt']
        
        for extension in extensiones_permitidas:
            contenido = b'Contenido'
            archivo = SimpleUploadedFile(
                name=f'archivo{extension}',
                content=contenido,
                content_type='application/octet-stream'
            )
            
            try:
                validar_extension_archivo(archivo)
            except ValidationError:
                pytest.fail(f"La extensión {extension} debería ser permitida")
    
    def test_validar_extension_no_permitida(self):
        """Test que extensiones no permitidas lanzan ValidationError."""
        extensiones_no_permitidas = ['.exe', '.bat', '.sh', '.com', '.scr']
        
        for extension in extensiones_no_permitidas:
            contenido = b'Contenido'
            archivo = SimpleUploadedFile(
                name=f'archivo{extension}',
                content=contenido,
                content_type='application/octet-stream'
            )
            
            with pytest.raises(ValidationError) as exc_info:
                validar_extension_archivo(archivo)
            
            assert 'extensión' in str(exc_info.value).lower() or 'permitida' in str(exc_info.value).lower()



