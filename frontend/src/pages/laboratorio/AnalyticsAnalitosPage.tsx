import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
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
import { useNavigate } from 'react-router-dom';
import { getAnalyticsAnalitos, type AnalyticsAnalitosResponse } from '../../services/limsApi';
import { useData } from '../../contexts/DataContext';
import { canAccessLimsModule } from '../../utils/limsAccess';

const DEFAULT_HASTA = '2026-09-29';

const AnalyticsAnalitosPage: React.FC = () => {
  const { currentUser } = useData();
  const navigate = useNavigate();
  const allowed = canAccessLimsModule(currentUser);

  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState(DEFAULT_HASTA);
  const [codigo, setCodigo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyticsAnalitosResponse | null>(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAnalyticsAnalitos({
        desde: desde || undefined,
        hasta: hasta || DEFAULT_HASTA,
        codigo: codigo || undefined,
        histograma: false,
      });
      setData(res);
    } catch {
      setError('No se pudo cargar la analítica.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [codigo, desde, hasta]);

  useEffect(() => {
    if (!allowed) return;
    void cargar();
  }, [allowed, cargar]);

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">Solo operadores LIMS.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/ordenes')} sx={{ mb: 1 }}>
        ← Órdenes LIMS
      </Button>
      <Typography variant="h5" gutterBottom>
        Analítica de resultados (agregados)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Conteos y percentiles por analito, sin datos de paciente. Por defecto hasta{' '}
        {DEFAULT_HASTA} (histórico importado LabWin). Solo lectura.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        <TextField
          size="small"
          label="Desde"
          type="date"
          InputLabelProps={{ shrink: true }}
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
        />
        <TextField
          size="small"
          label="Hasta"
          type="date"
          InputLabelProps={{ shrink: true }}
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
        />
        <TextField
          size="small"
          label="Código"
          placeholder="UREA"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value.toUpperCase())}
        />
        <Button variant="contained" onClick={() => void cargar()} disabled={loading}>
          {loading ? <CircularProgress size={18} /> : 'Actualizar'}
        </Button>
      </Paper>

      {error ? <Alert severity="warning">{error}</Alert> : null}

      {data ? (
        <>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Ventana {data.desde || '…'} → {data.hasta} · {data.total_resultados} resultados en
            tabla
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Código</TableCell>
                  <TableCell>Nombre</TableCell>
                  <TableCell align="right">N</TableCell>
                  <TableCell align="right">LabWin</TableCell>
                  <TableCell align="right">Nativo</TableCell>
                  <TableCell align="right">% fuera rango</TableCell>
                  <TableCell align="right">% crítico</TableCell>
                  <TableCell align="right">Mediana</TableCell>
                  <TableCell align="right">P25</TableCell>
                  <TableCell align="right">P75</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(data.analitos || []).map((a) => (
                  <TableRow key={a.codigo}>
                    <TableCell>{a.codigo}</TableCell>
                    <TableCell>{a.nombre}</TableCell>
                    <TableCell align="right">{a.n}</TableCell>
                    <TableCell align="right">{a.n_labwin}</TableCell>
                    <TableCell align="right">{a.n_nativo}</TableCell>
                    <TableCell align="right">{a.pct_fuera_rango}</TableCell>
                    <TableCell align="right">{a.pct_critico}</TableCell>
                    <TableCell align="right">{a.mediana ?? '—'}</TableCell>
                    <TableCell align="right">{a.p25 ?? '—'}</TableCell>
                    <TableCell align="right">{a.p75 ?? '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : null}
    </Box>
  );
};

export default AnalyticsAnalitosPage;
