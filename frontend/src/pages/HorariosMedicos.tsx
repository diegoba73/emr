import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns';
import { es } from 'date-fns/locale';
import { getMedicos, getRecursos } from '../services/apiService';
import {
  configurarSemana,
  createFeriado,
  createLicenciaMedico,
  deleteFeriado,
  deleteLicenciaMedico,
  Feriado,
  getFeriados,
  getHorarios,
  getLicenciasMedico,
  getTurnosPendientesFeriado,
  getTurnosPendientesLicencia,
  HorarioMedico,
  LicenciaMedico,
  MOTIVO_LICENCIA_OPTIONS,
  MotivoLicencia,
  TipoAgenda,
  TurnoAfectadoFeriado,
  updateFeriado,
  updateLicenciaMedico,
} from '../services/agendaMedica';
import { Medico, Recurso } from '../types';
import { getSafeClinicalActionMessage } from '../utils/apiError';
import { formatFechaHoraDisplay } from '../utils/dateFieldFormat';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const DIAS_CORTO = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];
const DURACIONES = [10, 15, 20, 30, 45, 60];

function toFechaIso(d: Date): string {
  return format(d, 'yyyy-MM-dd');
}

type DiaEdit = {
  activo: boolean;
  hora_inicio: string;
  hora_fin: string;
  recurso: string;
};

const emptyWeek = (): DiaEdit[] =>
  DIAS.map(() => ({ activo: false, hora_inicio: '09:00', hora_fin: '13:00', recurso: '' }));

function weekFromHorarios(horarios: HorarioMedico[], medicoId: number, tipo: TipoAgenda): DiaEdit[] {
  const week = emptyWeek();
  horarios
    .filter((h) => h.medico === medicoId && h.tipo === tipo && h.activo)
    .forEach((h) => {
      week[h.dia_semana] = {
        activo: true,
        hora_inicio: h.hora_inicio.slice(0, 5),
        hora_fin: h.hora_fin.slice(0, 5),
        recurso: h.recurso ? String(h.recurso) : '',
      };
    });
  return week;
}

function formatHoraTurno(iso: string | null): string {
  if (!iso) return '—';
  return formatFechaHoraDisplay(iso);
}

export default function HorariosMedicos() {
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [horarios, setHorarios] = useState<HorarioMedico[]>([]);
  const [feriados, setFeriados] = useState<Feriado[]>([]);
  const [licencias, setLicencias] = useState<LicenciaMedico[]>([]);
  const [medico, setMedico] = useState('');
  const [tipo, setTipo] = useState<TipoAgenda>('CONSULTA');
  const [duracion, setDuracion] = useState(20);
  const [dias, setDias] = useState<DiaEdit[]>(emptyWeek);
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [feriadoFecha, setFeriadoFecha] = useState('');
  const [feriadoNombre, setFeriadoNombre] = useState('');
  const [calendarioMes, setCalendarioMes] = useState(() => startOfMonth(new Date()));
  const [savingFeriado, setSavingFeriado] = useState(false);
  const [licInicio, setLicInicio] = useState('');
  const [licFin, setLicFin] = useState('');
  const [licMotivo, setLicMotivo] = useState<MotivoLicencia>('LICENCIA_MEDICA');
  const [licDetalle, setLicDetalle] = useState('');
  const [savingLicencia, setSavingLicencia] = useState(false);
  const [seguimiento, setSeguimiento] = useState<{
    feriado: Feriado;
    turnos: TurnoAfectadoFeriado[];
  } | null>(null);
  const [seguimientoLic, setSeguimientoLic] = useState<{
    licencia: LicenciaMedico;
    turnos: TurnoAfectadoFeriado[];
  } | null>(null);
  const [refrescandoPendientes, setRefrescandoPendientes] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const [m, r, h, f, lic] = await Promise.all([
        getMedicos(),
        getRecursos(),
        getHorarios(),
        getFeriados(),
        getLicenciasMedico(),
      ]);
      setMedicos(m);
      setRecursos(r);
      setHorarios(h);
      setFeriados(f);
      setLicencias(lic);
      if (m.length === 1) {
        setMedico(String(m[0].id));
        setDuracion(m[0].duracion_slot_min || 20);
        setDias(weekFromHorarios(h, m[0].id, 'CONSULTA'));
      }
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar los horarios.'));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const medicoId = medico ? Number(medico) : null;
  const recursosFiltrados = useMemo(
    () =>
      recursos.filter(
        (r) =>
          r.activo !== false &&
          (tipo === 'CONSULTA'
            ? r.tipo_recurso === 'CONSULTORIO'
            : ['SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'].includes(r.tipo_recurso))
      ),
    [recursos, tipo]
  );

  const feriadosConPendientes = useMemo(
    () => feriados.filter((f) => f.activo && (f.pendientes_count || 0) > 0),
    [feriados]
  );

  const licenciasDelMedico = useMemo(() => {
    if (!medicoId) return [];
    return licencias.filter((l) => l.medico === medicoId);
  }, [licencias, medicoId]);

  const licenciasConPendientes = useMemo(
    () => licencias.filter((l) => l.activo && (l.pendientes_count || 0) > 0),
    [licencias]
  );

  const feriadosPorFecha = useMemo(() => {
    const map = new Map<string, Feriado>();
    feriados.forEach((f) => {
      if (f.activo) map.set(f.fecha, f);
    });
    return map;
  }, [feriados]);

  const diasCalendario = useMemo(() => {
    const inicio = startOfWeek(startOfMonth(calendarioMes), { weekStartsOn: 1 });
    const fin = endOfWeek(endOfMonth(calendarioMes), { weekStartsOn: 1 });
    return eachDayOfInterval({ start: inicio, end: fin });
  }, [calendarioMes]);

  const seleccionarDiaCalendario = (dia: Date) => {
    const iso = toFechaIso(dia);
    setFeriadoFecha(iso);
    const existente = feriadosPorFecha.get(iso);
    setFeriadoNombre(existente ? existente.nombre : '');
  };

  const applyMedicoTipo = (nextMedico: string, nextTipo: TipoAgenda, list: HorarioMedico[], meds: Medico[]) => {
    setMedico(nextMedico);
    setTipo(nextTipo);
    const id = Number(nextMedico);
    const med = meds.find((m) => m.id === id);
    if (med) setDuracion(med.duracion_slot_min || 20);
    if (nextMedico) setDias(weekFromHorarios(list, id, nextTipo));
    else setDias(emptyWeek());
  };

  const patchDia = (index: number, patch: Partial<DiaEdit>) => {
    setDias((prev) => prev.map((d, i) => (i === index ? { ...d, ...patch } : d)));
  };

  const copiarLunesHabiles = () => {
    setDias((prev) => {
      const lun = prev[0];
      return prev.map((d, i) => (i >= 1 && i <= 4 ? { ...lun } : d));
    });
  };

  const mismoConsultorioTodos = () => {
    const primero = dias.find((d) => d.activo && d.recurso)?.recurso || dias[0]?.recurso || '';
    if (!primero) return;
    setDias((prev) => prev.map((d) => ({ ...d, recurso: primero })));
  };

  const save = async () => {
    if (!medicoId) return;
    setSaving(true);
    setError('');
    setOk('');
    try {
      const result = await configurarSemana({
        medico: medicoId,
        tipo,
        duracion_slot_min: duracion,
        dias: dias.map((d, i) => ({
          dia_semana: i,
          activo: d.activo,
          hora_inicio: d.activo ? d.hora_inicio : null,
          hora_fin: d.activo ? d.hora_fin : null,
          recurso: d.activo && d.recurso ? Number(d.recurso) : null,
        })),
      });
      const all = await getHorarios();
      setHorarios(all);
      setMedicos((prev) =>
        prev.map((m) =>
          m.id === medicoId ? { ...m, duracion_slot_min: result.duracion_slot_min } : m
        )
      );
      setDuracion(result.duracion_slot_min);
      setDias(weekFromHorarios(all, medicoId, tipo));
      setOk('Semana guardada. Los turnos ya reservados no se modifican.');
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo guardar la semana.'));
    } finally {
      setSaving(false);
    }
  };

  const abrirSeguimiento = (feriado: Feriado, turnos: TurnoAfectadoFeriado[]) => {
    setSeguimiento({ feriado, turnos });
  };

  const refreshPendientesSeguimiento = async () => {
    if (!seguimiento) return;
    setRefrescandoPendientes(true);
    setError('');
    try {
      const pend = await getTurnosPendientesFeriado(seguimiento.feriado.id);
      const list = await getFeriados();
      setFeriados(list);
      setSeguimiento({
        feriado: {
          ...seguimiento.feriado,
          pendientes_count: pend.count,
        },
        turnos: pend.turnos,
      });
      if (pend.count === 0) {
        setOk(`Feriado ${seguimiento.feriado.nombre}: ya no quedan turnos pendientes.`);
      }
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron actualizar los turnos pendientes.'));
    } finally {
      setRefrescandoPendientes(false);
    }
  };

  const altaFeriado = async () => {
    if (!feriadoFecha || !feriadoNombre.trim()) return;
    setSavingFeriado(true);
    setError('');
    setOk('');
    try {
      const created = await createFeriado({
        fecha: feriadoFecha,
        nombre: feriadoNombre.trim(),
      });
      const list = await getFeriados();
      setFeriados(list);
      setFeriadoFecha('');
      setFeriadoNombre('');
      const afectados = created.turnos_afectados || [];
      if (afectados.length > 0) {
        setOk(
          `Feriado guardado. Hay ${afectados.length} turno(s) ese día: reprogramalos o cancelalos.`
        );
        abrirSeguimiento(created, afectados);
      } else {
        setOk('Feriado guardado. Ese día no admite turnos nuevos.');
      }
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo guardar el feriado.'));
    } finally {
      setSavingFeriado(false);
    }
  };

  const desactivarFeriado = async (f: Feriado) => {
    setSavingFeriado(true);
    setError('');
    setOk('');
    try {
      await updateFeriado(f.id, { activo: false });
      setFeriados(await getFeriados());
      setOk(`Feriado desactivado: ${f.nombre}.`);
      if (seguimiento?.feriado.id === f.id) setSeguimiento(null);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo desactivar el feriado.'));
    } finally {
      setSavingFeriado(false);
    }
  };

  const eliminarFeriado = async (f: Feriado) => {
    setSavingFeriado(true);
    setError('');
    setOk('');
    try {
      await deleteFeriado(f.id);
      setFeriados(await getFeriados());
      setOk(`Feriado eliminado: ${f.nombre}.`);
      if (seguimiento?.feriado.id === f.id) setSeguimiento(null);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo eliminar el feriado.'));
    } finally {
      setSavingFeriado(false);
    }
  };

  const verPendientes = async (f: Feriado) => {
    setError('');
    try {
      const pend = await getTurnosPendientesFeriado(f.id);
      abrirSeguimiento(f, pend.turnos);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar los turnos del feriado.'));
    }
  };

  const guardarLicencia = async () => {
    if (!medicoId || !licInicio || !licFin) {
      setError('Elegí médico, fecha inicio y fecha fin de la licencia.');
      return;
    }
    setSavingLicencia(true);
    setError('');
    setOk('');
    try {
      const creada = await createLicenciaMedico({
        medico: medicoId,
        fecha_inicio: licInicio,
        fecha_fin: licFin,
        motivo: licMotivo,
        detalle: licDetalle.trim(),
        activo: true,
      });
      setLicencias(await getLicenciasMedico());
      setOk(
        `Licencia guardada (${creada.fecha_inicio} → ${creada.fecha_fin}). En esas fechas no se pueden sacar turnos con este profesional.`,
      );
      if ((creada.turnos_afectados || []).length > 0) {
        setSeguimientoLic({ licencia: creada, turnos: creada.turnos_afectados || [] });
      }
      setLicDetalle('');
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo guardar la licencia.'));
    } finally {
      setSavingLicencia(false);
    }
  };

  const desactivarLicencia = async (l: LicenciaMedico) => {
    setSavingLicencia(true);
    setError('');
    try {
      await updateLicenciaMedico(l.id, { activo: false });
      setLicencias(await getLicenciasMedico());
      setOk('Licencia desactivada: vuelve a admitir turnos en ese rango.');
      if (seguimientoLic?.licencia.id === l.id) setSeguimientoLic(null);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo desactivar la licencia.'));
    } finally {
      setSavingLicencia(false);
    }
  };

  const eliminarLicencia = async (l: LicenciaMedico) => {
    setSavingLicencia(true);
    setError('');
    try {
      await deleteLicenciaMedico(l.id);
      setLicencias(await getLicenciasMedico());
      setOk('Licencia eliminada.');
      if (seguimientoLic?.licencia.id === l.id) setSeguimientoLic(null);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo eliminar la licencia.'));
    } finally {
      setSavingLicencia(false);
    }
  };

  const verPendientesLicencia = async (l: LicenciaMedico) => {
    setError('');
    try {
      const pend = await getTurnosPendientesLicencia(l.id);
      setSeguimientoLic({ licencia: l, turnos: pend.turnos });
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar los turnos de la licencia.'));
    }
  };

  const refreshPendientesLicencia = async () => {
    if (!seguimientoLic) return;
    setRefrescandoPendientes(true);
    try {
      const pend = await getTurnosPendientesLicencia(seguimientoLic.licencia.id);
      setSeguimientoLic({ licencia: seguimientoLic.licencia, turnos: pend.turnos });
      setLicencias(await getLicenciasMedico());
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron actualizar los turnos.'));
    } finally {
      setRefrescandoPendientes(false);
    }
  };

  const stepSeconds = Math.max(60, duracion * 60);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Horarios de atención
      </Typography>
      <Typography sx={{ mb: 2 }}>
        Configurá la semana completa del médico: días activos, horario, consultorio/sala y duración del
        turno. Los cambios no modifican turnos ya reservados.
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {ok && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {ok}
        </Alert>
      )}
      {feriadosConPendientes.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Hay feriados con turnos pendientes de reprogramar o cancelar:{' '}
          {feriadosConPendientes
            .map((f) => `${f.fecha} (${f.nombre}: ${f.pendientes_count})`)
            .join(' · ')}
          . El día queda cerrado para turnos nuevos.
        </Alert>
      )}
      {licenciasConPendientes.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Hay licencias con turnos pendientes de reprogramar o cancelar:{' '}
          {licenciasConPendientes
            .map(
              (l) =>
                `${l.medico_nombre || `Médico #${l.medico}`} ${l.fecha_inicio}→${l.fecha_fin} (${l.pendientes_count})`,
            )
            .join(' · ')}
          . Esas fechas no admiten turnos nuevos con ese profesional.
        </Alert>
      )}
      {busy && <CircularProgress size={24} sx={{ mb: 2 }} />}

      <Paper sx={{ p: 2, display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
        <TextField
          select
          label="Médico"
          value={medico}
          onChange={(e) => applyMedicoTipo(e.target.value, tipo, horarios, medicos)}
          sx={{ minWidth: 260 }}
          disabled={busy || saving}
        >
          {medicos.map((m) => (
            <MenuItem key={m.id} value={String(m.id)}>
              {m.apellido}, {m.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Atención"
          value={tipo}
          onChange={(e) =>
            applyMedicoTipo(medico, e.target.value as TipoAgenda, horarios, medicos)
          }
          sx={{ minWidth: 160 }}
          disabled={busy || saving || !medico}
        >
          <MenuItem value="CONSULTA">Consulta</MenuItem>
          <MenuItem value="ESTUDIO">Estudio</MenuItem>
        </TextField>
        <TextField
          select
          label="Duración del turno"
          value={duracion}
          onChange={(e) => setDuracion(Number(e.target.value))}
          sx={{ minWidth: 180 }}
          disabled={busy || saving || !medico}
          helperText="Aplica a toda la agenda del médico"
        >
          {DURACIONES.map((m) => (
            <MenuItem key={m} value={m}>
              {m} minutos
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="outlined"
          disabled={busy || saving || !medico}
          onClick={copiarLunesHabiles}
        >
          Copiar lunes a días hábiles
        </Button>
        <Button
          variant="outlined"
          disabled={busy || saving || !medico}
          onClick={mismoConsultorioTodos}
        >
          Mismo {tipo === 'ESTUDIO' ? 'sala' : 'consultorio'} en todos
        </Button>
      </Paper>

      {medico && (
        <Paper sx={{ p: 1, overflowX: 'auto', mb: 3 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Día</TableCell>
                <TableCell>Activo</TableCell>
                <TableCell>Desde</TableCell>
                <TableCell>Hasta</TableCell>
                <TableCell>{tipo === 'ESTUDIO' ? 'Sala' : 'Consultorio'}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {DIAS.map((nombre, i) => {
                const d = dias[i];
                return (
                  <TableRow key={nombre}>
                    <TableCell>{nombre}</TableCell>
                    <TableCell>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={d.activo}
                            onChange={(e) => patchDia(i, { activo: e.target.checked })}
                            disabled={saving}
                          />
                        }
                        label={d.activo ? 'Atiende' : 'No'}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        type="time"
                        value={d.hora_inicio}
                        onChange={(e) => patchDia(i, { hora_inicio: e.target.value })}
                        inputProps={{ step: stepSeconds }}
                        InputLabelProps={{ shrink: true }}
                        disabled={saving || !d.activo}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        type="time"
                        value={d.hora_fin}
                        onChange={(e) => patchDia(i, { hora_fin: e.target.value })}
                        inputProps={{ step: stepSeconds }}
                        InputLabelProps={{ shrink: true }}
                        disabled={saving || !d.activo}
                        size="small"
                      />
                    </TableCell>
                    <TableCell sx={{ minWidth: 220 }}>
                      <TextField
                        select
                        fullWidth
                        size="small"
                        value={d.recurso}
                        onChange={(e) => patchDia(i, { recurso: e.target.value })}
                        disabled={saving || !d.activo}
                      >
                        <MenuItem value="">
                          {tipo === 'ESTUDIO' ? 'Seleccionar sala' : 'Seleccionar consultorio'}
                        </MenuItem>
                        {recursosFiltrados.map((r) => (
                          <MenuItem key={r.id} value={String(r.id)}>
                            {r.nombre}
                          </MenuItem>
                        ))}
                      </TextField>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <Box sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="contained"
              onClick={save}
              disabled={
                busy ||
                saving ||
                !medico ||
                dias.some((d) => d.activo && !d.recurso)
              }
            >
              {saving ? 'Guardando…' : 'Guardar semana'}
            </Button>
            {!busy && !dias.some((d) => d.activo) && (
              <Typography variant="body2" color="text.secondary">
                Ningún día activo: al guardar se quitan las franjas de {tipo === 'ESTUDIO' ? 'estudios' : 'consultas'} de este médico.
              </Typography>
            )}
          </Box>
        </Paper>
      )}

      <Typography variant="h6" gutterBottom>
        Feriados de la clínica
      </Typography>
      <Typography sx={{ mb: 2 }}>
        Elegí el día en el calendario, poné el nombre y guardá. Los feriados cierran la agenda de
        turnos para todos los médicos. Si ya hay turnos ese día, el feriado se guarda igual y debés
        reprogramarlos o cancelarlos; no se permiten turnos nuevos.
      </Typography>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'minmax(280px, 340px) 1fr' },
          gap: 2,
          mb: 2,
          alignItems: 'start',
        }}
      >
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <IconButton
              size="small"
              aria-label="Mes anterior"
              onClick={() => setCalendarioMes((m) => startOfMonth(subMonths(m, 1)))}
              disabled={busy || savingFeriado}
            >
              <ChevronLeftIcon />
            </IconButton>
            <Typography variant="subtitle1" sx={{ textTransform: 'capitalize' }}>
              {format(calendarioMes, 'MMMM yyyy', { locale: es })}
            </Typography>
            <IconButton
              size="small"
              aria-label="Mes siguiente"
              onClick={() => setCalendarioMes((m) => startOfMonth(addMonths(m, 1)))}
              disabled={busy || savingFeriado}
            >
              <ChevronRightIcon />
            </IconButton>
          </Box>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, 1fr)',
              gap: 0.5,
              textAlign: 'center',
            }}
          >
            {DIAS_CORTO.map((d) => (
              <Typography key={d} variant="caption" color="text.secondary" sx={{ py: 0.5 }}>
                {d}
              </Typography>
            ))}
            {diasCalendario.map((dia) => {
              const iso = toFechaIso(dia);
              const delMes = isSameMonth(dia, calendarioMes);
              const seleccionado = feriadoFecha === iso;
              const marcado = feriadosPorFecha.get(iso);
              const hoy = isSameDay(dia, new Date());
              return (
                <Button
                  key={iso}
                  size="small"
                  variant={seleccionado ? 'contained' : marcado ? 'outlined' : 'text'}
                  color={marcado && !seleccionado ? 'warning' : 'primary'}
                  disabled={busy || savingFeriado}
                  onClick={() => seleccionarDiaCalendario(dia)}
                  title={marcado ? marcado.nombre : undefined}
                  sx={{
                    minWidth: 0,
                    px: 0.5,
                    py: 0.75,
                    opacity: delMes ? 1 : 0.35,
                    fontWeight: hoy || seleccionado || marcado ? 700 : 400,
                    borderStyle: marcado && !seleccionado ? 'dashed' : undefined,
                  }}
                >
                  {format(dia, 'd')}
                </Button>
              );
            })}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Día con borde: feriado ya cargado. Clic para seleccionarlo.
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Fecha seleccionada"
            value={feriadoFecha || 'Elegí un día en el calendario'}
            InputProps={{ readOnly: true }}
            disabled={busy || savingFeriado}
          />
          <TextField
            label="Nombre"
            value={feriadoNombre}
            onChange={(e) => setFeriadoNombre(e.target.value)}
            disabled={busy || savingFeriado || !feriadoFecha}
            placeholder="Ej. Día de la Independencia"
            helperText={
              feriadoFecha && feriadosPorFecha.has(feriadoFecha)
                ? 'Ese día ya es feriado. Podés verlo en el listado o desactivarlo.'
                : ' '
            }
          />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              variant="contained"
              onClick={altaFeriado}
              disabled={
                busy ||
                savingFeriado ||
                !feriadoFecha ||
                !feriadoNombre.trim() ||
                feriadosPorFecha.has(feriadoFecha)
              }
            >
              {savingFeriado ? 'Guardando…' : 'Agregar feriado'}
            </Button>
            {feriadoFecha && feriadosPorFecha.has(feriadoFecha) && (
              <Button
                variant="outlined"
                onClick={() => void verPendientes(feriadosPorFecha.get(feriadoFecha)!)}
                disabled={savingFeriado}
              >
                Ver turnos del día
              </Button>
            )}
          </Box>
        </Paper>
      </Box>

      <Paper sx={{ p: 1, overflowX: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Fecha</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Pendientes</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {feriados.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography variant="body2" color="text.secondary">
                    No hay feriados cargados.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {feriados.map((f) => (
              <TableRow key={f.id}>
                <TableCell>{f.fecha}</TableCell>
                <TableCell>{f.nombre}</TableCell>
                <TableCell>{f.activo ? 'Activo' : 'Inactivo'}</TableCell>
                <TableCell>
                  {f.activo && (f.pendientes_count || 0) > 0 ? (
                    <Button size="small" onClick={() => void verPendientes(f)}>
                      {f.pendientes_count} turno(s)
                    </Button>
                  ) : (
                    '0'
                  )}
                </TableCell>
                <TableCell align="right">
                  {f.activo && (
                    <Button
                      size="small"
                      onClick={() => void desactivarFeriado(f)}
                      disabled={savingFeriado}
                    >
                      Desactivar
                    </Button>
                  )}
                  <Button
                    size="small"
                    color="error"
                    onClick={() => void eliminarFeriado(f)}
                    disabled={savingFeriado}
                  >
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
        Licencias del profesional
      </Typography>
      <Typography sx={{ mb: 2 }}>
        Elegí el médico arriba, cargá el rango y el motivo. Mientras la licencia esté activa,{' '}
        <strong>no se pueden sacar turnos</strong> con ese profesional en esas fechas (igual que un
        feriado, pero solo para él). Los turnos ya existentes no se cancelan solos: secretaría debe
        reprogramarlos o cancelarlos.
      </Typography>

      <Paper sx={{ p: 2, mb: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-start' }}>
        <TextField
          type="date"
          label="Desde"
          value={licInicio}
          onChange={(e) => setLicInicio(e.target.value)}
          InputLabelProps={{ shrink: true }}
          disabled={busy || savingLicencia || !medico}
        />
        <TextField
          type="date"
          label="Hasta"
          value={licFin}
          onChange={(e) => setLicFin(e.target.value)}
          InputLabelProps={{ shrink: true }}
          disabled={busy || savingLicencia || !medico}
        />
        <TextField
          select
          label="Motivo"
          value={licMotivo}
          onChange={(e) => setLicMotivo(e.target.value as MotivoLicencia)}
          sx={{ minWidth: 200 }}
          disabled={busy || savingLicencia || !medico}
        >
          {MOTIVO_LICENCIA_OPTIONS.map((o) => (
            <MenuItem key={o.value} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Detalle (opcional)"
          value={licDetalle}
          onChange={(e) => setLicDetalle(e.target.value)}
          sx={{ minWidth: 220 }}
          disabled={busy || savingLicencia || !medico}
          inputProps={{ maxLength: 200 }}
        />
        <Button
          variant="contained"
          onClick={() => void guardarLicencia()}
          disabled={busy || savingLicencia || !medico || !licInicio || !licFin}
        >
          {savingLicencia ? 'Guardando…' : 'Guardar licencia'}
        </Button>
      </Paper>

      <Paper sx={{ p: 1, overflowX: 'auto', mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Desde</TableCell>
              <TableCell>Hasta</TableCell>
              <TableCell>Motivo</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Pendientes</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!medico && (
              <TableRow>
                <TableCell colSpan={6}>Elegí un médico para ver y cargar sus licencias.</TableCell>
              </TableRow>
            )}
            {medico && licenciasDelMedico.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>Sin licencias cargadas para este profesional.</TableCell>
              </TableRow>
            )}
            {licenciasDelMedico.map((l) => (
              <TableRow key={l.id}>
                <TableCell>{l.fecha_inicio}</TableCell>
                <TableCell>{l.fecha_fin}</TableCell>
                <TableCell>
                  {l.motivo_display || l.motivo}
                  {l.detalle ? ` — ${l.detalle}` : ''}
                </TableCell>
                <TableCell>{l.activo ? 'Activa' : 'Inactiva'}</TableCell>
                <TableCell>
                  {l.activo && (l.pendientes_count || 0) > 0 ? (
                    <Button size="small" onClick={() => void verPendientesLicencia(l)}>
                      {l.pendientes_count} turno(s)
                    </Button>
                  ) : (
                    '0'
                  )}
                </TableCell>
                <TableCell align="right">
                  {l.activo && (
                    <Button
                      size="small"
                      onClick={() => void desactivarLicencia(l)}
                      disabled={savingLicencia}
                    >
                      Desactivar
                    </Button>
                  )}
                  <Button
                    size="small"
                    color="error"
                    onClick={() => void eliminarLicencia(l)}
                    disabled={savingLicencia}
                  >
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Dialog
        open={Boolean(seguimiento)}
        onClose={() => setSeguimiento(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          Turnos a gestionar — {seguimiento?.feriado.fecha} ({seguimiento?.feriado.nombre})
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            El feriado ya está cargado y ese día no admite turnos nuevos. Reprogramá o cancelá los
            turnos listados en el calendario.
          </Alert>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Hora</TableCell>
                <TableCell>Paciente</TableCell>
                <TableCell>Médico</TableCell>
                <TableCell>Estado</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(seguimiento?.turnos || []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>
                    No quedan turnos pendientes ese día.
                  </TableCell>
                </TableRow>
              )}
              {(seguimiento?.turnos || []).map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{formatHoraTurno(t.fecha_hora_inicio)}</TableCell>
                  <TableCell>{t.paciente_nombre || '—'}</TableCell>
                  <TableCell>{t.medico_nombre || '—'}</TableCell>
                  <TableCell>{t.estado}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button
            component={RouterLink}
            to="/turnos"
            variant="contained"
            onClick={() => setSeguimiento(null)}
          >
            Ir al calendario
          </Button>
          <Button onClick={() => void refreshPendientesSeguimiento()} disabled={refrescandoPendientes}>
            {refrescandoPendientes ? 'Actualizando…' : 'Actualizar lista'}
          </Button>
          <Button onClick={() => setSeguimiento(null)}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(seguimientoLic)}
        onClose={() => setSeguimientoLic(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          Turnos a gestionar — licencia{' '}
          {seguimientoLic
            ? `${seguimientoLic.licencia.fecha_inicio} → ${seguimientoLic.licencia.fecha_fin}`
            : ''}
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            La licencia ya está cargada: en ese rango no se pueden sacar turnos nuevos con este
            profesional. Reprogramá o cancelá los turnos listados.
          </Alert>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Hora</TableCell>
                <TableCell>Paciente</TableCell>
                <TableCell>Médico</TableCell>
                <TableCell>Estado</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(seguimientoLic?.turnos || []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>No quedan turnos pendientes en el rango.</TableCell>
                </TableRow>
              )}
              {(seguimientoLic?.turnos || []).map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{formatHoraTurno(t.fecha_hora_inicio)}</TableCell>
                  <TableCell>{t.paciente_nombre || '—'}</TableCell>
                  <TableCell>{t.medico_nombre || '—'}</TableCell>
                  <TableCell>{t.estado}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button
            component={RouterLink}
            to="/turnos"
            variant="contained"
            onClick={() => setSeguimientoLic(null)}
          >
            Ir al calendario
          </Button>
          <Button onClick={() => void refreshPendientesLicencia()} disabled={refrescandoPendientes}>
            {refrescandoPendientes ? 'Actualizando…' : 'Actualizar lista'}
          </Button>
          <Button onClick={() => setSeguimientoLic(null)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
