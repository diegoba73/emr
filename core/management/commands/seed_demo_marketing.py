"""
Datos ficticios ricos para demo promocional (local / staging).

Idempotente. Prefijos MKTG-* — no pisa el seed QA (QA-DEMO-*, LAB-DEMO-QA-*).
Requiere usuarios base de seed_data (medico1, paciente1, laboratorio1, …).
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from emr.models import SignosVitales
from internacion.models import Cama, Internacion, Sector
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno

User = get_user_model()

MKTG_RECURSO = 'MKTG DEMO Consultorio 1'
MKTG_PACIENTE_INT_1 = 'MKTG-00002'
MKTG_PACIENTE_INT_2 = 'MKTG-00003'
MKTG_PACIENTE_INT_3 = 'MKTG-00004'
MKTG_LIMS_VIVO = 'LAB-MKTG-00001'
MKTG_LIMS_FINAL = 'LAB-MKTG-00002'
MKTG_MUESTRA_VIVO = 'MUE-MKTG-00001'
MKTG_MUESTRA_FINAL = 'MUE-MKTG-00002'
MKTG_INT_1 = 'INT-MKTG-001'
MKTG_INT_2 = 'INT-MKTG-002'
MKTG_INT_3 = 'INT-MKTG-003'

# Motivos estables para turnos (get_or_create por motivo)
TURNO_SPECS = [
    ('MKTG DEMO TURNO HOY', 0, Turno.Estado.CONFIRMADO, True),
    ('MKTG DEMO TURNO MANANA', 1, Turno.Estado.CONFIRMADO, False),
    ('MKTG DEMO TURNO SEMANA', 5, Turno.Estado.RESERVADO, False),
    ('MKTG DEMO TURNO PASADO 1', -3, Turno.Estado.REALIZADO, True),
    ('MKTG DEMO TURNO PASADO 2', -10, Turno.Estado.REALIZADO, True),
    ('MKTG DEMO TURNO PASADO 3', -20, Turno.Estado.REALIZADO, True),
]


class Command(BaseCommand):
    help = 'Pobla datos ficticios MKTG para demo promocional (idempotente)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== seed_demo_marketing (MKTG) ==='))

        medico_user = User.objects.filter(username='medico1').first()
        paciente_user = User.objects.filter(username='paciente1').first()
        bio_user = User.objects.filter(username='bioquimico1').first()
        if not medico_user or not paciente_user:
            self.stdout.write('Usuarios base ausentes; ejecutando seed_data…')
            call_command('seed_data')
            medico_user = User.objects.get(username='medico1')
            paciente_user = User.objects.get(username='paciente1')
            bio_user = User.objects.filter(username='bioquimico1').first()

        medico = Medico.objects.filter(user=medico_user).first()
        if medico is None:
            raise CommandError('medico1 sin perfil Medico. Corré ./emrctl seed primero.')

        paciente_portal = Paciente.objects.filter(user=paciente_user).first()
        if paciente_portal is None:
            raise CommandError('paciente1 sin ficha Paciente. Corré ./emrctl seed primero.')

        tipo_glu = TipoExamen.objects.filter(codigo='GLU').first()
        tipo_hemo = TipoExamen.objects.filter(codigo='HEMO').first()
        tipo_col = TipoExamen.objects.filter(codigo='COL').first()
        muestra_sangre = TipoMuestra.objects.filter(codigo='SANGRE').first()
        if not tipo_glu or not muestra_sangre:
            raise CommandError('Catálogo LIMS básico ausente. Corré ./emrctl seed primero.')

        recurso = self._ensure_recurso()
        pac_int = self._ensure_internacion_pacientes()
        self._seed_turnos_y_hc(medico, paciente_portal, recurso, medico_user)
        self._seed_lims(
            medico,
            paciente_portal,
            tipo_glu,
            tipo_hemo,
            tipo_col,
            muestra_sangre,
            bio_user,
        )
        self._seed_internacion(medico, pac_int)

        self.stdout.write(self.style.SUCCESS('\n✓ Demo marketing lista'))
        self.stdout.write('  Abrí http://localhost:3000/demo')
        self.stdout.write('  Roles: medico1, laboratorio1, enfermeria1, paciente1')
        self.stdout.write(f'  LIMS vivo: {MKTG_LIMS_VIVO} | finalizado: {MKTG_LIMS_FINAL}')
        self.stdout.write(f'  Paciente portal: {paciente_portal.dni} (id={paciente_portal.pk})')

    def _ensure_recurso(self):
        recurso, created = Recurso.objects.get_or_create(
            nombre=MKTG_RECURSO,
            defaults={
                'ubicacion': Recurso.Ubicacion.CEHTA,
                'tipo_recurso': Recurso.TipoRecurso.CONSULTORIO,
                'activo': True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Recurso {recurso.nombre}')
            if created
            else f'  → Recurso {recurso.nombre}'
        )
        return recurso

    def _ensure_internacion_pacientes(self):
        specs = [
            (MKTG_PACIENTE_INT_1, 'Lucía', 'Fernández'),
            (MKTG_PACIENTE_INT_2, 'Martín', 'Rojas'),
            (MKTG_PACIENTE_INT_3, 'Elena', 'Suárez'),
        ]
        out = []
        for dni, nombre, apellido in specs:
            p, created = Paciente.objects.get_or_create(
                dni=dni,
                defaults={
                    'nombre': nombre,
                    'apellido': apellido,
                    'observaciones': 'MKTG DEMO - paciente internación (ficticio)',
                },
            )
            out.append(p)
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Paciente {dni}')
                if created
                else f'  → Paciente {dni}'
            )
        return out

    def _seed_turnos_y_hc(self, medico, paciente, recurso, medico_user):
        self.stdout.write('Turnos + HC…')
        now = timezone.now()
        for motivo, day_offset, estado, with_atencion in TURNO_SPECS:
            inicio = now + timedelta(days=day_offset)
            # Normalizar a franja mañana para agenda legible
            inicio = inicio.replace(hour=10, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(minutes=30)
            turno = Turno.objects.filter(motivo_reserva=motivo).first()
            if not turno:
                turno = Turno.objects.create(
                    paciente=paciente,
                    medico=medico,
                    recurso=recurso,
                    fecha_hora_inicio=inicio,
                    fecha_hora_fin=fin,
                    estado=estado,
                    motivo_reserva=motivo,
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ Turno {motivo}'))
            else:
                self.stdout.write(f'  → Turno {motivo}')

            if not with_atencion:
                continue
            atencion = Atencion.objects.filter(turno=turno).first()
            if not atencion:
                obs_map = {
                    'MKTG DEMO TURNO HOY': (
                        'MKTG DEMO — Control ambulatorio. Paciente estable, '
                        'refiere buena adherencia al tratamiento.'
                    ),
                    'MKTG DEMO TURNO PASADO 1': (
                        'MKTG DEMO — Consulta por disnea leve. ECG sin cambios agudos. '
                        'Se solicita laboratorio de control.'
                    ),
                    'MKTG DEMO TURNO PASADO 2': (
                        'MKTG DEMO — Seguimiento post-alta. Ajuste de medicación antihipertensiva.'
                    ),
                    'MKTG DEMO TURNO PASADO 3': (
                        'MKTG DEMO — Primera consulta. Antecedentes: HTA, dislipemia. '
                        'Plan: estudios y seguimiento cardiológico.'
                    ),
                }
                # Solo FINALIZADA: el dominio bloquea cualquier alta ambulatoria nueva si ya hay
                # una ABIERTA (p. ej. seed QA). Las MKTG son históricas; bypaseamos Atencion.save/full_clean.
                atencion = Atencion(
                    turno=turno,
                    paciente=paciente,
                    medico_principal=medico,
                    tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
                    tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
                    estado_clinico=Atencion.EstadoClinico.FINALIZADA,
                    observaciones_generales=obs_map.get(
                        motivo, 'MKTG DEMO — atención sintética'
                    ),
                )
                # models.Model.save evita exclusividad de situación (válido solo para seed histórico).
                from django.db import models as dj_models

                dj_models.Model.save(atencion, force_insert=True)
                Atencion.objects.filter(pk=atencion.pk).update(
                    fecha_cierre=inicio + timedelta(minutes=40)
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ Atención para {motivo}'))
            else:
                self.stdout.write(f'  → Atención para {motivo}')

            if not atencion.signos_vitales.exists():
                SignosVitales.objects.create(
                    atencion=atencion,
                    registrado_por=medico_user,
                    rol_registrador=SignosVitales.RolRegistrador.MEDICO,
                    fecha_registro=turno.fecha_hora_inicio,
                    tension_arterial='128/78',
                    frecuencia_cardiaca=72,
                    frecuencia_respiratoria=16,
                    temperatura=Decimal('36.5'),
                    saturacion_oxigeno=Decimal('98.0'),
                    peso=Decimal('78.50'),
                    talla=Decimal('1.72'),
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ Signos vitales ({motivo})'))

    def _seed_lims(
        self,
        medico,
        paciente,
        tipo_glu,
        tipo_hemo,
        tipo_col,
        muestra_sangre,
        bio_user,
    ):
        self.stdout.write('LIMS…')
        examenes_vivo = [e for e in (tipo_glu, tipo_hemo) if e]
        examenes_final = [e for e in (tipo_glu, tipo_col, tipo_hemo) if e]

        sol_vivo, created = SolicitudExamen.objects.get_or_create(
            numero=MKTG_LIMS_VIVO,
            defaults={
                'paciente': paciente,
                'medico_interno': medico,
                'origen_solicitud': 'AMBULATORIO_CEHTA',
                'estado': 'EN_PROCESO',
                'observaciones': 'MKTG DEMO - orden en proceso (laboratorio)',
            },
        )
        for ex in examenes_vivo:
            sol_vivo.tipos_examen.add(ex)
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Orden {MKTG_LIMS_VIVO}')
            if created
            else f'  → Orden {MKTG_LIMS_VIVO}'
        )

        muestra_v, mv_created = Muestra.objects.get_or_create(
            codigo_barra=MKTG_MUESTRA_VIVO,
            defaults={
                'solicitud': sol_vivo,
                'paciente': paciente,
                'tipo_muestra': muestra_sangre,
                'estado': 'TOMADA',
                'observaciones': 'MKTG DEMO - muestra viva',
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Muestra {MKTG_MUESTRA_VIVO}')
            if mv_created
            else f'  → Muestra {MKTG_MUESTRA_VIVO}'
        )

        for ex in examenes_vivo:
            res, r_created = ResultadoExamen.objects.get_or_create(
                solicitud=sol_vivo,
                tipo_examen=ex,
                defaults={
                    'valor_obtenido': '95' if ex.codigo == 'GLU' else 'Pendiente carga',
                    'es_patologico': False,
                    'muestra': muestra_v,
                    'unidad': 'mg/dL' if ex.codigo == 'GLU' else '',
                },
            )
            if r_created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Resultado vivo {ex.codigo}'))
            elif not res.valor_obtenido:
                res.valor_obtenido = '95' if ex.codigo == 'GLU' else 'Pendiente carga'
                res.muestra = muestra_v
                res.save(update_fields=['valor_obtenido', 'muestra'])

        sol_fin, created = SolicitudExamen.objects.get_or_create(
            numero=MKTG_LIMS_FINAL,
            defaults={
                'paciente': paciente,
                'medico_interno': medico,
                'origen_solicitud': 'AMBULATORIO_CEHTA',
                'estado': 'EN_PROCESO',
                'observaciones': 'MKTG DEMO - orden finalizada (portal paciente)',
            },
        )
        # Debe estar EN_PROCESO mientras se cargan resultados (regla de ResultadoExamen.clean).
        if sol_fin.estado == 'FINALIZADO':
            SolicitudExamen.objects.filter(pk=sol_fin.pk).update(estado='EN_PROCESO')
            sol_fin.refresh_from_db()
        for ex in examenes_final:
            sol_fin.tipos_examen.add(ex)
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Orden {MKTG_LIMS_FINAL} (base)')
            if created
            else f'  → Orden {MKTG_LIMS_FINAL}'
        )

        muestra_f, mf_created = Muestra.objects.get_or_create(
            codigo_barra=MKTG_MUESTRA_FINAL,
            defaults={
                'solicitud': sol_fin,
                'paciente': paciente,
                'tipo_muestra': muestra_sangre,
                'estado': 'RECIBIDA',
                'observaciones': 'MKTG DEMO - muestra finalizada',
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Muestra {MKTG_MUESTRA_FINAL}')
            if mf_created
            else f'  → Muestra {MKTG_MUESTRA_FINAL}'
        )

        valores = {
            'GLU': ('92', Decimal('92'), 'mg/dL', '70-100'),
            'COL': ('185', Decimal('185'), 'mg/dL', '< 200'),
            'HEMO': ('Dentro de parámetros', None, '', 'Ver informe'),
        }
        now = timezone.now()
        for ex in examenes_final:
            v_txt, v_num, unidad, rango = valores.get(
                ex.codigo, ('OK', None, '', '')
            )
            res, r_created = ResultadoExamen.objects.get_or_create(
                solicitud=sol_fin,
                tipo_examen=ex,
                defaults={
                    'valor_obtenido': v_txt,
                    'valor_numerico': v_num,
                    'unidad': unidad,
                    'rango_referencia_snapshot': rango,
                    'es_patologico': False,
                    'muestra': muestra_f,
                    'validado_por': bio_user,
                    'fecha_validacion': now - timedelta(days=2),
                    'observaciones': 'MKTG DEMO - resultado validado (ficticio)',
                },
            )
            if not r_created and res.validado_por_id is None and bio_user:
                res.valor_obtenido = v_txt
                res.valor_numerico = v_num
                res.unidad = unidad
                res.rango_referencia_snapshot = rango
                res.muestra = muestra_f
                res.validado_por = bio_user
                res.fecha_validacion = now - timedelta(days=2)
                res.save()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Resultado final validado {ex.codigo}'))
            elif r_created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Resultado final {ex.codigo}'))

        SolicitudExamen.objects.filter(pk=sol_fin.pk).update(estado='FINALIZADO')
        self.stdout.write(self.style.SUCCESS(f'  ✓ Orden {MKTG_LIMS_FINAL} → FINALIZADO'))

    def _ensure_sectores_camas(self):
        sector_uco, _ = Sector.objects.get_or_create(nombre='UCO')
        sector_uce, _ = Sector.objects.get_or_create(nombre='UCE')
        camas = []
        for sector, count, aislada_n in (
            (sector_uco, 6, 6),
            (sector_uce, 9, 9),
        ):
            for i in range(1, count + 1):
                cama, _ = Cama.objects.get_or_create(
                    nombre=f'Cama {i}',
                    sector=sector,
                    defaults={
                        'estado': 'DISPONIBLE',
                        'aislada': i == aislada_n,
                    },
                )
                camas.append(cama)
        return camas

    def _seed_internacion(self, medico, pacientes):
        self.stdout.write('Internación…')
        call_command('poblar_tipos_dieta')
        camas = self._ensure_sectores_camas()
        disponibles = [
            c
            for c in camas
            if c.estado == 'DISPONIBLE'
            or not Internacion.objects.filter(cama=c, activo=True).exists()
        ]
        # Preferir camas sin internación activa MKTG; reutilizar get_or_create por numero
        specs = [
            (MKTG_INT_1, pacientes[0], 'MKTG DEMO — Infarto agudo de miocardio (ficticio)', 2),
            (MKTG_INT_2, pacientes[1], 'MKTG DEMO — Insuficiencia cardíaca congestiva (ficticio)', 5),
            (MKTG_INT_3, pacientes[2], 'MKTG DEMO — Angina inestable (ficticio)', 1),
        ]
        now = timezone.now()
        used_camas = set()
        for numero, paciente, dx, days_ago in specs:
            existing = Internacion.objects.filter(numero_internacion=numero).first()
            if existing:
                self.stdout.write(f'  → Internación {numero}')
                continue
            cama = None
            for c in camas:
                if c.pk in used_camas:
                    continue
                if Internacion.objects.filter(cama=c, activo=True).exists():
                    continue
                cama = c
                break
            if cama is None:
                self.stdout.write(
                    self.style.WARNING(f'  ! Sin cama libre para {numero}; omitido')
                )
                continue
            used_camas.add(cama.pk)
            Internacion.objects.create(
                numero_internacion=numero,
                paciente=paciente,
                cama=cama,
                medico=medico,
                diagnostico_ingreso=dx,
                fecha_ingreso=now - timedelta(days=days_ago),
                activo=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Internación {numero} → {cama} ({paciente.dni})')
            )
        # Silenciar unused
        _ = disponibles
