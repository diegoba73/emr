import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import {
  listInterfacesInstrumento,
  listMensajesInstrumento,
  type InterfazInstrumento,
  type MensajeInstrumento,
} from '../../services/limsApi';
import { getSafeApiErrorMessage } from '../../utils/apiError';

const ESTADO_COLOR: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  OK: 'success',
  SIN_MATCH: 'warning',
  IQC_BLOQUEADO: 'error',
  ERROR: 'error',
};

const InstrumentosPage: React.FC = () => {
  const [interfaces, setInterfaces] = useState<InterfazInstrumento[]>([]);
  const [mensajes, setMensajes] = useState<MensajeInstrumento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [ifs, msgs] = await Promise.all([
        listInterfacesInstrumento(),
        listMensajesInstrumento({ excepciones: true }),
      ]);
      setInterfaces(ifs);
      setMensajes(msgs);
    } catch (e) {
      setError(getSafeApiErrorMessage(e, 'No se pudo cargar la interfaz de equipos.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5">Analizadores</Typography>
      <Typography variant="body2" color="text.secondary">
        Worklist e ingesta ASTM (CM260 / Sysmex XP-300). Los valores entran como borrador; el
        bioquímico valida en la orden. El cable físico se prueba con el simulador, no desde esta
        pantalla.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper variant="outlined">
        <Typography variant="subtitle1" sx={{ p: 2 }}>
          Interfaces
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Driver</TableCell>
                <TableCell>Equipo</TableCell>
                <TableCell>Transporte</TableCell>
                <TableCell>Activo</TableCell>
                <TableCell>Último contacto</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {interfaces.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.nombre}</TableCell>
                  <TableCell>{row.driver}</TableCell>
                  <TableCell>{row.equipo_codigo}</TableCell>
                  <TableCell>{row.transporte}</TableCell>
                  <TableCell>{row.activo ? 'Sí' : 'No'}</TableCell>
                  <TableCell>{row.ultimo_contacto || '—'}</TableCell>
                </TableRow>
              ))}
              {!loading && interfaces.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    No hay interfaces. En el servidor: <code>manage.py seed_instrumentos</code>.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Paper variant="outlined">
        <Typography variant="subtitle1" sx={{ p: 2 }}>
          Excepciones (sin match, IQC, error)
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Fecha</TableCell>
                <TableCell>Equipo</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Sample ID</TableCell>
                <TableCell>Detalle</TableCell>
                <TableCell>Orden</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mensajes.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{new Date(row.created_at).toLocaleString()}</TableCell>
                  <TableCell>{row.interfaz_driver}</TableCell>
                  <TableCell>
                    <Chip size="small" label={row.estado} color={ESTADO_COLOR[row.estado] || 'default'} />
                  </TableCell>
                  <TableCell>{row.sample_id || '—'}</TableCell>
                  <TableCell>{row.detalle}</TableCell>
                  <TableCell>{row.solicitud_numero || '—'}</TableCell>
                </TableRow>
              ))}
              {!loading && mensajes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>Sin excepciones recientes.</TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
};

export default InstrumentosPage;
