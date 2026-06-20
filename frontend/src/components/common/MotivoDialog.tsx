import React, { useCallback, useState } from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from '@mui/material';

export interface MotivoDialogOpenOptions {
  title: string;
  label?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Valor inicial del campo (p. ej. default de window.prompt). */
  initialMotivo?: string;
  /** Por defecto true: motivo obligatorio (mismo criterio que window.prompt previo). */
  required?: boolean;
  onConfirm: (motivo: string) => Promise<void>;
}

export interface MotivoDialogProps {
  open: boolean;
  title: string;
  label: string;
  motivo: string;
  onMotivoChange: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
  error?: string | null;
  confirmLabel?: string;
  cancelLabel?: string;
  required?: boolean;
}

export const MotivoDialog: React.FC<MotivoDialogProps> = ({
  open,
  title,
  label,
  motivo,
  onMotivoChange,
  onClose,
  onConfirm,
  loading = false,
  error = null,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  required = true,
}) => {
  const confirmDisabled = loading || (required && !motivo.trim());

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <TextField
          autoFocus
          fullWidth
          multiline
          minRows={3}
          label={label}
          value={motivo}
          onChange={(e) => onMotivoChange(e.target.value)}
          disabled={loading}
          required={required}
          margin="dense"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button variant="contained" color="primary" onClick={onConfirm} disabled={confirmDisabled}>
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export function useMotivoDialog() {
  const [open, setOpen] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<MotivoDialogOpenOptions | null>(null);

  const openMotivoDialog = useCallback((opts: MotivoDialogOpenOptions) => {
    setOptions(opts);
    setMotivo(opts.initialMotivo ?? '');
    setError(null);
    setLoading(false);
    setOpen(true);
  }, []);

  const closeMotivoDialog = useCallback(() => {
    if (loading) return;
    setOpen(false);
    setMotivo('');
    setError(null);
    setOptions(null);
  }, [loading]);

  const confirmMotivoDialog = useCallback(async () => {
    if (!options) return;
    const trimmed = motivo.trim();
    const required = options.required !== false;
    if (required && !trimmed) return;

    setLoading(true);
    setError(null);
    try {
      await options.onConfirm(trimmed);
      setOpen(false);
      setMotivo('');
      setOptions(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [motivo, options]);

  const dialogProps: MotivoDialogProps = {
    open,
    title: options?.title ?? '',
    label: options?.label ?? 'Motivo',
    motivo,
    onMotivoChange: setMotivo,
    onClose: closeMotivoDialog,
    onConfirm: confirmMotivoDialog,
    loading,
    error,
    confirmLabel: options?.confirmLabel,
    cancelLabel: options?.cancelLabel,
    required: options?.required !== false,
  };

  return { openMotivoDialog, dialogProps };
}
