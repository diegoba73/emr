import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
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
  Typography,
  CircularProgress,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { LimsTipoContenedor, LimsTipoMuestra, MuestraTransaccional } from '../../types/lims';
import {
  createMuestra,
  listContenedoresLims,
  listMuestrasPorSolicitud,
  listTiposMuestraLims,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import MuestraEstadoBadge from './MuestraEstadoBadge';
import MuestraAcciones from './MuestraAcciones';

export interface MuestrasOrdenPanelProps {
  solicitudId: number;
  solicitudNumero?: string | null;
  /** Oculta alta manual mientras la orden está pendiente (toma desde acciones de orden). */
  ordenEstado?: string;
  canOperate: boolean;
  /** Incrementar para forzar recarga tras cambios externos (ej. carga de resultados). */
  reloadToken?: number;
}

const MuestrasOrdenPanel: React.FC<MuestrasOrdenPanelProps> = ({
  solicitudId,
  solicitudNumero,
  ordenEstado,
  canOperate,
  reloadToken = 0,
}) => {
  const [rows, setRows] = useState<MuestraTransaccional[]>([]);
  const [loading, setLoading] = useState(true);
  const [tipos, setTipos] = useState<LimsTipoMuestra[]>([]);
  const [conts, setConts] = useState<LimsTipoContenedor[]>([]);
  const [openAlta, setOpenAlta] = useState(false);
  const [tipoId, setTipoId] = useState<number | ''>('');
  const [contId, setContId] = useState<number | ''>('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [m, t, c] = await Promise.all([
        listMuestrasPorSolicitud(solicitudId, solicitudNumero),
        listTiposMuestraLims({ activo: true }),
        listContenedoresLims(),
      ]);
      setRows(m);
      setTipos(t);
      setConts(c);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarMuestras));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [solicitudId, solicitudNumero, reloadToken]);

  const handleCrear = async () => {
    if (tipoId === '') {
      toast.error('Seleccione tipo de muestra');
      return;
    }
    setSaving(true);
    try {
      await createMuestra({
        solicitud_id: solicitudId,
        tipo_muestra_id: Number(tipoId),
        tipo_contenedor_id: contId === '' ? null : Number(contId),
        observaciones: '',
      });
      toast.success('Muestra creada');
      setOpenAlta(false);
      setTipoId('');
      setContId('');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCrearMuestra));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  const showAlta = canOperate && ordenEstado !== 'PENDIENTE';

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Muestras</Typography>
        {showAlta && (
          <Button variant="contained" size="small" onClick={() => setOpenAlta(true)}>
            Registrar muestra
          </Button>
        )}
      </Box>
      {canOperate && ordenEstado === 'PENDIENTE' && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Usá el botón <strong>Tomar muestra</strong> en acciones de orden para registrar la toma física.
        </Typography>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Ubicación</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary">Sin muestras registradas.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((m) => {
                const tipoNombre = tipos.find((t) => t.id === m.tipo_muestra)?.nombre || `ID ${m.tipo_muestra}`;
                return (
                  <TableRow key={m.id}>
                    <TableCell>{m.codigo_barra || '—'}</TableCell>
                    <TableCell>{tipoNombre}</TableCell>
                  <TableCell>
                    <MuestraEstadoBadge estado={m.estado} />
                  </TableCell>
                  <TableCell>{m.ubicacion_actual || '—'}</TableCell>
                  <TableCell align="right">
                    <MuestraAcciones muestra={m} canOperate={canOperate} onUpdated={load} />
                  </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openAlta} onClose={() => !saving && setOpenAlta(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nueva muestra</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal">
            <InputLabel>Tipo de muestra</InputLabel>
            <Select
              label="Tipo de muestra"
              value={tipoId === '' ? '' : String(tipoId)}
              onChange={(ev) => {
                const raw = ev.target.value;
                const str = typeof raw === 'number' ? String(raw) : raw;
                setTipoId(str === '' ? '' : Number(str));
              }}
            >
              <MenuItem value="">Seleccione…</MenuItem>
              {tipos.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.codigo} — {t.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <InputLabel>Contenedor (opcional)</InputLabel>
            <Select
              label="Contenedor (opcional)"
              value={contId === '' ? '' : String(contId)}
              onChange={(ev) => {
                const raw = ev.target.value;
                const str = typeof raw === 'number' ? String(raw) : raw;
                setContId(str === '' ? '' : Number(str));
              }}
            >
              <MenuItem value="">—</MenuItem>
              {conts.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.codigo} — {c.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAlta(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleCrear} disabled={saving}>
            Crear
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MuestrasOrdenPanel;
