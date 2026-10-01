import React, { useState } from 'react';
import {
  Alert,
  Autocomplete,
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
} from '../../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import {
  RECUENTO_BACTERIANO_OPCIONES,
  todasLecturasSinDesarrollo,
} from '../../../utils/limsMicroCultivoNegativo';

const CRECIMIENTOS = ['PENDIENTE', 'SIN_DESARROLLO', 'ESCASO', 'MODERADO', 'ABUNDANTE', 'MIXTO'];

export interface SiembrasLecturasPanelProps {
  estudioId: number;
  siembras: SiembraMicrobiologia[];
  lecturas: LecturaCultivo[];
  medios: MedioCultivo[];
  canOperate: boolean;
  onRefresh: () => void;
  onIrAInformes?: () => void;
}

const SiembrasLecturasPanel: React.FC<SiembrasLecturasPanelProps> = ({
  estudioId,
  siembras,
  lecturas,
  medios,
  canOperate,
  onRefresh,
  onIrAInformes,
}) => {
  const [medioId, setMedioId] = useState<number | ''>('');
  const [siembraIdLectura, setSiembraIdLectura] = useState<number | ''>('');
  const [lecturaForm, setLecturaForm] = useState({
    crecimiento: 'PENDIENTE',
    recuento_bacteriano: '',
    descripcion_colonias: '',
    tincion_gram: '',
    observaciones: '',
    es_preliminar: false,
    horas_incubacion: '',
  });

  const cultivoNegativo = todasLecturasSinDesarrollo(lecturas);

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
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarSiembra));
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
        recuento_bacteriano: lecturaForm.recuento_bacteriano.trim() || undefined,
        descripcion_colonias: lecturaForm.descripcion_colonias,
        tincion_gram: lecturaForm.tincion_gram,
        observaciones: lecturaForm.observaciones,
        es_preliminar: lecturaForm.es_preliminar,
        horas_incubacion: lecturaForm.horas_incubacion ? Number(lecturaForm.horas_incubacion) : null,
      });
      const negativo = lecturaForm.crecimiento === 'SIN_DESARROLLO';
      toast.success(
        negativo
          ? 'Lectura sin desarrollo registrada. No hace falta aislar ni antibiograma.'
          : 'Lectura registrada'
      );
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarLectura));
    }
  };

  return (
    <Box>
      {cultivoNegativo && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          action={
            onIrAInformes ? (
              <Button color="inherit" size="small" onClick={onIrAInformes}>
                Ir a Informes
              </Button>
            ) : undefined
          }
        >
          Cultivo <strong>sin desarrollo</strong>: no se requieren aislados ni antibiograma. Se puede
          emitir el informe final indicando que no hubo desarrollo bacteriano
          {onIrAInformes ? ' (pestaña Informes).' : '.'}
        </Alert>
      )}

      <Typography variant="subtitle1" gutterBottom>
        Siembras
      </Typography>
      {canOperate && (
        <Paper sx={{ p: 2, mb: 2 }}>
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

      <Typography variant="subtitle1" gutterBottom>
        Lecturas
      </Typography>
      {canOperate && siembras.length > 0 && (
        <Paper sx={{ p: 2, mb: 2 }}>
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
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Crecimiento</InputLabel>
              <Select
                label="Crecimiento"
                value={lecturaForm.crecimiento}
                onChange={(ev) => setLecturaForm((f) => ({ ...f, crecimiento: ev.target.value }))}
              >
                {CRECIMIENTOS.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c === 'SIN_DESARROLLO' ? 'Sin desarrollo' : c}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Autocomplete
              freeSolo
              size="small"
              sx={{ minWidth: 200 }}
              options={[...RECUENTO_BACTERIANO_OPCIONES]}
              value={lecturaForm.recuento_bacteriano}
              onInputChange={(_e, value) =>
                setLecturaForm((f) => ({ ...f, recuento_bacteriano: value }))
              }
              renderInput={(params) => (
                <TextField {...params} label="Recuento bacteriano" placeholder="UFC/ml" />
              )}
            />
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
          {lecturaForm.crecimiento === 'SIN_DESARROLLO' && (
            <Alert severity="info" sx={{ mb: 1, py: 0.5 }}>
              Sin desarrollo: no hace falta aislamiento ni antibiograma. Podés indicar el recuento
              (p. ej. &lt;10³ UFC/ml) y pasar a Informes.
            </Alert>
          )}
          <TextField
            fullWidth
            size="small"
            label="Descripción colonias"
            margin="dense"
            value={lecturaForm.descripcion_colonias}
            onChange={(ev) => setLecturaForm((f) => ({ ...f, descripcion_colonias: ev.target.value }))}
            disabled={lecturaForm.crecimiento === 'SIN_DESARROLLO'}
          />
          <TextField
            fullWidth
            size="small"
            label="Tinción Gram"
            margin="dense"
            value={lecturaForm.tincion_gram}
            onChange={(ev) => setLecturaForm((f) => ({ ...f, tincion_gram: ev.target.value }))}
            disabled={lecturaForm.crecimiento === 'SIN_DESARROLLO'}
          />
          <Button sx={{ mt: 1 }} variant="contained" onClick={crearLectura}>
            Registrar lectura
          </Button>
        </Paper>
      )}
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Siembra</TableCell>
              <TableCell>Crecimiento</TableCell>
              <TableCell>Recuento</TableCell>
              <TableCell>Preliminar</TableCell>
              <TableCell>Colonias</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {lecturas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography color="text.secondary">Sin lecturas.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              lecturas.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{l.id}</TableCell>
                  <TableCell>{l.siembra}</TableCell>
                  <TableCell>{l.crecimiento}</TableCell>
                  <TableCell>{l.recuento_bacteriano || '—'}</TableCell>
                  <TableCell>{l.es_preliminar ? 'Sí' : 'No'}</TableCell>
                  <TableCell>{l.descripcion_colonias || '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default SiembrasLecturasPanel;
