import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  TextField,
  Snackbar,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Visibility,
  Close,
  Person,
  Phone,
  Email,
  LocationOn,
  LocalHospital,
  CalendarToday,
  Science,
  Check,
  Edit,
  MedicalServices,
  Refresh,
  Assignment,
  Description,
} from '@mui/icons-material';
import { Paciente, Atencion } from '../types';
import { updatePaciente } from '../services/apiService';
import { apiService } from '../services/api';
import { useData } from '../contexts/DataContext';
import { canUpdatePacienteDemographics } from '../utils/permissions';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`patient-tabpanel-${index}`}
      aria-labelledby={`patient-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

interface PatientIntegratedViewProps {
  paciente: Paciente;
  /** En vista página el botón volver lo provee el layout (PatientDashboard) */
  onClose?: () => void;
  /** dialog: ficha en modal. page: ficha embebida en Patient 360 */
  variant?: 'dialog' | 'page';
}

const PatientIntegratedView: React.FC<PatientIntegratedViewProps> = ({ paciente, onClose, variant = 'dialog' }) => {
  const isPage = variant === 'page';
  const { currentUser } = useData();
  const canEditDemographics = canUpdatePacienteDemographics(currentUser);
  const [tabValue, setTabValue] = useState(0);
  const [atenciones, setAtenciones] = useState<Atencion[]>([]);
  const [loadingAtenciones, setLoadingAtenciones] = useState(false);
  const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);
  const [analisisLims, setAnalisisLims] = useState<any[]>([]);
  const [loadingAnalisis, setLoadingAnalisis] = useState(false);
  const [showResultadosDialog, setShowResultadosDialog] = useState(false);
  const [selectedAnalisis, setSelectedAnalisis] = useState<any>(null);
  const [resultadosDetallados, setResultadosDetallados] = useState<any[]>([]);
  const [loadingResultados, setLoadingResultados] = useState(false);
  
  // Estados para edición
  const [isEditing, setIsEditing] = useState(false);
  const [editedPaciente, setEditedPaciente] = useState<Paciente>(paciente);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [showSnackbar, setShowSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  

  // Función para cargar atenciones del paciente
  const loadAtenciones = useCallback(async () => {
    setLoadingAtenciones(true);
    try {
      const response = await apiService.getAtenciones({ paciente: paciente.id });
      const data = response.results || [];
      setAtenciones(data);
    } catch {
      setAtenciones([]);
    } finally {
      setLoadingAtenciones(false);
    }
  }, [paciente.id]);

  const loadResultadosDetallados = useCallback(async (solicitudId: number, solicitudInfo?: any) => {
    setLoadingResultados(true);
    try {
      const response = await fetch(`http://localhost:8001/api/laboratorio/resultados/?solicitud=${solicitudId}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Extraer todos los detalles de todos los resultados y aplanar el array
      const resultados = data.results || data || [];
      
      // Crear un mapa para poder acceder a la fecha del resultado
      const resultadosMap = new Map();
      resultados.forEach((resultado: any) => {
        resultadosMap.set(resultado.id, resultado);
      });
      
      const detallesPlanos = resultados.flatMap((resultado: any) => {
        // Agregar referencia a la fecha del resultado padre
        return (resultado.detalles || []).map((detalle: any) => ({
          ...detalle,
          _resultado_fecha: resultado.fecha_inicio_procesamiento,
          _resultado_id: resultado.id
        }));
      });
      
      // Filtrar resultados duplicados: mantener solo el más reciente por tipo de examen
      const detallesPorExamen = new Map();
      detallesPlanos.forEach((detalle: any) => {
        const examenId = detalle.tipo_examen_detail?.id || detalle.tipo_examen;
        const detalleActual = detallesPorExamen.get(examenId);
        const fechaActual = new Date(detalle._resultado_fecha || 0);
        const fechaExistente = new Date(detalleActual?._resultado_fecha || 0);
        
        if (!detalleActual || fechaActual > fechaExistente) {
          detallesPorExamen.set(examenId, detalle);
        }
      });
      
      const detallesFiltrados = Array.from(detallesPorExamen.values());
      
      // Filtrar solo los exámenes presentes en la solicitud actual
      // (exámenes individuales + todos los exámenes de los paneles actuales)
      let detallesFinales = detallesFiltrados;
      if (solicitudInfo) {
        try {
          // Obtener IDs de exámenes individuales
          const examenesIndividuales = new Set<number>();
          solicitudInfo.tipos_examen_detalle?.forEach((examen: any) => {
            const idNum = typeof examen.id === 'number' ? examen.id : Number(examen.id);
            if (!isNaN(idNum)) examenesIndividuales.add(idNum);
          });
          
          // Para los paneles, necesitamos cargar los componentes de cada panel
          const examenesPaneles = new Set<number>();
          if (solicitudInfo.paneles_detalle && solicitudInfo.paneles_detalle.length > 0) {
            const panelPromises = solicitudInfo.paneles_detalle.map(async (panel: any) => {
              try {
                const response = await fetch(`http://localhost:8001/api/laboratorio/componentes_panel/?panel=${panel.id}`);
                const data = await response.json();
                const componentes = data.results || data;
                if (Array.isArray(componentes)) {
                  componentes.forEach((comp: any) => {
                    const examenId = comp.tipo_examen?.id;
                    const idNum = typeof examenId === 'number' ? examenId : Number(examenId);
                    if (!isNaN(idNum)) {
                      examenesPaneles.add(idNum);
                    }
                  });
                }
              } catch {
                // Panel sin componentes cargables; continuar con el resto
              }
            });
            
            await Promise.all(panelPromises);
          }
          
          // Combinar exámenes individuales y de paneles (sin usar spread en Set para compatibilidad TS)
          const examenesSolicitados = new Set<number>();
          examenesIndividuales.forEach((id: number) => examenesSolicitados.add(id));
          examenesPaneles.forEach((id: number) => examenesSolicitados.add(id));
          
          // Filtrar detalles por exámenes solicitados
          detallesFinales = detallesFiltrados.filter((detalle: any) => {
            const examenId = detalle.tipo_examen_detail?.id || detalle.tipo_examen;
            return examenesSolicitados.has(examenId);
          });
        } catch {
          // Si hay error, usar todos los detalles (comportamiento anterior)
          detallesFinales = detallesFiltrados;
        }
      }
      
      setResultadosDetallados(detallesFinales);
    } catch {
      setResultadosDetallados([]);
    } finally {
      setLoadingResultados(false);
    }
  }, []);

  // Cargar atenciones del paciente
  useEffect(() => {
    loadAtenciones();
  }, [paciente.id, loadAtenciones]);

  // Función para recargar análisis manualmente
  const loadAnalisisLims = useCallback(async () => {
    setLoadingAnalisis(true);
    try {
      const response = await fetch(`http://localhost:8000/api/integracion-lims/analisis/paciente/${paciente.id}/`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      });
      
      if (!response.ok) {
        // Si es un 502, el LIMS no está disponible (esperado si no está corriendo)
        if (response.status === 502) {
          setAnalisisLims([]);
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setAnalisisLims(data.analisis || []);
    } catch {
      setAnalisisLims([]);
    } finally {
      setLoadingAnalisis(false);
    }
  }, [paciente.id]);

  // Cargar análisis del LIMS del paciente (carga inicial)
  useEffect(() => {
    if (paciente && paciente.id) {
      loadAnalisisLims();
    }
  }, [paciente.id, loadAnalisisLims]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Recargar análisis cuando se cambia a la pestaña de análisis de laboratorio
    if (newValue === 2 && paciente && paciente.id) {
      loadAnalisisLims();
    }
  };

  const handleOpenAtencion = (id: number) => {
    setSelectedAtencionId(id);
  };

  const handleCloseAtencion = () => {
    setSelectedAtencionId(null);
    // Recargar atenciones después de cerrar para reflejar cambios
    loadAtenciones();
  };

  // Función para cerrar el diálogo de resultados y recargar análisis
  const handleCloseResultados = () => {
    setShowResultadosDialog(false);
    setSelectedAnalisis(null);
    // Recargar análisis después de cerrar el diálogo para reflejar cambios
    if (paciente && paciente.id) {
      loadAnalisisLims();
    }
  };

  const formatDateTime = (value?: string | null) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  };

  const getEstadoColor = (estado?: string) => {
    switch (estado) {
      case 'ABIERTA': return 'success';
      case 'FINALIZADA': return 'default';
      case 'EN_REVISION': return 'warning';
      default: return 'default';
    }
  };

  const getTipoChipColor = (tipo?: string) => {
    switch (tipo) {
      case 'CONSULTA': return 'primary';
      case 'ESTUDIO': return 'info';
      case 'PROCEDIMIENTO': return 'warning';
      case 'CIRUGIA': return 'error';
      default: return 'default';
    }
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-ES');
  };

  // Funciones para edición
  const handleEditToggle = () => {
    setIsEditing(!isEditing);
    if (isEditing) {
      setEditingField(null);
    }
  };

  const handleFieldEdit = (field: string) => {
    if (!canEditDemographics) return;
    if (!isEditing) {
      setSnackbarMessage('Activa el modo edición para poder editar campos');
      setShowSnackbar(true);
      return;
    }
    setEditingField(field);
  };

  const handleFieldSave = async (field: string) => {
    try {
      await updatePaciente(paciente.id, {
        [field]: editedPaciente[field as keyof Paciente]
      });

      setSnackbarMessage('Campo actualizado exitosamente');
      setShowSnackbar(true);
      setEditingField(null);
      // Actualizar el paciente original
      Object.assign(paciente, editedPaciente);
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Error desconocido';
      setSnackbarMessage(`Error al actualizar: ${errorMessage}`);
      setShowSnackbar(true);
    }
  };

  const handleFieldCancel = () => {
    setEditedPaciente(paciente);
    setEditingField(null);
  };

  const handleFieldChange = (field: string, value: any) => {
    setEditedPaciente(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Componente para campos editables
  const EditableField: React.FC<{
    field: string;
    label: string;
    value: any;
    type?: 'text' | 'email' | 'tel';
    multiline?: boolean;
  }> = ({ field, label, value, type = 'text', multiline = false }) => {
    const isEditing = editingField === field;
    
    if (isEditing) {
      return (
        <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, width: '100%', mt: 0.5 }}>
          <TextField
            size="small"
            type={type}
            multiline={multiline}
            rows={multiline ? 3 : 1}
            value={editedPaciente[field as keyof Paciente] || ''}
            onChange={(e) => handleFieldChange(field, e.target.value)}
            autoFocus
            sx={{ minWidth: 200 }}
            inputProps={{
              // Asegurar que se acepten todos los caracteres Unicode, incluyendo ñ y Ñ
              lang: 'es',
              spellCheck: false,
            }}
            // Asegurar que no haya restricciones de caracteres
            onCompositionStart={(e) => {
              // Permitir composición de caracteres (necesario para algunos métodos de entrada)
              e.stopPropagation();
            }}
            onCompositionEnd={(e) => {
              // Permitir composición de caracteres
              e.stopPropagation();
            }}
          />
          <IconButton size="small" onClick={() => handleFieldSave(field)} color="success">
            <Check />
          </IconButton>
          <IconButton size="small" onClick={handleFieldCancel} color="error">
            <Close />
          </IconButton>
        </Box>
      );
    }
    
    return (
      <Box
        component="span"
        sx={{ 
          cursor: canEditDemographics ? 'pointer' : 'default',
          '&:hover': canEditDemographics ? { backgroundColor: 'action.hover' } : undefined,
          borderRadius: 1,
          p: 0.5,
          display: 'inline-flex',
          alignItems: 'center',
          opacity: canEditDemographics ? 0.7 : 1,
        }}
        onDoubleClick={() => canEditDemographics && handleFieldEdit(field)}
      >
        <Typography component="span" variant="body2">
          {value || 'No especificado'}
        </Typography>
      </Box>
    );
  };


  const handleCloseFicha = () => {
    if (onClose) onClose();
  };

  const tabbedSection = (
    <>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="patient tabs">
            <Tab 
              label="Información Personal" 
              icon={<Person />} 
              iconPosition="start"
            />
            <Tab 
              label="Atenciones" 
              icon={<MedicalServices />} 
              iconPosition="start"
            />
            <Tab 
              label="Análisis de Laboratorio" 
              icon={<Science />} 
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Tab 1: Información Personal */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Botón de modo edición */}
            {canEditDemographics && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
              <Button
                variant={isEditing ? "contained" : "outlined"}
                startIcon={<Edit />}
                onClick={handleEditToggle}
                color={isEditing ? "error" : "primary"}
              >
                {isEditing ? 'Finalizar Edición' : 'Modo Edición'}
              </Button>
            </Box>
            )}

            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
              <Box sx={{ flex: 1 }}>
                <Card>
                  <CardHeader title="Datos Personales" />
                  <CardContent>
                    <List>
                      <ListItem>
                        <ListItemIcon>
                          <Person />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Nombre"
                          secondary={
                            editingField !== 'nombre' ? (
                              <EditableField
                                field="nombre"
                                label="Nombre"
                                value={editedPaciente.nombre}
                              />
                            ) : null
                          }
                        />
                        {editingField === 'nombre' && (
                          <Box sx={{ flex: 1, ml: 2 }}>
                            <EditableField
                              field="nombre"
                              label="Nombre"
                              value={editedPaciente.nombre}
                            />
                          </Box>
                        )}
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <Person />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Apellido"
                          secondary={
                            editingField !== 'apellido' ? (
                              <EditableField
                                field="apellido"
                                label="Apellido"
                                value={editedPaciente.apellido}
                              />
                            ) : null
                          }
                        />
                        {editingField === 'apellido' && (
                          <Box sx={{ flex: 1, ml: 2 }}>
                            <EditableField
                              field="apellido"
                              label="Apellido"
                              value={editedPaciente.apellido}
                            />
                          </Box>
                        )}
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <CalendarToday />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Fecha de Nacimiento"
                          secondary={formatDate(editedPaciente.fecha_nacimiento)}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <Person />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Sexo"
                          secondary={
                            editingField !== 'sexo' ? (
                              <Box sx={{ display: 'inline-flex', alignItems: 'center', mt: 0.5 }}>
                                <Chip 
                                  label={
                                    editedPaciente.sexo === 'M' ? 'Masculino' :
                                    editedPaciente.sexo === 'F' ? 'Femenino' :
                                    editedPaciente.sexo === 'O' ? 'Otro' :
                                    'No informado'
                                  } 
                                  color={
                                    editedPaciente.sexo === 'M' ? 'primary' :
                                    editedPaciente.sexo === 'F' ? 'secondary' :
                                    'default'
                                  }
                                  size="small"
                                  onClick={() => canEditDemographics && isEditing && handleFieldEdit('sexo')}
                                  sx={{ cursor: canEditDemographics && isEditing ? 'pointer' : 'default' }}
                                />
                              </Box>
                            ) : null
                          }
                        />
                        {editingField === 'sexo' && (
                          <Box sx={{ flex: 1, ml: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                            <FormControl size="small" sx={{ minWidth: 150 }}>
                              <InputLabel>Sexo</InputLabel>
                              <Select
                                value={editedPaciente.sexo || ''}
                                onChange={(e) => handleFieldChange('sexo', e.target.value)}
                                label="Sexo"
                                autoFocus
                              >
                                <MenuItem value="">No especificado</MenuItem>
                                <MenuItem value="M">Masculino</MenuItem>
                                <MenuItem value="F">Femenino</MenuItem>
                                <MenuItem value="O">Otro</MenuItem>
                              </Select>
                            </FormControl>
                            <IconButton size="small" onClick={() => handleFieldSave('sexo')} color="success">
                              <Check />
                            </IconButton>
                            <IconButton size="small" onClick={handleFieldCancel} color="error">
                              <Close />
                            </IconButton>
                          </Box>
                        )}
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Box>

              <Box sx={{ flex: 1 }}>
                <Card>
                  <CardHeader title="Información de Contacto" />
                  <CardContent>
                    <List>
                      <ListItem>
                        <ListItemIcon>
                          <Phone />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Teléfono"
                          secondary={
                            editingField !== 'telefono' ? (
                              <EditableField
                                field="telefono"
                                label="Teléfono"
                                value={editedPaciente.telefono}
                                type="tel"
                              />
                            ) : null
                          }
                        />
                        {editingField === 'telefono' && (
                          <Box sx={{ flex: 1, ml: 2 }}>
                            <EditableField
                              field="telefono"
                              label="Teléfono"
                              value={editedPaciente.telefono}
                              type="tel"
                            />
                          </Box>
                        )}
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <Email />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Email"
                          secondary={
                            editingField !== 'email' ? (
                              <EditableField
                                field="email"
                                label="Email"
                                value={editedPaciente.email}
                                type="email"
                              />
                            ) : null
                          }
                        />
                        {editingField === 'email' && (
                          <Box sx={{ flex: 1, ml: 2 }}>
                            <EditableField
                              field="email"
                              label="Email"
                              value={editedPaciente.email}
                              type="email"
                            />
                          </Box>
                        )}
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          <LocationOn />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Dirección"
                          secondary={
                            editingField !== 'direccion' ? (
                              <EditableField
                                field="direccion"
                                label="Dirección"
                                value={editedPaciente.direccion}
                                multiline
                              />
                            ) : null
                          }
                        />
                        {editingField === 'direccion' && (
                          <Box sx={{ flex: 1, ml: 2 }}>
                            <EditableField
                              field="direccion"
                              label="Dirección"
                              value={editedPaciente.direccion}
                              multiline
                            />
                          </Box>
                        )}
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Box>
            </Box>

            <Box>
              <Card>
                <CardHeader title="Información Médica" />
                <CardContent>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <LocalHospital />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Obra Social"
                        secondary={
                          editingField !== 'obra_social' ? (
                            <EditableField
                              field="obra_social"
                              label="Obra Social"
                              value={editedPaciente.obra_social}
                            />
                          ) : null
                        }
                      />
                      {editingField === 'obra_social' && (
                        <Box sx={{ flex: 1, ml: 2 }}>
                          <EditableField
                            field="obra_social"
                            label="Obra Social"
                            value={editedPaciente.obra_social}
                          />
                        </Box>
                      )}
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <Assignment />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Número de Afiliado"
                        secondary={
                          editingField !== 'numero_afiliado' ? (
                            <EditableField
                              field="numero_afiliado"
                              label="Número de Afiliado"
                              value={editedPaciente.numero_afiliado}
                            />
                          ) : null
                        }
                      />
                      {editingField === 'numero_afiliado' && (
                        <Box sx={{ flex: 1, ml: 2 }}>
                          <EditableField
                            field="numero_afiliado"
                            label="Número de Afiliado"
                            value={editedPaciente.numero_afiliado}
                          />
                        </Box>
                      )}
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <Description />
                      </ListItemIcon>
                      <ListItemText 
                        primary="Observaciones"
                        secondary={
                          editingField !== 'observaciones' ? (
                            <EditableField
                              field="observaciones"
                              label="Observaciones"
                              value={editedPaciente.observaciones}
                              multiline
                            />
                          ) : null
                        }
                      />
                      {editingField === 'observaciones' && (
                        <Box sx={{ flex: 1, ml: 2 }}>
                          <EditableField
                            field="observaciones"
                            label="Observaciones"
                            value={editedPaciente.observaciones}
                            multiline
                          />
                        </Box>
                      )}
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Box>
          </Box>
        </TabPanel>

        {/* Tab 2: Atenciones */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Atenciones Médicas ({atenciones.length})
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Historial completo de atenciones clínicas del paciente (consultas, estudios, procedimientos, cirugías)
            </Typography>
          </Box>

          {loadingAtenciones ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : atenciones.length === 0 ? (
            <Alert severity="info">
              No hay atenciones médicas registradas para este paciente.
            </Alert>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Fecha</TableCell>
                    <TableCell>Médico</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Recurso / Ubicación</TableCell>
                    <TableCell align="right">Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {atenciones.map((atencion) => (
                    <TableRow key={atencion.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {formatDateTime(atencion.fecha_admision)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {atencion.fecha_cierre ? `Cierre: ${formatDateTime(atencion.fecha_cierre)}` : 'Sin cierre'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {atencion.medico_principal ? (
                          <Typography variant="body2">
                            Dr. {atencion.medico_principal.apellido || ''}, {atencion.medico_principal.nombre || ''}
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Médico no disponible
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={
                            atencion.tipo_intervencion === 'CONSULTA' ? 'Consulta Ambulatoria' :
                            atencion.tipo_intervencion === 'ESTUDIO' ? 'Estudio Médico' :
                            atencion.tipo_intervencion === 'PROCEDIMIENTO' ? 'Procedimiento' :
                            atencion.tipo_intervencion === 'CIRUGIA' ? 'Cirugía' :
                            atencion.tipo_intervencion
                          }
                          color={getTipoChipColor(atencion.tipo_intervencion) as any}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={
                            atencion.estado_clinico === 'ABIERTA' ? 'Abierta' :
                            atencion.estado_clinico === 'FINALIZADA' ? 'Finalizada' :
                            atencion.estado_clinico === 'EN_REVISION' ? 'En revisión' :
                            atencion.estado_clinico
                          }
                          color={getEstadoColor(atencion.estado_clinico) as any}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {atencion.turno?.recurso?.nombre ?? '—'}
                        </Typography>
                        {atencion.turno?.recurso?.ubicacion_display && (
                          <Typography variant="caption" color="text.secondary">
                            {atencion.turno.recurso.ubicacion_display}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleOpenAtencion(atencion.id)}
                          color="primary"
                          title="Ver detalle"
                        >
                          <Visibility />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Tab 3: Análisis de Laboratorio */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h6" gutterBottom>
                Análisis de Laboratorio ({analisisLims.length})
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Resultados de exámenes de laboratorio del LIMS
              </Typography>
            </Box>
            <Button
              variant="outlined"
              size="small"
              startIcon={<Refresh />}
              onClick={loadAnalisisLims}
              disabled={loadingAnalisis}
              sx={{ ml: 2 }}
            >
              {loadingAnalisis ? 'Actualizando...' : 'Actualizar'}
            </Button>
          </Box>

          {loadingAnalisis ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : analisisLims.length === 0 ? (
            <Alert severity="info">
              No hay análisis de laboratorio registrados para este paciente.
            </Alert>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Número</TableCell>
                    <TableCell>Fecha</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Médico</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analisisLims.map((analisis) => (
                    <TableRow key={analisis.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {analisis.numero || analisis.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatDate(analisis.fecha_solicitud)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={analisis.estado}
                          color={
                            analisis.estado === 'COMPLETADA' ? 'success' :
                            analisis.estado === 'EN_PROCESO' ? 'warning' :
                            analisis.estado === 'PENDIENTE' ? 'info' : 'default'
                          }
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {analisis.medico_nombre || 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<Science />}
                          onClick={async () => {
                            setSelectedAnalisis(analisis);
                            setShowResultadosDialog(true);
                            await loadResultadosDetallados(analisis.id, analisis);
                          }}
                        >
                          Ver Resultados
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>
    </>
  );

  return (
    <>
      {!isPage ? (
        <Dialog
          open
          onClose={onClose ?? (() => undefined)}
          maxWidth="lg"
          fullWidth
          PaperProps={{
            sx: { height: '90vh' }
          }}
        >
          <DialogTitle sx={{ position: 'relative' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar sx={{ bgcolor: 'primary.main' }}>
                {paciente.nombre?.charAt(0)}{paciente.apellido?.charAt(0)}
              </Avatar>
              <Box>
                <Typography variant="h6">
                  {paciente.nombre} {paciente.apellido}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  DNI: {paciente.dni} | ID: {paciente.id}
                </Typography>
              </Box>
            </Box>
            {onClose && (
              <IconButton
                onClick={onClose}
                sx={{
                  position: 'absolute',
                  right: 8,
                  top: 8,
                  color: 'grey.500'
                }}
              >
                <Close />
              </IconButton>
            )}
          </DialogTitle>

          <DialogContent sx={{ p: 0 }}>{tabbedSection}</DialogContent>
          <DialogActions>
            <Button onClick={handleCloseFicha}>Cerrar</Button>
          </DialogActions>
        </Dialog>
      ) : (
        <Box sx={{ width: '100%' }}>{tabbedSection}</Box>
      )}

      {/* AtencionDetailDrawer para mostrar detalles de atenciones */}
      <AtencionDetailDrawer
        atencionId={selectedAtencionId}
        open={Boolean(selectedAtencionId)}
        onClose={handleCloseAtencion}
        currentUserRole={currentUser?.rol}
      />

      {/* Dialog para mostrar resultados detallados del LIMS */}
      <Dialog
        open={showResultadosDialog}
        onClose={handleCloseResultados}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Science color="primary" />
              <Typography variant="h6">
                Resultados Detallados - {selectedAnalisis?.numero || selectedAnalisis?.id}
              </Typography>
            </Box>
            <IconButton 
              onClick={handleCloseResultados}
              sx={{ color: 'grey.500' }}
            >
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedAnalisis && (
            <Box sx={{ mt: 2 }}>
              {/* Información general */}
              <Card sx={{ mb: 3 }}>
                <CardHeader title="Información General" />
                <CardContent>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box sx={{ display: 'flex', gap: 4 }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="textSecondary">Número de Solicitud</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {selectedAnalisis.numero || selectedAnalisis.id}
                        </Typography>
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="textSecondary">Fecha</Typography>
                        <Typography variant="body1">
                          {formatDate(selectedAnalisis.fecha_solicitud)}
                        </Typography>
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 4 }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="textSecondary">Estado</Typography>
                        <Chip
                          label={selectedAnalisis.estado}
                          color={
                            selectedAnalisis.estado === 'COMPLETADA' ? 'success' :
                            selectedAnalisis.estado === 'EN_PROCESO' ? 'warning' :
                            selectedAnalisis.estado === 'PENDIENTE' ? 'info' : 'default'
                          }
                          size="small"
                        />
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="textSecondary">Médico</Typography>
                        <Typography variant="body1">
                          {selectedAnalisis.medico_nombre || 'N/A'}
                        </Typography>
                      </Box>
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary">Prioridad</Typography>
                      <Typography variant="body1">
                        {selectedAnalisis.prioridad || 'NORMAL'}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>

              {/* Exámenes agrupados por panel */}
              <Card sx={{ mb: 3 }}>
                <CardHeader title="🔬 Exámenes por Panel" />
                <CardContent>
                  {loadingResultados ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                      <CircularProgress />
                      <Typography variant="body2" sx={{ ml: 2 }}>
                        Cargando resultados...
                      </Typography>
                    </Box>
                  ) : resultadosDetallados.length > 0 ? (
                    <>
                      {/* Agrupar exámenes por panel */}
                      {(() => {
                        // Crear un mapa de paneles con sus exámenes
                        const examenesPorPanel: { [key: string]: any[] } = {};
                        const panelInfo: { [key: string]: any } = {};
                        
                        // Primero, obtener info de paneles
                        selectedAnalisis.paneles_detalle?.forEach((panel: any) => {
                          panelInfo[panel.id] = panel;
                          examenesPorPanel[panel.id] = [];
                        });
                        
                        // Agrupar exámenes por panel
                        resultadosDetallados.forEach((resultado: any) => {
                          // Buscar a qué panel pertenece este examen
                          let panelId = 'individual'; // Para exámenes individuales
                          
                          selectedAnalisis.paneles_detalle?.forEach((panel: any) => {
                            const tipoExamenId = resultado.tipo_examen_detail?.id || resultado.tipo_examen?.id || resultado.tipo_examen;
                            if (panel.componentes?.some((comp: any) => comp.tipo_examen?.id === tipoExamenId)) {
                              panelId = panel.id;
                            }
                          });
                          
                          if (!examenesPorPanel[panelId]) {
                            examenesPorPanel[panelId] = [];
                          }
                          examenesPorPanel[panelId].push(resultado);
                        });
                        
                        return Object.entries(examenesPorPanel).map(([panelId, examenes]) => {
                          if (examenes.length === 0) return null;
                          
                          const panel = panelInfo[panelId];
                          
                          return (
                            <Box key={panelId} sx={{ mb: 3 }}>
                              {/* Encabezado del panel */}
                              {panel && (
                                <Box sx={{ 
                                  backgroundColor: 'primary.main', 
                                  color: 'white', 
                                  p: 1.5, 
                                  borderRadius: '4px 4px 0 0',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 1
                                }}>
                                  <Science />
                                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                    {panel.codigo} - {panel.nombre}
                                  </Typography>
                                </Box>
                              )}
                              
                              {/* Tabla de exámenes del panel */}
                              <TableContainer component={Paper} variant="outlined" sx={{ 
                                borderRadius: panel ? '0 0 4px 4px' : '4px',
                                borderTop: panel ? 'none' : undefined
                              }}>
                                <Table size="small">
                                  {!panel && (
                                    <TableHead>
                                      <TableRow>
                                        <TableCell><strong>Examen</strong></TableCell>
                                        <TableCell><strong>Resultado</strong></TableCell>
                                        <TableCell><strong>Unidad</strong></TableCell>
                                        <TableCell><strong>Rango Normal</strong></TableCell>
                                        <TableCell><strong>Estado</strong></TableCell>
                                      </TableRow>
                                    </TableHead>
                                  )}
                                  <TableBody>
                                    {examenes.map((resultado: any, index: number) => {
                                      // Soporte para tipo_examen_detail o tipo_examen
                                      const tipoExamen = resultado.tipo_examen_detail || resultado.tipo_examen;
                                      const esObjeto = typeof tipoExamen === 'object';
                                      return (
                                        <TableRow key={index} hover sx={{ 
                                          backgroundColor: (t) =>
                                            panel ? t.palette.action.hover : t.palette.background.paper
                                        }}>
                                          <TableCell>
                                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                              {esObjeto ? (tipoExamen.codigo || 'N/A') : 'N/A'} - {esObjeto ? (tipoExamen.nombre || 'Sin nombre') : 'Sin nombre'}
                                            </Typography>
                                          </TableCell>
                                          <TableCell>
                                            <Typography variant="body2" sx={{
                                              fontWeight: 600,
                                              color: resultado.valor_resultado ? 'primary.main' : 'text.secondary'
                                            }}>
                                              {resultado.valor_resultado || 'Sin resultado'}
                                            </Typography>
                                          </TableCell>
                                          <TableCell>
                                            <Typography variant="body2">
                                              {esObjeto ? (tipoExamen.unidad_medida || 'N/A') : 'N/A'}
                                            </Typography>
                                          </TableCell>
                                          <TableCell>
                                            <Typography variant="body2">
                                              {esObjeto && tipoExamen.rango_referencia_min && tipoExamen.rango_referencia_max
                                                ? `${tipoExamen.rango_referencia_min} - ${tipoExamen.rango_referencia_max}`
                                                : esObjeto ? (tipoExamen.rango_referencia_texto || 'N/A') : 'N/A'
                                              }
                                            </Typography>
                                          </TableCell>
                                          <TableCell>
                                            <Chip
                                              label={resultado.valor_resultado ? 'Completado' : 'Pendiente'}
                                              color={resultado.valor_resultado ? 'success' : 'warning'}
                                              size="small"
                                            />
                                          </TableCell>
                                        </TableRow>
                                      );
                                    })}
                                  </TableBody>
                                </Table>
                              </TableContainer>
                            </Box>
                          );
                        }).filter(Boolean);
                      })()}
                    </>
                  ) : (
                    <Alert severity="info">
                      No hay resultados disponibles para esta solicitud.
                    </Alert>
                  )}
                </CardContent>
              </Card>

              {/* Observaciones */}
              {selectedAnalisis.observaciones && (
                <Card>
                  <CardHeader title="📝 Observaciones" />
                  <CardContent>
                    <Typography variant="body2" sx={{ p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                      {selectedAnalisis.observaciones || 'Sin observaciones'}
                    </Typography>
                  </CardContent>
                </Card>
              )}
            </Box>
          )}
        </DialogContent>

        <DialogActions>
          {/* Botón de cerrar removido - ahora se usa la X en el header */}
        </DialogActions>
      </Dialog>
      
      {/* Snackbar para mensajes */}
      <Snackbar
        open={showSnackbar}
        autoHideDuration={3000}
        onClose={() => setShowSnackbar(false)}
        message={snackbarMessage}
      />
    </>
  );
};

export default PatientIntegratedView;
