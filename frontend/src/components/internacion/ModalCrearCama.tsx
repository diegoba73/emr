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
  Typography,
  Chip,
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import {
  getSectores,
  getCamas,
  createSector,
  createCama,
  updateCama,
  deleteCama,
} from '../../services/internacion';
import { Sector, Cama } from '../../types';
import toast from 'react-hot-toast';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

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

interface EditarCamaFormData {
  camaId: number | undefined;
  nombre: string;
  sector: number | undefined;
  aislada: boolean;
  estado: Cama['estado'];
}

const getSectorNombre = (cama: Cama): string => {
  if (typeof cama.sector === 'object') {
    return cama.sector.nombre;
  }
  return cama.sector_nombre || '';
};

const getSectorId = (cama: Cama): number | undefined => {
  if (typeof cama.sector === 'object') {
    return cama.sector.id;
  }
  return typeof cama.sector === 'number' ? cama.sector : undefined;
};

const ModalCrearCama: React.FC<ModalCrearCamaProps> = ({ open, onClose, onSuccess }) => {
  const [tabValue, setTabValue] = useState(0);
  const [sectores, setSectores] = useState<Sector[]>([]);
  const [camas, setCamas] = useState<Cama[]>([]);
  const [loadingSectores, setLoadingSectores] = useState(false);
  const [loadingCamas, setLoadingCamas] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [camaSeleccionada, setCamaSeleccionada] = useState<Cama | null>(null);

  const {
    control: controlCama,
    handleSubmit: handleSubmitCama,
    reset: resetCama,
    formState: { errors: errorsCama },
  } = useForm<CamaFormData>({
    defaultValues: {
      nombre: '',
      sector: undefined as any,
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

  const {
    control: controlEditar,
    handleSubmit: handleSubmitEditar,
    reset: resetEditar,
    formState: { errors: errorsEditar },
  } = useForm<EditarCamaFormData>({
    defaultValues: {
      camaId: undefined,
      nombre: '',
      sector: undefined,
      aislada: false,
      estado: 'DISPONIBLE',
    },
  });

  useEffect(() => {
    if (open) {
      loadSectores();
      loadCamas();
    }
  }, [open]);

  const loadSectores = async () => {
    setLoadingSectores(true);
    try {
      const data = await getSectores();
      setSectores(data);
    } catch {
      toast.error('Error al cargar sectores');
    } finally {
      setLoadingSectores(false);
    }
  };

  const loadCamas = async () => {
    setLoadingCamas(true);
    try {
      const data = await getCamas();
      setCamas(
        [...data].sort((a, b) => {
          const sectorCompare = getSectorNombre(a).localeCompare(getSectorNombre(b));
          return sectorCompare !== 0 ? sectorCompare : a.nombre.localeCompare(b.nombre);
        })
      );
    } catch {
      toast.error('Error al cargar camas');
    } finally {
      setLoadingCamas(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError(null);
    resetCama({ nombre: '', sector: undefined, aislada: false });
    resetSector();
    resetEditar({
      camaId: undefined,
      nombre: '',
      sector: undefined,
      aislada: false,
      estado: 'DISPONIBLE',
    });
    setCamaSeleccionada(null);
  };

  const handleCamaSelect = (camaId: number) => {
    const cama = camas.find((c) => c.id === camaId);
    if (!cama) return;

    setCamaSeleccionada(cama);
    resetEditar({
      camaId: cama.id,
      nombre: cama.nombre,
      sector: getSectorId(cama),
      aislada: cama.aislada,
      estado: cama.estado,
    });
  };

  const onSubmitCama = async (data: CamaFormData) => {
    if (!data.sector) {
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
      resetCama({ nombre: '', sector: undefined, aislada: false });
      await loadCamas();
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const errorMessage = getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.camaCrear);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const onSubmitEditar = async (data: EditarCamaFormData) => {
    if (!data.camaId || !camaSeleccionada) {
      setError('Debe seleccionar una cama');
      return;
    }

    if (!data.nombre.trim()) {
      setError('El nombre de la cama es obligatorio');
      return;
    }

    const esOcupada = camaSeleccionada.estado === 'OCUPADA';

    if (!esOcupada && !data.sector) {
      setError('Debe seleccionar un sector');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const updateData: Parameters<typeof updateCama>[1] = {
        nombre: data.nombre.trim(),
        aislada: data.aislada,
      };

      if (!esOcupada) {
        updateData.sector = data.sector;
        updateData.estado = data.estado;
      }

      await updateCama(data.camaId, updateData);
      toast.success('Cama actualizada exitosamente');
      await loadCamas();
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const errorMessage = getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.camaActualizar);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleEliminarCama = async () => {
    if (!camaSeleccionada) return;

    if (camaSeleccionada.estado !== 'DISPONIBLE') {
      setError('Solo se pueden eliminar camas en estado DISPONIBLE');
      return;
    }

    if (!window.confirm(`¿Eliminar la cama "${camaSeleccionada.nombre}"?`)) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await deleteCama(camaSeleccionada.id);
      toast.success('Cama eliminada exitosamente');
      resetEditar({
        camaId: undefined,
        nombre: '',
        sector: undefined,
        aislada: false,
        estado: 'DISPONIBLE',
      });
      setCamaSeleccionada(null);
      await loadCamas();
      onSuccess();
    } catch (err: unknown) {
      const errorMessage = getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.camaActualizar);
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
      await loadSectores();
      setTabValue(0);
    } catch (err: unknown) {
      const errorMessage = getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.sectorCrear);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setTabValue(0);
    setError(null);
    resetCama({ nombre: '', sector: undefined, aislada: false });
    resetSector();
    resetEditar({
      camaId: undefined,
      nombre: '',
      sector: undefined,
      aislada: false,
      estado: 'DISPONIBLE',
    });
    setCamaSeleccionada(null);
    onClose();
  };

  const esCamaOcupada = camaSeleccionada?.estado === 'OCUPADA';

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Administrar Infraestructura</DialogTitle>
      <DialogContent>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Nueva Cama" />
            <Tab label="Editar Cama" />
            <Tab label="Nuevo Sector" />
          </Tabs>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

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

        {tabValue === 1 && (
          <Box component="form" onSubmit={handleSubmitEditar(onSubmitEditar)}>
            <FormControl fullWidth margin="normal" error={!!errorsEditar.camaId}>
              <InputLabel id="cama-edit-label">Cama *</InputLabel>
              <Controller
                name="camaId"
                control={controlEditar}
                rules={{ required: 'Debe seleccionar una cama' }}
                render={({ field }) => (
                  <Select
                    {...field}
                    value={field.value || ''}
                    labelId="cama-edit-label"
                    label="Cama *"
                    disabled={loadingCamas}
                    onChange={(e) => {
                      const value = Number(e.target.value);
                      field.onChange(value);
                      handleCamaSelect(value);
                    }}
                  >
                    {loadingCamas ? (
                      <MenuItem disabled>
                        <CircularProgress size={20} sx={{ mr: 1 }} />
                        Cargando camas...
                      </MenuItem>
                    ) : camas.length === 0 ? (
                      <MenuItem disabled>No hay camas registradas</MenuItem>
                    ) : (
                      camas.map((cama) => (
                        <MenuItem key={cama.id} value={cama.id}>
                          {getSectorNombre(cama)} — {cama.nombre} ({cama.estado})
                        </MenuItem>
                      ))
                    )}
                  </Select>
                )}
              />
              {errorsEditar.camaId && (
                <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                  {errorsEditar.camaId.message}
                </Box>
              )}
            </FormControl>

            {camaSeleccionada && (
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Estado actual:
                  </Typography>
                  <Chip label={camaSeleccionada.estado} size="small" />
                </Box>

                {esCamaOcupada && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Cama ocupada: solo podés editar el nombre y si es aislada. Para cambiar sector o
                    estado, gestioná la internación del paciente.
                  </Alert>
                )}

                <Controller
                  name="nombre"
                  control={controlEditar}
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
                      error={!!errorsEditar.nombre}
                      helperText={errorsEditar.nombre?.message}
                    />
                  )}
                />

                <FormControl fullWidth margin="normal" error={!!errorsEditar.sector}>
                  <InputLabel id="sector-edit-label">Sector *</InputLabel>
                  <Controller
                    name="sector"
                    control={controlEditar}
                    rules={{ required: esCamaOcupada ? false : 'El sector es obligatorio' }}
                    render={({ field }) => (
                      <Select
                        {...field}
                        value={field.value || ''}
                        labelId="sector-edit-label"
                        label="Sector *"
                        disabled={loadingSectores || esCamaOcupada}
                      >
                        {sectores.map((sector) => (
                          <MenuItem key={sector.id} value={sector.id}>
                            {sector.nombre}
                          </MenuItem>
                        ))}
                      </Select>
                    )}
                  />
                </FormControl>

                <FormControl fullWidth margin="normal">
                  <InputLabel id="estado-edit-label">Estado</InputLabel>
                  <Controller
                    name="estado"
                    control={controlEditar}
                    render={({ field }) => (
                      <Select
                        {...field}
                        labelId="estado-edit-label"
                        label="Estado"
                        disabled={esCamaOcupada}
                      >
                        <MenuItem value="DISPONIBLE">Disponible</MenuItem>
                        <MenuItem value="LIMPIEZA">En Limpieza</MenuItem>
                        <MenuItem value="MANTENIMIENTO">En Mantenimiento</MenuItem>
                      </Select>
                    )}
                  />
                </FormControl>

                <Controller
                  name="aislada"
                  control={controlEditar}
                  render={({ field }) => (
                    <FormControlLabel
                      control={<Switch {...field} checked={field.value} />}
                      label="Cama Aislada"
                      sx={{ mt: 2 }}
                    />
                  )}
                />

                {camaSeleccionada.estado === 'DISPONIBLE' && (
                  <Box sx={{ mt: 2 }}>
                    <Button
                      color="error"
                      variant="outlined"
                      onClick={handleEliminarCama}
                      disabled={loading}
                    >
                      Eliminar cama
                    </Button>
                  </Box>
                )}
              </>
            )}
          </Box>
        )}

        {tabValue === 2 && (
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
        {tabValue === 1 ? (
          <Button
            onClick={handleSubmitEditar(onSubmitEditar)}
            variant="contained"
            disabled={loading || loadingCamas || !camaSeleccionada}
          >
            {loading ? <CircularProgress size={20} /> : 'Guardar cambios'}
          </Button>
        ) : (
          <Button
            onClick={tabValue === 0 ? handleSubmitCama(onSubmitCama) : handleSubmitSector(onSubmitSector)}
            variant="contained"
            disabled={loading || loadingSectores}
          >
            {loading ? (
              <CircularProgress size={20} />
            ) : tabValue === 0 ? (
              'Crear Cama'
            ) : (
              'Crear Sector'
            )}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ModalCrearCama;
