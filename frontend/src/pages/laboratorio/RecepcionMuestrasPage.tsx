import React, { useCallback, useState } from 'react';
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
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import BarcodeScanInput from '../../components/lims/BarcodeScanInput';
import MuestraEstadoBadge from '../../components/lims/MuestraEstadoBadge';
import { postRecibirMuestraPorCodigo } from '../../services/limsApi';
import type { MuestraLookupLims } from '../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canOperateLims } from '../../utils/limsAccess';

interface RecepcionSesionItem {
  codigo: string;
  muestra: MuestraLookupLims;
  recibidaEn: string;
  extraccionCompleta?: boolean;
  tubosPendientes?: Array<{
    codigo_barra: string | null;
    tipo_contenedor_codigo?: string | null;
    tipo_contenedor_nombre?: string | null;
  }>;
}

const MAX_HISTORIAL = 20;

const RecepcionMuestrasPage: React.FC = () => {
  const { currentUser } = useData();
  const canOp = canOperateLims(currentUser);
  const [ubicacion, setUbicacion] = useState('Laboratorio');
  const [procesando, setProcesando] = useState(false);
  const [historial, setHistorial] = useState<RecepcionSesionItem[]>([]);
  const [ultimoPendientes, setUltimoPendientes] = useState<RecepcionSesionItem['tubosPendientes']>([]);

  const handleScan = useCallback(
    async (codigo: string) => {
      if (!canOp || procesando) return;
      setProcesando(true);
      try {
        const data = await postRecibirMuestraPorCodigo({
          codigo_barra: codigo,
          ubicacion_actual: ubicacion.trim() || 'Laboratorio',
        });
        const pendientes = data.tubos_pendientes_extraccion || [];
        setUltimoPendientes(pendientes);
        setHistorial((prev) =>
          [
            {
              codigo,
              muestra: data,
              recibidaEn: new Date().toISOString(),
              extraccionCompleta: data.extraccion_completa,
              tubosPendientes: pendientes,
            },
            ...prev.filter((h) => h.codigo !== codigo),
          ].slice(0, MAX_HISTORIAL)
        );
        if (data.extraccion_completa) {
          toast.success(`Recibida: ${codigo}. Todos los tubos de la orden.`);
        } else if (pendientes.length > 0) {
          const labels = pendientes
            .map(
              (p) =>
                p.codigo_barra ||
                p.tipo_contenedor_codigo ||
                p.tipo_contenedor_nombre ||
                'tubo'
            )
            .join(', ');
          toast.success(`Recibida: ${codigo}. Aún faltan: ${labels}`, { duration: 5000 });
        } else {
          toast.success(`Recibida: ${codigo}`);
        }
      } catch (e) {
        toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
      } finally {
        setProcesando(false);
      }
    },
    [canOp, procesando, ubicacion]
  );

  if (!canOp) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>La recepción por escaneo requiere rol laboratorio o administrador.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Recepción de muestras
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Escaneá cada tubo al recibirlo. Pasa a <strong>Recibida</strong> (confirma la toma e ingreso
        en un solo paso). Con el primer tubo la orden entra en proceso; podés cargar resultados de los
        ya recibidos aunque falten otros.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <TextField
          label="Ubicación de recepción"
          value={ubicacion}
          onChange={(e) => setUbicacion(e.target.value)}
          fullWidth
          margin="normal"
          helperText="Se asignará a cada muestra escaneada en esta sesión"
        />
        <BarcodeScanInput
          label="Escanear código del tubo"
          onScan={handleScan}
          disabled={procesando}
          sx={{ mt: 1 }}
        />
      </Paper>

      {ultimoPendientes && ultimoPendientes.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Tubos pendientes de recepción en la última orden:{' '}
          {ultimoPendientes
            .map(
              (p) =>
                `${p.codigo_barra || '—'}${
                  p.tipo_contenedor_codigo ? ` (${p.tipo_contenedor_codigo})` : ''
                }`
            )
            .join(' · ')}
        </Alert>
      )}

      {historial.length === 0 ? (
        <Alert severity="info">Aún no se recibieron muestras en esta sesión.</Alert>
      ) : (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="subtitle1">Recibidas en esta sesión</Typography>
            <Chip size="small" label={historial.length} color="primary" />
          </Box>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Código</TableCell>
                  <TableCell>Paciente</TableCell>
                  <TableCell>Orden</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Orden completa</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {historial.map((h) => (
                  <TableRow key={h.codigo}>
                    <TableCell>{h.codigo}</TableCell>
                    <TableCell>{h.muestra.paciente_nombre || '—'}</TableCell>
                    <TableCell>{h.muestra.solicitud_numero || h.muestra.solicitud}</TableCell>
                    <TableCell>
                      <MuestraEstadoBadge estado={h.muestra.estado} />
                    </TableCell>
                    <TableCell>
                      {h.extraccionCompleta ? (
                        <Chip size="small" color="success" label="Completa" />
                      ) : (
                        <Chip
                          size="small"
                          color="warning"
                          label={`Faltan ${h.tubosPendientes?.length ?? '?'}`}
                        />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
};

export default RecepcionMuestrasPage;
