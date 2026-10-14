import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { Calendar as CalendarBase } from 'react-big-calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { localizer } from '../utils/calendarLocalizer';
import AsyncAutocomplete from './common/AsyncAutocomplete';
import {
  getDiasDisponibles,
  getSlotsMedico,
  reservarHorario,
  DiaDisponible,
  SlotMedico,
  TipoAgenda,
} from '../services/agendaMedica';
import { Medico, Turno } from '../types';
import { getSafeClinicalActionMessage } from '../utils/apiError';

const Calendar = CalendarBase as any;

const fechaLocal = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

function inicioMes(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function finMes(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

type DiaEvent = {
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  fecha: string;
  cantidad: number;
};

const calendarMessages = {
  next: 'Siguiente',
  previous: 'Anterior',
  today: 'Hoy',
  month: 'Mes',
  week: 'Semana',
  day: 'Día',
  noEventsInRange: 'No hay turnos libres en este período',
  showMore: (total: number) => `+ ${total} más`,
  date: 'Fecha',
  time: 'Hora',
  event: 'Turno',
};

export default function ReservaTurnoPaciente({
  onReserved,
  turnos = [],
}: {
  onReserved: () => void;
  turnos?: Turno[];
}) {
  const hoy = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const [selectedMedico, setSelectedMedico] = useState<Medico | null>(null);
  const [tipo, setTipo] = useState<TipoAgenda>('CONSULTA');
  const [calendarDate, setCalendarDate] = useState(() => new Date());
  const [calendarView, setCalendarView] = useState<'month' | 'week' | 'day'>('month');
  const [diasLibres, setDiasLibres] = useState<DiaDisponible[]>([]);
  const [fechaElegida, setFechaElegida] = useState('');
  const [slots, setSlots] = useState<SlotMedico[]>([]);
  const [selected, setSelected] = useState<SlotMedico | null>(null);
  const [motivo, setMotivo] = useState('');
  const [loadingDias, setLoadingDias] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [reloadDias, setReloadDias] = useState(0);
  const savingRef = useRef(false);

  const medicoId = selectedMedico?.id ?? null;
  const duracionLabel = selectedMedico?.duracion_slot_min || slots[0]?.duracion_min;

  const rangoMes = useMemo(() => {
    const desdeDate = inicioMes(calendarDate);
    const hastaDate = finMes(calendarDate);
    const desde = fechaLocal(desdeDate < hoy ? hoy : desdeDate);
    const hasta = fechaLocal(hastaDate);
    return { desde, hasta };
  }, [calendarDate, hoy]);

  useEffect(() => {
    let active = true;
    setDiasLibres([]);
    setFechaElegida('');
    setSlots([]);
    setSelected(null);
    if (!medicoId) return;
    if (rangoMes.desde > rangoMes.hasta) {
      setDiasLibres([]);
      return;
    }
    setLoadingDias(true);
    setError('');
    getDiasDisponibles(medicoId, rangoMes.desde, rangoMes.hasta, tipo)
      .then((dias) => {
        if (active) setDiasLibres(dias);
      })
      .catch((e) => {
        if (active) {
          setError(getSafeClinicalActionMessage(e, 'No se pudo consultar los días disponibles.'));
        }
      })
      .finally(() => {
        if (active) setLoadingDias(false);
      });
    return () => {
      active = false;
    };
  }, [medicoId, tipo, rangoMes.desde, rangoMes.hasta, reloadDias]);

  useEffect(() => {
    let active = true;
    setSlots([]);
    setSelected(null);
    if (!medicoId || !fechaElegida) return;
    setLoadingSlots(true);
    getSlotsMedico(medicoId, fechaElegida, tipo)
      .then((s) => {
        if (active) setSlots(s);
      })
      .catch((e) => {
        if (active) {
          setError(getSafeClinicalActionMessage(e, 'No se pudo consultar la disponibilidad.'));
        }
      })
      .finally(() => {
        if (active) setLoadingSlots(false);
      });
    return () => {
      active = false;
    };
  }, [medicoId, fechaElegida, tipo]);

  const calendarEvents: DiaEvent[] = useMemo(
    () =>
      diasLibres.map((d) => {
        const start = new Date(`${d.fecha}T12:00:00`);
        return {
          title: d.cantidad_slots === 1 ? '1 libre' : `${d.cantidad_slots} libres`,
          start,
          end: start,
          allDay: true,
          fecha: d.fecha,
          cantidad: d.cantidad_slots,
        };
      }),
    [diasLibres],
  );

  const elegirDia = useCallback(
    (d: Date) => {
      if (saving) return;
      const local = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      if (local < hoy) return;
      const key = fechaLocal(local);
      setFechaElegida(key);
      setSuccess('');
      setCalendarDate(local);
    },
    [hoy, saving],
  );

  const reserve = async () => {
    if (!selected || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await reservarHorario(selected, motivo);
      setSuccess('Tu turno quedó reservado.');
      setSelected(null);
      setMotivo('');
      setFechaElegida('');
      setSlots([]);
      setReloadDias((r) => r + 1);
      onReserved();
    } catch (e) {
      setError(
        getSafeClinicalActionMessage(e, 'No se pudo reservar. Consultá nuevamente los horarios disponibles.'),
      );
      setReloadDias((r) => r + 1);
      if (fechaElegida && medicoId) {
        try {
          setSlots(await getSlotsMedico(medicoId, fechaElegida, tipo));
        } catch {
          /* ignore */
        }
      }
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const paso = !medicoId ? 1 : !fechaElegida ? 2 : 3;
  const medicoLabel = selectedMedico
    ? `${selectedMedico.apellido}, ${selectedMedico.nombre}`
    : '';

  return (
    <Box sx={{ my: 3 }}>
      <Typography variant="h6" gutterBottom>
        Pedir un turno
      </Typography>
      <Typography sx={{ mb: 2 }} color="text.secondary">
        Buscá tu médico, elegí el día en el calendario y después la hora libre.
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        <Chip label="1. Médico" color={paso >= 1 ? 'primary' : 'default'} variant={paso === 1 ? 'filled' : 'outlined'} />
        <Chip label="2. Día" color={paso >= 2 ? 'primary' : 'default'} variant={paso === 2 ? 'filled' : 'outlined'} />
        <Chip label="3. Hora" color={paso >= 3 ? 'primary' : 'default'} variant={paso === 3 ? 'filled' : 'outlined'} />
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          ¿Consulta o estudio?
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <Button
            variant={tipo === 'CONSULTA' ? 'contained' : 'outlined'}
            disabled={saving}
            onClick={() => {
              setTipo('CONSULTA');
              setSuccess('');
            }}
          >
            Consulta
          </Button>
          <Button
            variant={tipo === 'ESTUDIO' ? 'contained' : 'outlined'}
            disabled={saving}
            onClick={() => {
              setTipo('ESTUDIO');
              setSuccess('');
            }}
          >
            Estudio
          </Button>
        </Box>

        <AsyncAutocomplete<Medico>
          label="Buscar médico"
          endpoint="/medicos/"
          value={selectedMedico}
          onChange={(m) => {
            setSelectedMedico(m);
            setSuccess('');
            setCalendarDate(new Date());
            setCalendarView('month');
          }}
          getOptionLabel={(option) => {
            const apellido = option.apellido || '';
            const nombre = option.nombre || '';
            const esp =
              (option as Medico & { especialidad_nombre?: string }).especialidad_nombre ||
              (option.especialidad as { nombre?: string } | undefined)?.nombre ||
              '';
            const dur = option.duracion_slot_min ? ` · ${option.duracion_slot_min} min` : '';
            return `${apellido}, ${nombre}${esp ? ` — ${esp}` : ''}${dur}`.trim();
          }}
          placeholder="Escribí apellido o nombre (mín. 2 letras)"
          helperText={
            selectedMedico?.duracion_slot_min
              ? `Cada turno dura ${selectedMedico.duracion_slot_min} minutos`
              : 'Escribí para buscar y elegí un médico de la lista'
          }
          minSearchLength={2}
          debounceMs={400}
          disabled={saving}
          sx={{ maxWidth: 480 }}
        />
      </Paper>

      {medicoId && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Calendario de {medicoLabel}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Los días con turnos libres aparecen marcados. Tocá un día para ver las horas disponibles.
          </Typography>
          {loadingDias && <CircularProgress size={24} sx={{ mb: 1 }} />}
          <Box sx={{ height: 520 }} data-testid="reserva-calendario">
            <Calendar
              localizer={localizer}
              culture="es"
              events={calendarEvents}
              startAccessor="start"
              endAccessor="end"
              allDayAccessor="allDay"
              date={calendarDate}
              view={calendarView}
              views={['month', 'week', 'day']}
              onNavigate={(d: Date) => {
                if (!saving) setCalendarDate(d);
              }}
              onView={(v: string) => {
                if (!saving) setCalendarView(v as 'month' | 'week' | 'day');
              }}
              selectable
              longPressThreshold={10}
              onSelectSlot={(slotInfo: { start: Date }) => elegirDia(slotInfo.start)}
              onSelectEvent={(event: DiaEvent) => elegirDia(event.start)}
              onDrillDown={(d: Date) => {
                elegirDia(d);
                setCalendarView('day');
              }}
              eventPropGetter={() => ({
                style: {
                  backgroundColor: '#2e7d32',
                  borderColor: '#1b5e20',
                  color: '#fff',
                },
              })}
              dayPropGetter={(date: Date) => {
                const key = fechaLocal(date);
                const tiene = diasLibres.some((d) => d.fecha === key);
                const elegido = fechaElegida === key;
                if (elegido) {
                  return { style: { backgroundColor: 'rgba(25, 118, 210, 0.12)' } };
                }
                if (tiene) {
                  return { style: { backgroundColor: 'rgba(46, 125, 50, 0.06)' } };
                }
                return {};
              }}
              messages={calendarMessages}
              popup
            />
          </Box>
          {!loadingDias && medicoId && !diasLibres.length && (
            <Alert severity="info" sx={{ mt: 1 }}>
              Este médico no tiene turnos libres en este mes. Probá el mes siguiente con las flechas del
              calendario.
            </Alert>
          )}
        </Paper>
      )}

      {medicoId && fechaElegida && (
        <Paper sx={{ p: 2, mb: 2 }} data-testid="reserva-horarios">
          <Typography variant="subtitle1" gutterBottom>
            Horarios del{' '}
            {new Date(`${fechaElegida}T12:00:00`).toLocaleDateString('es-AR', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
            {duracionLabel ? ` · ${duracionLabel} min` : ''}
          </Typography>
          {loadingSlots && <CircularProgress size={24} />}
          {!loadingSlots && !slots.length && (
            <Alert severity="info">Ya no quedan horarios libres ese día. Elegí otro en el calendario.</Alert>
          )}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {slots.map((slot) => {
              const hora = new Date(slot.inicio).toLocaleTimeString('es-AR', {
                hour: '2-digit',
                minute: '2-digit',
              });
              return (
                <Button
                  key={slot.inicio}
                  variant="contained"
                  color="success"
                  disabled={saving}
                  onClick={() => setSelected(slot)}
                  sx={{ minWidth: 88, py: 1.5, fontSize: '1.05rem' }}
                >
                  {hora}
                </Button>
              );
            })}
          </Box>
        </Paper>
      )}

      {medicoId && !!turnos.length && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Tus turnos ya reservados aparecen en la lista de abajo.
        </Typography>
      )}

      <Dialog open={Boolean(selected)} onClose={() => { if (!saving) setSelected(null); }} fullWidth maxWidth="sm">
        <DialogTitle>Confirmar turno</DialogTitle>
        <DialogContent>
          {selected && (
            <Box sx={{ mb: 2 }}>
              <Typography>
                <strong>Médico:</strong> {medicoLabel || '—'}
              </Typography>
              <Typography>
                <strong>Atención:</strong> {tipo === 'ESTUDIO' ? 'Estudio' : 'Consulta'}
              </Typography>
              <Typography>
                <strong>Día y hora:</strong>{' '}
                {new Date(selected.inicio).toLocaleString('es-AR', {
                  weekday: 'long',
                  day: 'numeric',
                  month: 'long',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </Typography>
              <Typography>
                <strong>Duración:</strong> {selected.duracion_min} minutos
              </Typography>
              {selected.recurso_nombre && (
                <Typography>
                  <strong>{tipo === 'ESTUDIO' ? 'Sala' : 'Consultorio'}:</strong> {selected.recurso_nombre}
                </Typography>
              )}
            </Box>
          )}
          <TextField
            label="Motivo (opcional)"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            fullWidth
            inputProps={{ maxLength: 255 }}
            disabled={saving}
          />
        </DialogContent>
        <DialogActions>
          <Button disabled={saving} onClick={() => setSelected(null)}>
            Volver
          </Button>
          <Button variant="contained" disabled={saving} onClick={reserve}>
            {saving ? 'Reservando…' : 'Confirmar turno'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
