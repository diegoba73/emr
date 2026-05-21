"""
Service Layer para la gestión de transiciones de Turno a Atención.

Este módulo contiene la lógica de negocio atómica para iniciar atenciones médicas
derivadas de turnos, asegurando la integridad referencial y evitando lógica dispersa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from django.db import transaction

from turnos.models import Turno, Atencion, ConsultaAmbulatoria, RegistroProcedimiento, RegistroQuirurgico, Recurso


# Mensajes alineados con el contrato histórico de POST /api/atenciones/ (AtencionViewSet.create).
MSG_API_TURNO_INEXISTENTE = "El turno {turno_id} no existe."
MSG_API_PACIENTE = "El turno no tiene un paciente asignado."
MSG_API_MEDICO = "El turno no tiene un médico asignado. No se puede crear la atención."
MSG_API_RECURSO = "El turno no tiene un recurso asignado."


def resolve_tipo_intervencion_from_recurso(tipo_recurso: str) -> str:
    """
    Mapea el tipo de recurso físico al tipo de intervención clínica.
    """
    mapping = {
        Recurso.TipoRecurso.CONSULTORIO: Atencion.TipoIntervencion.CONSULTA,
        Recurso.TipoRecurso.SALA_PROCEDIMIENTO: Atencion.TipoIntervencion.ESTUDIO,
        Recurso.TipoRecurso.SALA_HEMODINAMIA: Atencion.TipoIntervencion.PROCEDIMIENTO,
        Recurso.TipoRecurso.QUIROFANO: Atencion.TipoIntervencion.CIRUGIA,
    }
    return mapping.get(tipo_recurso, Atencion.TipoIntervencion.CONSULTA)

logger = logging.getLogger(__name__)


class BusinessLogicError(Exception):
    """
    Excepción personalizada para errores de lógica de negocio.
    Usada para errores que deben retornarse como 400 Bad Request.
    """
    pass


@dataclass(frozen=True)
class IniciarAtencionOutcome:
    """Resultado de iniciar una atención desde turno."""

    atencion: Atencion
    created_new: bool


@dataclass(frozen=True)
class IniciarAtencionClinicaOutcome:
    """Resultado del flujo clínico C5.10.1 (turno → REALIZADO + atención idempotente)."""

    atencion: Atencion
    created_new: bool
    turno_estado_anterior: str
    turno_estado_nuevo: str
    turno_estado_changed: bool


class AtencionService:
    """
    Service Layer para operaciones relacionadas con Atención.
    Encapsula la lógica de negocio para transiciones de Turno a Atención.
    """

    @staticmethod
    def iniciar_atencion_desde_turno(
        turno_id: int,
        usuario_solicitante=None,
        *,
        observaciones_generales: str = "",
        api_post_compat: bool = False,
        actor=None,
    ) -> IniciarAtencionOutcome:
        """
        Inicia una atención médica derivada de un turno dentro de una sola transaction.atomic.

        Modo por defecto (api_post_compat=False) — flujo de orquestación completa:
        - Estado del turno solo RESERVADO/CONFIRMADO; pasa a REALIZADO
        - Crea Atencion y registro hijo según recurso

        Modo compat POST /api/atenciones/ (api_post_compat=True):
        - Mismas validaciones y textos que el AtencionViewSet.create histórico
        - Si ya existe Atención para el turno, devuelve esa fila sin error (idempotencia)
        - No cambia estado del Turno ni crea registro hijo
        - Auditoría de alta (``log_create``) solo en creación efectiva; en idempotencia no se registra evento

        Returns:
            IniciarAtencionOutcome: atencion + created_new (False si idempotencia en modo API)
        """
        logger.info(
            "Intentando iniciar atención desde turno %s (api_post_compat=%s). Usuario solicitante: %s",
            turno_id,
            api_post_compat,
            usuario_solicitante.username if usuario_solicitante else "N/A",
        )

        if api_post_compat:
            return AtencionService._iniciar_desde_turno_api_post(
                turno_id,
                usuario_solicitante=usuario_solicitante,
                observaciones_generales=observaciones_generales,
                actor=actor,
            )

        try:
            with transaction.atomic():
                try:
                    turno = Turno.objects.select_for_update().get(pk=turno_id)
                except Turno.DoesNotExist:
                    logger.error("Turno %s no existe", turno_id)
                    raise BusinessLogicError(f"El turno {turno_id} no existe")

                try:
                    atencion_existente = turno.atencion
                    logger.warning(
                        "El turno %s ya tiene una atención asociada (ID: %s)",
                        turno_id,
                        atencion_existente.id,
                    )
                    raise BusinessLogicError(
                        f"El turno {turno_id} ya tiene una atención asociada. "
                        f"No se puede crear una nueva atención."
                    )
                except Atencion.DoesNotExist:
                    pass

                estados_permitidos = ["RESERVADO", "CONFIRMADO"]
                if turno.estado not in estados_permitidos:
                    logger.warning(
                        "El turno %s está en estado '%s', no permite iniciar atención.",
                        turno_id,
                        turno.estado,
                    )
                    raise BusinessLogicError(
                        f"El turno está en estado '{turno.estado}'. "
                        f"Solo se pueden iniciar atenciones desde turnos en estado: "
                        f"{', '.join(estados_permitidos)}"
                    )

                if not turno.paciente:
                    logger.error("El turno %s no tiene paciente asociado", turno_id)
                    raise BusinessLogicError("El turno no tiene un paciente asociado")

                if not turno.medico:
                    logger.error("El turno %s no tiene médico asociado", turno_id)
                    raise BusinessLogicError("El turno no tiene un médico asociado")

                if not turno.recurso:
                    logger.error("El turno %s no tiene recurso asociado", turno_id)
                    raise BusinessLogicError("El turno no tiene un recurso asociado")

                estado_anterior = turno.estado
                turno.estado = "REALIZADO"
                turno.save(update_fields=["estado", "updated_at"])
                logger.info(
                    "Estado del turno %s cambiado de '%s' a 'REALIZADO'",
                    turno_id,
                    estado_anterior,
                )

                tipo_atencion = turno.recurso.tipo_recurso
                tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)

                logger.info(
                    "Creando Atencion: tipo_atencion=%s, tipo_intervencion=%s",
                    tipo_atencion,
                    tipo_intervencion,
                )

                atencion = Atencion.objects.create(
                    turno=turno,
                    paciente=turno.paciente,
                    medico_principal=turno.medico,
                    tipo_atencion=tipo_atencion,
                    tipo_intervencion=tipo_intervencion,
                    estado_clinico=Atencion.EstadoClinico.ABIERTA,
                )

                logger.info("Atencion %s creada exitosamente para turno %s", atencion.id, turno_id)

                AtencionService._crear_registro_hijo(atencion, tipo_atencion)

                logger.info(
                    "Atención %s iniciada exitosamente desde turno %s (tipo registro %s)",
                    atencion.id,
                    turno_id,
                    tipo_atencion,
                )

                return IniciarAtencionOutcome(atencion=atencion, created_new=True)

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(
                "Error inesperado al iniciar atención desde turno %s: %s",
                turno_id,
                str(e),
                exc_info=True,
            )
            raise

    @staticmethod
    def _iniciar_desde_turno_api_post(
        turno_id,
        *,
        usuario_solicitante,
        observaciones_generales: str,
        actor,
    ) -> IniciarAtencionOutcome:
        """Lógica exclusiva de POST /api/atenciones/ (idempotencia, sin hijo, sin cambio de turno)."""
        from auditoria.audit_service import log_create

        with transaction.atomic():
            try:
                turno = (
                    Turno.objects.select_related("paciente", "medico", "recurso")
                    # PG: FOR UPDATE con OUTER JOIN por FKs nulas; bloquear solo la fila de turnos.
                    .select_for_update(of=("self",))
                    .get(pk=turno_id)
                )
            except Turno.DoesNotExist:
                raise BusinessLogicError(MSG_API_TURNO_INEXISTENTE.format(turno_id=turno_id))

            existing = (
                Atencion.objects.select_related("paciente", "medico_principal", "turno")
                .select_for_update(of=("self",))
                .filter(turno_id=turno.pk)
                .first()
            )
            if existing is not None:
                return IniciarAtencionOutcome(atencion=existing, created_new=False)

            if not turno.paciente:
                raise BusinessLogicError(MSG_API_PACIENTE)
            if not turno.medico:
                raise BusinessLogicError(MSG_API_MEDICO)
            if not turno.recurso:
                raise BusinessLogicError(MSG_API_RECURSO)

            tipo_atencion = turno.recurso.tipo_recurso
            tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)

            atencion = Atencion.objects.create(
                turno=turno,
                paciente=turno.paciente,
                medico_principal=turno.medico,
                tipo_atencion=tipo_atencion,
                tipo_intervencion=tipo_intervencion,
                estado_clinico=Atencion.EstadoClinico.ABIERTA,
                observaciones_generales=observaciones_generales,
            )

            logger.info(
                "Atención %s creada para turno %s. Paciente: %s, Médico: %s",
                atencion.id,
                turno_id,
                atencion.paciente_id,
                atencion.medico_principal_id,
            )

            log_create(
                actor=actor,
                entity=atencion,
                module="turnos",
                metadata={"view": "AtencionViewSet.create"},
            )

            return IniciarAtencionOutcome(atencion=atencion, created_new=True)

    @staticmethod
    def iniciar_atencion_clinica_desde_turno(turno: Turno) -> IniciarAtencionClinicaOutcome:
        """
        Flujo clínico activo (C5.10.1): idempotente, mueve turno a REALIZADO, crea hijo si es alta nueva.

        El turno debe estar bloqueado con ``select_for_update`` en la capa de vista.
        No registra auditoría (la coordina ``TurnoViewSet.iniciar_atencion``).
        """
        estados_inicio_nueva = (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO)

        if turno.estado in (Turno.Estado.CANCELADO, Turno.Estado.DISPONIBLE):
            raise BusinessLogicError(
                f"El turno está en estado '{turno.estado}'. "
                "No se puede iniciar atención clínica."
            )

        existing = Atencion.objects.filter(turno_id=turno.pk).first()
        estado_anterior = turno.estado

        if existing is not None:
            turno_estado_changed = False
            if turno.estado != Turno.Estado.REALIZADO:
                turno.estado = Turno.Estado.REALIZADO
                turno.save(update_fields=["estado", "updated_at"])
                turno_estado_changed = True
            return IniciarAtencionClinicaOutcome(
                atencion=existing,
                created_new=False,
                turno_estado_anterior=estado_anterior,
                turno_estado_nuevo=turno.estado,
                turno_estado_changed=turno_estado_changed,
            )

        if turno.estado == Turno.Estado.REALIZADO:
            raise BusinessLogicError(
                "El turno está realizado pero no tiene atención asociada."
            )

        if turno.estado not in estados_inicio_nueva:
            raise BusinessLogicError(
                f"El turno está en estado '{turno.estado}'. "
                f"Solo se pueden iniciar atenciones desde turnos en estado: "
                f"{', '.join(estados_inicio_nueva)}"
            )

        if not turno.paciente:
            raise BusinessLogicError("El turno no tiene un paciente asociado")
        if not turno.medico:
            raise BusinessLogicError("El turno no tiene un médico asociado")
        if not turno.recurso:
            raise BusinessLogicError("El turno no tiene un recurso asociado")

        turno.estado = Turno.Estado.REALIZADO
        turno.save(update_fields=["estado", "updated_at"])

        tipo_atencion = turno.recurso.tipo_recurso
        tipo_intervencion = resolve_tipo_intervencion_from_recurso(tipo_atencion)

        atencion = Atencion.objects.create(
            turno=turno,
            paciente=turno.paciente,
            medico_principal=turno.medico,
            tipo_atencion=tipo_atencion,
            tipo_intervencion=tipo_intervencion,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )
        AtencionService._crear_registro_hijo(atencion, tipo_atencion)

        return IniciarAtencionClinicaOutcome(
            atencion=atencion,
            created_new=True,
            turno_estado_anterior=estado_anterior,
            turno_estado_nuevo=turno.estado,
            turno_estado_changed=True,
        )

    @staticmethod
    def _crear_registro_hijo(atencion: Atencion, tipo_atencion: str) -> None:
        """
        Factory method para crear el registro hijo correspondiente según el tipo de recurso.
        
        Args:
            atencion: Instancia de Atencion recién creada
            tipo_atencion: Tipo de atención/recurso (CONSULTORIO, SALA_PROCEDIMIENTO, etc.)
        """
        logger.debug(
            f"Creando registro hijo para Atencion {atencion.id}, tipo_atencion={tipo_atencion}"
        )
        
        # Mapeo de tipo_recurso a registro hijo
        if tipo_atencion == Recurso.TipoRecurso.CONSULTORIO:
            # Crear ConsultaAmbulatoria
            ConsultaAmbulatoria.objects.create(atencion=atencion)
            logger.info(f"ConsultaAmbulatoria creada para Atencion {atencion.id}")
            
        elif tipo_atencion == Recurso.TipoRecurso.SALA_PROCEDIMIENTO:
            # Crear RegistroProcedimiento (requiere descripcion_procedimiento mínimo)
            RegistroProcedimiento.objects.create(
                atencion=atencion,
                descripcion_procedimiento=f"Procedimiento iniciado desde turno {atencion.turno_id}"
            )
            logger.info(f"RegistroProcedimiento creado para Atencion {atencion.id}")
            
        elif tipo_atencion in [Recurso.TipoRecurso.QUIROFANO, Recurso.TipoRecurso.SALA_HEMODINAMIA]:
            # Crear RegistroQuirurgico (requiere anestesista, diagnostico_preoperatorio, protocolo_quirurgico)
            # Como estos campos son requeridos, usamos valores por defecto temporales
            # En producción, estos deberían ser proporcionados por el usuario
            from medicos.models import Medico
            # Usar el médico principal como anestesista por defecto (se puede cambiar después)
            anestesista = atencion.medico_principal
            
            RegistroQuirurgico.objects.create(
                atencion=atencion,
                anestesista=anestesista,
                diagnostico_preoperatorio="Pendiente de completar",
                protocolo_quirurgico="Pendiente de completar",
            )
            logger.info(f"RegistroQuirurgico creado para Atencion {atencion.id}")
            
        else:
            logger.warning(
                f"Tipo de recurso '{tipo_atencion}' no tiene mapeo a registro hijo. "
                f"Atencion {atencion.id} creada sin registro hijo."
            )
            # No crear registro hijo si no hay mapeo definido

