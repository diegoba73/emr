import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material';
import SlotPickerStaff from './SlotPickerStaff';
import type { SlotMedico, TipoAgenda } from '../../services/agendaMedica';
import { formatLocalDateTimeSeconds } from '../../utils/formatLocalDateTime';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

export interface ReprogramarTurnoDialogProps {
  open: boolean;
  onClose: () => void;
  medicoId: number | null;
  turnoId: number;
  /** CONSULTA por defecto; ESTUDIO para turnos de pedido de estudio. */
  tipoAgenda?: TipoAgenda;
  onConfirm: (payload: {
    fecha_hora_inicio: string;
    fecha_hora_fin: string;
    motivo: string;
    recurso_id?: number;
  }) => Promise<void>;
}

/**
 * Reprogramar consulta: 1) elegir horario libre del médico → 2) motivo → confirmar.
 * Sin prompt de WhatsApp.
 */
const ReprogramarTurnoDialog: React.FC<ReprogramarTurnoDialogProps> = ({
  open,
  onClose,
  medicoId,
  turnoId: _turnoId,
  tipoAgenda = 'CONSULTA',
  onConfirm,
}) => {
  const [slot, setSlot] = useState<SlotMedico | null>(null);
  const [motivo, setMotivo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setSlot(null);
    setMotivo('');
    setError(null);
    setLoading(false);
  }, [open, medicoId]);

  const handleConfirm = async () => {
    if (!slot) {
      setError('Elegí el nuevo horario libre del médico.');
      return;
    }
    const trimmed = motivo.trim();
    if (!trimmed) {
      setError('El motivo de reprogramación es obligatorio.');
      return;
    }
    const inicio = new Date(slot.inicio);
    const fin = new Date(slot.fin || inicio.getTime() + (slot.duracion_min || 20) * 60_000);
    setLoading(true);
    setError(null);
    try {
      await onConfirm({
        fecha_hora_inicio: formatLocalDateTimeSeconds(inicio),
        fecha_hora_fin: formatLocalDateTimeSeconds(fin),
        motivo: trimmed,
        recurso_id: slot.recurso_id || undefined,
      });
      onClose();
    } catch (e: unknown) {
      setError(
        getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.turnoReprogramar)
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Reprogramar turno</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Elegí un horario libre de la agenda del médico y luego indicá el motivo.
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 2, mb: 2 }}>
          <SlotPickerStaff
            medicoId={medicoId}
            tipo={tipoAgenda}
            value={slot}
            onChange={setSlot}
            disabled={loading}
          />
        </Box>
        {slot?.recurso_nombre && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
            {tipoAgenda === 'ESTUDIO' ? 'Sala' : 'Consultorio'}: {slot.recurso_nombre}
          </Typography>
        )}
        <TextField
          fullWidth
          multiline
          minRows={3}
          label="Motivo de reprogramación (obligatorio)"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          disabled={loading}
          required
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={loading || !slot || !motivo.trim()}
        >
          {loading ? 'Reprogramando…' : 'Reprogramar'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ReprogramarTurnoDialog;
