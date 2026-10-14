import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControlLabel,
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
import { getMedicos, getRecursos } from '../services/apiService';
import {
  configurarSemana,
  getHorarios,
  HorarioMedico,
  TipoAgenda,
} from '../services/agendaMedica';
import { Medico, Recurso } from '../types';
import { getSafeClinicalActionMessage } from '../utils/apiError';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const DURACIONES = [10, 15, 20, 30, 45, 60];

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

export default function HorariosMedicos() {
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [horarios, setHorarios] = useState<HorarioMedico[]>([]);
  const [medico, setMedico] = useState('');
  const [tipo, setTipo] = useState<TipoAgenda>('CONSULTA');
  const [duracion, setDuracion] = useState(20);
  const [dias, setDias] = useState<DiaEdit[]>(emptyWeek);
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const load = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const [m, r, h] = await Promise.all([getMedicos(), getRecursos(), getHorarios()]);
      setMedicos(m);
      setRecursos(r);
      setHorarios(h);
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
        <Paper sx={{ p: 1, overflowX: 'auto' }}>
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
                          {tipo === 'ESTUDIO' ? 'Seleccionar sala' : 'Sin asignar'}
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
                (tipo === 'ESTUDIO' && dias.some((d) => d.activo && !d.recurso))
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
    </Box>
  );
}
