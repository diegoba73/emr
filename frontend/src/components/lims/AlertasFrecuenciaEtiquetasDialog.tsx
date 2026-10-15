import React from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import type { AlertaFrecuenciaOrden } from '../../services/limsApi';

export interface AlertasFrecuenciaEtiquetasDialogProps {
  open: boolean;
  numeroOrden?: string | null;
  alertas: AlertaFrecuenciaOrden[];
  onContinuar: () => void;
  onQuitarExamenes: () => void;
  onCancelar: () => void;
}

/**
 * Puerta de revisión al imprimir etiquetas (ambulatorio): lab/bioquímico
 * decide si deja los ensayos con alerta de obra social o los quita.
 */
const AlertasFrecuenciaEtiquetasDialog: React.FC<AlertasFrecuenciaEtiquetasDialogProps> = ({
  open,
  numeroOrden,
  alertas,
  onContinuar,
  onQuitarExamenes,
  onCancelar,
}) => {
  return (
    <Dialog open={open} onClose={onCancelar} fullWidth maxWidth="sm">
      <DialogTitle>
        Revisar frecuencia — {numeroOrden || 'orden'}
      </DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Esta orden ambulatoria incluye determinaciones que la obra social suele
          limitar. Revisá antes de imprimir etiquetas.
        </Alert>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Podés continuar con la impresión o quitar los exámenes en conflicto.
        </Typography>
        <List dense disablePadding>
          {alertas.map((a) => (
            <ListItem key={a.codigo} alignItems="flex-start" sx={{ px: 0 }}>
              <ListItemText
                primary={`${a.nombre} (${a.codigo})`}
                secondary={a.mensaje}
                primaryTypographyProps={{ fontWeight: 600 }}
              />
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1, px: 3, pb: 2 }}>
        <Button onClick={onCancelar}>Cancelar</Button>
        <Button color="warning" variant="outlined" onClick={onQuitarExamenes}>
          Quitar exámenes…
        </Button>
        <Button color="primary" variant="contained" onClick={onContinuar}>
          Continuar e imprimir
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AlertasFrecuenciaEtiquetasDialog;
