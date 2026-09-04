import React, { useEffect, useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import {
  ESTADOS_OBRA_SOCIAL,
  normalizeEstadoObraSocial,
  type EstadoObraSocialLims,
} from '../../utils/limsObraSocial';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

export interface EstadoObraSocialDialogProps {
  open: boolean;
  numero?: string | null;
  value?: string | null;
  saving?: boolean;
  onClose: () => void;
  onSave: (estado: EstadoObraSocialLims) => Promise<void>;
}

const EstadoObraSocialDialog: React.FC<EstadoObraSocialDialogProps> = ({
  open,
  numero,
  value,
  saving = false,
  onClose,
  onSave,
}) => {
  const [estado, setEstado] = useState<EstadoObraSocialLims>('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) setEstado(normalizeEstadoObraSocial(value));
  }, [open, value]);

  const handleSave = async () => {
    setBusy(true);
    try {
      await onSave(estado);
      toast.success('Estado de obra social actualizado.');
      onClose();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
    } finally {
      setBusy(false);
    }
  };

  const working = busy || saving;

  return (
    <Dialog open={open} onClose={working ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        Obra social{numero ? ` — ${numero}` : ''}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Situación de cobertura de esta orden analítica. Se puede cargar con la orden pendiente o
          ya en proceso.
        </Typography>
        <FormControl>
          <RadioGroup
            value={estado}
            onChange={(e) => setEstado(e.target.value as EstadoObraSocialLims)}
          >
            <FormControlLabel value="" control={<Radio />} label="Sin cargar" />
            {ESTADOS_OBRA_SOCIAL.map((opt) => (
              <FormControlLabel
                key={opt.value}
                value={opt.value}
                control={<Radio />}
                label={opt.label}
              />
            ))}
          </RadioGroup>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={working}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={() => void handleSave()} disabled={working}>
          {working ? 'Guardando…' : 'Guardar'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EstadoObraSocialDialog;
