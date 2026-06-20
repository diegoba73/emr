import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Tabs,
  Tab,
  Box,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import { getSectores, createSector, createCama } from '../../services/internacion';
import { Sector } from '../../types';
import toast from 'react-hot-toast';

interface ModalCrearCamaProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface CamaFormData {
  nombre: string;
  sector: number | undefined;
  aislada: boolean;
}

interface SectorFormData {
  nombre: string;
}

const ModalCrearCama: React.FC<ModalCrearCamaProps> = ({ open, onClose, onSuccess }) => {
  const [tabValue, setTabValue] = useState(0);
  const [sectores, setSectores] = useState<Sector[]>([]);
  const [loadingSectores, setLoadingSectores] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    control: controlCama,
    handleSubmit: handleSubmitCama,
    reset: resetCama,
    formState: { errors: errorsCama },
  } = useForm<CamaFormData>({
    defaultValues: {
      nombre: '',
      sector: undefined as any, // Inicializar sin valor para evitar warning de MUI
      aislada: false,
    },
  });

  const {
    control: controlSector,
    handleSubmit: handleSubmitSector,
    reset: resetSector,
    formState: { errors: errorsSector },
  } = useForm<SectorFormData>({
    defaultValues: {
      nombre: '',
    },
  });

  // Cargar sectores al abrir el modal
  useEffect(() => {
    if (open) {
      loadSectores();
    }
  }, [open]);

  const loadSectores = async () => {
    setLoadingSectores(true);
    try {
      const data = await getSectores();
      setSectores(data);
    } catch (err: any) {
      console.error('Error loading sectores:', err);
      toast.error('Error al cargar sectores');
    } finally {
      setLoadingSectores(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError(null);
    resetCama({ nombre: '', sector: 0, aislada: false });
    resetSector();
  };

  const onSubmitCama = async (data: CamaFormData) => {
    if (!data.sector || data.sector === 0) {
      setError('Debe seleccionar un sector');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await createCama({
        nombre: data.nombre.trim(),
        sector: data.sector,
        estado: 'DISPONIBLE',
        aislada: data.aislada,
      });
      toast.success('Cama creada exitosamente');
      resetCama();
      onSuccess();
      onClose();
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.response?.data?.detail || err.message || 'Error al crear la cama';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const onSubmitSector = async (data: SectorFormData) => {
    setLoading(true);
    setError(null);

    try {
      await createSector({
        nombre: data.nombre.trim(),
      });
      toast.success('Sector creado exitosamente');
      resetSector();
      // Recargar sectores para que aparezca en el select de camas
      await loadSectores();
      // Cambiar a la pestaña de camas para que el usuario pueda crear una cama en el nuevo sector
      setTabValue(0);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.response?.data?.detail || err.message || 'Error al crear el sector';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setTabValue(0);
    setError(null);
    resetCama({ nombre: '', sector: 0, aislada: false });
    resetSector();
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Administrar Infraestructura</DialogTitle>
      <DialogContent>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Nueva Cama" />
            <Tab label="Nuevo Sector" />
          </Tabs>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Tab: Nueva Cama */}
        {tabValue === 0 && (
          <Box component="form" onSubmit={handleSubmitCama(onSubmitCama)}>
            <FormControl fullWidth margin="normal" error={!!errorsCama.sector}>
              <InputLabel id="sector-label">Sector *</InputLabel>
              <Controller
                name="sector"
                control={controlCama}
                rules={{ required: 'El sector es obligatorio' }}
                render={({ field }) => (
                  <Select
                    {...field}
                    value={field.value || ''}
                    labelId="sector-label"
                    label="Sector *"
                    disabled={loadingSectores}
                  >
                    {loadingSectores ? (
                      <MenuItem disabled>
                        <CircularProgress size={20} sx={{ mr: 1 }} />
                        Cargando sectores...
                      </MenuItem>
                    ) : sectores.length === 0 ? (
                      <MenuItem disabled>No hay sectores disponibles</MenuItem>
                    ) : (
                      sectores.map((sector) => (
                        <MenuItem key={sector.id} value={sector.id}>
                          {sector.nombre}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                )}
              />
              {errorsCama.sector && (
                <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                  {errorsCama.sector.message}
                </Box>
              )}
            </FormControl>

            <Controller
              name="nombre"
              control={controlCama}
              rules={{
                required: 'El nombre de la cama es obligatorio',
                minLength: {
                  value: 2,
                  message: 'El nombre debe tener al menos 2 caracteres',
                },
              }}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  margin="normal"
                  label="Nombre de la Cama *"
                  error={!!errorsCama.nombre}
                  helperText={errorsCama.nombre?.message}
                />
              )}
            />

            <Controller
              name="aislada"
              control={controlCama}
              render={({ field }) => (
                <FormControlLabel
                  control={<Switch {...field} checked={field.value} />}
                  label="Cama Aislada"
                  sx={{ mt: 2 }}
                />
              )}
            />
          </Box>
        )}

        {/* Tab: Nuevo Sector */}
        {tabValue === 1 && (
          <Box component="form" onSubmit={handleSubmitSector(onSubmitSector)}>
            <Controller
              name="nombre"
              control={controlSector}
              rules={{
                required: 'El nombre del sector es obligatorio',
                minLength: {
                  value: 2,
                  message: 'El nombre debe tener al menos 2 caracteres',
                },
              }}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  margin="normal"
                  label="Nombre del Sector *"
                  error={!!errorsSector.nombre}
                  helperText={errorsSector.nombre?.message}
                  autoFocus
                />
              )}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          onClick={tabValue === 0 ? handleSubmitCama(onSubmitCama) : handleSubmitSector(onSubmitSector)}
          variant="contained"
          disabled={loading || loadingSectores}
        >
          {loading ? <CircularProgress size={20} /> : tabValue === 0 ? 'Crear Cama' : 'Crear Sector'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalCrearCama;

