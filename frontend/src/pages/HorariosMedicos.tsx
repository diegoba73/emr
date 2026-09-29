import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress, MenuItem, Paper, TextField, Typography } from '@mui/material';
import { getMedicos, getRecursos } from '../services/apiService';
import { deleteHorario, getHorarios, HorarioMedico, saveHorario, updateHorario, TipoAgenda } from '../services/agendaMedica';
import { Medico, Recurso } from '../types';
import { getSafeClinicalActionMessage } from '../utils/apiError';
const dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
export default function HorariosMedicos() {
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [horarios, setHorarios] = useState<HorarioMedico[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [medico, setMedico] = useState('');
  const [dia, setDia] = useState(0);
  const [inicio, setInicio] = useState('09:00');
  const [fin, setFin] = useState('13:00');
  const [tipo, setTipo] = useState<TipoAgenda>('CONSULTA');
  const [recurso, setRecurso] = useState('');
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    Promise.all([getMedicos(), getRecursos(), getHorarios()]).then(([m, r, h]) => {
      if (!active) return;
      setMedicos(m); setRecursos(r); setHorarios(h);
      if (m.length === 1) setMedico(String(m[0].id));
    }).catch(e => { if (active) setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar los horarios.')); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, []);
  const save = async () => {
    setBusy(true); setError('');
    try {
      const data = { medico: Number(medico), dia_semana: dia, hora_inicio: inicio, hora_fin: fin,
        tipo, recurso: recurso ? Number(recurso) : null, activo: true, duracion_slot_min: 20 };
      if (editing) await updateHorario(editing, data);
      else await saveHorario(data);
      setEditing(null);
      setHorarios(await getHorarios());
    } catch (e) { setError(getSafeClinicalActionMessage(e, 'No se pudo guardar el horario.')); }
    finally { setBusy(false); }
  };
  const remove = async (id: number) => {
    setBusy(true); setError('');
    try { await deleteHorario(id); setHorarios(await getHorarios()); }
    catch (e) { setError(getSafeClinicalActionMessage(e, 'No se pudo quitar el horario.')); }
    finally { setBusy(false); }
  };
  return <Box sx={{ p: 3 }}>
    <Typography variant="h5" gutterBottom>Horarios de atención</Typography>
    <Typography sx={{ mb: 2 }}>Configurá las franjas semanales para consultas y estudios. Cada turno dura 20 minutos. Los cambios no modifican turnos ya reservados.</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {busy && <CircularProgress size={24} />}
    <Paper sx={{ p: 2, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
      <TextField select label="Médico" value={medico} onChange={e => { setMedico(e.target.value); setEditing(null); }} sx={{ minWidth: 250 }} disabled={busy}>
        {medicos.map(m => <MenuItem key={m.id} value={String(m.id)}>{m.apellido}, {m.nombre}</MenuItem>)}
      </TextField>
      <TextField select label="Día" value={dia} onChange={e => setDia(Number(e.target.value))} sx={{ minWidth: 140 }} disabled={busy}>
        {dias.map((d, i) => <MenuItem key={d} value={i}>{d}</MenuItem>)}
      </TextField>
      <TextField select label="Atención" value={tipo} onChange={e => { setTipo(e.target.value as TipoAgenda); setRecurso(''); }} sx={{ minWidth: 160 }} disabled={busy}>
        <MenuItem value="CONSULTA">Consulta</MenuItem><MenuItem value="ESTUDIO">Estudio</MenuItem>
      </TextField>
      <TextField type="time" label="Desde" value={inicio} onChange={e => setInicio(e.target.value)} inputProps={{ step: 1200 }} InputLabelProps={{ shrink: true }} disabled={busy} />
      <TextField type="time" label="Hasta" value={fin} onChange={e => setFin(e.target.value)} inputProps={{ step: 1200 }} InputLabelProps={{ shrink: true }} disabled={busy} />
      <TextField select label={tipo === 'ESTUDIO' ? 'Sala' : 'Consultorio (opcional)'} value={recurso} onChange={e => setRecurso(e.target.value)} sx={{ minWidth: 230 }} disabled={busy}>
        <MenuItem value="">Sin asignar</MenuItem>
        {recursos.filter(r => r.activo !== false && (tipo === 'CONSULTA' ? r.tipo_recurso === 'CONSULTORIO' : ['SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'].includes(r.tipo_recurso))).map(r => <MenuItem key={r.id} value={String(r.id)}>{r.nombre}</MenuItem>)}
      </TextField>
      <Button onClick={save} disabled={busy || !medico || (tipo === 'ESTUDIO' && !recurso)} variant="contained">{editing ? 'Guardar cambios' : 'Agregar franja'}</Button>
      {editing && <Button disabled={busy} onClick={() => setEditing(null)}>Cancelar edición</Button>}
    </Paper>
    <Box sx={{ mt: 2 }}>
      {!busy && medico && !horarios.some(h => h.medico === Number(medico)) && <Alert severity="info">Este médico todavía no tiene horarios publicados para reservas del paciente.</Alert>}
      {horarios.filter(h => h.medico === Number(medico)).sort((a,b) => a.dia_semana-b.dia_semana || a.hora_inicio.localeCompare(b.hora_inicio)).map(h => <Paper key={h.id} sx={{ p: 2, mb: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography>{dias[h.dia_semana]} · {h.hora_inicio.slice(0,5)}–{h.hora_fin.slice(0,5)} · {h.tipo === 'ESTUDIO' ? 'Estudios' : 'Consultas'} · 20 min {h.activo ? '' : '· Inactivo'}</Typography>
        <Box><Button disabled={busy} onClick={() => {
          setEditing(h.id); setDia(h.dia_semana); setInicio(h.hora_inicio.slice(0,5)); setFin(h.hora_fin.slice(0,5));
          setTipo(h.tipo); setRecurso(h.recurso ? String(h.recurso) : '');
        }}>Editar</Button>
        <Button color="error" disabled={busy} onClick={() => remove(h.id)}>Quitar franja</Button></Box>
      </Paper>)}
    </Box>
  </Box>;
}
