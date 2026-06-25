import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Box,
  Typography,
} from '@mui/material';
import { Cama } from '../../types';
import { updateCama } from '../../services/apiService';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

interface ModalGestionarCamaProps {
  open: boolean;
  onClose: () => void;
  cama: Cama | null;
  onSuccess: () => void;
}

const ModalGestionarCama: React.FC<ModalGestionarCamaProps> = ({
  open,
  onClose,
  cama,
  onSuccess,
}) => {
  const [estado, setEstado] = useState<'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO'>(
    (cama?.estado as 'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO') || 'DISPONIBLE'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (cama) {
      setEstado(cama.estado as 'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO');
    }
  }, [cama]);

  const handleSubmit = async () => {
    if (!cama) return;

    if (estado === cama.estado) {
      onClose();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await updateCama(cama.id, { estado });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.camaActualizar));
    } finally {
      setLoading(false);
    }
  };

  const getEstadoOptions = () => {
    if (!cama) return [];
    
    // Si está en LIMPIEZA, puede pasar a DISPONIBLE o MANTENIMIENTO
    if (cama.estado === 'LIMPIEZA') {
      return [
        { value: 'DISPONIBLE', label: 'Disponible' },
        { value: 'MANTENIMIENTO', label: 'En Mantenimiento' },
      ];
    }
    
    // Si está en MANTENIMIENTO, puede pasar a DISPONIBLE o LIMPIEZA
    if (cama.estado === 'MANTENIMIENTO') {
      return [
        { value: 'DISPONIBLE', label: 'Disponible' },
        { value: 'LIMPIEZA', label: 'En Limpieza' },
      ];
    }
    
    // Si está disponible, puede pasar a LIMPIEZA o MANTENIMIENTO
    if (cama.estado === 'DISPONIBLE') {
      return [
        { value: 'LIMPIEZA', label: 'En Limpieza' },
        { value: 'MANTENIMIENTO', label: 'En Mantenimiento' },
      ];
    }
    
    return [];
  };

  if (!cama) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Gestionar Estado - {cama.nombre} ({typeof cama.sector === 'object' ? cama.sector.nombre : cama.sector_nombre || 'N/A'})
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Estado actual: <strong>{cama.estado}</strong>
          </Typography>

          <FormControl fullWidth>
            <InputLabel>Nuevo Estado</InputLabel>
            <Select
              value={estado}
              onChange={(e) => setEstado(e.target.value as 'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO')}
              label="Nuevo Estado"
            >
              {getEstadoOptions().map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || estado === cama.estado}
        >
          {loading ? <CircularProgress size={20} /> : 'Actualizar Estado'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalGestionarCama;

