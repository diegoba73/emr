import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import AsyncAutocomplete from '../common/AsyncAutocomplete';
import SlotPickerStaff from './SlotPickerStaff';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import {
  asignarTurnoEstudio,
  createEstudioComplementario,
  agendarTurnoEstudioDesdeAgenda,
  listTiposEstudioComplementario,
} from '../../services/estudiosComplementariosApi';
import {
  getCirugiaAbordajes,
  getCirugiaEspecialidades,
  getCirugiaProcedimientos,
} from '../../services/apiService';
import { ORIGEN_OPTIONS, practicaOptionsFromTipos } from '../../modules/estudios/constants';
import { parseEstudiosApiError } from '../../modules/estudios/apiErrors';
import { listRecursosProcCirugiaAgenda } from '../../utils/recursosEstudio';
import { formatLocalDateTimeSeconds } from '../../utils/formatLocalDateTime';
import { formatPacienteLabel } from '../../utils/pacienteFormat';
import { getSafeClinicalActionMessage, CLINICAL_ACTION_ERRORS } from '../../utils/apiError';
import type { SlotMedico } from '../../services/agendaMedica';
import type { Medico, Paciente, Recurso } from '../../types';
import type {
  CirugiaAbordajeCatalogo,
  CirugiaEspecialidadCatalogo,
  CirugiaProcedimientoCatalogo,
  CreateEstudioComplementarioPayload,
  EstudioPractica,
  TipoEstudioComplementario,
} from '../../types/estudios';

/** Tipo de actividad del alta unificado (consulta = Turno; resto = EstudioComplementario). */
export type TipoActividadProgramacion =
  | 'CONSULTA'
  | 'ESTUDIO'
  | 'PROCEDIMIENTO'
  | 'CIRUGIA';

function labelMedico(m: Medico): string {
  const ap = (m.apellido || '').trim();
  const no = (m.nombre || '').trim();
  if (ap && no) return `${ap}, ${no}`;
  return ap || no || `Médico #${m.id}`;
}

function parseLocalDateTime(fecha: string, hora: string): Date | null {
  if (!fecha || !hora) return null;
  const [y, mo, d] = fecha.split('-').map(Number);
  const timeParts = hora.split(':').map(Number);
  const h = timeParts[0] ?? 0;
  const mi = timeParts[1] ?? 0;
  const s = timeParts[2] ?? 0;
  const dt = new Date(y, mo - 1, d, h, mi, s);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

export interface ProgramacionTurnoFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  /** Paciente preseleccionado (p. ej. rol paciente). */
  initialPacienteId?: number | null;
  /** Tipo inicial. */
  initialTipo?: TipoActividadProgramacion;
  /** Si false, oculta Consulta médica (solo estudios). Default true. */
  allowConsulta?: boolean;
  submitLabel?: string;
  /** Slot del calendario (p. ej. franja de sobreturno). */
  initialDateTime?: Date | null;
  /** Secretaría: turno extra sobre un horario ya ocupado. */
  initialEsSobreturno?: boolean;
  initialMedicoId?: number | null;
  initialRecursoId?: number | null;
}

const ProgramacionTurnoForm: React.FC<ProgramacionTurnoFormProps> = ({
  onSuccess,
  onCancel,
  initialPacienteId = null,
  initialTipo = 'CONSULTA',
  allowConsulta = true,
  submitLabel = 'Crear',
  initialDateTime = null,
  initialEsSobreturno = false,
  initialMedicoId = null,
  initialRecursoId = null,
}) => {
  const {
    currentUser,
    medicos,
    loadMedicos,
    pacientes,
    loadPacientes,
    refreshTurnos,
    recursos,
    loadRecursos,
  } = useData();
  const rol = (currentUser?.rol || '').toLowerCase();
  const esPaciente = rol === 'paciente';
  const puedeSobreturno = !esPaciente && (rol === 'secretaria' || rol === 'admin' || Boolean(currentUser?.is_staff));

  const [tipoActividad, setTipoActividad] = useState<TipoActividadProgramacion>(
    allowConsulta ? initialTipo : initialTipo === 'CONSULTA' ? 'ESTUDIO' : initialTipo
  );
  const [paciente, setPaciente] = useState<Paciente | null>(null);
  const [medico, setMedico] = useState<Medico | null>(null);
  const [anestesista, setAnestesista] = useState<Medico | null>(null);
  const [motivo, setMotivo] = useState('');
  const [practica, setPractica] = useState<EstudioPractica>('');
  const [tipoEstudioId, setTipoEstudioId] = useState<number | undefined>();
  const [procSeleccionado, setProcSeleccionado] = useState<{
    id: number;
    nombre: string;
    clasificacion_quirurgica?: string;
  } | null>(null);
  const [cirEsp, setCirEsp] = useState<number | null>(null);
  const [cirProc, setCirProc] = useState<number | null>(null);
  const [cirAbr, setCirAbr] = useState<number | null>(null);
  const [origen, setOrigen] = useState('INTERNO');
  const [centro, setCentro] = useState('');
  const [descripcion, setDescripcion] = useState('');

  const [slot, setSlot] = useState<SlotMedico | null>(null);
  const [fechaManual, setFechaManual] = useState('');
  const [horaManual, setHoraManual] = useState('');
  const [duracionMin, setDuracionMin] = useState(20);
  const [recursoId, setRecursoId] = useState<number | null>(initialRecursoId);
  const [esSobreturno, setEsSobreturno] = useState(Boolean(initialEsSobreturno && puedeSobreturno));

  const [tipos, setTipos] = useState<TipoEstudioComplementario[]>([]);
  const [recursosProc, setRecursosProc] = useState<Recurso[]>([]);
  const [cirEspOptions, setCirEspOptions] = useState<CirugiaEspecialidadCatalogo[]>([]);
  const [cirProcOptions, setCirProcOptions] = useState<CirugiaProcedimientoCatalogo[]>([]);
  const [cirAbrOptions, setCirAbrOptions] = useState<CirugiaAbordajeCatalogo[]>([]);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingCatalogos, setLoadingCatalogos] = useState(true);

  const practicaOptions = useMemo(() => practicaOptionsFromTipos(tipos), [tipos]);
  const usaSlots =
    (tipoActividad === 'CONSULTA' || tipoActividad === 'ESTUDIO') && !esSobreturno;
  const tipoAgendaSlot = tipoActividad === 'ESTUDIO' ? 'ESTUDIO' : 'CONSULTA';
  const recursosConsulta = useMemo(
    () =>
      (recursos || []).filter(
        (r) =>
          r.activo !== false &&
          (r.tipo_recurso === 'CONSULTORIO' || !r.tipo_recurso)
      ),
    [recursos]
  );

  useEffect(() => {
    loadMedicos?.();
    loadPacientes?.();
    loadRecursos?.();
  }, [loadMedicos, loadPacientes, loadRecursos]);

  useEffect(() => {
    if (esPaciente && currentUser?.paciente?.id) {
      const p = pacientes.find((x) => x.id === currentUser.paciente!.id) || null;
      if (p) setPaciente(p);
      else if (initialPacienteId) {
        setPaciente({ id: initialPacienteId } as Paciente);
      }
    } else if (initialPacienteId) {
      const p = pacientes.find((x) => x.id === initialPacienteId) || null;
      if (p) setPaciente(p);
    }
  }, [esPaciente, currentUser, pacientes, initialPacienteId]);

  useEffect(() => {
    if (!initialMedicoId || !medicos?.length) return;
    const m = medicos.find((x) => x.id === initialMedicoId) || null;
    if (m) setMedico(m);
  }, [initialMedicoId, medicos]);

  useEffect(() => {
    if (!initialDateTime) return;
    const d = initialDateTime;
    setFechaManual(
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    );
    setHoraManual(
      `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    );
  }, [initialDateTime]);

  useEffect(() => {
    setEsSobreturno(Boolean(initialEsSobreturno && puedeSobreturno));
  }, [initialEsSobreturno, puedeSobreturno]);

  useEffect(() => {
    if (initialRecursoId) setRecursoId(initialRecursoId);
  }, [initialRecursoId]);

  useEffect(() => {
    let active = true;
    setLoadingCatalogos(true);
    Promise.all([
      listTiposEstudioComplementario().catch(() => [] as TipoEstudioComplementario[]),
      listRecursosProcCirugiaAgenda().catch(() => [] as Recurso[]),
      getCirugiaEspecialidades()
        .then((rows) => rows as CirugiaEspecialidadCatalogo[])
        .catch(() => [] as CirugiaEspecialidadCatalogo[]),
    ])
      .then(([t, r, esp]) => {
        if (!active) return;
        setTipos(t);
        setRecursosProc(r);
        setCirEspOptions(esp);
      })
      .finally(() => {
        if (active) setLoadingCatalogos(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!cirEsp) {
      setCirProcOptions([]);
      return;
    }
    let active = true;
    getCirugiaProcedimientos(cirEsp)
      .then((rows) => {
        if (active) setCirProcOptions(rows as CirugiaProcedimientoCatalogo[]);
      })
      .catch(() => {
        if (active) setCirProcOptions([]);
      });
    return () => {
      active = false;
    };
  }, [cirEsp]);

  useEffect(() => {
    if (!cirProc) {
      setCirAbrOptions([]);
      return;
    }
    let active = true;
    getCirugiaAbordajes(cirProc)
      .then((rows) => {
        if (active) setCirAbrOptions(rows as CirugiaAbordajeCatalogo[]);
      })
      .catch(() => {
        if (active) setCirAbrOptions([]);
      });
    return () => {
      active = false;
    };
  }, [cirProc]);

  const resetPrestacion = () => {
    setPractica('');
    setTipoEstudioId(undefined);
    setProcSeleccionado(null);
    setCirEsp(null);
    setCirProc(null);
    setCirAbr(null);
    setAnestesista(null);
    setSlot(null);
    setFechaManual('');
    setHoraManual('');
    setRecursoId(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const pacienteId = paciente?.id || (esPaciente ? currentUser?.paciente?.id : 0) || 0;
    if (!pacienteId) {
      setError('Seleccioná el paciente.');
      return;
    }
    if (!medico?.id) {
      setError(
        tipoActividad === 'CIRUGIA'
          ? 'Seleccioná el cirujano.'
          : 'Seleccioná el profesional / médico.'
      );
      return;
    }

    if (tipoActividad === 'CONSULTA') {
      if (esSobreturno) {
        const inicio = parseLocalDateTime(fechaManual, horaManual);
        if (!inicio) {
          setError('Indicá fecha y hora del sobreturno.');
          return;
        }
        const rid = recursoId;
        if (!rid) {
          setError('Seleccioná el consultorio del sobreturno.');
          return;
        }
        setSaving(true);
        try {
          const fin = new Date(inicio.getTime() + duracionMin * 60_000);
          await apiService.createTurno({
            paciente_id: pacienteId,
            medico_id: medico.id,
            recurso_id: rid,
            fecha_hora_inicio: formatLocalDateTimeSeconds(inicio),
            fecha_hora_fin: formatLocalDateTimeSeconds(fin),
            estado: 'CONFIRMADO',
            motivo_reserva: motivo || '',
            es_sobreturno: true,
          } as any);
          await refreshTurnos?.();
          onSuccess?.();
        } catch (err) {
          setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.turnoGuardar));
        } finally {
          setSaving(false);
        }
        return;
      }
      if (!slot) {
        setError('Elegí un horario libre.');
        return;
      }
      if (!slot.recurso_id) {
        setError('El horario no tiene consultorio asignado. Revisá Horarios de atención.');
        return;
      }
      setSaving(true);
      try {
        const inicio = new Date(slot.inicio);
        const fin = new Date(slot.fin || inicio.getTime() + (slot.duracion_min || 20) * 60_000);
        await apiService.createTurno({
          paciente_id: pacienteId,
          medico_id: medico.id,
          recurso_id: slot.recurso_id,
          fecha_hora_inicio: formatLocalDateTimeSeconds(inicio),
          fecha_hora_fin: formatLocalDateTimeSeconds(fin),
          estado: 'CONFIRMADO',
          motivo_reserva: motivo || '',
        } as any);
        await refreshTurnos?.();
        onSuccess?.();
      } catch (err) {
        setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.turnoGuardar));
      } finally {
        setSaving(false);
      }
      return;
    }

    if (tipoActividad === 'ESTUDIO') {
      if (!practica && !tipoEstudioId) {
        setError('Seleccioná el estudio.');
        return;
      }
      if (!slot) {
        setError('Elegí un horario libre.');
        return;
      }
      if (!slot.recurso_id) {
        setError('El horario no tiene sala asignada. Revisá Horarios de atención (tipo Estudio).');
        return;
      }
      setSaving(true);
      try {
        const inicio = new Date(slot.inicio);
        const fin = new Date(slot.fin || inicio.getTime() + (slot.duracion_min || 20) * 60_000);
        await agendarTurnoEstudioDesdeAgenda({
          paciente_id: pacienteId,
          recurso_id: slot.recurso_id,
          fecha_hora_inicio: inicio.toISOString(),
          fecha_hora_fin: fin.toISOString(),
          ...(tipoEstudioId ? { tipo_estudio: tipoEstudioId } : { practica }),
          origen,
          descripcion_clinica: descripcion || motivo || '',
          medico_id: medico.id,
        });
        await refreshTurnos?.();
        onSuccess?.();
      } catch (err) {
        setError(parseEstudiosApiError(err, 'No se pudo agendar el estudio.'));
      } finally {
        setSaving(false);
      }
      return;
    }

    // PROCEDIMIENTO / CIRUGIA — fecha/hora manual
    if (tipoActividad === 'PROCEDIMIENTO' && !procSeleccionado?.id) {
      setError('Seleccioná un procedimiento del catálogo.');
      return;
    }
    if (tipoActividad === 'CIRUGIA') {
      if (!anestesista?.id) {
        setError('Seleccioná el anestesista.');
        return;
      }
      if (!cirEsp || !cirProc) {
        setError('Seleccioná especialidad y procedimiento quirúrgico.');
        return;
      }
    }
    const inicio = parseLocalDateTime(fechaManual, horaManual);
    if (!inicio) {
      setError('Indicá fecha y hora del turno.');
      return;
    }
    if (!recursoId) {
      setError('Seleccioná la sala o quirófano.');
      return;
    }
    const fin = new Date(inicio.getTime() + (duracionMin || 60) * 60_000);
    setSaving(true);
    try {
      const payload: CreateEstudioComplementarioPayload =
        tipoActividad === 'PROCEDIMIENTO'
          ? {
              paciente_id: pacienteId,
              tipo_actividad: 'PROCEDIMIENTO',
              procedimiento_catalogo: procSeleccionado!.id,
              medico_solicitante: medico.id,
              origen,
              descripcion_clinica: descripcion,
              centro_realizador: centro,
            }
          : {
              paciente_id: pacienteId,
              tipo_actividad: 'CIRUGIA',
              cirugia_especialidad: cirEsp,
              cirugia_procedimiento: cirProc,
              cirugia_abordaje: cirAbr,
              medico_solicitante: medico.id,
              anestesista_previsto: anestesista!.id,
              origen,
              descripcion_clinica: descripcion,
              centro_realizador: centro,
            };
      const created = await createEstudioComplementario(payload);
      await asignarTurnoEstudio(created.id, {
        recurso_id: recursoId,
        fecha_hora_inicio: inicio.toISOString(),
        fecha_hora_fin: fin.toISOString(),
        medico_id: medico.id,
      });
      await refreshTurnos?.();
      onSuccess?.();
    } catch (err) {
      setError(parseEstudiosApiError(err, 'No se pudo crear y agendar la solicitud.'));
    } finally {
      setSaving(false);
    }
  };

  if (loadingCatalogos) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!esPaciente ? (
        <AsyncAutocomplete<Paciente>
          label="Paciente *"
          endpoint="/pacientes/"
          value={paciente}
          onChange={setPaciente}
          getOptionLabel={formatPacienteLabel}
          required
          minSearchLength={2}
        />
      ) : (
        <TextField
          label="Paciente"
          value={formatPacienteLabel(paciente || undefined)}
          disabled
          fullWidth
        />
      )}

      <Autocomplete
        options={medicos || []}
        value={medico}
        onChange={(_e, opt) => {
          setMedico(opt);
          setSlot(null);
        }}
        getOptionLabel={labelMedico}
        isOptionEqualToValue={(a, b) => a.id === b.id}
        renderInput={(params) => (
          <TextField
            {...params}
            label={tipoActividad === 'CIRUGIA' ? 'Cirujano *' : 'Profesional / médico *'}
            required
          />
        )}
      />

      {tipoActividad === 'CIRUGIA' && (
        <Autocomplete
          options={medicos || []}
          value={anestesista}
          onChange={(_e, opt) => setAnestesista(opt)}
          getOptionLabel={labelMedico}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          renderInput={(params) => <TextField {...params} label="Anestesista *" required />}
        />
      )}

      <FormControl fullWidth>
        <InputLabel>Tipo de actividad</InputLabel>
        <Select
          label="Tipo de actividad"
          value={tipoActividad}
          onChange={(e) => {
            setTipoActividad(e.target.value as TipoActividadProgramacion);
            resetPrestacion();
          }}
        >
          {allowConsulta && <MenuItem value="CONSULTA">Consulta médica</MenuItem>}
          <MenuItem value="ESTUDIO">Estudio</MenuItem>
          <MenuItem value="PROCEDIMIENTO">Procedimiento (no quirúrgico)</MenuItem>
          <MenuItem value="CIRUGIA">Cirugía</MenuItem>
        </Select>
      </FormControl>

      {tipoActividad === 'CONSULTA' && (
        <TextField
          label="Motivo de consulta"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          fullWidth
          multiline
          minRows={2}
          inputProps={{ maxLength: 255 }}
        />
      )}

      {puedeSobreturno && tipoActividad === 'CONSULTA' && (
        <FormControlLabel
          control={
            <Checkbox
              checked={esSobreturno}
              onChange={(e) => {
                setEsSobreturno(e.target.checked);
                if (e.target.checked) setSlot(null);
              }}
              disabled={saving}
            />
          }
          label="Sobreturno (extra sobre un horario ya ocupado)"
        />
      )}

      {esSobreturno && tipoActividad === 'CONSULTA' && (
        <Alert severity="info">
          La secretaría agenda un paciente adicional en este bloque horario del médico. El turno
          queda marcado como sobreturno.
        </Alert>
      )}

      {tipoActividad === 'ESTUDIO' && (
        <Autocomplete
          options={practicaOptions}
          value={practicaOptions.find((m) => m.value === practica) || null}
          onChange={(_e, opt) => {
            const val = (opt?.value || '') as EstudioPractica;
            const tipo = tipos.find((t) => (t.practica || t.codigo) === val);
            setPractica(val);
            setTipoEstudioId(tipo?.id);
          }}
          getOptionLabel={(o) => o.label}
          isOptionEqualToValue={(a, b) => a.value === b.value}
          renderInput={(params) => <TextField {...params} label="Estudio *" required />}
        />
      )}

      {tipoActividad === 'PROCEDIMIENTO' && (
        <AsyncAutocomplete<{ id: number; nombre: string; clasificacion_quirurgica?: string }>
          label="Procedimiento *"
          endpoint="/procedimientos-catalogo/"
          value={procSeleccionado}
          onChange={(opt) => {
            if (opt && opt.clasificacion_quirurgica === 'QUIRURGICO') {
              setError('Ese ítem es quirúrgico; usá el alta Cirugía.');
              setProcSeleccionado(null);
              return;
            }
            setProcSeleccionado(opt);
          }}
          getOptionLabel={(o) => o.nombre}
          required
          minSearchLength={2}
          placeholder="Buscar procedimiento…"
        />
      )}

      {tipoActividad === 'CIRUGIA' && (
        <>
          <Autocomplete
            options={cirEspOptions}
            value={cirEspOptions.find((e) => e.id === cirEsp) || null}
            onChange={(_e, opt) => {
              setCirEsp(opt?.id || null);
              setCirProc(null);
              setCirAbr(null);
            }}
            getOptionLabel={(o) => o.nombre}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            renderInput={(params) => (
              <TextField {...params} label="Especialidad quirúrgica *" required />
            )}
          />
          <Autocomplete
            options={cirProcOptions}
            disabled={!cirEsp}
            value={cirProcOptions.find((p) => p.id === cirProc) || null}
            onChange={(_e, opt) => {
              setCirProc(opt?.id || null);
              setCirAbr(null);
            }}
            getOptionLabel={(o) => o.nombre}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            renderInput={(params) => (
              <TextField {...params} label="Procedimiento quirúrgico *" required />
            )}
          />
          <Autocomplete
            options={cirAbrOptions}
            disabled={!cirProc}
            value={cirAbrOptions.find((a) => a.id === cirAbr) || null}
            onChange={(_e, opt) => setCirAbr(opt?.id || null)}
            getOptionLabel={(o) => o.nombre}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            renderInput={(params) => <TextField {...params} label="Abordaje (opcional)" />}
          />
        </>
      )}

      {tipoActividad !== 'CONSULTA' && (
        <>
          <FormControl fullWidth>
            <InputLabel>Origen</InputLabel>
            <Select label="Origen" value={origen} onChange={(e) => setOrigen(e.target.value)}>
              {ORIGEN_OPTIONS.map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {(tipoActividad === 'PROCEDIMIENTO' || tipoActividad === 'CIRUGIA') && (
            <TextField
              label="Centro realizador"
              value={centro}
              onChange={(e) => setCentro(e.target.value)}
              fullWidth
            />
          )}
          <TextField
            label="Descripción clínica"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
        </>
      )}

      {usaSlots && (
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 2 }}>
          <SlotPickerStaff
            medicoId={medico?.id ?? null}
            tipo={tipoAgendaSlot}
            value={slot}
            onChange={setSlot}
            disabled={saving}
          />
        </Box>
      )}

      {(esSobreturno && tipoActividad === 'CONSULTA') || !usaSlots ? (
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="subtitle2" color="text.secondary">
            {esSobreturno && tipoActividad === 'CONSULTA'
              ? 'Horario del sobreturno (mismo bloque del médico)'
              : 'Fecha y hora (acordada con el equipo)'}
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            <TextField
              label="Fecha *"
              type="date"
              value={fechaManual}
              onChange={(e) => setFechaManual(e.target.value)}
              InputLabelProps={{ shrink: true }}
              required
              sx={{ minWidth: 160 }}
            />
            <TextField
              label="Hora *"
              type="time"
              value={horaManual}
              onChange={(e) => setHoraManual(e.target.value)}
              InputLabelProps={{ shrink: true }}
              required
              sx={{ minWidth: 140 }}
            />
            <TextField
              label="Duración (min)"
              type="number"
              value={duracionMin}
              onChange={(e) =>
                setDuracionMin(
                  Number(e.target.value) || (esSobreturno && tipoActividad === 'CONSULTA' ? 20 : 60)
                )
              }
              inputProps={{ min: 15, step: 5 }}
              sx={{ width: 140 }}
            />
          </Box>
          {esSobreturno && tipoActividad === 'CONSULTA' ? (
            <Autocomplete
              options={recursosConsulta}
              value={recursosConsulta.find((r) => r.id === recursoId) || null}
              onChange={(_e, opt) => setRecursoId(opt?.id ?? null)}
              getOptionLabel={(r) => r.nombre || `Recurso #${r.id}`}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              renderInput={(params) => (
                <TextField {...params} label="Consultorio *" required />
              )}
            />
          ) : (
            <Autocomplete
              options={recursosProc}
              value={recursosProc.find((r) => r.id === recursoId) || null}
              onChange={(_e, opt) => setRecursoId(opt?.id ?? null)}
              getOptionLabel={(r) =>
                `${r.nombre}${r.tipo_recurso ? ` (${r.tipo_recurso.replace(/_/g, ' ')})` : ''}`
              }
              isOptionEqualToValue={(a, b) => a.id === b.id}
              renderInput={(params) => (
                <TextField {...params} label="Sala / quirófano *" required />
              )}
            />
          )}
          {!usaSlots && !esSobreturno && !recursosProc.length && (
            <Alert severity="warning">
              No hay salas ni quirófanos activos. Configurá recursos en Administración.
            </Alert>
          )}
        </Box>
      ) : null}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, pt: 1 }}>
        {onCancel && (
          <Button onClick={onCancel} disabled={saving}>
            Cancelar
          </Button>
        )}
        <Button type="submit" variant="contained" disabled={saving}>
          {saving ? 'Guardando…' : submitLabel}
        </Button>
      </Box>
    </Box>
  );
};

export default ProgramacionTurnoForm;
