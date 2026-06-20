import React, { useState } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { MuestraTransaccional } from '../../types/lims';
import {
  formatDrfError,
  postMuestraCancelar,
  postMuestraConservar,
  postMuestraDescartar,
  postMuestraRecibir,
  postMuestraRechazar,
  postMuestraTomar,
} from '../../services/limsApi';

export interface MuestraAccionesProps {
  muestra: MuestraTransaccional;
  canOperate: boolean;
  onUpdated: () => void;
}

const MuestraAcciones: React.FC<MuestraAccionesProps> = ({ muestra, canOperate, onUpdated }) => {
  const [openRechazar, setOpenRechazar] = useState(false);
  const [motivoRechazo, setMotivoRechazo] = useState('');
  const [openUbicacion, setOpenUbicacion] = useState<'recibir' | 'conservar' | null>(null);
  const [ubicacion, setUbicacion] = useState('');
  const [obsExtra, setObsExtra] = useState('');
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
      toast.success('Muestra actualizada');
      onUpdated();
    } catch (e) {
      toast.error(formatDrfError(e));
    } finally {
      setBusy(false);
    }
  };

  const e = muestra.estado;

  const showTomar = e === 'PENDIENTE_TOMA';
  const showRecibir = e === 'TOMADA';
  const showRechazar = !['RECHAZADA', 'DESCARTADA', 'CANCELADA'].includes(e);
  const showConservar = e === 'RECIBIDA' || e === 'EN_PROCESO';
  const showDescartar = e === 'RECIBIDA' || e === 'CONSERVADA';
  const showCancelar = !['DESCARTADA', 'CANCELADA', 'RECHAZADA'].includes(e);

  if (!canOperate) return null;

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
      <ButtonGroup size="small" variant="outlined">
        {showTomar && (
          <Button
            disabled={busy}
            onClick={() =>
              run(async () => {
                await postMuestraTomar(muestra.id, {});
              })
            }
          >
            Tomar
          </Button>
        )}
        {showRecibir && (
          <Button
            disabled={busy}
            onClick={() => {
              setUbicacion(muestra.ubicacion_actual || '');
              setObsExtra('');
              setOpenUbicacion('recibir');
            }}
          >
            Recibir
          </Button>
        )}
        {showRechazar && (
          <Button disabled={busy} color="warning" onClick={() => setOpenRechazar(true)}>
            Rechazar
          </Button>
        )}
        {showConservar && (
          <Button
            disabled={busy}
            onClick={() => {
              setUbicacion(muestra.ubicacion_actual || '');
              setObsExtra('');
              setOpenUbicacion('conservar');
            }}
          >
            Conservar
          </Button>
        )}
        {showDescartar && (
          <Button
            disabled={busy}
            color="secondary"
            onClick={() =>
              run(async () => {
                await postMuestraDescartar(muestra.id, {});
              })
            }
          >
            Descartar
          </Button>
        )}
        {showCancelar && (
          <Button
            disabled={busy}
            color="error"
            onClick={() =>
              run(async () => {
                await postMuestraCancelar(muestra.id, { motivo: 'Cancelación operativa', observaciones: '' });
              })
            }
          >
            Cancelar
          </Button>
        )}
      </ButtonGroup>

      <Dialog open={openRechazar} onClose={() => !busy && setOpenRechazar(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Rechazar muestra</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Motivo de rechazo (obligatorio)"
            fullWidth
            multiline
            minRows={2}
            value={motivoRechazo}
            onChange={(ev) => setMotivoRechazo(ev.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRechazar(false)} disabled={busy}>
            Cerrar
          </Button>
          <Button
            color="warning"
            disabled={busy || !motivoRechazo.trim()}
            onClick={() =>
              run(async () => {
                await postMuestraRechazar(muestra.id, { motivo_rechazo: motivoRechazo.trim() });
                setOpenRechazar(false);
                setMotivoRechazo('');
              })
            }
          >
            Confirmar rechazo
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openUbicacion !== null} onClose={() => !busy && setOpenUbicacion(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{openUbicacion === 'recibir' ? 'Recibir muestra' : 'Conservar muestra'}</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="Ubicación actual (opcional)"
            fullWidth
            value={ubicacion}
            onChange={(ev) => setUbicacion(ev.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Observaciones (opcional)"
            fullWidth
            multiline
            minRows={2}
            value={obsExtra}
            onChange={(ev) => setObsExtra(ev.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenUbicacion(null)} disabled={busy}>
            Cerrar
          </Button>
          <Button
            disabled={busy}
            variant="contained"
            onClick={() =>
              run(async () => {
                if (openUbicacion === 'recibir') {
                  await postMuestraRecibir(muestra.id, {
                    ubicacion_actual: ubicacion,
                    observaciones: obsExtra,
                  });
                } else if (openUbicacion === 'conservar') {
                  await postMuestraConservar(muestra.id, {
                    ubicacion_actual: ubicacion,
                    observaciones: obsExtra,
                  });
                }
                setOpenUbicacion(null);
              })
            }
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MuestraAcciones;
