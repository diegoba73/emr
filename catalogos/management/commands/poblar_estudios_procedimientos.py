"""
Management command para poblar estudios diagnósticos y procedimientos
con datos profesionales y actualizados según estándares internacionales.
"""
from django.core.management.base import BaseCommand
from catalogos.models import EstudioDiagnostico, ProcedimientoCatalogo


class Command(BaseCommand):
    help = 'Pobla la base de datos con estudios diagnósticos y procedimientos profesionales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todos los estudios y procedimientos existentes antes de poblar',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Eliminando estudios y procedimientos existentes...')
            EstudioDiagnostico.objects.all().delete()
            ProcedimientoCatalogo.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Estudios y procedimientos eliminados'))

        # Estudios Diagnósticos - Lista profesional y actualizada
        estudios = [
            # IMAGENOLOGÍA CARDIACA
            {
                'nombre': 'Ecocardiograma Transtorácico',
                'descripcion': 'Estudio de imagen cardíaca no invasivo que evalúa la estructura y función del corazón mediante ultrasonido.'
            },
            {
                'nombre': 'Ecocardiograma Transesofágico',
                'descripcion': 'Ecocardiograma realizado mediante sonda esofágica para mejor visualización de estructuras cardíacas.'
            },
            {
                'nombre': 'Ecocardiograma de Estrés',
                'descripcion': 'Ecocardiograma realizado durante ejercicio o fármacos para evaluar isquemia miocárdica.'
            },
            {
                'nombre': 'Ecocardiograma de Estrés con Dobutamina',
                'descripcion': 'Ecocardiograma de estrés farmacológico con dobutamina para evaluación de viabilidad miocárdica.'
            },
            {
                'nombre': 'Ecocardiograma 3D',
                'descripcion': 'Ecocardiograma con reconstrucción tridimensional para evaluación volumétrica precisa.'
            },
            {
                'nombre': 'Ecocardiograma con Contraste',
                'descripcion': 'Ecocardiograma con medio de contraste para mejor definición de cavidades y perfusión miocárdica.'
            },
            {
                'nombre': 'Ecocardiograma Fetal',
                'descripcion': 'Evaluación ecocardiográfica de estructuras cardíacas fetales durante el embarazo.'
            },
            
            # HEMODINAMIA E INTERVENCIONISMO
            {
                'nombre': 'Cateterismo Cardíaco Derecho',
                'descripcion': 'Estudio invasivo para medir presiones y saturación de oxígeno en cavidades derechas y arteria pulmonar.'
            },
            {
                'nombre': 'Cateterismo Cardíaco Izquierdo',
                'descripcion': 'Estudio invasivo para evaluación de arterias coronarias, función ventricular y presiones intracardíacas.'
            },
            {
                'nombre': 'Coronariografía',
                'descripcion': 'Visualización de arterias coronarias mediante cateterismo e inyección de contraste radiológico.'
            },
            {
                'nombre': 'Angiografía de Ventrículo Izquierdo',
                'descripcion': 'Evaluación de función sistólica y diastólica del ventrículo izquierdo mediante contraste.'
            },
            {
                'nombre': 'Estudio Hemodinámico Completo',
                'descripcion': 'Evaluación completa de presiones, gasto cardíaco y resistencias vasculares.'
            },
            {
                'nombre': 'Test de Oclusión de Balón',
                'descripcion': 'Evaluación de viabilidad de cierre de defectos cardíacos mediante oclusión temporal.'
            },
            
            # IMAGENOLOGÍA VASCULAR
            {
                'nombre': 'Ecodoppler de Vasos del Cuello',
                'descripcion': 'Evaluación de arterias carótidas y vertebrales mediante ultrasonido y doppler.'
            },
            {
                'nombre': 'Ecodoppler de Miembros Inferiores',
                'descripcion': 'Evaluación de flujo arterial y venoso en miembros inferiores.'
            },
            {
                'nombre': 'Ecodoppler de Miembros Superiores',
                'descripcion': 'Evaluación de flujo arterial y venoso en miembros superiores.'
            },
            {
                'nombre': 'Ecodoppler de Aorta Abdominal',
                'descripcion': 'Evaluación de diámetro y morfología de aorta abdominal para detección de aneurismas.'
            },
            {
                'nombre': 'Angiografía por Tomografía Computada (Angio-TC)',
                'descripcion': 'Estudio de imagen vascular mediante tomografía computada con contraste.'
            },
            {
                'nombre': 'Angiografía por Resonancia Magnética (Angio-RM)',
                'descripcion': 'Estudio de imagen vascular mediante resonancia magnética sin contraste radiológico.'
            },
            
            # ARRITMIAS Y ELECTROFISIOLOGÍA
            {
                'nombre': 'Holter de 24 Horas',
                'descripcion': 'Monitoreo continuo de electrocardiograma durante 24 horas para detección de arritmias.'
            },
            {
                'nombre': 'Holter de 7 Días',
                'descripcion': 'Monitoreo continuo de electrocardiograma durante 7 días para eventos infrecuentes.'
            },
            {
                'nombre': 'Monitoreo de Eventos (Event Recorder)',
                'descripcion': 'Dispositivo portátil para registro de eventos sintomáticos durante 30 días o más.'
            },
            {
                'nombre': 'Test de Mesa Basculante (Tilt Test)',
                'descripcion': 'Estudio para diagnóstico de síncope vasovagal mediante cambios posturales controlados.'
            },
            {
                'nombre': 'Estudio Electrofisiológico',
                'descripcion': 'Estudio invasivo para mapeo y caracterización de arritmias mediante catéteres intracardíacos.'
            },
            {
                'nombre': 'Test de Ejercicio (Ergometría)',
                'descripcion': 'Electrocardiograma durante ejercicio en cinta o bicicleta para evaluación de isquemia y capacidad funcional.'
            },
            {
                'nombre': 'Test de Ejercicio con Gases',
                'descripcion': 'Ergometría con análisis de intercambio gaseoso para evaluación de capacidad funcional cardiorrespiratoria.'
            },
            
            # IMAGENOLOGÍA GENERAL
            {
                'nombre': 'Radiografía de Tórax',
                'descripcion': 'Estudio radiológico básico para evaluación de silueta cardíaca y campos pulmonares.'
            },
            {
                'nombre': 'Tomografía Computada de Tórax',
                'descripcion': 'Estudio de imagen de alta resolución para evaluación de estructuras torácicas y mediastino.'
            },
            {
                'nombre': 'Resonancia Magnética Cardíaca',
                'descripcion': 'Estudio de imagen de alta resolución para evaluación de estructura, función y viabilidad miocárdica.'
            },
            {
                'nombre': 'Resonancia Magnética Cardíaca con Perfusión',
                'descripcion': 'RM cardíaca con contraste para evaluación de perfusión miocárdica e isquemia.'
            },
            {
                'nombre': 'Tomografía por Emisión de Positrones (PET)',
                'descripcion': 'Estudio de medicina nuclear para evaluación de metabolismo y viabilidad miocárdica.'
            },
            {
                'nombre': 'Gammagrafía de Perfusión Miocárdica',
                'descripcion': 'Estudio de medicina nuclear para evaluación de perfusión miocárdica en reposo y estrés.'
            },
            
            # LABORATORIO Y BIOQUÍMICA
            {
                'nombre': 'Perfil Lipídico Completo',
                'descripcion': 'Evaluación de colesterol total, LDL, HDL, triglicéridos y apolipoproteínas.'
            },
            {
                'nombre': 'Troponina Cardíaca (hs-Tn)',
                'descripcion': 'Biomarcador de alta sensibilidad para diagnóstico de infarto agudo de miocardio.'
            },
            {
                'nombre': 'Pro-BNP / NT-proBNP',
                'descripcion': 'Biomarcador para diagnóstico y seguimiento de insuficiencia cardíaca.'
            },
            {
                'nombre': 'Hemograma Completo',
                'descripcion': 'Evaluación de células sanguíneas, hemoglobina y parámetros hematológicos.'
            },
            {
                'nombre': 'Coagulograma Completo',
                'descripcion': 'Evaluación de función de coagulación sanguínea y tiempo de protrombina.'
            },
            {
                'nombre': 'Función Renal Completa',
                'descripcion': 'Evaluación de función renal mediante creatinina, urea y filtrado glomerular estimado.'
            },
            {
                'nombre': 'Función Hepática',
                'descripcion': 'Evaluación de enzimas hepáticas y función del hígado.'
            },
            {
                'nombre': 'Electrolitos Séricos',
                'descripcion': 'Evaluación de sodio, potasio, cloro y otros electrolitos esenciales.'
            },
            {
                'nombre': 'Hemoglobina Glicosilada (HbA1c)',
                'descripcion': 'Marcador de control glucémico a largo plazo en pacientes diabéticos.'
            },
            {
                'nombre': 'Perfil Tiroideo Completo',
                'descripcion': 'Evaluación de función tiroidea mediante TSH, T4 libre y T3.'
            },
        ]

        # Procedimientos - Lista profesional y actualizada
        procedimientos = [
            # INTERVENCIONISMO CORONARIO
            {
                'nombre': 'Angioplastia Coronaria con Stent',
                'descripcion': 'Intervención percutánea para revascularización de arterias coronarias mediante stent.'
            },
            {
                'nombre': 'Angioplastia Coronaria con Stent Farmacoactivo (DES)',
                'descripcion': 'Angioplastia con stent liberador de fármacos para reducir reestenosis.'
            },
            {
                'nombre': 'Angioplastia Coronaria con Balón',
                'descripcion': 'Dilatación de estenosis coronaria mediante balón sin implante de stent.'
            },
            {
                'nombre': 'Aterectomía Rotacional',
                'descripcion': 'Remoción de placa aterosclerótica mediante dispositivo rotatorio.'
            },
            {
                'nombre': 'Aterectomía Direccional',
                'descripcion': 'Remoción de placa aterosclerótica mediante dispositivo de corte direccional.'
            },
            {
                'nombre': 'Trombectomía Mecánica',
                'descripcion': 'Remoción de trombos coronarios mediante dispositivos de aspiración.'
            },
            {
                'nombre': 'Intervención Coronaria Compleja (Bifurcación)',
                'descripcion': 'Angioplastia de lesiones en bifurcaciones coronarias con técnicas especializadas.'
            },
            {
                'nombre': 'Intervención Coronaria Compleja (Oclusión Crónica)',
                'descripcion': 'Revascularización de oclusiones coronarias crónicas mediante técnicas avanzadas.'
            },
            
            # INTERVENCIONISMO ESTRUCTURAL
            {
                'nombre': 'Implante de Válvula Aórtica Percutánea (TAVI)',
                'descripcion': 'Reemplazo valvular aórtico mediante cateterismo sin cirugía abierta.'
            },
            {
                'nombre': 'Valvuloplastia Mitral Percutánea',
                'descripcion': 'Dilatación de estenosis mitral mediante balón percutáneo.'
            },
            {
                'nombre': 'Reparación Mitral Percutánea (MitraClip)',
                'descripcion': 'Reparación de insuficiencia mitral mediante dispositivo de clip percutáneo.'
            },
            {
                'nombre': 'Cierre de Comunicación Interauricular (ASD)',
                'descripcion': 'Cierre percutáneo de defecto septal auricular mediante dispositivo oclusor.'
            },
            {
                'nombre': 'Cierre de Conducto Arterioso Persistente (PCA)',
                'descripcion': 'Cierre percutáneo de conducto arterioso mediante dispositivo oclusor.'
            },
            {
                'nombre': 'Cierre de Comunicación Interventricular (CIV)',
                'descripcion': 'Cierre percutáneo de defecto septal ventricular mediante dispositivo oclusor.'
            },
            {
                'nombre': 'Cierre de Orejuela de Aurícula Izquierda',
                'descripcion': 'Cierre percutáneo de orejuela izquierda para prevención de embolias en fibrilación auricular.'
            },
            {
                'nombre': 'Valvuloplastia Pulmonar',
                'descripcion': 'Dilatación de estenosis pulmonar mediante balón percutáneo.'
            },
            {
                'nombre': 'Valvuloplastia Tricúspide',
                'descripcion': 'Dilatación de estenosis tricúspide mediante balón percutáneo.'
            },
            
            # ELECTROFISIOLOGÍA E INTERVENCIONISMO ARRÍTMICO
            {
                'nombre': 'Ablación por Radiofrecuencia',
                'descripcion': 'Eliminación de focos arritmogénicos mediante energía de radiofrecuencia.'
            },
            {
                'nombre': 'Ablación por Crioterapia',
                'descripcion': 'Eliminación de focos arritmogénicos mediante energía de frío (crioablación).'
            },
            {
                'nombre': 'Ablación de Fibrilación Auricular',
                'descripcion': 'Ablación compleja para tratamiento de fibrilación auricular mediante aislamiento de venas pulmonares.'
            },
            {
                'nombre': 'Ablación de Taquicardia Ventricular',
                'descripcion': 'Ablación de taquicardias ventriculares mediante mapeo electroanatómico.'
            },
            {
                'nombre': 'Ablación de Taquicardia Supraventricular',
                'descripcion': 'Ablación de taquicardias supraventriculares (AVNRT, AVRT, etc.).'
            },
            {
                'nombre': 'Ablación de Flutter Auricular',
                'descripcion': 'Ablación de flutter auricular mediante lesión lineal en istmo cavotricuspídeo.'
            },
            {
                'nombre': 'Implante de Marcapasos Definitivo',
                'descripcion': 'Implante de sistema de marcapasos para tratamiento de bradiarritmias.'
            },
            {
                'nombre': 'Implante de Cardiodesfibrilador (DAI)',
                'descripcion': 'Implante de dispositivo para prevención de muerte súbita por arritmias ventriculares.'
            },
            {
                'nombre': 'Implante de Resincronizador Cardíaco (TRC)',
                'descripcion': 'Implante de dispositivo biventricular para tratamiento de insuficiencia cardíaca.'
            },
            {
                'nombre': 'Reemplazo de Generador de Marcapasos/DAI',
                'descripcion': 'Reemplazo de batería de dispositivo cardíaco implantable.'
            },
            {
                'nombre': 'Revisión/Reposicionamiento de Electrodo',
                'descripcion': 'Reposicionamiento o extracción de electrodos de dispositivos cardíacos.'
            },
            
            # INTERVENCIONISMO VASCULAR
            {
                'nombre': 'Angioplastia de Arterias Periféricas',
                'descripcion': 'Dilatación de estenosis en arterias de miembros inferiores o superiores.'
            },
            {
                'nombre': 'Stent en Arterias Periféricas',
                'descripcion': 'Implante de stent en arterias periféricas para tratamiento de estenosis.'
            },
            {
                'nombre': 'Angioplastia de Arterias Renales',
                'descripcion': 'Dilatación de estenosis de arterias renales para tratamiento de hipertensión renovascular.'
            },
            {
                'nombre': 'Embolización de Aneurismas',
                'descripcion': 'Tratamiento endovascular de aneurismas mediante coils o stents cubiertos.'
            },
            {
                'nombre': 'Trombectomía Mecánica Periférica',
                'descripcion': 'Remoción de trombos en arterias periféricas mediante dispositivos de aspiración.'
            },
            
            # PROCEDIMIENTOS DIAGNÓSTICOS INVASIVOS
            {
                'nombre': 'Biopsia Endomiocárdica',
                'descripcion': 'Obtención de muestra de tejido miocárdico para diagnóstico histológico.'
            },
            {
                'nombre': 'Test de Oclusión de Balón con Mediciones',
                'descripcion': 'Evaluación hemodinámica durante oclusión temporal de defectos cardíacos.'
            },
            {
                'nombre': 'Estudio de Presión Intracoronaria (FFR)',
                'descripcion': 'Medición de reserva fraccional de flujo para evaluación funcional de estenosis coronarias.'
            },
            {
                'nombre': 'Ecografía Intracoronaria (IVUS)',
                'descripcion': 'Visualización de estructura de pared arterial mediante ultrasonido intracoronario.'
            },
            {
                'nombre': 'Tomografía de Coherencia Óptica (OCT)',
                'descripcion': 'Visualización de alta resolución de pared arterial mediante luz coherente.'
            },
            
            # PROCEDIMIENTOS QUIRÚRGICOS CARDÍACOS
            {
                'nombre': 'Cirugía de Revascularización Miocárdica (By-pass)',
                'descripcion': 'Cirugía de revascularización coronaria mediante injertos de safena o mamaria.'
            },
            {
                'nombre': 'Reemplazo Valvular Aórtico',
                'descripcion': 'Cirugía de reemplazo de válvula aórtica mediante prótesis mecánica o biológica.'
            },
            {
                'nombre': 'Reemplazo Valvular Mitral',
                'descripcion': 'Cirugía de reemplazo de válvula mitral mediante prótesis mecánica o biológica.'
            },
            {
                'nombre': 'Reparación Valvular Mitral',
                'descripcion': 'Cirugía de reparación de válvula mitral preservando válvula nativa.'
            },
            {
                'nombre': 'Cirugía de Aneurisma de Aorta',
                'descripcion': 'Reparación quirúrgica de aneurismas aórticos mediante prótesis vascular.'
            },
            {
                'nombre': 'Cirugía de Defectos Congénitos',
                'descripcion': 'Corrección quirúrgica de defectos cardíacos congénitos.'
            },
            {
                'nombre': 'Ablación Quirúrgica de Arritmias (Maze)',
                'descripcion': 'Cirugía de ablación de fibrilación auricular mediante técnica de laberinto.'
            },
        ]

        # Crear estudios diagnósticos
        self.stdout.write('Creando estudios diagnósticos...')
        estudios_creados = 0
        estudios_actualizados = 0
        
        for estudio_data in estudios:
            estudio, created = EstudioDiagnostico.objects.update_or_create(
                nombre=estudio_data['nombre'],
                defaults={
                    'descripcion': estudio_data['descripcion'],
                    'activo': True
                }
            )
            if created:
                estudios_creados += 1
            else:
                estudios_actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Estudios diagnósticos: {estudios_creados} creados, {estudios_actualizados} actualizados'
            )
        )

        # Crear procedimientos
        self.stdout.write('Creando procedimientos...')
        procedimientos_creados = 0
        procedimientos_actualizados = 0
        
        for procedimiento_data in procedimientos:
            procedimiento, created = ProcedimientoCatalogo.objects.update_or_create(
                nombre=procedimiento_data['nombre'],
                defaults={
                    'descripcion': procedimiento_data['descripcion'],
                    'activo': True
                }
            )
            if created:
                procedimientos_creados += 1
            else:
                procedimientos_actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Procedimientos: {procedimientos_creados} creados, {procedimientos_actualizados} actualizados'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado. Total: {len(estudios)} estudios y {len(procedimientos)} procedimientos disponibles.'
            )
        )






