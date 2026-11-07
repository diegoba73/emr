import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { accionLlegada, getTableroRecepcion } from '../services/recepcionApi';
import type { LlegadaRecepcion } from '../types/recepcion';
import { getSafeClinicalActionMessage } from '../utils/apiError';
import { formatHoraDisplay } from '../utils/dateFieldFormat';
import { apiService } from '../services/api';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';
import { useData } from '../contexts/DataContext';

function fechaHoyLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const horaTurno = (iso?: string | null) => {
  if (!iso) return '—';
  try {
    return formatHoraDisplay(new Date(iso)) || '—';
  } catch {
    return '—';
  }
};

const ESTADOS_COLA = ['EN_ESPERA_RECEPCION', 'EN_ESPERA', 'LLAMADO', 'EN_ATENCION'] as const;

/**
 * Cola del médico: pacientes aceptados en recepción → Llamar (TV + push app).
 * «En atención» inicia/abre la consulta clínica del turno.
 */
const MedicoCola: React.FC = () => {
  const { currentUser } = useData();
  const [llegadas, setLlegadas] = useState<LlegadaRecepcion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [atencionId, setAtencionId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const fecha = fechaHoyLocal();

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await getTableroRecepcion(fecha, null);
      const activas = (data.llegadas || [])
        .filter((l) => (ESTADOS_COLA as readonly string[]).includes(l.estado_flujo))
        .sort((a, b) => {
          const ta = a.turno_inicio
            ? new Date(a.turno_inicio).getTime()
            : Number.MAX_SAFE_INTEGER;
          const tb = b.turno_inicio
            ? new Date(b.turno_inicio).getTime()
            : Number.MAX_SAFE_INTEGER;
          if (ta !== tb) return ta - tb;
          return (a.id || 0) - (b.id || 0);
        });
      setLlegadas(activas);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo cargar tu cola.'));
    } finally {
      setLoading(false);
    }
  }, [fecha]);

  useEffect(() => {
    setLoading(true);
    void load();
    const id = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(id);
  }, [load]);

  const abrirConsultaDesdeLlegada = async (l: LlegadaRecepcion) => {
    if (!l.turno) {
      throw new Error('Esta llegada no tiene turno; no se puede abrir la consulta.');
    }
    const result = await apiService.iniciarAtencionTurno(l.turno);
    const id = result.atencion?.id;
    if (!id) {
      throw new Error('No se obtuvo la atención clínica del turno.');
    }
    setAtencionId(id);
    setDrawerOpen(true);
  };

  const onAccion = async (
    l: LlegadaRecepcion,
    accion: 'llamar' | 'en-atencion' | 'atendido' | 'no-asistio'
  ) => {
    setBusyId(l.id);
    try {
      if (accion === 'en-atencion') {
        if (l.estado_flujo !== 'EN_ATENCION') {
          await accionLlegada(l.id, 'en-atencion');
        }
        await abrirConsultaDesdeLlegada(l);
        await load();
        return;
      }
      await accionLlegada(l.id, accion);
      await load();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo completar la acción.'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Box sx={{ p: 2 }} data-demo="page-medico-cola">
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          Mis pacientes en espera
        </Typography>
        <Button variant="outlined" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        Cola ordenada por hora de turno. Si el paciente del horario no llegó, podés atender a quien
        llegó anticipado. <strong>Llamar</strong>: TV + aviso en la app.{' '}
        <strong>En atención</strong>: abre la consulta.
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading && llegadas.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Hora turno</TableCell>
                <TableCell>Paciente</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Destino</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell align="right" sx={{ minWidth: 280 }}>
                  Acciones
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {llegadas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography color="text.secondary">
                      Nadie en espera de <strong>tus</strong> turnos. Si secretaría ya hizo
                      check-in y no aparece, el turno puede estar cargado con otro perfil de
                      médico (homónimo). En recepción mirá la columna «Médico / destino».
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                llegadas.map((l) => {
                  const busy = busyId === l.id;
                  const puedeLlamar = [
                    'EN_ESPERA_RECEPCION',
                    'EN_ESPERA',
                    'LLAMADO',
                  ].includes(l.estado_flujo);
                  return (
                    <TableRow key={l.id} hover selected={l.estado_flujo === 'LLAMADO'}>
                      <TableCell>{l.numero_orden_dia ?? '—'}</TableCell>
                      <TableCell>{horaTurno(l.turno_inicio)}</TableCell>
                      <TableCell>
                        <Typography fontWeight={600}>{l.paciente_nombre}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          DNI {l.paciente_dni || '—'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={l.tipo_actividad || '—'} />
                      </TableCell>
                      <TableCell>{l.destino || l.destino_label || '—'}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={
                            l.estado_flujo === 'LLAMADO'
                              ? 'primary'
                              : l.estado_flujo === 'EN_ATENCION'
                                ? 'success'
                                : 'info'
                          }
                          label={l.estado_flujo.replace(/_/g, ' ')}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Stack
                          direction="row"
                          spacing={1}
                          useFlexGap
                          flexWrap="wrap"
                          justifyContent="flex-end"
                        >
                          {puedeLlamar && (
                            <Button
                              size="medium"
                              variant="contained"
                              color="primary"
                              disabled={busy}
                              onClick={() => void onAccion(l, 'llamar')}
                            >
                              Llamar
                            </Button>
                          )}
                          {(l.estado_flujo === 'LLAMADO' || l.estado_flujo === 'EN_ATENCION') && (
                            <Button
                              size="medium"
                              variant="outlined"
                              disabled={busy}
                              onClick={() => void onAccion(l, 'en-atencion')}
                            >
                              {l.estado_flujo === 'EN_ATENCION' ? 'Abrir consulta' : 'En atención'}
                            </Button>
                          )}
                          {['LLAMADO', 'EN_ATENCION'].includes(l.estado_flujo) && (
                            <Button
                              size="medium"
                              variant="contained"
                              color="success"
                              disabled={busy}
                              onClick={() => void onAccion(l, 'atendido')}
                            >
                              Atendido
                            </Button>
                          )}
                          <Button
                            size="medium"
                            color="error"
                            variant="text"
                            disabled={busy}
                            onClick={() => void onAccion(l, 'no-asistio')}
                          >
                            No asistió
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <AtencionDetailDrawer
        atencionId={atencionId}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setAtencionId(null);
          void load();
        }}
        currentUser={currentUser}
        forceEdit
        initialTab="detalle"
        onIntervencionSaved={async () => {
          await load();
        }}
      />
    </Box>
  );
};

export default MedicoCola;
