import React, { useCallback, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  Link,
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
import { Link as RouterLink } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import BarcodeScanInput from '../../components/lims/BarcodeScanInput';
import MuestraEstadoBadge from '../../components/lims/MuestraEstadoBadge';
import { EstudioMicrobiologiaEstadoBadge } from '../../components/lims/micro/MicroBadges';
import { postRecibirLabCodigo } from '../../services/limsApi';
import type { EstudioMicrobiologia, MuestraLookupLims } from '../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canOperateLims } from '../../utils/limsAccess';

interface RecepcionSesionItem {
  codigo: string;
  tipo: 'tubo' | 'micro';
  muestra?: MuestraLookupLims;
  estudio?: EstudioMicrobiologia;
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
        const data = await postRecibirLabCodigo({
          codigo_barra: codigo,
          ubicacion_actual: ubicacion.trim() || 'Laboratorio',
        });

        if (data.tipo === 'micro' && data.estudio) {
          const estudio = data.estudio;
          const item: RecepcionSesionItem = {
            codigo,
            tipo: 'micro',
            estudio,
            recibidaEn: new Date().toISOString(),
            extraccionCompleta: true,
          };
          setUltimoPendientes([]);
          setHistorial((prev) =>
            [item, ...prev.filter((h) => h.codigo !== codigo)].slice(0, MAX_HISTORIAL)
          );
          toast.success(
            `Micro recibida: ${estudio.codigo_barra || estudio.numero || codigo}`
          );
          return;
        }

        if (data.tipo !== 'tubo' || !data.muestra) {
          toast.error('No se pudo interpretar el código recibido.');
          return;
        }

        const muestra = data.muestra;
        const pendientes = data.tubos_pendientes_extraccion || [];
        const item: RecepcionSesionItem = {
          codigo,
          tipo: 'tubo',
          muestra,
          recibidaEn: new Date().toISOString(),
          extraccionCompleta: data.extraccion_completa,
          tubosPendientes: pendientes,
        };
        setUltimoPendientes(pendientes);
        setHistorial((prev) =>
          [item, ...prev.filter((h) => h.codigo !== codigo)].slice(0, MAX_HISTORIAL)
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
        Escaneá tubos <strong>LAB-…-nn</strong> (lab clínico) o etiquetas de microbiología{' '}
        <strong>LAB-…</strong> (mismo número de protocolo). El backend resuelve el tipo; no hace falta
        elegir pantalla.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <TextField
          label="Ubicación de recepción"
          value={ubicacion}
          onChange={(e) => setUbicacion(e.target.value)}
          fullWidth
          margin="normal"
          helperText="Se asigna a tubos de lab clínico (no aplica a microbiología)"
        />
        <BarcodeScanInput
          label="Escanear código LAB-…"
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
                  <TableCell>Tipo</TableCell>
                  <TableCell>Paciente</TableCell>
                  <TableCell>Orden / Pedido</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Completa</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {historial.map((h) => (
                  <TableRow key={`${h.tipo}-${h.codigo}`}>
                    <TableCell>{h.codigo}</TableCell>
                    <TableCell>
                      {h.tipo === 'micro' ? (
                        <Chip size="small" label="Microbiología" color="secondary" variant="outlined" />
                      ) : (
                        <Chip size="small" label="Lab. Clínico" color="primary" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>
                      {h.tipo === 'micro'
                        ? h.estudio?.paciente_nombre || '—'
                        : h.muestra?.paciente_nombre || '—'}
                    </TableCell>
                    <TableCell>
                      {h.tipo === 'micro' && h.estudio ? (
                        <Link
                          component={RouterLink}
                          to={`/laboratorio/microbiologia/estudios/${h.estudio.id}`}
                        >
                          {h.estudio.numero || `#${h.estudio.id}`}
                        </Link>
                      ) : (
                        h.muestra?.solicitud_numero || h.muestra?.solicitud
                      )}
                    </TableCell>
                    <TableCell>
                      {h.tipo === 'micro' && h.estudio ? (
                        <EstudioMicrobiologiaEstadoBadge estado={h.estudio.estado} />
                      ) : h.muestra ? (
                        <MuestraEstadoBadge estado={h.muestra.estado} />
                      ) : null}
                    </TableCell>
                    <TableCell>
                      {h.tipo === 'micro' || h.extraccionCompleta ? (
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
