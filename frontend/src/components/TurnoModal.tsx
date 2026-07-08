import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Drawer,
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Typography,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Close } from '@mui/icons-material';
import { useQueryClient } from '@tanstack/react-query';
import { useData } from '../contexts/DataContext';
import { apiService } from '../services/api';
import { Paciente, Medico, Turno } from '../types';
import AsyncAutocomplete from './common/AsyncAutocomplete';
import { MotivoDialog, useMotivoDialog } from './common/MotivoDialog';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';
import { formatLocalDateTimeSeconds } from '../utils/formatLocalDateTime';
import { formatFecha, formatHora } from '../utils/dateFieldFormat';
import { turnoInicioFromApi } from '../utils/turnoDatetimeFromApi';
import { getTurnoModalFormInitKey } from '../utils/turnoModalInitKey';
import {
  canCreateTurno,
  canEditTurno as canEditTurnoByRole,
  canConfirmarTurno,
  canCancelarTurnoAccion,
  canReprogramarTurno,
  canMarcarRealizadoTurno,
  canMarcarNoAsistioTurno,
  canMutateTurnosGlobally,
  pacientePuedeMutarTurno,
  getCurrentMedicoId,
  shouldLockMedicoField,
} from '../utils/turnoPermissions';
import {
  CLINICAL_ACTION_ERRORS,
  getSafeClinicalActionMessage,
} from '../utils/apiError';
import { isTurnoEstudio, listRecursosEstudioAgenda } from '../utils/recursosEstudio';
import { getTurnoAgendaKind, TURNO_KIND_META } from '../utils/turnoKind';
import { Link as RouterLink } from 'react-router-dom';
import AgendaTipoSelector, { type AgendaTipo } from './turnos/AgendaTipoSelector';
import { asignarTurnoEstudio, agendarTurnoEstudioDesdeAgenda, listTiposEstudioComplementario } from '../services/estudiosComplementariosApi';
import { parseEstudiosApiError } from '../modules/estudios/apiErrors';
import { canAsignarTurnoEstudio } from '../modules/estudios/permissions';
import type { EstudioComplementario, TipoEstudioComplementario } from '../types/estudios';
import { ORIGEN_OPTIONS } from '../modules/estudios/constants';
import { pacienteLabelFromList } from '../utils/estudioAgendaFormat';
import {
  buildEstudioTipoCatalogOptions,
  isEstudioTipoCatalogFallbackId,
  resolveEstudioModalidadFromTipoId,
} from '../utils/estudioTipoCatalog';
import type { Recurso } from '../types';

const getMedicoLabel = (medico?: Medico | null) => {
  if (!medico) return '';
  const nombre = medico.nombre || '';
  const apellido = medico.apellido || '';
  const displayName = `${nombre} ${apellido}`.trim();
  return displayName ? `Dr. ${displayName}` : `Médico ${medico.id}`;
};

interface TurnoFormData {
  paciente: string;
  medico: string;
  recurso: string;
  fecha: string;
  horaInicio: string;
  duracionMin: number;
  motivo: string;
  estado: 'RESERVADO' | 'CONFIRMADO' | 'REALIZADO' | 'CANCELADO';
  prioridad: 'NORMAL' | 'ALTA' | 'URGENTE';
}

interface TurnoModalProps {
  open: boolean;
  onClose: () => void;
  editingTurno?: any;
  onSuccess?: () => void;
  /** Slot elegido en react-big-calendar; no se usa al editar un turno existente. */
  selectedDateTime?: Date | null;
  onOpenAtencion?: (atencionId: number) => void;
  /** Solo lectura por rol (enfermería, turno ajeno, etc.). Backend sigue siendo SoT. */
  forceReadOnly?: boolean;
  /** Al crear: tipo inicial (consulta o estudio). */
  initialAgendaTipo?: AgendaTipo;
  /** Estudio preseleccionado (p. ej. desde módulo Estudios). */
  initialEstudio?: EstudioComplementario | null;
}

const TurnoModal: React.FC<TurnoModalProps> = ({
  open,
  onClose,
  editingTurno,
  onSuccess,
  selectedDateTime = null,
  onOpenAtencion,
  forceReadOnly = false,
  initialAgendaTipo = 'consulta',
  initialEstudio = null,
}) => {
  const {
    recursos,
    currentUser,
    loadRecursos,
    refreshTurnos,
    pacientes,
    loadPacientes,
  } = useData();
  const queryClient = useQueryClient();
  const { openMotivoDialog, dialogProps: motivoDialogProps } = useMotivoDialog();

  /** Turno recargado del API (incluye `atencion` anidada) al abrir el panel */
  const [turnoEfectivo, setTurnoEfectivo] = useState<Turno | undefined>(undefined);
  useEffect(() => {
    if (!open) {
      setTurnoEfectivo(undefined);
      return;
    }
    if (!editingTurno?.id) {
      setTurnoEfectivo(editingTurno);
      return;
    }
    setTurnoEfectivo(editingTurno);
    let cancelled = false;
    (async () => {
      try {
        const t = await apiService.getTurno(editingTurno.id);
        if (!cancelled) {
          setTurnoEfectivo(t);
        }
      } catch (e) {
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, editingTurno?.id]);

  /** Usar para reglas de UI (atención/consulta); puede incluir datos más recientes que `editingTurno` */
  const turnoVista = turnoEfectivo ?? editingTurno;

  // Estados para los objetos seleccionados (para AsyncAutocomplete)
  const [selectedPaciente, setSelectedPaciente] = useState<Paciente | null>(null);
  const [selectedMedico, setSelectedMedico] = useState<Medico | null>(null);

  const pacienteSeleccionado = useMemo<Paciente | null>(() => {
    if (!editingTurno) return null;
    const turnoPaciente = editingTurno.paciente && typeof editingTurno.paciente === 'object'
      ? editingTurno.paciente as Paciente
      : null;
    const pacienteId = turnoPaciente?.id
      || editingTurno.paciente_id
      || (typeof editingTurno.paciente === 'number' ? editingTurno.paciente : null);

    if (!pacienteId) return turnoPaciente || null;

    if (turnoPaciente) {
      return {
        ...turnoPaciente,
        id: turnoPaciente.id ?? pacienteId,
        nombre: turnoPaciente.nombre || '',
        apellido: turnoPaciente.apellido || '',
        dni: turnoPaciente.dni || '',
      } as Paciente;
    }

    // Si no encontramos el paciente en la lista local, retornar null
    // AsyncAutocomplete lo cargará desde el servidor si es necesario
    return null;
  }, [editingTurno]);

  const medicoSeleccionado = useMemo<Medico | null>(() => {
    if (!editingTurno) return null;
    const turnoMedico = editingTurno.medico && typeof editingTurno.medico === 'object'
      ? editingTurno.medico as Medico
      : null;
    const medicoId = turnoMedico?.id
      || editingTurno.medico_id
      || editingTurno.medico?.id
      || null;

    if (!medicoId) return turnoMedico || null;

    if (turnoMedico) {
      return {
        ...turnoMedico,
        id: turnoMedico.id ?? medicoId,
        nombre: turnoMedico.nombre || '',
        apellido: turnoMedico.apellido || '',
        matricula: turnoMedico.matricula || '',
        especialidad: turnoMedico.especialidad,
      } as Medico;
    }

    // Si no encontramos el médico en la lista local, retornar null
    // AsyncAutocomplete lo cargará desde el servidor si es necesario
    return null;
  }, [editingTurno]);

  // Inicializar valores seleccionados cuando se abre el modal o cambia editingTurno
  useEffect(() => {
    if (!open) {
      setSelectedPaciente(null);
      setSelectedMedico(null);
      return;
    }

    // Si estamos editando, usar los valores calculados
    if (editingTurno) {
      setSelectedPaciente(pacienteSeleccionado);
      setSelectedMedico(medicoSeleccionado);
    } else {
      setSelectedPaciente(null);
      setSelectedMedico(null);
    }
  }, [open, editingTurno, pacienteSeleccionado, medicoSeleccionado]);

  const [formData, setFormData] = useState<TurnoFormData>({
    paciente: '',
    medico: '',
    recurso: '',
    fecha: '',
    horaInicio: '',
    duracionMin: 60,
    motivo: '',
    estado: 'RESERVADO',
    prioridad: 'NORMAL',
  });

  const [isLoadingData, setIsLoadingData] = useState(false);
  const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);

  const lastFormInitKeyRef = useRef<string>('');


  // No filtrar manualmente, dejar que Autocomplete lo haga con filterOptions

  // Estados disponibles según el rol del usuario
  const estadosDisponibles = useMemo(() => {
    const isPaciente = currentUser?.rol === 'PACIENTE';
    const isMedico = currentUser?.rol === 'MEDICO';

    let estados: Array<{ value: string; label: string }> = [];

    if (isPaciente) {
      estados = [
        { value: 'RESERVADO', label: 'Reservado' },
        { value: 'CANCELADO', label: 'Cancelado' },
      ];
    } else if (isMedico) {
      estados = [
        { value: 'CONFIRMADO', label: 'Confirmado' },
        { value: 'REALIZADO', label: 'Realizado' },
        { value: 'CANCELADO', label: 'Cancelado' },
      ];
    } else {
      // Secretarias y otros roles ven todos
      estados = [
        { value: 'RESERVADO', label: 'Reservado' },
        { value: 'CONFIRMADO', label: 'Confirmado' },
        { value: 'REALIZADO', label: 'Realizado' },
        { value: 'CANCELADO', label: 'Cancelado' },
      ];
    }

    // Si el estado actual del turno no está en la lista (por ejemplo, un turno existente con estado no disponible para este rol),
    // incluirlo para que se pueda mostrar pero no cambiar
    if (editingTurno?.estado && !estados.some(e => e.value === editingTurno.estado)) {
      const estadoLabels: { [key: string]: string } = {
        'RESERVADO': 'Reservado',
        'CONFIRMADO': 'Confirmado',
        'REALIZADO': 'Realizado',
        'CANCELADO': 'Cancelado'
      };
      estados.unshift({
        value: editingTurno.estado,
        label: estadoLabels[editingTurno.estado] || editingTurno.estado
      });
    }

    return estados;
  }, [currentUser?.rol, editingTurno?.estado]);

  const [loading, setLoading] = useState(false);

  const puedeAgendarEstudio = canAsignarTurnoEstudio(currentUser);
  const lockEstudioSelection = Boolean(initialEstudio?.id);
  const [agendaTipo, setAgendaTipo] = useState<AgendaTipo>('consulta');
  const [recursosEstudio, setRecursosEstudio] = useState<Recurso[]>([]);
  const [tiposEstudio, setTiposEstudio] = useState<TipoEstudioComplementario[]>([]);
  const [tipoEstudioId, setTipoEstudioId] = useState('');
  const [estudioOrigen, setEstudioOrigen] = useState('EXTERNO');
  const [loadingEstudioForm, setLoadingEstudioForm] = useState(false);
  const [estudioFormError, setEstudioFormError] = useState<string | null>(null);

  const isModoEstudio = !editingTurno && agendaTipo === 'estudio';
  const isModoConsulta = !editingTurno && agendaTipo === 'consulta';

  const canMutateByRole = useMemo(() => {
    if (forceReadOnly || !currentUser) return false;
    if (editingTurno) return canEditTurnoByRole(currentUser, turnoVista);
    if (initialEstudio || agendaTipo === 'estudio') return puedeAgendarEstudio;
    return canCreateTurno(currentUser);
  }, [forceReadOnly, currentUser, editingTurno, turnoVista, initialEstudio, agendaTipo, puedeAgendarEstudio]);

  const lockMedicoField = shouldLockMedicoField(currentUser);
  const turnoParaAcciones = (turnoVista as Turno | undefined) ?? editingTurno;

  const handleConfirmarTurno = async () => {
    if (!editingTurno?.id) return;
    setLoading(true);
    try {
      const { turno } = await apiService.confirmarTurno(editingTurno.id);
      setTurnoEfectivo(turno);
      alert('Turno confirmado');
      onSuccess?.();
    } catch (error: unknown) {
      alert(getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoConfirmar));
    } finally {
      setLoading(false);
    }
  };

  const handleCancelarTurnoAccion = () => {
    if (!editingTurno?.id) return;
    openMotivoDialog({
      title: 'Cancelar turno',
      label: 'Motivo de cancelación (obligatorio)',
      confirmLabel: 'Cancelar turno',
      onConfirm: async (motivo) => {
        try {
          const { turno } = await apiService.cancelarTurno(editingTurno.id, motivo);
          setTurnoEfectivo(turno);
          alert('Turno cancelado');
          onSuccess?.();
        } catch (error: unknown) {
          throw new Error(
            getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoCancelar)
          );
        }
      },
    });
  };

  const handleMarcarRealizado = async () => {
    if (!editingTurno?.id) return;
    setLoading(true);
    try {
      const { turno } = await apiService.marcarRealizadoTurno(editingTurno.id);
      setTurnoEfectivo(turno);
      alert('Turno marcado como realizado');
      onSuccess?.();
    } catch (error: unknown) {
      alert(getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoRealizado));
    } finally {
      setLoading(false);
    }
  };

  const handleMarcarNoAsistio = () => {
    if (!editingTurno?.id) return;
    openMotivoDialog({
      title: 'Registrar no asistencia',
      label: 'Motivo de no asistencia (obligatorio)',
      confirmLabel: 'Confirmar',
      initialMotivo: 'No asistió',
      onConfirm: async (motivo) => {
        try {
          const { turno } = await apiService.marcarNoAsistioTurno(editingTurno.id, motivo);
          setTurnoEfectivo(turno);
          alert('No asistencia registrada');
          onSuccess?.();
        } catch (error: unknown) {
          throw new Error(
            getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoNoAsistio)
          );
        }
      },
    });
  };

  const recursosLoadAttemptedRef = useRef(false);

  // Cargar recursos bajo demanda al abrir (sin refreshAll: evita bloquear la página Turnos).
  useEffect(() => {
    if (!open) {
      recursosLoadAttemptedRef.current = false;
      setIsLoadingData(false);
      return;
    }
    if (recursos.length > 0) {
      setIsLoadingData(false);
      return;
    }
    if (recursosLoadAttemptedRef.current) {
      return;
    }
    recursosLoadAttemptedRef.current = true;
    setIsLoadingData(true);
    void (async () => {
      try {
        await loadRecursos();
      } finally {
        setIsLoadingData(false);
      }
    })();
  }, [open, recursos.length, loadRecursos]);

  useEffect(() => {
    if (!open || editingTurno) return;
    const tipo: AgendaTipo =
      initialAgendaTipo === 'estudio' && puedeAgendarEstudio ? 'estudio' : 'consulta';
    setAgendaTipo(tipo);
    setEstudioFormError(null);
    if (initialEstudio?.paciente_id) {
      setFormData((prev) => ({
        ...prev,
        paciente: String(initialEstudio.paciente_id),
      }));
      const p = pacientes.find((x) => x.id === initialEstudio.paciente_id);
      if (p) setSelectedPaciente(p);
    }
    if (initialEstudio?.tipo_estudio) {
      setTipoEstudioId(String(initialEstudio.tipo_estudio));
    }
  }, [open, editingTurno, initialAgendaTipo, initialEstudio, puedeAgendarEstudio, pacientes]);

  useEffect(() => {
    if (open) return;
    setTiposEstudio([]);
    setTipoEstudioId('');
    setRecursosEstudio([]);
    setEstudioFormError(null);
    setLoadingEstudioForm(false);
  }, [open]);

  const estudioFormActivo =
    open && !editingTurno && agendaTipo === 'estudio' && puedeAgendarEstudio;

  useEffect(() => {
    if (!estudioFormActivo) return;
    if (pacientes.length === 0) {
      void loadPacientes();
    }
    let cancelled = false;
    setLoadingEstudioForm(true);
    setEstudioFormError(null);
    (async () => {
      const errors: string[] = [];
      try {
        const [salasResult, tiposResult] = await Promise.allSettled([
          listRecursosEstudioAgenda(),
          listTiposEstudioComplementario(),
        ]);

        if (cancelled) return;

        if (salasResult.status === 'fulfilled') {
          const salas = salasResult.value;
          setRecursosEstudio(salas);
          setFormData((prev) => {
            const salaValida =
              prev.recurso && salas.some((s) => String(s.id) === prev.recurso);
            if (salaValida || salas.length === 0) return prev;
            return { ...prev, recurso: String(salas[0].id) };
          });
        } else {
          errors.push('salas');
          setRecursosEstudio([]);
        }

        if (tiposResult.status === 'fulfilled') {
          const catalog = buildEstudioTipoCatalogOptions(tiposResult.value);
          setTiposEstudio(catalog);
          setTipoEstudioId((prev) => {
            if (prev && catalog.some((t) => String(t.id) === prev)) return prev;
            if (initialEstudio?.tipo_estudio) {
              const match = catalog.find((t) => t.id === initialEstudio.tipo_estudio);
              if (match) return String(match.id);
            }
            return catalog[0] ? String(catalog[0].id) : '';
          });
        } else {
          errors.push('tipos de estudio');
          setTiposEstudio(buildEstudioTipoCatalogOptions([]));
        }

        if (errors.length > 0) {
          setEstudioFormError(
            `No se pudieron cargar: ${errors.join(' y ')}. ${errors.includes('tipos de estudio') ? 'Se muestran modalidades genéricas.' : ''}`.trim()
          );
        }
      } finally {
        if (!cancelled) setLoadingEstudioForm(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [estudioFormActivo, loadPacientes, pacientes.length, initialEstudio?.tipo_estudio, initialEstudio?.id]);

  // Si el perfil médico llega después de abrir el modal (p. ej. post-login), sincronizar el formulario.
  useEffect(() => {
    if (!open || !lockMedicoField) return;
    const medicoId = getCurrentMedicoId(currentUser);
    if (!medicoId) return;
    setFormData((prev) => (prev.medico ? prev : { ...prev, medico: String(medicoId) }));
    setSelectedMedico((prev) => {
      if (prev?.id === medicoId) return prev;
      const m = currentUser?.medico;
      if (!m) return prev;
      return {
        id: m.id,
        nombre: (m as Medico).nombre || currentUser?.first_name || '',
        apellido: (m as Medico).apellido || currentUser?.last_name || '',
        matricula: m.matricula || '',
      } as Medico;
    });
  }, [open, lockMedicoField, currentUser, currentUser?.medico?.id]);

  // Efecto para actualizar el estado del formulario cuando cambia el estado del turno
  useEffect(() => {
    const st = turnoVista?.estado;
    if (st) {
      setFormData((prev) => ({
        ...prev,
        estado: st as any,
      }));
    }
  }, [turnoVista?.estado]);

  // Inicialización idempotente del formulario: una sola vez por apertura lógica (initKey).
  useEffect(() => {
    if (!open) {
      lastFormInitKeyRef.current = '';
      setFormData({
        paciente: '',
        medico: '',
        recurso: '',
        fecha: '',
        horaInicio: '',
        duracionMin: 60,
        motivo: '',
        estado: 'RESERVADO',
        prioridad: 'NORMAL',
      });
      return;
    }

    const initKey = getTurnoModalFormInitKey(open, editingTurno?.id, selectedDateTime ?? null);
    if (lastFormInitKeyRef.current === initKey) {
      return;
    }
    lastFormInitKeyRef.current = initKey;

    if (editingTurno) {
      const pacienteId = editingTurno.paciente_id ?? editingTurno.paciente?.id ?? null;
      const medicoId = editingTurno.medico_id ?? editingTurno.medico?.id ?? null;
      const recursoId = editingTurno.recurso_id ?? editingTurno.recurso?.id ?? null;

      const inicioDt = turnoInicioFromApi(editingTurno.fecha_hora_inicio);
      const fechaFormateada = inicioDt ? formatFecha(inicioDt) : '';
      const horaFormateada = inicioDt ? formatHora(inicioDt) : '';

      let duracion = 60;
      if (editingTurno.fecha_hora_inicio && editingTurno.fecha_hora_fin) {
        const inicio = turnoInicioFromApi(editingTurno.fecha_hora_inicio);
        const fin = turnoInicioFromApi(editingTurno.fecha_hora_fin);
        if (inicio && fin) {
          duracion = Math.round((fin.getTime() - inicio.getTime()) / (1000 * 60));
          if (duracion <= 0) duracion = 60;
        }
      }

      setFormData({
        paciente: pacienteId ? String(pacienteId) : '',
        medico: medicoId ? String(medicoId) : '',
        recurso: recursoId ? String(recursoId) : '',
        fecha: fechaFormateada,
        horaInicio: horaFormateada,
        duracionMin: duracion,
        motivo: editingTurno.motivo_reserva || editingTurno.motivo_consulta || '',
        estado: (() => {
          const estadoTurno = editingTurno.estado;
          if (estadoTurno && ['RESERVADO', 'CONFIRMADO', 'REALIZADO', 'CANCELADO'].includes(estadoTurno)) {
            const estadosDisponiblesValues = estadosDisponibles.map(e => e.value);
            if (estadosDisponiblesValues.includes(estadoTurno)) {
              return estadoTurno;
            }
          }
          return (estadosDisponibles.length > 0 ? estadosDisponibles[0].value : 'RESERVADO') as 'RESERVADO' | 'CONFIRMADO' | 'REALIZADO' | 'CANCELADO';
        })(),
        prioridad: editingTurno.prioridad || 'NORMAL',
      });
      return;
    }

    let pacienteId = '';
    if (currentUser?.rol === 'PACIENTE') {
      const idFromUser = currentUser?.paciente?.id;
      if (idFromUser) {
        pacienteId = idFromUser.toString();
      }
    }

    let medicoId = '';
    if (lockMedicoField && currentUser?.medico?.id) {
      medicoId = String(currentUser.medico.id);
    }

    const baseEstado = (estadosDisponibles.length > 0 ? estadosDisponibles[0].value : 'RESERVADO') as 'RESERVADO' | 'CONFIRMADO' | 'REALIZADO' | 'CANCELADO';

    if (selectedDateTime && !Number.isNaN(selectedDateTime.getTime())) {
      setFormData({
        paciente: pacienteId,
        medico: medicoId,
        recurso: '',
        fecha: formatFecha(selectedDateTime),
        horaInicio: formatHora(selectedDateTime),
        duracionMin: 60,
        motivo: '',
        estado: baseEstado,
        prioridad: 'NORMAL',
      });
    } else {
      setFormData({
        paciente: pacienteId,
        medico: medicoId,
        recurso: '',
        fecha: '',
        horaInicio: '',
        duracionMin: 60,
        motivo: '',
        estado: baseEstado,
        prioridad: 'NORMAL',
      });
    }
    setSelectedPaciente(null);
    setSelectedMedico(null);
    if (lockMedicoField && currentUser?.medico?.id) {
      const m = currentUser.medico;
      setSelectedMedico({
        id: m.id,
        nombre: (m as Medico).nombre || currentUser.first_name || '',
        apellido: (m as Medico).apellido || currentUser.last_name || '',
        matricula: m.matricula || '',
      } as Medico);
    }
  }, [
    open,
    editingTurno,
    editingTurno?.id,
    selectedDateTime,
    currentUser?.rol,
    currentUser?.paciente?.id,
    currentUser?.medico?.id,
    lockMedicoField,
    estadosDisponibles,
  ]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canMutateByRole && !(agendaTipo === 'estudio' && puedeAgendarEstudio && !editingTurno)) return;

    if (!editingTurno && agendaTipo === 'estudio') {
      setLoading(true);
      setEstudioFormError(null);
      try {
        if (!formData.fecha || !formData.horaInicio) {
          setEstudioFormError('Indique fecha y hora del turno.');
          return;
        }
        const pacienteId =
          lockEstudioSelection && initialEstudio?.paciente_id
            ? initialEstudio.paciente_id
            : Number(formData.paciente);
        if (!pacienteId || Number.isNaN(pacienteId)) {
          setEstudioFormError('Seleccione el paciente.');
          return;
        }
        if (!formData.recurso) {
          setEstudioFormError('Seleccione la sala de estudio.');
          return;
        }
        if (!lockEstudioSelection && !tipoEstudioId) {
          setEstudioFormError('Indique el tipo de estudio a realizar.');
          return;
        }
        if (
          !lockEstudioSelection &&
          isEstudioTipoCatalogFallbackId(tipoEstudioId) &&
          !resolveEstudioModalidadFromTipoId(tipoEstudioId, tiposEstudio)
        ) {
          setEstudioFormError('Seleccione un tipo de estudio válido.');
          return;
        }
        const inicio = new Date(`${formData.fecha}T${formData.horaInicio}:00`);
        if (Number.isNaN(inicio.getTime())) {
          setEstudioFormError('Fecha u hora inválida.');
          return;
        }
        const fin = new Date(inicio.getTime() + formData.duracionMin * 60_000);
        const turnoPayload = {
          recurso_id: Number(formData.recurso),
          fecha_hora_inicio: inicio.toISOString(),
          fecha_hora_fin: fin.toISOString(),
        };

        if (lockEstudioSelection && initialEstudio?.id) {
          await asignarTurnoEstudio(initialEstudio.id, turnoPayload);
        } else {
          await agendarTurnoEstudioDesdeAgenda({
            paciente_id: pacienteId,
            ...(isEstudioTipoCatalogFallbackId(tipoEstudioId)
              ? {
                  modalidad: resolveEstudioModalidadFromTipoId(tipoEstudioId, tiposEstudio)!,
                }
              : { tipo_estudio: Number(tipoEstudioId) }),
            origen: estudioOrigen,
            descripcion_clinica: formData.motivo || '',
            ...turnoPayload,
          });
        }
        await refreshTurnos();
        onSuccess?.();
        onClose();
      } catch (err) {
        setEstudioFormError(parseEstudiosApiError(err, 'No se pudo asignar el turno de estudio.'));
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);

    try {
      // Validaciones básicas
      if (!formData.fecha || !formData.horaInicio) {
        alert('Por favor, complete la fecha y hora del turno');
        setLoading(false);
        return;
      }

      const resolvedMedicoId = lockMedicoField
        ? getCurrentMedicoId(currentUser)
        : formData.medico
          ? Number(formData.medico)
          : undefined;

      if (!resolvedMedicoId || Number.isNaN(resolvedMedicoId) || resolvedMedicoId <= 0) {
        alert('Por favor, seleccione un médico');
        setLoading(false);
        return;
      }

      if (!formData.recurso) {
        alert('Por favor, seleccione un recurso');
        setLoading(false);
        return;
      }

      if (!isPaciente()) {
        const pacienteIdRaw = formData.paciente?.trim();
        const pacienteId = pacienteIdRaw ? Number(pacienteIdRaw) : NaN;
        const tienePacienteValido = !Number.isNaN(pacienteId) && pacienteId > 0;
        const pacienteEnEdicion = editingTurno?.paciente_id ?? editingTurno?.paciente?.id;
        if (!tienePacienteValido && !pacienteEnEdicion) {
          alert('Por favor, seleccione un paciente');
          setLoading(false);
          return;
        }
      }

      // Construir payload - en modo edición, enviar todos los campos necesarios
      const payload: any = {};
      
      // Campos requeridos - siempre incluirlos
      if (formData.paciente && formData.paciente.trim() !== '') {
        const pacienteId = Number(formData.paciente);
        if (!isNaN(pacienteId) && pacienteId > 0) {
          payload.paciente_id = pacienteId;
        }
      } else if (editingTurno && editingTurno.paciente_id) {
        // Si estamos editando y no hay paciente en el form, mantener el original
        payload.paciente_id = editingTurno.paciente_id;
      }
      
      // Médico (ya validado arriba)
      payload.medico_id = resolvedMedicoId;
      
      // Recurso - validar que sea un número válido
      if (formData.recurso && formData.recurso.trim() !== '') {
        const recursoId = Number(formData.recurso);
        if (!isNaN(recursoId) && recursoId > 0) {
          payload.recurso_id = recursoId;
        } else {
          throw new Error('Por favor, seleccione un recurso válido');
        }
      } else if (editingTurno && editingTurno.recurso_id) {
        // Si estamos editando y no hay recurso en el form, mantener el original
        payload.recurso_id = editingTurno.recurso_id;
      } else {
        throw new Error('Por favor, seleccione un recurso');
      }
      
      const [year, month, day] = formData.fecha.split('-').map(Number);
      const timeParts = formData.horaInicio.split(':').map(Number);
      const hours = timeParts[0] ?? 0;
      const minutes = timeParts[1] ?? 0;
      const seconds = timeParts[2] ?? 0;

      const fechaInicioLocal = new Date(year, month - 1, day, hours, minutes, seconds);
      const fechaFinLocal = new Date(fechaInicioLocal.getTime() + formData.duracionMin * 60 * 1000);

      payload.fecha_hora_inicio = formatLocalDateTimeSeconds(fechaInicioLocal);
      payload.fecha_hora_fin = formatLocalDateTimeSeconds(fechaFinLocal);
      
      if (!editingTurno) {
        payload.estado = formData.estado || 'RESERVADO';
      }

      // Motivo
      payload.motivo_reserva = formData.motivo || '';

      // Rol PACIENTE: si el cliente ya conoce el id de ficha, lo enviamos; si no, el
      // backend (ensure_paciente_linked_to_user) resuelve o devuelve error claro.
      if (currentUser?.rol === 'PACIENTE' && currentUser.paciente?.id) {
        payload.paciente_id = Number(currentUser.paciente.id);
      }

      // No enviar prioridad ya que no existe en el modelo del backend
      // payload.prioridad se omite

      if (editingTurno) {
        const origMedicoId = editingTurno.medico_id ?? editingTurno.medico?.id;
        const origRecursoId = editingTurno.recurso_id ?? editingTurno.recurso?.id;
        const origInicio = turnoInicioFromApi(editingTurno);
        const origInicioStr = origInicio ? formatLocalDateTimeSeconds(origInicio) : '';
        const logisticChanged =
          payload.fecha_hora_inicio !== origInicioStr ||
          payload.medico_id !== origMedicoId ||
          payload.recurso_id !== origRecursoId;

        if (logisticChanged && canReprogramarTurno(currentUser, editingTurno)) {
          setLoading(false);
          openMotivoDialog({
            title: 'Reprogramar turno',
            label: 'Motivo de reprogramación (obligatorio)',
            confirmLabel: 'Reprogramar',
            initialMotivo: formData.motivo || '',
            onConfirm: async (motivoRep) => {
              try {
                await apiService.reprogramarTurno(editingTurno.id, {
                  fecha_hora_inicio: payload.fecha_hora_inicio,
                  fecha_hora_fin: payload.fecha_hora_fin,
                  motivo: motivoRep,
                  ...(payload.medico_id ? { medico_id: payload.medico_id } : {}),
                  ...(payload.recurso_id ? { recurso_id: payload.recurso_id } : {}),
                });
                const patchMotivo: Record<string, unknown> = { motivo_reserva: payload.motivo_reserva };
                if (payload.paciente_id) {
                  patchMotivo.paciente_id = payload.paciente_id;
                }
                if (Object.keys(patchMotivo).length > 0) {
                  await apiService.updateTurno(editingTurno.id, patchMotivo);
                }
                onSuccess?.();
                onClose();
              } catch (error: unknown) {
                throw new Error(
                  getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoReprogramar)
                );
              }
            },
          });
          return;
        } else {
          const patchPayload = { ...payload };
          delete patchPayload.estado;
          delete patchPayload.fecha_hora_inicio;
          delete patchPayload.fecha_hora_fin;
          delete patchPayload.medico_id;
          delete patchPayload.recurso_id;
          await apiService.updateTurno(editingTurno.id, patchPayload);
        }
      } else {
        await apiService.createTurno(payload);
      }

      onSuccess?.();
      onClose();
    } catch (error: unknown) {
      alert(getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoGuardar));
    } finally {
      setLoading(false);
    }
  };

  const isPaciente = () => currentUser?.rol === 'PACIENTE';
  const isMedico = () => currentUser?.rol === 'MEDICO';
  
  // Turno bloqueado: paciente hasta finalizar; staff/médico por atención cerrada
  const isTurnoBloqueado = () => {
    const t = turnoVista;
    if (!t) return false;
    if (isPaciente()) return !pacientePuedeMutarTurno(currentUser, t);
    const atencionCerrada =
      t.atencion?.estado_clinico === 'FINALIZADA' || Boolean(t.atencion?.fecha_cierre);
    if (atencionCerrada) return true;
    if (t.estado === 'REALIZADO' && t.atencion?.consulta_cargada) return true;
    return false;
  };
  const isTurnoRealizado = () => isTurnoBloqueado();
  const isTurnoDeEstudio = Boolean(editingTurno && isTurnoEstudio(editingTurno));
  const canEditFormFields = () => {
    if (!canMutateByRole || isTurnoBloqueado()) return false;
    if (isTurnoDeEstudio) {
      if (canMutateTurnosGlobally(currentUser)) return true;
      if (isMedico() && canEditTurnoByRole(currentUser, turnoVista)) return true;
      if (isPaciente() && pacientePuedeMutarTurno(currentUser, turnoVista)) return true;
      return false;
    }
    return true;
  };

  // Resolver el nombre completo del paciente actual
  const getCurrentPacienteNombre = () => {
    if (!isPaciente()) return '';
    // Usar información del currentUser directamente
    return `${currentUser?.first_name || ''} ${currentUser?.last_name || ''}`.trim() || 'Paciente';
  };

  // Función helper para obtener el texto del botón según el tipo de recurso
  const getButtonText = (turno: Turno | null) => {
    if (!turno || !turno.recurso) return '📋 Crear Registro';
    
    const tipoRecurso = turno.recurso.tipo_recurso;
    const tieneRegistro = turno.atencion?.id ? true : false;
    
    // Detectar si hay consulta_ambulatoria específicamente para CONSULTORIO
    const tieneConsulta = tipoRecurso === 'CONSULTORIO' && 
      (turno.atencion?.consulta_ambulatoria?.id || 
       (turno.atencion?.consulta_ambulatoria && typeof turno.atencion.consulta_ambulatoria === 'object' && 'id' in turno.atencion.consulta_ambulatoria));
    
    if (tieneRegistro || turno.estado === 'REALIZADO') {
      switch (tipoRecurso) {
        case 'CONSULTORIO': {
          const consultaCargada =
            turno.estado === 'REALIZADO' || Boolean(turno.atencion?.consulta_cargada);
          if (!tieneConsulta) return '📋 Ver Consulta';
          return consultaCargada ? '📋 Ver consulta' : '📋 Completar consulta';
        }
        case 'SALA_PROCEDIMIENTO':
          return '📊 Ver Estudio';
        case 'SALA_HEMODINAMIA':
          return '🔬 Ver Procedimiento';
        case 'QUIROFANO':
          return '⚕️ Ver Cirugía';
        default:
          return '📋 Ver Registro';
      }
    } else {
      switch (tipoRecurso) {
        case 'CONSULTORIO':
          return '📋 Crear Consulta';
        case 'SALA_PROCEDIMIENTO':
          return '📊 Crear Estudio';
        case 'SALA_HEMODINAMIA':
          return '🔬 Crear Procedimiento';
        case 'QUIROFANO':
          return '⚕️ Crear Cirugía';
        default:
          return '📋 Crear Registro';
      }
    }
  };

  // ============================================================
  // HANDLER 1: VER CONSULTA (atención existente - solo lectura)
  // 🔒 NO crea nada, NO hace refresh, SOLO abre el drawer
  // ============================================================
  const handleVerConsulta = (atencionId: number) => {
    if (onOpenAtencion) {
      onOpenAtencion(atencionId);
      onClose();
    } else {
      setSelectedAtencionId(atencionId);
    }
  };

  // ============================================================
  // HANDLER 2: CREAR CONSULTA (nueva atención)
  // Solo se ejecuta cuando NO existe atención
  // ============================================================
  const handleCrearConsulta = async () => {
    if (!editingTurno) return;

    try {
      const result = await apiService.iniciarAtencionTurno(editingTurno.id);
      const atencion = result.atencion;

      queryClient.setQueryData(['atencion', atencion.id], atencion);
      queryClient.invalidateQueries({ queryKey: ['atenciones'] });
      queryClient.invalidateQueries({ queryKey: ['turnos'] });

      if (onOpenAtencion) {
        onOpenAtencion(atencion.id);
        onClose();
      } else {
        setSelectedAtencionId(atencion.id);
      }
    } catch (error: unknown) {
      alert(
        getSafeClinicalActionMessage(error, CLINICAL_ACTION_ERRORS.turnoIniciarAtencion)
      );
    }
  };

  // ============================================================
  // HANDLER PRINCIPAL: Decide entre VER o CREAR
  // ============================================================
  const handleOpenAtencion = async () => {
    if (!editingTurno) {
      alert('Error: No hay turno seleccionado.');
      return;
    }

    const tv = turnoVista;

    if (!editingTurno.paciente) {
      alert('Error: El turno debe tener un paciente asignado.');
      return;
    }

    if (!editingTurno.medico) {
      alert('Error: El turno debe tener un médico asignado.');
      return;
    }

    if (!editingTurno.recurso) {
      alert('Error: El turno debe tener un recurso asignado.');
      return;
    }

    if (tv && !['CONFIRMADO', 'REALIZADO', 'RESERVADO'].includes(tv.estado)) {
      alert('El turno debe estar RESERVADO, CONFIRMADO o REALIZADO para acceder al registro clínico.');
      return;
    }

    const atencionDelTurno = tv?.atencion;

    if (atencionDelTurno?.id) {
      if (tv?.estado === 'CONFIRMADO' || tv?.estado === 'RESERVADO') {
        try {
          await apiService.iniciarAtencionTurno(editingTurno.id);
          queryClient.invalidateQueries({ queryKey: ['turnos'] });
        } catch (syncError: unknown) {
          alert(
            getSafeClinicalActionMessage(
              syncError,
              CLINICAL_ACTION_ERRORS.turnoSincronizarAtencion
            )
          );
          return;
        }
      }
      handleVerConsulta(atencionDelTurno.id);
      return;
    }
    
    if (tv?.estado === 'REALIZADO') {
      try {
        const atenciones = await apiService.getAtenciones({ turno: editingTurno.id });
        const atencionExistente = atenciones.results?.[0];

        if (atencionExistente) {
          handleVerConsulta(atencionExistente.id);
          return;
        }
      } catch {
      }
    }

    if (isTurnoBloqueado()) {
      alert(
        'No se puede crear una nueva atención: el turno está finalizado o la consulta ya fue cargada.'
      );
      return;
    }
    await handleCrearConsulta();
  };

  const puedeAccederRegistroClinico = () => {
    if (!isMedico() || !editingTurno) return false;
    if (!editingTurno.paciente || !editingTurno.medico || !editingTurno.recurso) return false;
    const st = turnoVista?.estado;
    return st === 'CONFIRMADO' || st === 'REALIZADO' || st === 'RESERVADO';
  };

  /** Con turno bloqueado: mostrar si hay atención en el payload, o si está REALIZADO (se busca atención en API al abrir) */
  const mostrarBotonRegistroClinico = () => {
    if (!puedeAccederRegistroClinico()) return false;
    if (isTurnoBloqueado()) {
      if (turnoVista?.atencion?.id) return true;
      if (turnoVista?.estado === 'REALIZADO') return true;
      return false;
    }
    return true;
  };

  // Verificar si tenemos datos críticos disponibles
  const recursosActivos = useMemo(() => {
    const activos = recursos.filter((r) => r.activo);
    if (isModoConsulta || (!editingTurno && agendaTipo === 'consulta')) {
      return activos.filter((r) => r.tipo_recurso === 'CONSULTORIO');
    }
    if (isModoEstudio) {
      return recursosEstudio;
    }
    return activos;
  }, [recursos, recursosEstudio, editingTurno, agendaTipo, isModoConsulta, isModoEstudio]);

  const sinRecursosConsultorio =
    !isLoadingData && recursos.filter((r) => r.activo && r.tipo_recurso === 'CONSULTORIO').length === 0;
  const sinRecursosEstudio =
    !loadingEstudioForm && isModoEstudio && recursosEstudio.length === 0;
  const sinRecursosDisponibles = isModoEstudio ? sinRecursosEstudio : sinRecursosConsultorio;

  return (
  <>
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      keepMounted
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 520, md: 600 },
          maxWidth: '100vw',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography variant="h6" component="div">
          {editingTurno
            ? isTurnoDeEstudio
              ? '📊 Turno de estudio complementario'
              : forceReadOnly || !canMutateByRole
                ? '👁️ Ver turno (solo lectura)'
                : isTurnoRealizado()
                  ? '✅ Turno Realizado (Solo Lectura)'
                  : `✏️ Editar ${TURNO_KIND_META[getTurnoAgendaKind(editingTurno)].label.toLowerCase()}`
            : '📅 Nuevo turno'}
        </Typography>
        <IconButton onClick={onClose} sx={{ color: 'grey.500' }} aria-label="Cerrar panel de turno">
          <Close />
        </IconButton>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', px: 2, py: 0 }}>
        {isLoadingData ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 4 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Cargando datos...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Cargando datos desde el servidor...
            </Typography>
          </Box>
        ) : (
        <Box id="turno-form" component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
          {!editingTurno && !lockEstudioSelection && (
            <AgendaTipoSelector
              value={agendaTipo}
              onChange={(next) => {
                setAgendaTipo(next);
                setEstudioFormError(null);
                setFormData((prev) => ({ ...prev, recurso: '' }));
              }}
              showEstudio={puedeAgendarEstudio}
            />
          )}
          {isTurnoDeEstudio && editingTurno?.estudio_complementario?.id && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Este horario corresponde a un <strong>estudio complementario</strong> en sala (no a una
              consulta con médico). Para cambiar fecha o sala, abrí el estudio en{' '}
              <RouterLink
                to={`/estudios-complementarios/${editingTurno.estudio_complementario.id}`}
              >
                Estudios complementarios
              </RouterLink>
              .
            </Alert>
          )}
          {estudioFormError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {estudioFormError}
            </Alert>
          )}
          {isModoEstudio && loadingEstudioForm && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={28} />
            </Box>
          )}
          {sinRecursosConsultorio && isModoConsulta && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No hay consultorios configurados. Un administrador debe crear al menos un consultorio
              en Recursos o ejecutar <strong>python manage.py crear_recursos_iniciales</strong>.
            </Alert>
          )}
          {isModoEstudio && !loadingEstudioForm && sinRecursosEstudio && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No hay salas de estudio activas. Creá recursos tipo sala de procedimiento o hemodinamia.
            </Alert>
          )}

          {/* ——— Estudio complementario (nuevo) ——— */}
          {isModoEstudio && !loadingEstudioForm && (
            <>
              {lockEstudioSelection && initialEstudio && (
                <Alert severity="success" variant="outlined" sx={{ mb: 2 }}>
                  <Typography variant="body2" fontWeight={600} gutterBottom>
                    Estudio #{initialEstudio.id}
                    {initialEstudio.tipo_estudio_nombre
                      ? ` — ${initialEstudio.tipo_estudio_nombre}`
                      : ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Paciente: {pacienteLabelFromList(initialEstudio.paciente_id, pacientes)}
                  </Typography>
                  {initialEstudio.descripcion_clinica && (
                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                      {initialEstudio.descripcion_clinica}
                    </Typography>
                  )}
                </Alert>
              )}
              {!lockEstudioSelection && (
                <>
                  <AsyncAutocomplete<Paciente>
                    label="👤 Paciente"
                    endpoint="/pacientes/"
                    getOptionLabel={(option) =>
                      `${option.nombre || ''} ${option.apellido || ''} (${option.dni || 'Sin DNI'})`.trim()
                    }
                    onChange={(newValue) => {
                      setSelectedPaciente(newValue);
                      setFormData({ ...formData, paciente: newValue ? String(newValue.id) : '' });
                    }}
                    value={selectedPaciente}
                    required
                    placeholder="Buscar paciente por nombre, apellido o DNI"
                    debounceMs={300}
                    minSearchLength={2}
                    sx={{ mb: 2 }}
                  />
                  <FormControl fullWidth sx={{ mb: 2 }} required disabled={tiposEstudio.length === 0}>
                    <InputLabel>Tipo de estudio</InputLabel>
                    <Select
                      value={tipoEstudioId}
                      label="Tipo de estudio"
                      onChange={(e) => setTipoEstudioId(String(e.target.value))}
                    >
                      {tiposEstudio.length === 0 ? (
                        <MenuItem disabled value="">
                          Cargando tipos…
                        </MenuItem>
                      ) : (
                        tiposEstudio.map((t) => (
                          <MenuItem key={t.id} value={String(t.id)}>
                            {t.nombre}
                          </MenuItem>
                        ))
                      )}
                    </Select>
                  </FormControl>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Origen del pedido</InputLabel>
                    <Select
                      value={estudioOrigen}
                      label="Origen del pedido"
                      onChange={(e) => setEstudioOrigen(String(e.target.value))}
                    >
                      {ORIGEN_OPTIONS.filter((o) => o.value !== 'IMPORTADO_HISTORICO').map((o) => (
                        <MenuItem key={o.value} value={o.value}>
                          {o.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    fullWidth
                    multiline
                    minRows={2}
                    label="Notas / indicación clínica (opcional)"
                    value={formData.motivo}
                    onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                    sx={{ mb: 2 }}
                  />
                </>
              )}
              <FormControl fullWidth sx={{ mb: 2 }} required disabled={recursosEstudio.length === 0}>
                <InputLabel>Sala de estudio</InputLabel>
                <Select
                  value={formData.recurso}
                  label="Sala de estudio"
                  onChange={(e) => setFormData({ ...formData, recurso: String(e.target.value) })}
                >
                  {recursosEstudio.map((r) => (
                    <MenuItem key={r.id} value={String(r.id)}>
                      {r.nombre} ({r.ubicacion})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </>
          )}

          {/* ——— Consulta médica ——— */}
          {(isModoConsulta || editingTurno) && !isTurnoDeEstudio && (
            <>
          {/* Campo Paciente - Solo mostrar selector si NO es paciente */}
          {!isPaciente() && (
            <AsyncAutocomplete<Paciente>
              label="👤 Paciente"
              endpoint="/pacientes/"
              getOptionLabel={(option) => `${option.nombre || ''} ${option.apellido || ''} (${option.dni || 'Sin DNI'})`.trim()}
              onChange={(newValue) => {
                setSelectedPaciente(newValue);
                setFormData({ ...formData, paciente: newValue ? String(newValue.id) : '' });
              }}
              value={selectedPaciente}
              required
              placeholder="Escriba al menos 2 caracteres para buscar por nombre, apellido o DNI..."
              helperText={isTurnoRealizado() ? "Turno realizado - No se puede editar" : "Búsqueda asíncrona en servidor"}
              debounceMs={300}
              minSearchLength={2}
              disabled={!canEditFormFields()}
              sx={{ mb: 2 }}
            />
          )}

          {/* Mostrar información del paciente si es paciente */}
          {isPaciente() && (
            <TextField
              fullWidth
              label="👤 Paciente"
              value={getCurrentPacienteNombre() || 'Paciente'}
              disabled
              sx={{ mb: 2 }}
              helperText="Tu perfil de paciente será usado automáticamente"
            />
          )}

          {lockMedicoField ? (
            <TextField
              fullWidth
              label="👨‍⚕️ Médico"
              value={
                getMedicoLabel(selectedMedico) ||
                (currentUser?.medico
                  ? `Dr. ${currentUser.medico.nombre || currentUser.first_name || ''} ${currentUser.medico.apellido || currentUser.last_name || ''}`.trim()
                  : 'Médico asignado')
              }
              disabled
              sx={{ mb: 2 }}
              helperText="Solo podés gestionar turnos con tu ficha médica"
            />
          ) : (
            <AsyncAutocomplete<Medico>
              label="👨‍⚕️ Médico"
              endpoint="/medicos/"
              getOptionLabel={(option) => {
                const apellido = option.apellido || '';
                const nombre = option.nombre || '';
                const especialidad = (option as any).especialidad_nombre || (option.especialidad as any)?.nombre || 'Sin esp.';
                return `${apellido}, ${nombre} - ${especialidad}`.trim();
              }}
              onChange={(newValue) => {
                setSelectedMedico(newValue);
                setFormData({ ...formData, medico: newValue ? String(newValue.id) : '' });
              }}
              value={selectedMedico}
              required
              placeholder="Escriba al menos 2 caracteres para buscar por nombre, apellido o matrícula..."
              helperText={isTurnoRealizado() ? 'Turno realizado - No se puede editar' : 'Búsqueda asíncrona en servidor'}
              debounceMs={500}
              minSearchLength={2}
              disabled={!canEditFormFields()}
              sx={{ mb: 2 }}
            />
          )}

          <FormControl fullWidth sx={{ mb: 2 }} disabled={!canEditFormFields()}>
            <InputLabel>{editingTurno ? '🏥 Recurso' : '🏥 Consultorio'}</InputLabel>
            <Select
              value={formData.recurso}
              label={editingTurno ? '🏥 Recurso' : '🏥 Consultorio'}
              onChange={(e) => setFormData({...formData, recurso: String(e.target.value)})}
              required
              disabled={!canEditFormFields()}
            >
              {recursosActivos.map(recurso => (
                <MenuItem key={recurso.id} value={String(recurso.id)}>
                  {recurso.nombre}
                  {editingTurno
                    ? ` (${recurso.tipo_recurso_display || recurso.tipo_recurso})`
                    : ''}
                </MenuItem>
              ))}
              {recursosActivos.length === 0 && (
                <MenuItem disabled value="">
                  {editingTurno ? 'Sin recursos disponibles' : 'Sin consultorios disponibles'}
                </MenuItem>
              )}
            </Select>
          </FormControl>
            </>
          )}

          {(isModoEstudio || isModoConsulta || (editingTurno && !isTurnoDeEstudio)) && (
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              fullWidth
              label="📅 Fecha"
              type="date"
              value={formData.fecha}
              onChange={(e) => setFormData({...formData, fecha: e.target.value})}
              InputLabelProps={{ shrink: true }}
              required
              disabled={!canEditFormFields()}
            />

            <TextField
              fullWidth
              label="🕐 Hora Inicio"
              type="time"
              value={formData.horaInicio}
              onChange={(e) => setFormData({...formData, horaInicio: e.target.value})}
              InputLabelProps={{ shrink: true }}
              required
              disabled={!canEditFormFields()}
            />

            <TextField
              fullWidth
              label="⏱️ Duración (min)"
              type="number"
              value={formData.duracionMin}
              onChange={(e) => setFormData({...formData, duracionMin: Number(e.target.value)})}
              inputProps={{ min: 10, step: 5 }}
              required
              disabled={!canEditFormFields()}
            />
          </Box>
          )}

          {isTurnoDeEstudio && editingTurno && (
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="📅 Fecha"
                value={formData.fecha}
                disabled
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                fullWidth
                label="🕐 Hora"
                value={formData.horaInicio}
                disabled
                InputLabelProps={{ shrink: true }}
              />
            </Box>
          )}

          {((isModoConsulta || editingTurno) && !isTurnoDeEstudio) && (
          <>
          <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <Box sx={{ flex: '1 1 200px', mb: 1 }}>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                Estado del turno
              </Typography>
              <Chip
                label={turnoVista?.estado || formData.estado || '—'}
                color="primary"
                variant="outlined"
                size="small"
              />
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                Use las acciones del pie del modal (confirmar, cancelar, marcar realizado, no asistió).
              </Typography>
            </Box>

            <FormControl fullWidth disabled={!canEditFormFields()} sx={{ flex: '1 1 200px' }}>
              <InputLabel>🚨 Prioridad</InputLabel>
              <Select
                value={formData.prioridad}
                label="🚨 Prioridad"
                onChange={(e) => setFormData({...formData, prioridad: e.target.value})}
                disabled={!canEditFormFields()}
              >
                <MenuItem value="NORMAL">Normal</MenuItem>
                <MenuItem value="ALTA">Alta</MenuItem>
                <MenuItem value="URGENTE">Urgente</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <TextField
            fullWidth
            multiline
            rows={3}
            label="📝 Motivo de consulta"
            value={formData.motivo}
            onChange={(e) => setFormData({...formData, motivo: e.target.value})}
            placeholder="Describe el motivo de la consulta..."
            disabled={!canEditFormFields()}
            sx={{ mb: 2 }}
          />

          {/* Botón para crear/ver atención médica (solo para médicos) */}
          {mostrarBotonRegistroClinico() && (
            <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
              <Button
                fullWidth
                variant="outlined"
                color="primary"
                onClick={handleOpenAtencion}
                disabled={loading}
                sx={{ py: 1.5 }}
              >
                {getButtonText((turnoVista as Turno) ?? null)}
              </Button>
            </Box>
          )}
          </>
          )}
        </Box>
        )}
      </Box>

      <Box
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: 1,
        }}
      >
        <Button onClick={onClose} disabled={loading}>
          Cerrar
        </Button>
        {editingTurno && canConfirmarTurno(currentUser, turnoParaAcciones) && (
          <Button
            variant="outlined"
            color="primary"
            onClick={handleConfirmarTurno}
            disabled={loading || isTurnoBloqueado()}
          >
            Confirmar turno
          </Button>
        )}
        {editingTurno && canCancelarTurnoAccion(currentUser, turnoParaAcciones) && (
          <Button
            variant="outlined"
            color="warning"
            onClick={handleCancelarTurnoAccion}
            disabled={loading || isTurnoBloqueado()}
          >
            Cancelar turno
          </Button>
        )}
        {editingTurno && canMarcarRealizadoTurno(currentUser, turnoParaAcciones) && (
          <Button
            variant="outlined"
            color="success"
            onClick={handleMarcarRealizado}
            disabled={loading || isTurnoBloqueado()}
          >
            Marcar realizado
          </Button>
        )}
        {editingTurno && canMarcarNoAsistioTurno(currentUser, turnoParaAcciones) && (
          <Button
            variant="outlined"
            color="error"
            onClick={handleMarcarNoAsistio}
            disabled={loading || isTurnoBloqueado()}
          >
            No asistió
          </Button>
        )}
        {(canEditFormFields() || (isModoEstudio && puedeAgendarEstudio && !editingTurno)) && (
          <Button
            type="submit"
            form="turno-form"
            variant="contained"
            disabled={loading || sinRecursosDisponibles || (isModoEstudio && loadingEstudioForm)}
            color={isModoEstudio ? 'success' : 'primary'}
          >
            {loading
              ? 'Guardando...'
              : editingTurno
                ? 'Actualizar turno'
                : isModoEstudio
                  ? 'Confirmar turno de estudio'
                  : 'Crear consulta'}
          </Button>
        )}
        {(forceReadOnly || (editingTurno && !canMutateByRole)) && (
          <Typography variant="body2" color="text.secondary" sx={{ flex: '1 1 100%', order: -1, mb: 1 }}>
            No tenés permiso para modificar este turno. La eliminación física no está disponible (use cambio de
            estado cuando exista el flujo de negocio).
          </Typography>
        )}
        {isTurnoRealizado() && (
          <Typography variant="body2" color="text.secondary" sx={{ flex: '1 1 100%', order: -1, mb: 1 }}>
            {turnoVista?.atencion?.consulta_cargada && turnoVista?.estado !== 'REALIZADO'
              ? 'La consulta de este turno ya fue cargada: no se puede modificar el turno.'
              : 'Este turno está finalizado: no se puede editar. Solo se puede abrir el registro clínico si aplica.'}
          </Typography>
        )}
      </Box>
    </Drawer>

    {/* Drawer de Atención - SOLO si NO hay callback onOpenAtencion del padre */}
    {/* Si hay onOpenAtencion, el drawer vive en el contenedor padre (Calendar) */}
    {!onOpenAtencion && (
      <AtencionDetailDrawer
        atencionId={selectedAtencionId}
        open={Boolean(selectedAtencionId)}
        onClose={async () => {
          setSelectedAtencionId(null);
          // Recargar turnos para actualizar la información de atención y estado
          await refreshTurnos();
          // Recargar el turno actual si estamos editando
          if (editingTurno) {
            try {
              await apiService.getTurno(editingTurno.id);
              if (onSuccess) {
                onSuccess();
              }
            } catch (error) {
              if (onSuccess) {
                onSuccess();
              }
            }
          }
        }}
        currentUserRole={currentUser?.rol}
        onIntervencionSaved={async () => {
          // Recargar turnos después de guardar una intervención
          await refreshTurnos();
          if (editingTurno) {
            try {
              await apiService.getTurno(editingTurno.id);
              if (onSuccess) {
                onSuccess();
              }
            } catch (error) {
              if (onSuccess) {
                onSuccess();
              }
            }
          } else if (onSuccess) {
            onSuccess();
          }
        }}
      />
    )}
    <MotivoDialog {...motivoDialogProps} />
  </>
  );
};

export default TurnoModal;
