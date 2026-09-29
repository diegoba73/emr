import React, { useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField, Typography } from '@mui/material';
import { Calendar as CalendarBase } from 'react-big-calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { localizer } from '../utils/calendarLocalizer';
import { getMedicos } from '../services/apiService';
import { getSlotsMedico, reservarHorario, SlotMedico, TipoAgenda } from '../services/agendaMedica';
import { Medico, Turno } from '../types';
import { getSafeClinicalActionMessage } from '../utils/apiError';
const Calendar = CalendarBase as any;
const fechaLocal = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
export default function ReservaTurnoPaciente({ onReserved, turnos = [] }: { onReserved: () => void; turnos?: Turno[] }) {
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [medico, setMedico] = useState('');
  const [tipo, setTipo] = useState<TipoAgenda>('CONSULTA');
  const [fecha, setFecha] = useState(new Date());
  const [view, setView] = useState('day');
  const [slots, setSlots] = useState<SlotMedico[]>([]);
  const [selected, setSelected] = useState<SlotMedico | null>(null);
  const [motivo, setMotivo] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [reload, setReload] = useState(0);
  const savingRef = useRef(false);
  useEffect(() => { getMedicos().then(setMedicos).catch(e => setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar los médicos.'))); }, []);
  const fechaStr = fechaLocal(fecha);
  useEffect(() => {
    let active = true;
    setSlots([]); setSelected(null);
    if (!medico) return;
    setLoading(true);
    getSlotsMedico(Number(medico), fechaStr, tipo).then(s => { if (active) setSlots(s); })
      .catch(e => { if (active) setError(getSafeClinicalActionMessage(e, 'No se pudo consultar la disponibilidad.')); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [medico, fechaStr, tipo, reload]);
  const reserve = async () => {
    if (!selected || savingRef.current) return;
    savingRef.current = true; setSaving(true); setError(''); setSuccess('');
    try {
      await reservarHorario(selected, motivo);
      setSuccess('Tu turno quedó reservado.'); setSelected(null); setMotivo(''); onReserved();
    } catch (e) { setError(getSafeClinicalActionMessage(e, 'No se pudo reservar. Consultá nuevamente los horarios disponibles.')); }
    finally { savingRef.current = false; setSaving(false); setReload(r => r+1); }
  };
  const disponibles = slots.map(s => ({ title: 'Disponible', start: new Date(s.inicio), end: new Date(s.fin), slot: s }));
  const propios = turnos.filter(t => String(t.medico?.id || t.medico_id) === medico && t.estado !== 'CANCELADO')
    .map(t => ({ title: `Mi turno · ${t.estado}`, start: new Date(t.fecha_hora_inicio),
      end: new Date(t.fecha_hora_fin || new Date(t.fecha_hora_inicio).getTime()+20*60*1000), slot: null }));
  const events = [...disponibles, ...propios];
  return <Box sx={{ my: 3 }}>
    <Typography variant="h6" gutterBottom>Reservar un turno</Typography>
    <Typography sx={{ mb: 2 }}>Elegí el médico, la atención y el día. Seleccioná un horario disponible para reservar tu turno de 20 minutos.</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
      <TextField select label="Médico" value={medico} onChange={e => { setMedico(e.target.value); setSuccess(''); }} sx={{ minWidth: 260 }} disabled={saving}>
        {medicos.map(m => <MenuItem key={m.id} value={String(m.id)}>{m.apellido}, {m.nombre}</MenuItem>)}
      </TextField>
      <TextField select label="Atención" value={tipo} onChange={e => setTipo(e.target.value as TipoAgenda)} sx={{ minWidth: 150 }} disabled={saving}>
        <MenuItem value="CONSULTA">Consulta</MenuItem><MenuItem value="ESTUDIO">Estudio</MenuItem>
      </TextField>
      <TextField type="date" label="Día" value={fechaStr} InputLabelProps={{ shrink: true }} inputProps={{ min: fechaLocal(new Date()) }} disabled={saving}
        onChange={e => { if (e.target.value) { setFecha(new Date(`${e.target.value}T12:00:00`)); setView('day'); } }} />
    </Box>
    {loading && <CircularProgress size={24} />}
    {medico && !loading && !slots.length && <Alert severity="info">No hay horarios disponibles para ese médico, atención y día.</Alert>}
    {medico && <Calendar localizer={localizer} culture="es" events={events} date={fecha} view={view}
      views={['month', 'day']} onNavigate={(d: Date) => { if (!saving) setFecha(d); }} onView={setView}
      onDrillDown={(d: Date) => { setFecha(d); setView('day'); }}
      onSelectEvent={(event: { slot: SlotMedico | null }) => { if (!saving && !loading) setSelected(event.slot); }}
      step={20} timeslots={3} min={new Date(2000,0,1,0)} max={new Date(2000,0,1,23,59)}
      eventPropGetter={(event: { slot: SlotMedico | null }) => ({ style: { backgroundColor: event.slot ? '#237a46' : '#3456a8' } })}
      scrollToTime={disponibles[0]?.start || new Date(2000,0,1,9)} style={{ height: 620, marginTop: 16 }}
      messages={{ today: 'Hoy', previous: 'Anterior', next: 'Siguiente', month: 'Mes', day: 'Día', noEventsInRange: 'Sin horarios disponibles', date: 'Fecha', time: 'Hora', event: 'Turno' }} />}
    {medico && <Typography variant="caption">Se muestran los horarios libres del día seleccionado. En la vista mensual, elegí un día para consultar su disponibilidad.</Typography>}
    <Dialog open={Boolean(selected)} onClose={() => { if (!saving) setSelected(null); }} fullWidth maxWidth="sm">
      <DialogTitle>Confirmar reserva</DialogTitle>
      <DialogContent>
        <Typography sx={{ mb: 2 }}>{medicos.find(m => String(m.id) === medico)?.apellido} · {tipo === 'ESTUDIO' ? 'Estudio' : 'Consulta'} · {selected && new Date(selected.inicio).toLocaleString('es-AR')} · 20 minutos</Typography>
        <TextField label="Motivo (opcional)" value={motivo} onChange={e => setMotivo(e.target.value)} fullWidth inputProps={{ maxLength: 255 }} disabled={saving} />
      </DialogContent>
      <DialogActions><Button disabled={saving} onClick={() => setSelected(null)}>Volver</Button><Button variant="contained" disabled={saving} onClick={reserve}>{saving ? 'Reservando…' : 'Confirmar turno'}</Button></DialogActions>
    </Dialog>
  </Box>;
}
