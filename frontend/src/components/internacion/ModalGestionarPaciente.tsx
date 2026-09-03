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
  Stack,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Person as PersonIcon,
  LocalHospital as HospitalIcon,
  CalendarToday as CalendarIcon,
  Description as DescriptionIcon,
  Edit,
  Save,
  Cancel,
  RestaurantMenu,
} from '@mui/icons-material';
import { Cama, InternacionCama, Paciente, Medico, DiagnosticoCIE10, TipoDieta } from '../../types';
import { darAltaInternacion, getInternacion, getInternaciones, updateInternacion, buscarDiagnosticosCIE10, iniciarEvolucionDiariaInternacion, iniciarNotaInternacion } from '../../services/apiService';
import { getTiposDieta, getRevistaInternacionContexto, type RevistaInternacionContexto } from '../../services/internacion';
import { apiService } from '../../services/api';
import { useData } from '../../contexts/DataContext';
import { canDarAltaInternacion, canOperateInternacionClinica, canWriteHcMedico, canWriteHcEnfermeria, canWriteHcKinesiologia, getDefaultInternacionModalTab } from '../../utils/permissions';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import AtencionDetailDrawer from '../../modules/atenciones/components/AtencionDetailDrawer';
import RevistaInternacionWorkspace from './RevistaInternacionWorkspace';
import FormulariosHcInternacion from './FormulariosHcInternacion';

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
  const { currentUser } = useData();
  const [internacion, setInternacion] = useState<InternacionCama | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [confirmAlta, setConfirmAlta] = useState(false);
  const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tab, setTab] = useState(0);
  const [revistaContexto, setRevistaContexto] = useState<RevistaInternacionContexto | null>(null);
  const [loadingRevista, setLoadingRevista] = useState(false);
  const [revistaError, setRevistaError] = useState<string | null>(null);
  
  // Estados para modo edición
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState<{
    paciente: number | null;
    medico: number | null;
    diagnostico_ingreso: string;
    diagnostico_cie_id: number | null;
    tipo_dieta_id: number | null;
  }>({
    paciente: null,
    medico: null,
    diagnostico_ingreso: '',
    diagnostico_cie_id: null,
    tipo_dieta_id: null,
  });
  const [tiposDieta, setTiposDieta] = useState<TipoDieta[]>([]);
  const [loadingTiposDieta, setLoadingTiposDieta] = useState(false);
  
  // Estados para búsqueda de pacientes con API
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [pacienteInputValue, setPacienteInputValue] = useState('');
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  const pacienteInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<Paciente | null>(null);

  // Estados para búsqueda de médicos con API (igual que ModalIngresarPaciente)
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [medicoInputValue, setMedicoInputValue] = useState('');
  const [searchingMedicos, setSearchingMedicos] = useState(false);
  const medicoInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const [medicoSeleccionado, setMedicoSeleccionado] = useState<Medico | null>(null);
  
  // Estados para búsqueda de diagnósticos CIE-10
  const [diagnosticoOptions, setDiagnosticoOptions] = useState<DiagnosticoCIE10[]>([]);
  const [diagnosticoInputValue, setDiagnosticoInputValue] = useState('');
  const [searchingDiagnosticos, setSearchingDiagnosticos] = useState(false);
  const diagnosticoInputReason = useRef<'input' | 'selection' | 'clear'>('input');

  useEffect(() => {
    if (open && cama?.internacion_actual) {
      setTab(getDefaultInternacionModalTab(currentUser));
      loadInternacion();
      return;
    }
    if (open) {
      return;
    }
    setInternacion(null);
    setConfirmAlta(false);
    setError(null);
    setSuccessMessage(null);
    setIsEditing(false);
    setDiagnosticoOptions([]);
    setDiagnosticoInputValue('');
    setPacienteOptions([]);
    setPacienteInputValue('');
    setPacienteSeleccionado(null);
    setMedicoOptions([]);
    setMedicoInputValue('');
    setMedicoSeleccionado(null);
    setTiposDieta([]);
    setLoadingTiposDieta(false);
    setTab(0);
    setRevistaContexto(null);
    setRevistaError(null);
  }, [open, cama]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoadingTiposDieta(true);
    getTiposDieta()
      .then((tipos) => {
        if (active) setTiposDieta(tipos);
      })
      .catch(() => {
        if (active) {
          setTiposDieta([]);
          setError('No se pudieron cargar los tipos de dieta.');
        }
      })
      .finally(() => {
        if (active) setLoadingTiposDieta(false);
      });
    return () => {
      active = false;
    };
  }, [open]);
  
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

  // Búsqueda de médicos en el servidor (igual que ModalIngresarPaciente)
  useEffect(() => {
    if (!open || !isEditing) {
      setSearchingMedicos(false);
      return;
    }

    if (medicoInputReason.current !== 'input') {
      medicoInputReason.current = 'input';
      return;
    }

    const query = medicoInputValue.trim();
    if (query.length < 2) {
      setSearchingMedicos(false);
      return;
    }

    const timeoutId = setTimeout(() => {
      let active = true;
      setSearchingMedicos(true);

      apiService.buscarMedicos(query)
        .then(results => {
          if (!active) return;
          setMedicoOptions(results);
        })
        .catch(() => {
          if (active) {
            setMedicoOptions([]);
          }
        })
        .finally(() => {
          if (active) setSearchingMedicos(false);
        });
    }, 200);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [medicoInputValue, open, isEditing]);

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
  useEffect(() => {
    const pacienteId = editedData.paciente !== null && editedData.paciente !== undefined 
      ? editedData.paciente 
      : (internacion?.paciente || null);
    
    if (pacienteId) {
      const found = pacienteOptions.find(p => p.id === pacienteId);
      if (found) {
        setPacienteSeleccionado(found);
        return;
      }
      
      apiService.getPaciente(pacienteId)
        .then(paciente => {
          setPacienteSeleccionado(paciente);
          if (!pacienteOptions.find(p => p.id === paciente.id)) {
            setPacienteOptions(prev => [...prev, paciente]);
          }
        })
        .catch(() => {
          setPacienteSeleccionado(null);
        });
    } else {
      setPacienteSeleccionado(null);
    }
  }, [editedData.paciente, internacion?.paciente, pacienteOptions]);

  // Cargar médico asignado por ID para preseleccionar en edición/visualización
  useEffect(() => {
    const medicoId = editedData.medico !== null && editedData.medico !== undefined
      ? editedData.medico
      : (internacion?.medico || null);

    if (!medicoId) {
      setMedicoSeleccionado(null);
      return;
    }

    let active = true;
    apiService.getMedico(medicoId)
      .then(medico => {
        if (!active) return;
        setMedicoSeleccionado(medico);
        setMedicoOptions(prev =>
          prev.find(m => m.id === medico.id) ? prev : [...prev, medico]
        );
        const label = `${medico.apellido || ''}, ${medico.nombre || ''}`.trim();
        if (label) {
          medicoInputReason.current = 'selection';
          setMedicoInputValue(label);
        }
      })
      .catch(() => {
        if (active) setMedicoSeleccionado(null);
      });

    return () => {
      active = false;
    };
  }, [editedData.medico, internacion?.medico]);

  const loadRevistaContexto = async (internacionId: number) => {
    setLoadingRevista(true);
    setRevistaError(null);
    try {
      const data = await getRevistaInternacionContexto(internacionId);
      setRevistaContexto(data);
    } catch {
      setRevistaContexto(null);
      setRevistaError('No se pudo cargar el contexto de revista.');
    } finally {
      setLoadingRevista(false);
    }
  };

  const loadInternacion = async () => {
    if (!cama?.internacion_actual) {
      return;
    }

    const internacionId = cama.internacion_actual.id_internacion;
    setLoadingData(true);
    setError(null);
    try {
      let found: InternacionCama | undefined;
      try {
        found = await getInternacion(internacionId);
      } catch {
        const internaciones = await getInternaciones();
        found = internaciones.find((i) => i.id === internacionId);
      }
      if (!found) {
        setError('No se encontró la internación');
        return;
      }
      setInternacion(found);
      setEditedData({
        paciente: found.paciente,
        medico: found.medico,
        diagnostico_ingreso: found.diagnostico_ingreso || '',
        diagnostico_cie_id: found.diagnostico_cie?.id || null,
        tipo_dieta_id: found.tipo_dieta?.id || null,
      });
      if (found.diagnostico_cie) {
        setDiagnosticoInputValue(`${found.diagnostico_cie.codigo} - ${found.diagnostico_cie.descripcion}`);
      } else {
        setDiagnosticoInputValue('');
      }
      await loadRevistaContexto(internacionId);
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.internacionCargar));
    } finally {
      setLoadingData(false);
    }
  };

  const handleEditToggle = async () => {
    if (!isEditing) {
      setIsEditing(true);
      setError(null);
      if (medicoSeleccionado) {
        const label = `${medicoSeleccionado.apellido || ''}, ${medicoSeleccionado.nombre || ''}`.trim();
        medicoInputReason.current = 'selection';
        setMedicoInputValue(label);
      }
    } else {
      // Desactivar modo edición - restaurar datos originales
      setIsEditing(false);
      if (internacion) {
        setEditedData({
          paciente: internacion.paciente,
          medico: internacion.medico,
          diagnostico_ingreso: internacion.diagnostico_ingreso || '',
          diagnostico_cie_id: internacion.diagnostico_cie?.id || null,
          tipo_dieta_id: internacion.tipo_dieta?.id || null,
        });
        
        if (internacion.diagnostico_cie) {
          setDiagnosticoInputValue(`${internacion.diagnostico_cie.codigo} - ${internacion.diagnostico_cie.descripcion}`);
        } else {
          setDiagnosticoInputValue('');
        }

        if (medicoSeleccionado && internacion.medico === medicoSeleccionado.id) {
          const label = `${medicoSeleccionado.apellido || ''}, ${medicoSeleccionado.nombre || ''}`.trim();
          medicoInputReason.current = 'selection';
          setMedicoInputValue(label);
        } else if (!internacion.medico) {
          setMedicoInputValue('');
          setMedicoSeleccionado(null);
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

      updateData.tipo_dieta_id = editedData.tipo_dieta_id;

      const updated = await updateInternacion(internacionId, updateData);
      
      // Actualizar el estado local
      setInternacion(updated);
      setEditedData({
        paciente: updated.paciente,
        medico: updated.medico,
        diagnostico_ingreso: updated.diagnostico_ingreso || '',
        diagnostico_cie_id: updated.diagnostico_cie?.id || null,
        tipo_dieta_id: updated.tipo_dieta?.id || null,
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

  const internacionIdActual = internacion?.id || cama?.internacion_actual?.id_internacion;

  const ensureRevistaAtencion = async (): Promise<number | null> => {
    if (!internacionIdActual) return null;
    if (revistaContexto?.evolucion_hoy?.atencion_id) {
      return revistaContexto.evolucion_hoy.atencion_id;
    }
    setLoading(true);
    setError(null);
    try {
      const atencion = await iniciarEvolucionDiariaInternacion(internacionIdActual);
      await loadRevistaContexto(internacionIdActual);
      return atencion.id;
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, 'No se pudo preparar la evolución de hoy.'));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const handleIniciarInterconsulta = async () => {
    if (!internacionIdActual) return;
    setLoading(true);
    setError(null);
    try {
      const atencion = await iniciarNotaInternacion(internacionIdActual, 'INTERCONSULTA');
      await loadRevistaContexto(internacionIdActual);
      setSelectedAtencionId(atencion.id);
      setDrawerOpen(true);
    } catch (err: unknown) {
      setError(getSafeClinicalActionMessage(err, 'No se pudo iniciar la interconsulta.'));
    } finally {
      setLoading(false);
    }
  };

  const handleDrawerClose = () => {
    setDrawerOpen(false);
    setSelectedAtencionId(null);
    if (internacionIdActual) {
      loadRevistaContexto(internacionIdActual);
    }
  };

  if (!cama?.internacion_actual) {
    return null;
  }

  const internacionData = cama.internacion_actual;
  const canOperateClinica = canOperateInternacionClinica(currentUser);
  const canWriteSoap = canWriteHcMedico(currentUser);
  const canWriteEnfermeria = canWriteHcEnfermeria(currentUser);
  const canWriteKinesiologia = canWriteHcKinesiologia(currentUser);
  const canDarAlta = canDarAltaInternacion(currentUser);
  const diagnosticoVisible =
    internacion?.diagnostico_cie
      ? `${internacion.diagnostico_cie.codigo} - ${internacion.diagnostico_cie.descripcion}`
      : internacion?.diagnostico_ingreso || internacionData.diagnostico || '';

  const getMedicoLabel = (option: Medico) => {
    const name = `${option.apellido || ''}, ${option.nombre || ''}`;
    const esp = option.especialidad?.nombre || option.especialidad_nombre || '';
    return `${name}${esp ? ` - ${esp}` : ''}`.trim() || `Médico ${option.id}`;
  };

  const atencionHoyId = revistaContexto?.evolucion_hoy?.atencion_id ?? null;

  return (
    <Dialog open={open} onClose={isEditing ? undefined : onClose} maxWidth="xl" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Gestionar Paciente - {cama.nombre} ({typeof cama.sector === 'object' ? cama.sector.nombre : cama.sector_nombre || 'N/A'})
          </Typography>
          {!isEditing && canOperateClinica && tab === 0 && (
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
      <Tabs
        value={tab}
        onChange={(_e, value) => setTab(value)}
        sx={{ px: 3, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="Datos del paciente" />
        <Tab label="Formularios HC" />
        <Tab label="Revista de sala" />
      </Tabs>
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

            {diagnosticoVisible && (
              <Alert severity="info" sx={{ mb: 2 }} icon={<DescriptionIcon />}>
                <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.25 }}>
                  Diagnóstico
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, whiteSpace: 'pre-wrap' }}>
                  {diagnosticoVisible}
                </Typography>
              </Alert>
            )}

            {isEditing && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Modo edición activado. Modifique los campos y haga clic en "Guardar Cambios" para aplicar todas las modificaciones.
              </Alert>
            )}

            {tab === 0 && (
            <>
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
                  options={medicoOptions}
                  getOptionLabel={getMedicoLabel}
                  value={medicoSeleccionado ?? null}
                  inputValue={medicoInputValue}
                  onInputChange={(_, newInputValue, reason) => {
                    if (reason === 'input') {
                      medicoInputReason.current = 'input';
                      setMedicoInputValue(newInputValue);
                    } else if (reason === 'clear') {
                      medicoInputReason.current = 'clear';
                      setMedicoInputValue('');
                      setMedicoOptions(medicoSeleccionado ? [medicoSeleccionado] : []);
                    }
                  }}
                  onChange={(_, newValue) => {
                    medicoInputReason.current = 'selection';
                    setMedicoSeleccionado(newValue);
                    setEditedData(prev => ({ ...prev, medico: newValue?.id ?? null }));
                    if (newValue) {
                      setMedicoInputValue(getMedicoLabel(newValue));
                      setMedicoOptions(prev =>
                        prev.find(m => m.id === newValue.id) ? prev : [...prev, newValue]
                      );
                    } else {
                      setMedicoInputValue('');
                    }
                  }}
                  size="small"
                  fullWidth
                  loading={searchingMedicos}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Médico"
                      placeholder="Escribe al menos 2 caracteres para buscar..."
                    />
                  )}
                  isOptionEqualToValue={(option, value) => option.id === value?.id}
                  noOptionsText={
                    medicoInputValue.trim().length < 2
                      ? 'Escribe al menos 2 caracteres para buscar médicos'
                      : searchingMedicos
                        ? 'Buscando...'
                        : 'No se encontraron médicos'
                  }
                  filterOptions={(options) => options}
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

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <RestaurantMenu sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                  Tipo de dieta:
                </Typography>
              </Box>
              {isEditing ? (
                <Autocomplete
                  options={
                    internacion?.tipo_dieta &&
                    typeof internacion.tipo_dieta === 'object' &&
                    internacion.tipo_dieta.id &&
                    !tiposDieta.some((t) => t.id === internacion.tipo_dieta?.id)
                      ? [...tiposDieta, internacion.tipo_dieta]
                      : tiposDieta
                  }
                  getOptionLabel={(option) => option.nombre || ''}
                  value={
                    tiposDieta.find((t) => t.id === editedData.tipo_dieta_id)
                    || (internacion?.tipo_dieta?.id === editedData.tipo_dieta_id ? internacion.tipo_dieta : null)
                    || null
                  }
                  onChange={(_, newValue) => {
                    setEditedData((prev) => ({ ...prev, tipo_dieta_id: newValue?.id ?? null }));
                  }}
                  size="small"
                  fullWidth
                  loading={loadingTiposDieta}
                  slotProps={{
                    popper: { sx: { zIndex: 1400 } },
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Tipo de dieta"
                      placeholder="Sin dieta asignada"
                      helperText={
                        loadingTiposDieta
                          ? 'Cargando tipos de dieta…'
                          : tiposDieta.length === 0
                            ? 'No hay tipos de dieta activos. Revisá Catálogos → Tipos de dieta.'
                            : undefined
                      }
                    />
                  )}
                  isOptionEqualToValue={(option, value) => option.id === value?.id}
                  noOptionsText={
                    loadingTiposDieta
                      ? 'Cargando tipos de dieta…'
                      : 'No hay tipos de dieta cargados'
                  }
                />
              ) : (
                <Typography variant="body1" sx={{ ml: 4 }}>
                  {internacion?.tipo_dieta?.nombre || internacionData.tipo_dieta || 'Sin dieta asignada'}
                </Typography>
              )}
            </Box>
            </>
            )}

            {tab === 1 && internacionIdActual && (
              <FormulariosHcInternacion
                internacionId={internacionIdActual}
                internacion={internacion}
                currentUser={currentUser}
                onInternacionUpdated={setInternacion}
              />
            )}

            {tab === 2 && internacionIdActual && (
              <RevistaInternacionWorkspace
                internacionId={internacionIdActual}
                contexto={revistaContexto}
                loading={loadingRevista}
                error={revistaError}
                canOperateClinica={canOperateClinica && !isEditing}
                canWriteSoap={canWriteSoap && !isEditing}
                canPedirLaboratorioEstudios={canWriteSoap && !isEditing}
                canWriteEnfermeria={canWriteEnfermeria && !isEditing}
                canWriteKinesiologia={canWriteKinesiologia && !isEditing}
                atencionHoyId={atencionHoyId}
                ensuringAtencion={loading}
                paciente={pacienteSeleccionado}
                medicoId={internacion?.medico ?? editedData.medico ?? null}
                onEnsureAtencion={ensureRevistaAtencion}
                onRefresh={() => {
                  if (internacionIdActual) {
                    loadRevistaContexto(internacionIdActual);
                  }
                }}
                onIniciarInterconsulta={
                  canWriteSoap && !isEditing ? handleIniciarInterconsulta : undefined
                }
                iniciandoInterconsulta={loading}
                onAbrirAtencion={
                  canOperateClinica && !isEditing
                    ? (atencionId) => {
                        setSelectedAtencionId(atencionId);
                        setDrawerOpen(true);
                      }
                    : undefined
                }
              />
            )}
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
            {canDarAlta && tab === 0 && (
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
            )}
          </>
        )}
      </DialogActions>

      <AtencionDetailDrawer
        atencionId={selectedAtencionId}
        open={drawerOpen}
        onClose={handleDrawerClose}
        forceEdit={canOperateClinica}
        onIntervencionSaved={() => {
          if (internacionIdActual) {
            loadRevistaContexto(internacionIdActual);
          }
        }}
      />
    </Dialog>
  );
};

export default ModalGestionarPaciente;
