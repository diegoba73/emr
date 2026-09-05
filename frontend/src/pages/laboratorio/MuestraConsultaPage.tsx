import React, { useCallback, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import BarcodeScanInput from '../../components/lims/BarcodeScanInput';
import MuestraEstadoBadge from '../../components/lims/MuestraEstadoBadge';
import { EstudioMicrobiologiaEstadoBadge } from '../../components/lims/micro/MicroBadges';
import { getLabCodigoPorCodigo } from '../../services/limsApi';
import type { EstudioMicrobiologia, MuestraLookupLims } from '../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsModule } from '../../utils/limsAccess';

const formatFecha = (iso?: string | null) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('es-AR');
  } catch {
    return iso;
  }
};

const MuestraConsultaPage: React.FC = () => {
  const { currentUser } = useData();
  const allowed = canAccessLimsModule(currentUser);
  const [loading, setLoading] = useState(false);
  const [muestra, setMuestra] = useState<MuestraLookupLims | null>(null);
  const [estudio, setEstudio] = useState<EstudioMicrobiologia | null>(null);

  const handleScan = useCallback(
    async (codigo: string) => {
      if (!allowed) return;
      setLoading(true);
      try {
        const data = await getLabCodigoPorCodigo(codigo);
        if (data.tipo === 'micro' && data.estudio) {
          setEstudio(data.estudio);
          setMuestra(null);
          toast.success('Pedido de microbiología encontrado');
          return;
        }
        if (data.tipo === 'tubo' && data.muestra) {
          setMuestra(data.muestra);
          setEstudio(null);
          toast.success('Muestra encontrada');
          return;
        }
        setMuestra(null);
        setEstudio(null);
        toast.error('Código no reconocido');
      } catch (e) {
        setMuestra(null);
        setEstudio(null);
        toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarMuestras));
      } finally {
        setLoading(false);
      }
    },
    [allowed]
  );

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tiene permisos para consultar muestras.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, maxWidth: 900, mx: 'auto' }} data-demo="page-muestras">
      <Typography variant="h5" gutterBottom>
        Consulta de muestra
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Escanee el código <strong>LAB-…</strong> (tubo con sufijo <strong>-nn</strong>, o protocolo de
        microbiología). El sistema resuelve si es lab clínico o cultivo.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <BarcodeScanInput
          label="Código de barras"
          onScan={handleScan}
          disabled={loading}
          helperText="El lector USB escribe el código y confirma con Enter"
        />
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <CircularProgress size={28} />
          </Box>
        )}
      </Paper>

      {estudio && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">{estudio.codigo_barra || estudio.numero}</Typography>
            <EstudioMicrobiologiaEstadoBadge estado={estudio.estado} />
            <Chip size="small" label="Microbiología" color="secondary" variant="outlined" />
          </Box>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Pedido:</strong>{' '}
            <Link component={RouterLink} to={`/laboratorio/microbiologia/estudios/${estudio.id}`}>
              {estudio.numero || `#${estudio.id}`}
            </Link>
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Paciente:</strong> {estudio.paciente_nombre || '—'}
            {estudio.paciente_dni ? ` · DNI ${estudio.paciente_dni}` : ''}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Tipo de cultivo:</strong>{' '}
            {estudio.tipo_cultivo_nombre || estudio.tipo_estudio || '—'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Tipo de muestra:</strong>{' '}
            {estudio.tipo_muestra_micro_nombre || estudio.muestra_tipo_nombre || '—'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Código de barras:</strong> {estudio.codigo_barra || '—'}
          </Typography>
          <Typography variant="body2">
            <strong>Inicio / recepción:</strong> {formatFecha(estudio.fecha_inicio)}
          </Typography>
          <Button
            component={RouterLink}
            to={`/laboratorio/microbiologia/estudios/${estudio.id}`}
            variant="outlined"
            size="small"
            sx={{ mt: 2 }}
          >
            Ver pedido de microbiología
          </Button>
        </Paper>
      )}

      {muestra && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">{muestra.codigo_barra}</Typography>
            <MuestraEstadoBadge estado={muestra.estado} />
            <Chip size="small" label="Lab. Clínico" color="primary" variant="outlined" />
          </Box>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Orden:</strong>{' '}
            <Link component={RouterLink} to={`/laboratorio/ordenes/${muestra.solicitud}`}>
              {muestra.solicitud_numero || `#${muestra.solicitud}`}
            </Link>
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Paciente:</strong> {muestra.paciente_nombre || '—'}
            {muestra.paciente_dni ? ` · DNI ${muestra.paciente_dni}` : ''}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Tipo:</strong>{' '}
            {muestra.tipo_muestra_codigo
              ? `${muestra.tipo_muestra_codigo} — ${muestra.tipo_muestra_nombre}`
              : `ID ${muestra.tipo_muestra}`}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Ubicación:</strong> {muestra.ubicacion_actual || '—'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Toma:</strong> {formatFecha(muestra.fecha_toma)}
          </Typography>
          <Typography variant="body2">
            <strong>Recepción:</strong> {formatFecha(muestra.fecha_recepcion)}
          </Typography>
          <Button
            component={RouterLink}
            to={`/laboratorio/ordenes/${muestra.solicitud}`}
            variant="outlined"
            size="small"
            sx={{ mt: 2 }}
          >
            Ver orden completa
          </Button>
        </Paper>
      )}

      {muestra && (muestra.eventos?.length ?? 0) > 0 && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Historial de custodia
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Acción</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Observaciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {muestra.eventos!.map((ev) => (
                  <TableRow key={ev.id}>
                    <TableCell>{formatFecha(ev.fecha)}</TableCell>
                    <TableCell>{ev.accion}</TableCell>
                    <TableCell>
                      {ev.estado_anterior || '—'} → {ev.estado_nuevo || '—'}
                    </TableCell>
                    <TableCell>{ev.observaciones || '—'}</TableCell>
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

export default MuestraConsultaPage;
