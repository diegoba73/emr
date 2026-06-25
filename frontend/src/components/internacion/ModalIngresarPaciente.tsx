import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Box,
  Autocomplete,
} from '@mui/material';
import { Cama, Paciente, Medico, DiagnosticoCIE10 } from '../../types';
import { buscarDiagnosticosCIE10 } from '../../services/apiService';
import { createInternacion } from '../../services/internacion';
import { apiService } from '../../services/api';
import { formatPacienteLabel } from '../../utils/pacienteFormat';

interface ModalIngresarPacienteProps {
  open: boolean;
  onClose: () => void;
  cama: Cama | null;
  onSuccess: () => void;
}

const ModalIngresarPaciente: React.FC<ModalIngresarPacienteProps> = ({
  open,
  onClose,
  cama,
  onSuccess,
}) => {
  const [selectedPaciente, setSelectedPaciente] = useState<Paciente | null>(null);
  const [selectedMedico, setSelectedMedico] = useState<Medico | null>(null);
  const [selectedDiagnostico, setSelectedDiagnostico] = useState<DiagnosticoCIE10 | null>(null);
  const [diagnosticoTextoLibre, setDiagnosticoTextoLibre] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Estados para búsqueda en servidor
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [diagnosticoOptions, setDiagnosticoOptions] = useState<DiagnosticoCIE10[]>([]);
  const [pacienteInputValue, setPacienteInputValue] = useState('');
  const [medicoInputValue, setMedicoInputValue] = useState('');
  const [diagnosticoInputValue, setDiagnosticoInputValue] = useState('');
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  const [searchingMedicos, setSearchingMedicos] = useState(false);
  const [searchingDiagnosticos, setSearchingDiagnosticos] = useState(false);
  const pacienteInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const medicoInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const diagnosticoInputReason = useRef<'input' | 'selection' | 'clear'>('input');

  useEffect(() => {
    if (!open) {
      // Reset form when closing
      setSelectedPaciente(null);
      setSelectedMedico(null);
      setSelectedDiagnostico(null);
      setDiagnosticoTextoLibre('');
      setError(null);
      setPacienteOptions([]);
      setMedicoOptions([]);
      setDiagnosticoOptions([]);
      setPacienteInputValue('');
      setMedicoInputValue('');
      setDiagnosticoInputValue('');
      return;
    }
  }, [open]);

  // Búsqueda de pacientes en el servidor
  useEffect(() => {
    if (!open) return;

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
  }, [pacienteInputValue, open]);

  // Búsqueda de médicos en el servidor
  useEffect(() => {
    if (!open) return;

    if (medicoInputReason.current !== 'input') {
      medicoInputReason.current = 'input';
      return;
    }

    const query = medicoInputValue.trim();
    if (query.length < 2) {
      setMedicoOptions([]);
      setSearchingMedicos(false);
      return;
    }

    // Debounce optimizado: esperar 200ms para búsquedas más rápidas
    const timeoutId = setTimeout(() => {
      let active = true;
      setSearchingMedicos(true);

      apiService.buscarMedicos(query)
        .then(results => {
          if (!active) return;
          setMedicoOptions(results);
        })
        .catch(error => {
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
  }, [medicoInputValue, open]);

  // Búsqueda de diagnósticos CIE-10 en el servidor
  useEffect(() => {
    if (!open) {
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

    // Debounce optimizado: esperar 200ms para búsquedas más rápidas
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
            setError('Error al buscar diagnósticos. Por favor intente nuevamente.');
          }
        })
        .finally(() => {
          if (active) setSearchingDiagnosticos(false);
        });
    }, 200);

    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
  }, [diagnosticoInputValue, open]);

  const getPacienteLabel = (option: Paciente) => formatPacienteLabel(option);

  const getMedicoLabel = (option: Medico) => {
    const name = `${option.apellido || ''}, ${option.nombre || ''}`;
    const esp = option.especialidad?.nombre || '';
    return `${name}${esp ? ` - ${esp}` : ''}`.trim() || `Médico ${option.id}`;
  };

  const getDiagnosticoLabel = (option: DiagnosticoCIE10) => {
    return `${option.codigo} - ${option.descripcion}`;
  };

  const handleSubmit = async () => {
    if (!cama || !selectedPaciente || (!selectedDiagnostico && !diagnosticoTextoLibre.trim())) {
      setError('Por favor complete todos los campos requeridos (paciente y diagnóstico)');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const internacionData: any = {
        paciente: selectedPaciente.id,
        cama: cama.id,
        medico: selectedMedico?.id || null,
      };
      
      if (selectedDiagnostico) {
        internacionData.diagnostico_cie_id = selectedDiagnostico.id;
      }
      
      if (diagnosticoTextoLibre.trim()) {
        internacionData.diagnostico_ingreso = diagnosticoTextoLibre.trim();
      }
      
      await createInternacion(internacionData);

      onSuccess();
      onClose();
    } catch (err: any) {
      // Manejar errores de validación del backend
      let errorMsg = 'Error al ingresar paciente';
      
      if (err.response?.data) {
        const data = err.response.data;
        
        // Error de cama no disponible
        if (data.cama) {
          errorMsg = Array.isArray(data.cama) ? data.cama[0] : data.cama;
        }
        // Error de paciente ya internado
        else if (data.paciente) {
          errorMsg = Array.isArray(data.paciente) ? data.paciente[0] : data.paciente;
        }
        // Error de diagnóstico
        else if (data.diagnostico_cie || data.diagnostico_ingreso) {
          errorMsg = Array.isArray(data.diagnostico_cie) 
            ? data.diagnostico_cie[0] 
            : Array.isArray(data.diagnostico_ingreso)
            ? data.diagnostico_ingreso[0]
            : 'Debe proporcionar un diagnóstico CIE-10 o un diagnóstico de ingreso';
        }
        // Error general
        else if (data.error || data.detail || data.message) {
          errorMsg = data.error || data.detail || data.message;
        }
        // Errores de validación múltiples
        else if (typeof data === 'object') {
          const firstError = Object.values(data)[0];
          errorMsg = Array.isArray(firstError) ? firstError[0] : String(firstError);
        }
      } else if (err.message) {
        errorMsg = err.message;
      }
      
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Ingresar Paciente - {cama?.nombre} {cama?.sector && `(Sector: ${typeof cama.sector === 'object' ? cama.sector.nombre : cama.sector_nombre || 'N/A'})`}
      </DialogTitle>
      <DialogContent>
        <>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box sx={{ mb: 2, mt: 1 }}>
            <Autocomplete
              options={pacienteOptions}
              getOptionLabel={getPacienteLabel}
              value={selectedPaciente ?? null}
              inputValue={pacienteInputValue}
              onChange={(event, newValue) => {
                setSelectedPaciente(newValue);
                pacienteInputReason.current = 'selection';
                if (newValue) {
                  setPacienteInputValue(getPacienteLabel(newValue));
                } else {
                  setPacienteInputValue('');
                }
              }}
              onInputChange={(_, newInputValue, reason) => {
                if (reason === 'input') {
                  pacienteInputReason.current = 'input';
                  setPacienteInputValue(newInputValue);
                } else if (reason === 'clear') {
                  pacienteInputReason.current = 'clear';
                  setPacienteInputValue('');
                  setPacienteOptions([]);
                }
              }}
              size="small"
              fullWidth
              loading={searchingPacientes}
              renderInput={(params) => (
                <TextField 
                  {...params} 
                  label="Paciente *" 
                  required
                  placeholder="Escriba al menos 2 caracteres para buscar..."
                />
              )}
              renderOption={(props, option) => (
                <li {...props} key={option.id}>
                  {getPacienteLabel(option)}
                </li>
              )}
              isOptionEqualToValue={(option, value) => option.id === value?.id}
              noOptionsText={
                searchingPacientes 
                  ? "Buscando pacientes..." 
                  : pacienteInputValue.length < 2 
                    ? "Escriba al menos 2 caracteres para buscar"
                    : "No se encontraron pacientes"
              }
              filterOptions={(options) => options} // No filtrar, el servidor ya filtra
            />
          </Box>

          <Box sx={{ mb: 2 }}>
            <Autocomplete
              options={medicoOptions}
              getOptionLabel={getMedicoLabel}
              value={selectedMedico ?? null}
              inputValue={medicoInputValue}
              onChange={(event, newValue) => {
                setSelectedMedico(newValue);
                medicoInputReason.current = 'selection';
                if (newValue) {
                  setMedicoInputValue(getMedicoLabel(newValue));
                } else {
                  setMedicoInputValue('');
                }
              }}
              onInputChange={(_, newInputValue, reason) => {
                if (reason === 'input') {
                  medicoInputReason.current = 'input';
                  setMedicoInputValue(newInputValue);
                } else if (reason === 'clear') {
                  medicoInputReason.current = 'clear';
                  setMedicoInputValue('');
                  setMedicoOptions([]);
                }
              }}
              size="small"
              fullWidth
              loading={searchingMedicos}
              renderInput={(params) => (
                <TextField 
                  {...params} 
                  label="Médico" 
                  placeholder="Escriba al menos 2 caracteres para buscar (opcional)"
                />
              )}
              renderOption={(props, option) => (
                <li {...props} key={option.id}>
                  {getMedicoLabel(option)}
                </li>
              )}
              isOptionEqualToValue={(option, value) => option.id === value?.id}
              noOptionsText={
                searchingMedicos 
                  ? "Buscando médicos..." 
                  : medicoInputValue.length < 2 
                    ? "Escriba al menos 2 caracteres para buscar (opcional)"
                    : "No se encontraron médicos"
              }
              filterOptions={(options) => options} // No filtrar, el servidor ya filtra
            />
          </Box>

          <Box sx={{ mb: 2 }}>
            <Autocomplete
              options={diagnosticoOptions}
              getOptionLabel={getDiagnosticoLabel}
              value={selectedDiagnostico ?? null}
              inputValue={diagnosticoInputValue}
              onChange={(event, newValue) => {
                setSelectedDiagnostico(newValue);
                diagnosticoInputReason.current = 'selection';
                if (newValue) {
                  setDiagnosticoInputValue(getDiagnosticoLabel(newValue));
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
                }
              }}
              size="small"
              fullWidth
              loading={searchingDiagnosticos}
              renderInput={(params) => (
                <TextField 
                  {...params} 
                  label="Diagnóstico CIE-10 *" 
                  required
                  placeholder="Escriba al menos 2 caracteres para buscar (código o descripción)..."
                />
              )}
              renderOption={(props, option) => (
                <li {...props} key={option.id}>
                  {getDiagnosticoLabel(option)}
                </li>
              )}
              isOptionEqualToValue={(option, value) => option.id === value?.id}
              noOptionsText={
                searchingDiagnosticos 
                  ? "Buscando diagnósticos..." 
                  : diagnosticoInputValue.length < 2 
                    ? "Escriba al menos 2 caracteres para buscar"
                    : "No se encontraron diagnósticos"
              }
              filterOptions={(options) => options} // No filtrar, el servidor ya filtra
            />
          </Box>

          <TextField
            fullWidth
            multiline
            rows={3}
            label="Diagnóstico adicional (texto libre)"
            value={diagnosticoTextoLibre}
            onChange={(e) => setDiagnosticoTextoLibre(e.target.value)}
            sx={{ mb: 2 }}
            placeholder="Opcional: agregue información adicional al diagnóstico CIE-10"
            helperText="Use este campo solo si necesita agregar información adicional al diagnóstico CIE-10 seleccionado"
          />
        </>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || !selectedPaciente || (!selectedDiagnostico && !diagnosticoTextoLibre.trim())}
        >
          {loading ? <CircularProgress size={20} /> : 'Ingresar'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalIngresarPaciente;
