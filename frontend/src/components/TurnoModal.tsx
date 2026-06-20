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
  shouldLockMedicoField,
} from '../utils/turnoPermissions';

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
}

const TurnoModal: React.FC<TurnoModalProps> = ({
  open,
  onClose,
  editingTurno,
  onSuccess,
  selectedDateTime = null,
  onOpenAtencion,
  forceReadOnly = false,
}) => {
  const {
    recursos,
    currentUser,
    refreshAll,
    refreshTurnos
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
        console.warn('No se pudo recargar el turno.');
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

  const canMutateByRole = useMemo(() => {
    if (forceReadOnly || !currentUser) return false;
    if (editingTurno) return canEditTurnoByRole(currentUser, turnoVista);
    return canCreateTurno(currentUser);
  }, [forceReadOnly, currentUser, editingTurno, turnoVista]);

  const lockMedicoField = shouldLockMedicoField(currentUser);
  const turnoParaAcciones = (turnoVista as Turno | undefined) ?? editingTurno;

  const handleConfirmarTurno = async () => {
    if (!editingTurno?.id) return;
    setLoading(true);
    try {
      const { turno, message } = await apiService.confirmarTurno(editingTurno.id);
      setTurnoEfectivo(turno);
      alert(message || 'Turno confirmado');
      onSuccess?.();
    } catch (error: any) {
      alert(error.message || 'No se pudo confirmar el turno');
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
          const { turno, message } = await apiService.cancelarTurno(editingTurno.id, motivo);
          setTurnoEfectivo(turno);
          alert(message || 'Turno cancelado');
          onSuccess?.();
        } catch (error: any) {
          throw new Error(error.message || 'No se pudo cancelar el turno');
        }
      },
    });
  };

  const handleMarcarRealizado = async () => {
    if (!editingTurno?.id) return;
    setLoading(true);
    try {
      const { turno, message } = await apiService.marcarRealizadoTurno(editingTurno.id);
      setTurnoEfectivo(turno);
      alert(message || 'Turno marcado como realizado');
      onSuccess?.();
    } catch (error: any) {
      alert(error.message || 'No se pudo marcar el turno como realizado');
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
          const { turno, message } = await apiService.marcarNoAsistioTurno(editingTurno.id, motivo);
          setTurnoEfectivo(turno);
          alert(message || 'No asistencia registrada');
          onSuccess?.();
        } catch (error: any) {
          throw new Error(error.message || 'No se pudo registrar no asistencia');
        }
      },
    });
  };

  // Forzar carga de datos cuando se abre el modal
  useEffect(() => {
    if (open) {
      // Si faltan datos críticos, intentar cargarlos inmediatamente
      const faltanDatosCriticos = recursos.length === 0;

      if (faltanDatosCriticos) {
        setIsLoadingData(true);

        // Forzar recarga inmediata
        const loadData = async () => {
          try {
            // Recargar el contexto completo
            await refreshAll();
          } catch (error) {
            console.error('Error forzando carga de datos.');
          } finally {
            setIsLoadingData(false);
          }
        };

        loadData();
      } else {
        setIsLoadingData(false);
      }
    }
  }, [open, recursos.length, refreshAll]);

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
    if (!canMutateByRole) return;
    setLoading(true);

    try {
      // Validaciones básicas
      if (!formData.fecha || !formData.horaInicio) {
        alert('Por favor, complete la fecha y hora del turno');
        setLoading(false);
        return;
      }

      if (!formData.medico) {
        alert('Por favor, seleccione un médico');
        setLoading(false);
        return;
      }

      if (!formData.recurso) {
        alert('Por favor, seleccione un recurso');
        setLoading(false);
        return;
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
      
      // Médico - validar que sea un número válido
      if (formData.medico && formData.medico.trim() !== '') {
        const medicoId = Number(formData.medico);
        if (!isNaN(medicoId) && medicoId > 0) {
          payload.medico_id = medicoId;
        } else {
          console.error('ID de médico inválido.');
          throw new Error('Por favor, seleccione un médico válido');
        }
      } else if (editingTurno && editingTurno.medico_id) {
        // Si estamos editando y no hay médico en el form, mantener el original
        payload.medico_id = editingTurno.medico_id;
      } else {
        throw new Error('Por favor, seleccione un médico');
      }
      
      // Recurso - validar que sea un número válido
      if (formData.recurso && formData.recurso.trim() !== '') {
        const recursoId = Number(formData.recurso);
        if (!isNaN(recursoId) && recursoId > 0) {
          payload.recurso_id = recursoId;
        } else {
          console.error('ID de recurso inválido.');
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

      if (lockMedicoField && currentUser?.medico?.id) {
        payload.medico_id = Number(currentUser.medico.id);
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
              } catch (error: any) {
                const errorMessage =
                  error.message || error.response?.data?.error || 'Error desconocido al guardar el turno';
                throw new Error(errorMessage);
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
    } catch (error: any) {
      console.error('Error al guardar turno.');
      const errorMessage = error.message || error.response?.data?.error || 'Error desconocido al guardar el turno';
      alert(`Error al guardar turno: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const isPaciente = () => currentUser?.rol === 'PACIENTE';
  const isMedico = () => currentUser?.rol === 'MEDICO';
  
  // REALIZADO o consulta ambulatoria ya cargada con contenido → no editar turno ni crear otra atención
  const isTurnoBloqueado = () => {
    const t = turnoVista;
    if (!t) return false;
    if (t.estado === 'REALIZADO') return true;
    if (t.atencion?.consulta_cargada) return true;
    return false;
  };
  const isTurnoRealizado = () => isTurnoBloqueado();
  const canEditFormFields = () => canMutateByRole && !isTurnoBloqueado();

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
      } else {
        setSelectedAtencionId(atencion.id);
      }
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.error ||
        error.message ||
        'Error al iniciar la atención.';
      alert(`Error: ${errorMessage}`);
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
        } catch (syncError: any) {
          const msg =
            syncError?.response?.data?.detail ||
            syncError?.message ||
            'Error al sincronizar el turno con la atención.';
          alert(`Error: ${msg}`);
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
        console.error('Error al buscar atención asociada al turno.');
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
  const hasCriticalData = recursos.length > 0;

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
            ? forceReadOnly || !canMutateByRole
              ? '👁️ Ver turno (solo lectura)'
              : isTurnoRealizado()
                ? '✅ Turno Realizado (Solo Lectura)'
                : '✏️ Editar Turno'
            : '➕ Nuevo Turno'}
        </Typography>
        <IconButton onClick={onClose} sx={{ color: 'grey.500' }} aria-label="Cerrar panel de turno">
          <Close />
        </IconButton>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', px: 2, py: 0 }}>
        {isLoadingData || !hasCriticalData ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 4 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Cargando datos...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isLoadingData ? 'Cargando datos desde el servidor...' : 'Esperando a que se carguen los datos necesarios...'}
            </Typography>
          </Box>
        ) : (
        <Box id="turno-form" component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
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
              required={!selectedDateTime}
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
              value={getMedicoLabel(selectedMedico) || 'Médico asignado'}
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
            <InputLabel>🏥 Recurso</InputLabel>
            <Select
              value={formData.recurso}
              label="🏥 Recurso"
              onChange={(e) => setFormData({...formData, recurso: String(e.target.value)})}
              required
              disabled={!canEditFormFields()}
            >
              {recursos.filter(r => r.activo).map(recurso => (
                <MenuItem key={recurso.id} value={String(recurso.id)}>
                  {recurso.nombre} ({recurso.tipo_recurso_display || recurso.tipo_recurso})
                </MenuItem>
              ))}
            </Select>
          </FormControl>


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
        {canEditFormFields() && (
          <Button
            type="submit"
            form="turno-form"
            variant="contained"
            disabled={loading}
          >
            {loading ? 'Guardando...' : (editingTurno ? 'Actualizar Turno' : 'Crear Turno')}
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
              console.error('Error recargando turno.');
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
              console.error('Error recargando turno después de guardar.');
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
