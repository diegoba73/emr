import React, { useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  deleteLecturaCultivo,
  deleteSiembraMicrobiologia,
  updateLecturaCultivo,
  updateSiembraMicrobiologia,
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
  const [editSiembra, setEditSiembra] = useState<SiembraMicrobiologia | null>(null);
  const [editSiembraForm, setEditSiembraForm] = useState({
    condicion_incubacion: '',
    temperatura_c: '',
    atmosfera: '',
    observaciones: '',
  });
  const [editLectura, setEditLectura] = useState<LecturaCultivo | null>(null);
  const [editLecturaForm, setEditLecturaForm] = useState({
    crecimiento: 'PENDIENTE',
    recuento_bacteriano: '',
    descripcion_colonias: '',
    tincion_gram: '',
    observaciones: '',
    es_preliminar: false,
    horas_incubacion: '',
  });
  const [editSaving, setEditSaving] = useState(false);

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

  const eliminarSiembra = async (s: SiembraMicrobiologia) => {
    const nLect = lecturas.filter((l) => l.siembra === s.id).length;
    const msg =
      nLect > 0
        ? `¿Eliminar siembra #${s.id}? También se eliminarán ${nLect} lectura(s) y todo lo que cuelgue (aislados, antibiogramas, resultados). Esta acción no se puede deshacer.`
        : `¿Eliminar siembra #${s.id}? Esta acción no se puede deshacer.`;
    if (!window.confirm(msg)) return;
    try {
      await deleteSiembraMicrobiologia(s.id);
      toast.success('Siembra eliminada');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEliminarRegistroMicro));
    }
  };

  const eliminarLectura = async (l: LecturaCultivo) => {
    if (
      !window.confirm(
        `¿Eliminar lectura #${l.id}? También se eliminarán aislados, identificaciones, antibiogramas y resultados asociados. Esta acción no se puede deshacer.`
      )
    ) {
      return;
    }
    try {
      await deleteLecturaCultivo(l.id);
      toast.success('Lectura eliminada');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEliminarRegistroMicro));
    }
  };

  const openEditarSiembra = (s: SiembraMicrobiologia) => {
    setEditSiembra(s);
    setEditSiembraForm({
      condicion_incubacion: s.condicion_incubacion || '',
      temperatura_c: s.temperatura_c != null && s.temperatura_c !== '' ? String(s.temperatura_c) : '',
      atmosfera: s.atmosfera || '',
      observaciones: s.observaciones || '',
    });
  };

  const guardarSiembra = async () => {
    if (!editSiembra) return;
    setEditSaving(true);
    try {
      await updateSiembraMicrobiologia(editSiembra.id, {
        condicion_incubacion: editSiembraForm.condicion_incubacion,
        temperatura_c: editSiembraForm.temperatura_c ? editSiembraForm.temperatura_c : null,
        atmosfera: editSiembraForm.atmosfera,
        observaciones: editSiembraForm.observaciones,
      });
      toast.success('Siembra actualizada');
      setEditSiembra(null);
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarSiembra));
    } finally {
      setEditSaving(false);
    }
  };

  const openEditarLectura = (l: LecturaCultivo) => {
    setEditLectura(l);
    setEditLecturaForm({
      crecimiento: l.crecimiento || 'PENDIENTE',
      recuento_bacteriano: l.recuento_bacteriano || '',
      descripcion_colonias: l.descripcion_colonias || '',
      tincion_gram: l.tincion_gram || '',
      observaciones: l.observaciones || '',
      es_preliminar: Boolean(l.es_preliminar),
      horas_incubacion: l.horas_incubacion != null ? String(l.horas_incubacion) : '',
    });
  };

  const guardarLectura = async () => {
    if (!editLectura) return;
    setEditSaving(true);
    try {
      await updateLecturaCultivo(editLectura.id, {
        crecimiento: editLecturaForm.crecimiento,
        recuento_bacteriano: editLecturaForm.recuento_bacteriano,
        descripcion_colonias: editLecturaForm.descripcion_colonias,
        tincion_gram: editLecturaForm.tincion_gram,
        observaciones: editLecturaForm.observaciones,
        es_preliminar: editLecturaForm.es_preliminar,
        horas_incubacion: editLecturaForm.horas_incubacion
          ? Number(editLecturaForm.horas_incubacion)
          : null,
      });
      toast.success('Lectura actualizada');
      setEditLectura(null);
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarLectura));
    } finally {
      setEditSaving(false);
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
              {canOperate && <TableCell />}
            </TableRow>
          </TableHead>
          <TableBody>
            {siembras.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canOperate ? 5 : 4}>
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
                  {canOperate && (
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Button size="small" onClick={() => openEditarSiembra(s)}>
                        Editar
                      </Button>
                      <Button size="small" color="error" onClick={() => eliminarSiembra(s)}>
                        Eliminar
                      </Button>
                    </TableCell>
                  )}
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
              {canOperate && <TableCell />}
            </TableRow>
          </TableHead>
          <TableBody>
            {lecturas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canOperate ? 7 : 6}>
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
                  {canOperate && (
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Button size="small" onClick={() => openEditarLectura(l)}>
                        Editar
                      </Button>
                      <Button size="small" color="error" onClick={() => eliminarLectura(l)}>
                        Eliminar
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(editSiembra)} onClose={() => setEditSiembra(null)} fullWidth maxWidth="sm">
        <DialogTitle>Editar siembra #{editSiembra?.id}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              size="small"
              label="Condición incubación"
              value={editSiembraForm.condicion_incubacion}
              onChange={(e) =>
                setEditSiembraForm((f) => ({ ...f, condicion_incubacion: e.target.value }))
              }
            />
            <TextField
              size="small"
              label="Temperatura (°C)"
              value={editSiembraForm.temperatura_c}
              onChange={(e) => setEditSiembraForm((f) => ({ ...f, temperatura_c: e.target.value }))}
            />
            <TextField
              size="small"
              label="Atmósfera"
              value={editSiembraForm.atmosfera}
              onChange={(e) => setEditSiembraForm((f) => ({ ...f, atmosfera: e.target.value }))}
            />
            <TextField
              size="small"
              label="Observaciones"
              fullWidth
              multiline
              minRows={2}
              value={editSiembraForm.observaciones}
              onChange={(e) => setEditSiembraForm((f) => ({ ...f, observaciones: e.target.value }))}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditSiembra(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarSiembra} disabled={editSaving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(editLectura)} onClose={() => setEditLectura(null)} fullWidth maxWidth="sm">
        <DialogTitle>Editar lectura #{editLectura?.id}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel>Crecimiento</InputLabel>
              <Select
                label="Crecimiento"
                value={editLecturaForm.crecimiento}
                onChange={(e) =>
                  setEditLecturaForm((f) => ({ ...f, crecimiento: e.target.value }))
                }
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
              options={[...RECUENTO_BACTERIANO_OPCIONES]}
              value={editLecturaForm.recuento_bacteriano}
              onInputChange={(_e, value) =>
                setEditLecturaForm((f) => ({ ...f, recuento_bacteriano: value }))
              }
              renderInput={(params) => (
                <TextField {...params} label="Recuento bacteriano" />
              )}
            />
            <TextField
              size="small"
              label="Horas incubación"
              value={editLecturaForm.horas_incubacion}
              onChange={(e) =>
                setEditLecturaForm((f) => ({ ...f, horas_incubacion: e.target.value }))
              }
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={editLecturaForm.es_preliminar}
                  onChange={(e) =>
                    setEditLecturaForm((f) => ({ ...f, es_preliminar: e.target.checked }))
                  }
                />
              }
              label="Preliminar"
            />
            <TextField
              size="small"
              label="Descripción colonias"
              fullWidth
              value={editLecturaForm.descripcion_colonias}
              onChange={(e) =>
                setEditLecturaForm((f) => ({ ...f, descripcion_colonias: e.target.value }))
              }
              disabled={editLecturaForm.crecimiento === 'SIN_DESARROLLO'}
            />
            <TextField
              size="small"
              label="Tinción Gram"
              fullWidth
              value={editLecturaForm.tincion_gram}
              onChange={(e) =>
                setEditLecturaForm((f) => ({ ...f, tincion_gram: e.target.value }))
              }
              disabled={editLecturaForm.crecimiento === 'SIN_DESARROLLO'}
            />
            <TextField
              size="small"
              label="Observaciones"
              fullWidth
              multiline
              minRows={2}
              value={editLecturaForm.observaciones}
              onChange={(e) =>
                setEditLecturaForm((f) => ({ ...f, observaciones: e.target.value }))
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditLectura(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarLectura} disabled={editSaving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SiembrasLecturasPanel;
