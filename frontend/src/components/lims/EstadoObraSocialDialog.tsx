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
  TextField,
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
  monto?: string | number | null;
  saving?: boolean;
  onClose: () => void;
  onSave: (estado: EstadoObraSocialLims, monto: number | null) => Promise<void>;
}

function montoToInput(monto?: string | number | null): string {
  if (monto === null || monto === undefined || monto === '') return '';
  return String(monto);
}

function parseMontoInput(raw: string): number | null {
  const texto = raw.trim().replace(',', '.');
  if (!texto) return null;
  const n = Number(texto);
  if (!Number.isFinite(n) || n < 0) {
    throw new Error('Monto inválido');
  }
  return Math.round(n * 100) / 100;
}

const EstadoObraSocialDialog: React.FC<EstadoObraSocialDialogProps> = ({
  open,
  numero,
  value,
  monto,
  saving = false,
  onClose,
  onSave,
}) => {
  const [estado, setEstado] = useState<EstadoObraSocialLims>('');
  const [montoTexto, setMontoTexto] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setEstado(normalizeEstadoObraSocial(value));
      setMontoTexto(montoToInput(monto));
    }
  }, [open, value, monto]);

  const handleSave = async () => {
    setBusy(true);
    try {
      let montoValor: number | null = null;
      if (estado === 'DEBE_ABONAR') {
        try {
          montoValor = parseMontoInput(montoTexto);
        } catch {
          toast.error('Ingresá un monto válido (opcional) o dejalo vacío.');
          return;
        }
      }
      await onSave(estado, montoValor);
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
        {estado === 'DEBE_ABONAR' ? (
          <TextField
            sx={{ mt: 2 }}
            fullWidth
            size="small"
            label="Monto a abonar (opcional)"
            value={montoTexto}
            onChange={(e) => setMontoTexto(e.target.value)}
            placeholder="Ej: 1500.50"
            inputProps={{ inputMode: 'decimal' }}
            helperText="Para que recepción sepa cuánto cobrarle al paciente."
          />
        ) : null}
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
