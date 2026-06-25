import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  TextField,
  Autocomplete,
} from '@mui/material';
import {
  Person as PersonIcon,
  LocalHospital as HospitalIcon,
  CalendarToday as CalendarIcon,
  Description as DescriptionIcon,
  Edit,
  Save,
  Cancel,
} from '@mui/icons-material';
import { Cama, InternacionCama, Paciente, DiagnosticoCIE10 } from '../../types';
import { darAltaInternacion, getInternaciones, updateInternacion, buscarDiagnosticosCIE10 } from '../../services/apiService';
import { apiService } from '../../services/api';
import { useData } from '../../contexts/DataContext';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

interface ModalGestionarPacienteProps {
  open: boolean;
  onClose: () => void;
  cama: Cama | null;
  onSuccess: () => void;
}

const ModalGestionarPaciente: React.FC<ModalGestionarPacienteProps> = ({
  open,
  onClose,
  cama,
  onSuccess,
}) => {
  const { medicos: medicosContext } = useData();
  const [internacion, setInternacion] = useState<InternacionCama | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [confirmAlta, setConfirmAlta] = useState(false);
  
  // Estados para modo edición
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState<{
    paciente: number | null;
    medico: number | null;
    diagnostico_ingreso: string;
    diagnostico_cie_id: number | null;
  }>({
    paciente: null,
    medico: null,
    diagnostico_ingreso: '',
    diagnostico_cie_id: null,
  });
  
  // Estados para búsqueda de pacientes con API
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [pacienteInputValue, setPacienteInputValue] = useState('');
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  const pacienteInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<Paciente | null>(null);
  
  // Estados para búsqueda de diagnósticos CIE-10
  const [diagnosticoOptions, setDiagnosticoOptions] = useState<DiagnosticoCIE10[]>([]);
  const [diagnosticoInputValue, setDiagnosticoInputValue] = useState('');
  const [searchingDiagnosticos, setSearchingDiagnosticos] = useState(false);
  const diagnosticoInputReason = useRef<'input' | 'selection' | 'clear'>('input');

  useEffect(() => {
    if (open && cama?.internacion_actual) {
      loadInternacion();
    } else {
      setInternacion(null);
      setConfirmAlta(false);
      setError(null);
      setSuccessMessage(null);
      setIsEditing(false);
      setDiagnosticoOptions([]);
      setDiagnosticoInputValue('');
      setPacienteOptions([]);
      setPacienteInputValue('');
    }
  }, [open, cama]);
  
  // Búsqueda de pacientes en el servidor (igual que ModalIngresarPaciente)
  useEffect(() => {
    if (!open || !isEditing) {
      setPacienteOptions([]);
      setSearchingPacientes(false);
      return;
    }

    if (pacienteInputReason.current !== 'input') {
      pacienteInputReason.current = 'input';
      return;
    }

    const query = pacienteInputValue.trim();
    if (query.length < 2) {
      setPacienteOptions([]);
      setSearchingPacientes(false);
      return;
    }

    // Debounce optimizado: esperar 200ms para búsquedas más rápidas
    const timeoutId = setTimeout(() => {
      let active = true;
      setSearchingPacientes(true);

      apiService.buscarPacientes(query)
        .then(results => {
          if (!active) return;
          setPacienteOptions(results);
        })
        .catch(error => {
          if (active) {
            setPacienteOptions([]);
          }
        })
        .finally(() => {
          if (active) setSearchingPacientes(false);
        });
    }, 200);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [pacienteInputValue, open, isEditing]);

  // Búsqueda de diagnósticos CIE-10 en el servidor
  useEffect(() => {
    if (!open || !isEditing) {
      setDiagnosticoOptions([]);
      setSearchingDiagnosticos(false);
      return;
    }

    if (diagnosticoInputReason.current !== 'input') {
      diagnosticoInputReason.current = 'input';
      return;
    }

    const query = diagnosticoInputValue.trim();
    if (query.length < 2) {
      setDiagnosticoOptions([]);
      setSearchingDiagnosticos(false);
      return;
    }

    // Debounce: esperar 250ms después de que el usuario deje de escribir
    let active = true;
    const timeoutId = setTimeout(() => {
      setSearchingDiagnosticos(true);

      buscarDiagnosticosCIE10(query)
        .then(results => {
          if (!active) return;
          setDiagnosticoOptions(results);
        })
        .catch(error => {
          if (active) {
            setDiagnosticoOptions([]);
          }
        })
        .finally(() => {
          if (active) setSearchingDiagnosticos(false);
        });
    }, 250);

    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
  }, [diagnosticoInputValue, open, isEditing]);

  // Cargar paciente seleccionado cuando hay un pacienteId (tanto en modo edición como visualización)
  // Calculamos pacienteId aquí dentro del useEffect para evitar problemas con hooks condicionales
  useEffect(() => {
    const pacienteId = editedData.paciente !== null && editedData.paciente !== undefined 
      ? editedData.paciente 
      : (internacion?.paciente || null);
    
    if (pacienteId) {
      // Si ya está en las opciones, usarlo
      const found = pacienteOptions.find(p => p.id === pacienteId);
      if (found) {
        setPacienteSeleccionado(found);
        return;
      }
      
      // Si no está en las opciones, buscarlo por ID desde la API
      apiService.getPaciente(pacienteId)
        .then(paciente => {
          setPacienteSeleccionado(paciente);
          // Agregarlo a las opciones si no está
          if (!pacienteOptions.find(p => p.id === paciente.id)) {
            setPacienteOptions(prev => [...prev, paciente]);
          }
        })
        .catch(error => {
          setPacienteSeleccionado(null);
        });
    } else {
      setPacienteSeleccionado(null);
    }
  }, [editedData.paciente, internacion?.paciente, pacienteOptions]);

  const loadInternacion = async () => {
    if (!cama?.internacion_actual) {
      return;
    }

    const internacionId = cama.internacion_actual.id_internacion;
    setLoadingData(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/internacion/internaciones/${internacionId}/`, {
        credentials: 'include',
      });
      if (response.ok) {
        const found = await response.json();
        setInternacion(found);
        setEditedData({
          paciente: found.paciente,
          medico: found.medico,
          diagnostico_ingreso: found.diagnostico_ingreso || '',
          diagnostico_cie_id: found.diagnostico_cie?.id || null,
        });
        
        // Si hay un diagnóstico CIE, establecer el input value
        if (found.diagnostico_cie) {
          setDiagnosticoInputValue(`${found.diagnostico_cie.codigo} - ${found.diagnostico_cie.descripcion}`);
        } else {
          setDiagnosticoInputValue('');
        }
      } else {
        // Fallback: buscar en la lista
        const internaciones = await getInternaciones();
        const found = internaciones.find((i) => i.id === internacionId);
        if (found) {
          setInternacion(found);
          setEditedData({
            paciente: found.paciente,
            medico: found.medico,
            diagnostico_ingreso: found.diagnostico_ingreso || '',
            diagnostico_cie_id: found.diagnostico_cie?.id || null,
          });
          
          // Si hay un diagnóstico CIE, establecer el input value
          if (found.diagnostico_cie) {
            setDiagnosticoInputValue(`${found.diagnostico_cie.codigo} - ${found.diagnostico_cie.descripcion}`);
          } else {
            setDiagnosticoInputValue('');
          }
        } else {
          setError('No se encontró la internación');
        }
      }
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.internacionCargar));
    } finally {
      setLoadingData(false);
    }
  };

  const handleEditToggle = async () => {
    if (!isEditing) {
      // Activar modo edición
      setIsEditing(true);
      setError(null);
      // Los pacientes se cargarán automáticamente con búsqueda API cuando el usuario escriba
    } else {
      // Desactivar modo edición - restaurar datos originales
      setIsEditing(false);
      if (internacion) {
        setEditedData({
          paciente: internacion.paciente,
          medico: internacion.medico,
          diagnostico_ingreso: internacion.diagnostico_ingreso || '',
          diagnostico_cie_id: internacion.diagnostico_cie?.id || null,
        });
        
        // Restaurar input value del diagnóstico CIE
        if (internacion.diagnostico_cie) {
          setDiagnosticoInputValue(`${internacion.diagnostico_cie.codigo} - ${internacion.diagnostico_cie.descripcion}`);
        } else {
          setDiagnosticoInputValue('');
        }
      }
      setError(null);
      setSuccessMessage(null);
    }
  };

  const handleSaveAll = async () => {
    if (!internacion) return;

    const internacionId = internacion.id || cama?.internacion_actual?.id_internacion;
    if (!internacionId) {
      setError('No se pudo identificar la internación para guardar');
      return;
    }

    // Validaciones
    if (!editedData.paciente) {
      setError('Debe seleccionar un paciente');
      return;
    }
    if (!editedData.diagnostico_cie_id && !editedData.diagnostico_ingreso.trim()) {
      setError('Debe seleccionar un diagnóstico CIE-10 o ingresar un diagnóstico de texto libre');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updateData: any = {
        paciente: editedData.paciente,
        medico: editedData.medico || null,
      };
      
      // Incluir diagnóstico CIE-10 si está seleccionado
      if (editedData.diagnostico_cie_id) {
        updateData.diagnostico_cie_id = editedData.diagnostico_cie_id;
      }
      
      // Incluir diagnóstico de texto libre si está presente
      if (editedData.diagnostico_ingreso.trim()) {
        updateData.diagnostico_ingreso = editedData.diagnostico_ingreso.trim();
      }

      const updated = await updateInternacion(internacionId, updateData);
      
      // Actualizar el estado local
      setInternacion(updated);
      setEditedData({
        paciente: updated.paciente,
        medico: updated.medico,
        diagnostico_ingreso: updated.diagnostico_ingreso || '',
        diagnostico_cie_id: updated.diagnostico_cie?.id || null,
      });
      
      // Actualizar input value del diagnóstico CIE
      if (updated.diagnostico_cie) {
        setDiagnosticoInputValue(`${updated.diagnostico_cie.codigo} - ${updated.diagnostico_cie.descripcion}`);
      } else {
        setDiagnosticoInputValue('');
      }
      
      // Desactivar modo edición
      setIsEditing(false);
      setSuccessMessage('Cambios guardados exitosamente');
      
      // Recargar para sincronizar con el panel
      setTimeout(async () => {
        await loadInternacion();
        onSuccess();
      }, 500);
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.internacionActualizar));
    } finally {
      setLoading(false);
    }
  };

  const handleDarAlta = async () => {
    if (!internacion) return;

    if (!confirmAlta) {
      setConfirmAlta(true);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await darAltaInternacion(internacion.id);
      // El backend ya actualiza:
      // - fecha_alta = ahora
      // - activo = False
      // - cama.estado = 'LIMPIEZA'
      // Todos estos datos quedan registrados en la base de datos para historial
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.internacionAlta));
      setConfirmAlta(false);
    } finally {
      setLoading(false);
    }
  };

  // Debug: Log para verificar que el médico se encuentra
  useEffect(() => {
    if (cama?.internacion_actual && medicosContext.length > 0) {
      const medicoId = internacion?.medico || cama.internacion_actual?.id_internacion;
      if (medicoId) {
        const found = medicosContext.find((m) => m.id === medicoId);
        if (found) {
        }
      }
    }
  }, [cama, internacion, medicosContext]);

  if (!cama?.internacion_actual) {
    return null;
  }

  const internacionData = cama.internacion_actual;
  const medicoId = editedData.medico !== null && editedData.medico !== undefined
    ? editedData.medico
    : (internacion?.medico || null);
  
  const medicoSeleccionado = medicoId ? (medicosContext.find((m) => m.id === medicoId) || null) : null;
  const medicosActivos = medicosContext;

  return (
    <Dialog open={open} onClose={isEditing ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Gestionar Paciente - {cama.nombre} ({typeof cama.sector === 'object' ? cama.sector.nombre : cama.sector_nombre || 'N/A'})
          </Typography>
          {!isEditing && (
            <Button
              variant="outlined"
              color="primary"
              size="small"
              startIcon={<Edit />}
              onClick={handleEditToggle}
              disabled={loading || loadingData}
            >
              Modo Edición
            </Button>
          )}
        </Box>
      </DialogTitle>
      <DialogContent>
        {loadingData ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            {successMessage && (
              <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
                {successMessage}
              </Alert>
            )}

            {confirmAlta && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                ¿Está seguro que desea dar de alta a este paciente? La cama pasará a estado "Limpieza" y todos los datos quedarán registrados en el historial.
              </Alert>
            )}

            {isEditing && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Modo edición activado. Modifique los campos y haga clic en "Guardar Cambios" para aplicar todas las modificaciones.
              </Alert>
            )}

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <PersonIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                  Paciente:
                </Typography>
              </Box>
              {isEditing ? (
                <Autocomplete
                  options={pacienteOptions}
                  getOptionLabel={(option) => {
                    const label = `${option.apellido || ''}, ${option.nombre || ''} - DNI: ${option.dni || ''}`;
                    return label.trim() || `Paciente ${option.id}`;
                  }}
                  value={pacienteSeleccionado}
                  inputValue={pacienteInputValue}
                  onInputChange={(event, newInputValue, reason) => {
                    pacienteInputReason.current = reason as 'input' | 'selection' | 'clear';
                    setPacienteInputValue(newInputValue);
                  }}
                  onChange={(event, newValue) => {
                    pacienteInputReason.current = 'selection';
                    setPacienteSeleccionado(newValue);
                    setEditedData(prev => ({ ...prev, paciente: newValue?.id ?? null }));
                  }}
                  size="small"
                  fullWidth
                  loading={searchingPacientes}
                  renderInput={(params) => (
                    <TextField 
                      {...params} 
                      label="Paciente" 
                      required
                      placeholder="Escribe al menos 2 caracteres para buscar..."
                    />
                  )}
                  isOptionEqualToValue={(option, value) => option.id === value?.id}
                  noOptionsText={pacienteInputValue.length < 2 
                    ? "Escribe al menos 2 caracteres para buscar pacientes" 
                    : searchingPacientes 
                    ? "Buscando..." 
                    : "No se encontraron pacientes"}
                  filterOptions={(options) => options} // No filtrar localmente, usar resultados de API
                />
              ) : (
                <Typography variant="body1" sx={{ ml: 4 }}>
                  {pacienteSeleccionado
                    ? `${pacienteSeleccionado.apellido || ''}, ${pacienteSeleccionado.nombre || ''}`
                    : internacionData?.nombre_paciente || 'Paciente no disponible'}
                </Typography>
              )}
            </Box>

            <Divider sx={{ my: 2 }} />

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <HospitalIcon sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                  Médico:
                </Typography>
              </Box>
              {isEditing ? (
                <Autocomplete
                  options={medicosActivos}
                  getOptionLabel={(option) => {
                    const name = `${option.apellido || ''}, ${option.nombre || ''}`;
                    const esp = option.especialidad?.nombre || '';
                    return `${name}${esp ? ` - ${esp}` : ''}`.trim() || `Médico ${option.id}`;
                  }}
                  value={medicoSeleccionado ?? null}
                  onChange={(event, newValue) => {
                    setEditedData(prev => ({ ...prev, medico: newValue?.id ?? null }));
                  }}
                  size="small"
                  fullWidth
                  renderInput={(params) => (
                    <TextField {...params} label="Médico" placeholder="Sin asignar" />
                  )}
                  isOptionEqualToValue={(option, value) => option.id === value?.id}
                  noOptionsText="No hay médicos disponibles"
                  filterOptions={(options, params) => {
                    const filtered = options.filter((option) => {
                      const searchTerm = params.inputValue.toLowerCase();
                      const nombre = (option.nombre || '').toLowerCase();
                      const apellido = (option.apellido || '').toLowerCase();
                      const especialidad = (option.especialidad?.nombre || '').toLowerCase();
                      return nombre.includes(searchTerm) || 
                             apellido.includes(searchTerm) || 
                             especialidad.includes(searchTerm);
                    });
                    return filtered;
                  }}
                />
              ) : (
                <Typography variant="body1" sx={{ ml: 4 }}>
                  {medicoSeleccionado
                    ? `${medicoSeleccionado.apellido || ''}, ${medicoSeleccionado.nombre || ''}`
                    : internacionData.nombre_medico || 'Sin asignar'}
                </Typography>
              )}
            </Box>

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <CalendarIcon sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                  Fecha de Ingreso:
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ ml: 4 }}>
                {new Date(internacionData.fecha_ingreso).toLocaleString('es-AR')}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Chip
                  label={`${internacionData.dias_internacion} días`}
                  color="primary"
                  size="small"
                  sx={{ mr: 1 }}
                />
                <Typography variant="body2" color="text.secondary">
                  Días de internación
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <DescriptionIcon sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                  Diagnóstico CIE-10:
                </Typography>
              </Box>
              {isEditing ? (
                <Autocomplete
                  options={diagnosticoOptions}
                  getOptionLabel={(option) => `${option.codigo} - ${option.descripcion}`}
                  value={diagnosticoOptions.find(d => d.id === editedData.diagnostico_cie_id) || null}
                  inputValue={diagnosticoInputValue}
                  onChange={(event, newValue) => {
                    diagnosticoInputReason.current = 'selection';
                    setEditedData(prev => ({ 
                      ...prev, 
                      diagnostico_cie_id: newValue?.id || null 
                    }));
                    if (newValue) {
                      setDiagnosticoInputValue(`${newValue.codigo} - ${newValue.descripcion}`);
                    } else {
                      setDiagnosticoInputValue('');
                    }
                  }}
                  onInputChange={(_, newInputValue, reason) => {
                    if (reason === 'input') {
                      diagnosticoInputReason.current = 'input';
                      setDiagnosticoInputValue(newInputValue);
                    } else if (reason === 'clear') {
                      diagnosticoInputReason.current = 'clear';
                      setDiagnosticoInputValue('');
                      setDiagnosticoOptions([]);
                      setEditedData(prev => ({ ...prev, diagnostico_cie_id: null }));
                    }
                  }}
                  size="small"
                  fullWidth
                  loading={searchingDiagnosticos}
                  renderInput={(params) => (
                    <TextField 
                      {...params} 
                      label="Diagnóstico CIE-10" 
                      placeholder="Escriba al menos 2 caracteres para buscar (código o descripción)..."
                    />
                  )}
                  isOptionEqualToValue={(option, value) => option.id === value?.id}
                  noOptionsText={
                    searchingDiagnosticos
                      ? "Buscando diagnósticos..."
                      : diagnosticoInputValue.length < 2
                        ? "Escriba al menos 2 caracteres"
                        : "No se encontraron diagnósticos"
                  }
                  filterOptions={(options) => options}
                />
              ) : (
                <Typography variant="body1" sx={{ ml: 4 }}>
                  {internacion?.diagnostico_cie 
                    ? `${internacion.diagnostico_cie.codigo} - ${internacion.diagnostico_cie.descripcion}`
                    : 'Sin diagnóstico CIE-10'}
                </Typography>
              )}
            </Box>

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <DescriptionIcon sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                  Diagnóstico (texto libre):
                </Typography>
              </Box>
              {isEditing ? (
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  value={editedData.diagnostico_ingreso}
                  onChange={(e) => {
                    setEditedData(prev => ({ ...prev, diagnostico_ingreso: e.target.value }));
                  }}
                  placeholder="Ingrese un diagnóstico de texto libre (opcional si ya seleccionó CIE-10)"
                />
              ) : (
                <Typography variant="body1" sx={{ ml: 4, whiteSpace: 'pre-wrap' }}>
                  {internacion?.diagnostico_ingreso || 'Sin diagnóstico de texto libre'}
                </Typography>
              )}
            </Box>
          </>
        )}
      </DialogContent>
      <DialogActions>
        {isEditing ? (
          <>
            <Button
              onClick={handleEditToggle}
              disabled={loading}
              startIcon={<Cancel />}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleSaveAll}
              variant="contained"
              color="primary"
              disabled={loading || !editedData.paciente || (!editedData.diagnostico_cie_id && !editedData.diagnostico_ingreso.trim())}
              startIcon={<Save />}
            >
              {loading ? <CircularProgress size={20} /> : 'Guardar Cambios'}
            </Button>
          </>
        ) : (
          <>
            <Button onClick={onClose} disabled={loading}>
              Cerrar
            </Button>
            <Button
              onClick={handleDarAlta}
              variant="contained"
              color={confirmAlta ? 'error' : 'primary'}
              disabled={loading || loadingData}
            >
              {loading ? (
                <CircularProgress size={20} />
              ) : confirmAlta ? (
                'Confirmar Alta'
              ) : (
                'Dar de Alta'
              )}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ModalGestionarPaciente;
