import React, { useState } from 'react';
import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { LecturaCultivo, MedioCultivo, SiembraMicrobiologia } from '../../../types/lims';
import {
  createLecturaCultivo,
  createSiembraMicrobiologia,
  formatDrfError,
} from '../../../services/limsApi';

const CRECIMIENTOS = ['PENDIENTE', 'SIN_DESARROLLO', 'ESCASO', 'MODERADO', 'ABUNDANTE', 'MIXTO'];

export interface SiembrasLecturasPanelProps {
  estudioId: number;
  siembras: SiembraMicrobiologia[];
  lecturas: LecturaCultivo[];
  medios: MedioCultivo[];
  canOperate: boolean;
  onRefresh: () => void;
}

const SiembrasLecturasPanel: React.FC<SiembrasLecturasPanelProps> = ({
  estudioId,
  siembras,
  lecturas,
  medios,
  canOperate,
  onRefresh,
}) => {
  const [medioId, setMedioId] = useState<number | ''>('');
  const [siembraIdLectura, setSiembraIdLectura] = useState<number | ''>('');
  const [lecturaForm, setLecturaForm] = useState({
    crecimiento: 'PENDIENTE',
    descripcion_colonias: '',
    tincion_gram: '',
    observaciones: '',
    es_preliminar: false,
    horas_incubacion: '',
  });

  const crearSiembra = async () => {
    if (medioId === '') {
      toast.error('Seleccione medio de cultivo');
      return;
    }
    try {
      await createSiembraMicrobiologia({ estudio_id: estudioId, medio_id: Number(medioId) });
      toast.success('Siembra registrada');
      setMedioId('');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  const crearLectura = async () => {
    if (siembraIdLectura === '') {
      toast.error('Seleccione siembra');
      return;
    }
    try {
      await createLecturaCultivo({
        siembra_id: Number(siembraIdLectura),
        crecimiento: lecturaForm.crecimiento,
        descripcion_colonias: lecturaForm.descripcion_colonias,
        tincion_gram: lecturaForm.tincion_gram,
        observaciones: lecturaForm.observaciones,
        es_preliminar: lecturaForm.es_preliminar,
        horas_incubacion: lecturaForm.horas_incubacion ? Number(lecturaForm.horas_incubacion) : null,
      });
      toast.success('Lectura registrada');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Siembras
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Medio</TableCell>
              <TableCell>Fecha</TableCell>
              <TableCell>Condición</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {siembras.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography color="text.secondary">Sin siembras.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              siembras.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{s.id}</TableCell>
                  <TableCell>{medios.find((m) => m.id === s.medio)?.nombre || s.medio}</TableCell>
                  <TableCell>{s.fecha_siembra ? new Date(s.fecha_siembra).toLocaleString() : '—'}</TableCell>
                  <TableCell>{s.condicion_incubacion || '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {canOperate && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Nueva siembra
          </Typography>
          <FormControl size="small" sx={{ minWidth: 220, mr: 2 }}>
            <InputLabel>Medio</InputLabel>
            <Select label="Medio" value={medioId === '' ? '' : String(medioId)} onChange={(ev) => setMedioId(ev.target.value === '' ? '' : Number(ev.target.value))}>
              <MenuItem value="">—</MenuItem>
              {medios.filter((m) => m.activo !== false).map((m) => (
                <MenuItem key={m.id} value={m.id}>
                  {m.codigo} — {m.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="contained" onClick={crearSiembra}>
            Registrar siembra
          </Button>
        </Paper>
      )}

      <Typography variant="subtitle1" gutterBottom>
        Lecturas
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Siembra</TableCell>
              <TableCell>Crecimiento</TableCell>
              <TableCell>Preliminar</TableCell>
              <TableCell>Colonias</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {lecturas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary">Sin lecturas.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              lecturas.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{l.id}</TableCell>
                  <TableCell>{l.siembra}</TableCell>
                  <TableCell>{l.crecimiento}</TableCell>
                  <TableCell>{l.es_preliminar ? 'Sí' : 'No'}</TableCell>
                  <TableCell>{l.descripcion_colonias || '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {canOperate && siembras.length > 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Nueva lectura
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Siembra</InputLabel>
              <Select
                label="Siembra"
                value={siembraIdLectura === '' ? '' : String(siembraIdLectura)}
                onChange={(ev) => setSiembraIdLectura(ev.target.value === '' ? '' : Number(ev.target.value))}
              >
                <MenuItem value="">—</MenuItem>
                {siembras.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    #{s.id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Crecimiento</InputLabel>
              <Select
                label="Crecimiento"
                value={lecturaForm.crecimiento}
                onChange={(ev) => setLecturaForm((f) => ({ ...f, crecimiento: ev.target.value }))}
              >
                {CRECIMIENTOS.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Horas incub."
              value={lecturaForm.horas_incubacion}
              onChange={(ev) => setLecturaForm((f) => ({ ...f, horas_incubacion: ev.target.value }))}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={lecturaForm.es_preliminar}
                  onChange={(ev) => setLecturaForm((f) => ({ ...f, es_preliminar: ev.target.checked }))}
                />
              }
              label="Preliminar"
            />
          </Box>
          <TextField
            fullWidth
            size="small"
            label="Descripción colonias"
            margin="dense"
            value={lecturaForm.descripcion_colonias}
            onChange={(ev) => setLecturaForm((f) => ({ ...f, descripcion_colonias: ev.target.value }))}
          />
          <TextField
            fullWidth
            size="small"
            label="Tinción Gram"
            margin="dense"
            value={lecturaForm.tincion_gram}
            onChange={(ev) => setLecturaForm((f) => ({ ...f, tincion_gram: ev.target.value }))}
          />
          <Button sx={{ mt: 1 }} variant="contained" onClick={crearLectura}>
            Registrar lectura
          </Button>
        </Paper>
      )}
    </Box>
  );
};

export default SiembrasLecturasPanel;
