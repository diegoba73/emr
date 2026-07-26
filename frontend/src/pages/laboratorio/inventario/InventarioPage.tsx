import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import {
  createLoteInsumo,
  getInventarioAlertas,
  listInsumosLab,
  listLotesInsumo,
  listMovimientosStock,
  type InsumoLab,
  type InventarioAlertas,
  type LoteInsumo,
  type MovimientoStock,
} from '../../../services/limsApi';

const InventarioPage: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [insumos, setInsumos] = useState<InsumoLab[]>([]);
  const [lotes, setLotes] = useState<LoteInsumo[]>([]);
  const [movimientos, setMovimientos] = useState<MovimientoStock[]>([]);
  const [alertas, setAlertas] = useState<InventarioAlertas | null>(null);
  const [loading, setLoading] = useState(true);
  const [loteForm, setLoteForm] = useState({
    insumo: '',
    codigo_lote: '',
    cantidad: '100',
    fecha_vencimiento: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [i, l, m, a] = await Promise.all([
        listInsumosLab(),
        listLotesInsumo(),
        listMovimientosStock(),
        getInventarioAlertas(),
      ]);
      setInsumos(i);
      setLotes(l);
      setMovimientos(m);
      setAlertas(a);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Error cargando inventario');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const submitLote = async () => {
    try {
      await createLoteInsumo({
        insumo: Number(loteForm.insumo),
        codigo_lote: loteForm.codigo_lote,
        cantidad: Number(loteForm.cantidad),
        fecha_vencimiento: loteForm.fecha_vencimiento || null,
      });
      toast.success('Lote creado');
      setLoteForm({ insumo: '', codigo_lote: '', cantidad: '100', fecha_vencimiento: '' });
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'No se pudo crear el lote');
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Inventario de laboratorio
      </Typography>
      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Insumos" />
        <Tab label="Lotes" />
        <Tab label="Movimientos" />
        <Tab label="Alertas" />
      </Tabs>
      {loading && <CircularProgress size={24} />}

      {tab === 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell align="right">Stock</TableCell>
              <TableCell align="right">Mín.</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {insumos.map((i) => (
              <TableRow key={i.id}>
                <TableCell>{i.codigo}</TableCell>
                <TableCell>{i.nombre}</TableCell>
                <TableCell>{i.tipo}</TableCell>
                <TableCell align="right">{i.stock_actual}</TableCell>
                <TableCell align="right">{i.stock_min}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {tab === 1 && (
        <Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
            <TextField
              size="small"
              label="Insumo ID"
              value={loteForm.insumo}
              onChange={(e) => setLoteForm((p) => ({ ...p, insumo: e.target.value }))}
            />
            <TextField
              size="small"
              label="Código lote"
              value={loteForm.codigo_lote}
              onChange={(e) => setLoteForm((p) => ({ ...p, codigo_lote: e.target.value }))}
            />
            <TextField
              size="small"
              label="Cantidad"
              type="number"
              value={loteForm.cantidad}
              onChange={(e) => setLoteForm((p) => ({ ...p, cantidad: e.target.value }))}
            />
            <TextField
              size="small"
              type="date"
              label="Vence"
              InputLabelProps={{ shrink: true }}
              value={loteForm.fecha_vencimiento}
              onChange={(e) => setLoteForm((p) => ({ ...p, fecha_vencimiento: e.target.value }))}
            />
            <Button variant="contained" onClick={submitLote}>
              Alta lote
            </Button>
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Insumo</TableCell>
                <TableCell>Lote</TableCell>
                <TableCell align="right">Cantidad</TableCell>
                <TableCell>Vence</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lotes.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>
                    {l.insumo_codigo} — {l.insumo_nombre}
                  </TableCell>
                  <TableCell>{l.codigo_lote}</TableCell>
                  <TableCell align="right">{l.cantidad}</TableCell>
                  <TableCell>{l.fecha_vencimiento || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 2 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Fecha</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>Insumo</TableCell>
              <TableCell>Lote</TableCell>
              <TableCell align="right">Cant.</TableCell>
              <TableCell>Motivo</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {movimientos.map((m) => (
              <TableRow key={m.id}>
                <TableCell>{new Date(m.created_at).toLocaleString('es-AR')}</TableCell>
                <TableCell>{m.tipo}</TableCell>
                <TableCell>{m.insumo_codigo}</TableCell>
                <TableCell>{m.lote_codigo}</TableCell>
                <TableCell align="right">{m.cantidad}</TableCell>
                <TableCell>{m.motivo}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {tab === 3 && alertas && (
        <Box>
          {(alertas.bajo_minimo.length === 0 && alertas.por_vencer.length === 0) && (
            <Alert severity="success">Sin alertas de stock.</Alert>
          )}
          {alertas.bajo_minimo.map((a) => (
            <Alert key={`min-${a.insumo_id}`} severity="warning" sx={{ mb: 1 }}>
              Bajo mínimo: {a.codigo} ({a.stock_actual}/{a.stock_min} {a.unidad})
            </Alert>
          ))}
          {alertas.por_vencer.map((a) => (
            <Alert key={`v-${a.lote_id}`} severity="error" sx={{ mb: 1 }}>
              Por vencer: {a.insumo_codigo}/{a.codigo_lote} en {a.dias_restantes} días
            </Alert>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default InventarioPage;
