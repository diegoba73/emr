import os
import logging
import pymysql
import psycopg2
from tqdm import tqdm
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# IMPORTS DE MODELOS (Asegúrate que coincidan con tus apps)
from pacientes.models import Paciente
from medicos.models import Medico
from laboratorio.models import TipoMuestra, TipoExamen, SolicitudExamen, ResultadoExamen

# Configuración de Logging
logging.basicConfig(
    filename='migration_lims_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class Command(BaseCommand):
    help = 'Migra datos del LIMS Legacy (MySQL) al nuevo EMR (Postgres)'

    def add_arguments(self, parser):
        parser.add_argument('--mysql-host', type=str, required=True)
        parser.add_argument('--mysql-port', type=int, default=3306)
        parser.add_argument('--mysql-user', type=str, required=True)
        parser.add_argument('--mysql-password', type=str, required=True)
        parser.add_argument('--mysql-db', type=str, required=True)
        parser.add_argument('--dry-run', action='store_true', help='Simulación sin guardar cambios')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== INICIANDO MIGRACIÓN LIMS ==='))
        dry_run = options['dry_run']

        # 1. CONEXIÓN MYSQL (LEGACY)
        try:
            mysql_conn = pymysql.connect(
                host=options['mysql_host'],
                port=options['mysql_port'],
                user=options['mysql_user'],
                password=options['mysql_password'],
                database=options['mysql_db'],
                cursorclass=pymysql.cursors.DictCursor
            )
            self.stdout.write(self.style.SUCCESS('✅ Conexión MySQL Exitosa'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error conectando MySQL: {e}'))
            return

        # 2. PROBAR CONEXIÓN POSTGRES (SOLO VALIDACIÓN)
        try:
            # Hardcodeado para asegurar conexión local
            pg_conn = psycopg2.connect(
                dbname='synesis_db',
                user='postgres',
                password='postgres',
                host='localhost',
                port=5432
            )
            pg_conn.close()
            self.stdout.write(self.style.SUCCESS('✅ Conexión Postgres Exitosa'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error conectando Postgres: {e}'))
            return

        try:
            with mysql_conn.cursor() as cursor:
                
                # --- FASE 1: CATÁLOGOS ---
                
                # 1.1 Tipos de Muestra
                self.stdout.write('Migrando Tipos de Muestra...')
                cursor.execute("SELECT id, nombre, codigo, descripcion FROM laboratorio_tipomuestra")
                muestras = cursor.fetchall()
                mapa_muestras = {} 
                
                for m in tqdm(muestras):
                    if not dry_run:
                        # Usamos get_or_create para evitar duplicados
                        obj, _ = TipoMuestra.objects.get_or_create(
                            codigo=m['codigo'],
                            defaults={
                                'nombre': m['nombre'], 
                                'descripcion': m.get('descripcion') or '' # Manejo de posible null
                            }
                        )
                        mapa_muestras[m['id']] = obj

                # 1.2 Tipos de Examen
                self.stdout.write('Migrando Tipos de Examen...')
                # Usamos campos que sabemos que existen por la inspección
                cursor.execute("""
                    SELECT id, nombre, codigo, descripcion, precio, rango_referencia_texto, unidad_medida 
                    FROM laboratorio_tipoexamen
                """)
                examenes = cursor.fetchall()
                mapa_examenes = {}
                
                # Muestra default para evitar errores de FK si falta el mapeo
                muestra_default = TipoMuestra.objects.first()

                for ex in tqdm(examenes):
                    if not dry_run:
                        obj, _ = TipoExamen.objects.get_or_create(
                            codigo=ex['codigo'],
                            defaults={
                                'nombre': ex['nombre'],
                                'descripcion': ex.get('descripcion') or '',
                                'precio': ex.get('precio') or 0,
                                'rango_referencia_texto': ex.get('rango_referencia_texto') or '',
                                'tipo_muestra_requerida': muestra_default # Simplificación necesaria
                            }
                        )
                        mapa_examenes[ex['id']] = obj

                # --- FASE 2: TRANSACCIONAL ---
                
                # 2.1 Solicitudes
                self.stdout.write('Migrando Solicitudes...')
                cursor.execute("""
                    SELECT id, numero, fecha_solicitud, paciente_id, observaciones
                    FROM laboratorio_solicitudexamen
                """)
                solicitudes = cursor.fetchall()
                mapa_solicitudes = {}

                for sol in tqdm(solicitudes):
                    if dry_run: continue

                    # Búsqueda de Paciente (paciente_id en legacy es el DNI string)
                    dni_legacy = str(sol['paciente_id']).strip() if sol['paciente_id'] else ''
                    paciente = Paciente.objects.filter(dni=dni_legacy).first()
                    
                    if not paciente:
                        # Si no encontramos paciente, logueamos y saltamos
                        logging.error(f"Solicitud {sol['id']} omitida: Paciente DNI {dni_legacy} no encontrado")
                        continue

                    # Crear Solicitud (Usando transaction atomic por seguridad)
                    with transaction.atomic():
                        obj = SolicitudExamen.objects.create(
                            paciente=paciente,
                            fecha_solicitud=sol['fecha_solicitud'] or timezone.now(),
                            observaciones=sol.get('observaciones') or '',
                            estado='PENDIENTE',
                            # Si tu modelo tiene campo 'numero' único:
                            numero=sol['numero'] if sol['numero'] else f"MIG-{sol['id']}"
                        )
                        mapa_solicitudes[sol['id']] = obj

                # 2.2 Resultados
                self.stdout.write('Migrando Resultados...')
                # JOIN clave entre detalle y cabecera legacy
                query_resultados = """
                    SELECT 
                        d.valor_numerico, d.valor_texto, d.es_normal, d.observaciones,
                        d.tipo_examen_id, r.solicitud_id, r.fecha_validacion
                    FROM laboratorio_resultadodetalle d
                    JOIN laboratorio_resultadoexamen r ON d.resultado_id = r.id
                """
                cursor.execute(query_resultados)
                resultados = cursor.fetchall()
                
                batch_resultados = []
                for res in tqdm(resultados):
                    if dry_run: continue
                    
                    solicitud_django = mapa_solicitudes.get(res['solicitud_id'])
                    examen_django = mapa_examenes.get(res['tipo_examen_id'])
                    
                    if solicitud_django and examen_django:
                        # Mapeo de valores
                        valor = res['valor_texto']
                        if not valor and res['valor_numerico'] is not None:
                            valor = str(res['valor_numerico'])
                        
                        r = ResultadoExamen(
                            solicitud=solicitud_django,
                            tipo_examen=examen_django,
                            valor_obtenido=valor or '',
                            es_patologico=not (res['es_normal'] == 1), # 1 es normal en legacy -> False es patologico
                            observaciones=res.get('observaciones') or '',
                            fecha_validacion=res.get('fecha_validacion')
                        )
                        batch_resultados.append(r)
                
                if not dry_run and batch_resultados:
                    self.stdout.write(f'Insertando {len(batch_resultados)} resultados...')
                    ResultadoExamen.objects.bulk_create(batch_resultados, batch_size=1000)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error General: {e}'))
            import traceback
            traceback.print_exc()
        finally:
            mysql_conn.close()
            self.stdout.write(self.style.SUCCESS('=== MIGRACIÓN FINALIZADA ==='))
