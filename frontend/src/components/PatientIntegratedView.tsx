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
  Stack,
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
import { getSolicitudExamen, listSolicitudesExamen } from '../services/limsApi';
import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';
import { useData } from '../contexts/DataContext';
import { canUpdatePacienteDemographics } from '../utils/permissions';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';
import ResultadosOrdenLista from './lims/ResultadosOrdenLista';

function medicoSolicitudLabel(s: SolicitudExamenLims | null | undefined): string {
  if (!s) return 'N/A';
  return (
    s.medico_display ||
    s.medico_interno_nombre ||
    s.medico_externo_nombre ||
    'N/A'
  );
}

function chipColorEstado(estado: string): 'success' | 'warning' | 'info' | 'default' {
  if (estado === 'FINALIZADO' || estado === 'COMPLETADA') return 'success';
  if (estado === 'EN_PROCESO' || estado === 'INFORMADO_PARCIAL' || estado === 'LISTO_PARA_VALIDAR') {
    return 'warning';
  }
  if (estado === 'PENDIENTE') return 'info';
  return 'default';
}

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
  /** Pestaña inicial: 0 demografía, 1 atenciones, 2 análisis lab */
  initialTab?: number;
}

const PatientIntegratedView: React.FC<PatientIntegratedViewProps> = ({
  paciente,
  onClose,
  variant = 'dialog',
  initialTab = 0,
}) => {
  const isPage = variant === 'page';
  const { currentUser } = useData();
  const canEditDemographics = canUpdatePacienteDemographics(currentUser);
  const [tabValue, setTabValue] = useState(() =>
    initialTab >= 0 && initialTab <= 2 ? initialTab : 0
  );
  const [atenciones, setAtenciones] = useState<Atencion[]>([]);
  const [loadingAtenciones, setLoadingAtenciones] = useState(false);
  const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);
  const [analisisLims, setAnalisisLims] = useState<SolicitudExamenLims[]>([]);
  const [loadingAnalisis, setLoadingAnalisis] = useState(false);
  const [showResultadosDialog, setShowResultadosDialog] = useState(false);
  const [selectedAnalisis, setSelectedAnalisis] = useState<SolicitudExamenLims | null>(null);
  const [resultadosDetallados, setResultadosDetallados] = useState<ResultadoExamenLims[]>([]);
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

  const loadResultadosDetallados = useCallback(async (solicitudId: number) => {
    setLoadingResultados(true);
    try {
      const orden = await getSolicitudExamen(solicitudId);
      setSelectedAnalisis(orden);
      if (orden.resultados_visibles === false) {
        setResultadosDetallados([]);
      } else {
        setResultadosDetallados(orden.resultados || []);
      }
    } catch {
      setResultadosDetallados([]);
    } finally {
      setLoadingResultados(false);
    }
  }, []);

  useEffect(() => {
    if (initialTab >= 0 && initialTab <= 2) {
      setTabValue(initialTab);
    }
  }, [initialTab, paciente.id]);

  useEffect(() => {
    loadAtenciones();
  }, [paciente.id, loadAtenciones]);

  const loadAnalisisLims = useCallback(async () => {
    setLoadingAnalisis(true);
    try {
      const rows = await listSolicitudesExamen({ paciente: paciente.id });
      rows.sort((a, b) => {
        const fa = a.fecha_solicitud || '';
        const fb = b.fecha_solicitud || '';
        return fb.localeCompare(fa);
      });
      setAnalisisLims(rows);
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
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          <Chip
                            size="small"
                            label={
                              atencion.contexto_atencion_display ||
                              (atencion.contexto_atencion === 'GUARDIA'
                                ? 'Guardia'
                                : atencion.contexto_atencion === 'INTERNACION'
                                  ? 'Internación'
                                  : 'Ambulatoria')
                            }
                            color={
                              atencion.contexto_atencion === 'INTERNACION'
                                ? 'warning'
                                : atencion.contexto_atencion === 'GUARDIA'
                                  ? 'error'
                                  : 'info'
                            }
                          />
                          {atencion.tipo_intervencion && atencion.tipo_intervencion !== 'CONSULTA' && (
                            <Chip
                              size="small"
                              label={
                                atencion.tipo_intervencion === 'ESTUDIO'
                                  ? 'Estudio'
                                  : atencion.tipo_intervencion === 'PROCEDIMIENTO'
                                    ? 'Procedimiento'
                                    : atencion.tipo_intervencion === 'CIRUGIA'
                                      ? 'Cirugía'
                                      : atencion.tipo_intervencion
                              }
                              color={getTipoChipColor(atencion.tipo_intervencion) as any}
                              variant="outlined"
                            />
                          )}
                        </Stack>
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
                    <TableCell>Número / perfiles</TableCell>
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
                        <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {(analisis.paneles_nombres || []).slice(0, 4).map((nombre) => (
                            <Chip key={nombre} size="small" label={nombre} variant="outlined" />
                          ))}
                          {(analisis.paneles_nombres?.length || 0) > 4 && (
                            <Chip
                              size="small"
                              label={`+${(analisis.paneles_nombres?.length || 0) - 4}`}
                              variant="outlined"
                            />
                          )}
                          {!analisis.paneles_nombres?.length &&
                            (analisis.tipos_examen_nombres || []).slice(0, 3).map((nombre) => (
                              <Chip key={nombre} size="small" label={nombre} variant="outlined" />
                            ))}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatDate(analisis.fecha_solicitud)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={analisis.estado}
                          color={chipColorEstado(analisis.estado)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {medicoSolicitudLabel(analisis)}
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
                            await loadResultadosDetallados(analisis.id);
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
                          color={chipColorEstado(selectedAnalisis.estado)}
                          size="small"
                        />
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="textSecondary">Médico</Typography>
                        <Typography variant="body1">
                          {medicoSolicitudLabel(selectedAnalisis)}
                        </Typography>
                      </Box>
                    </Box>
                    {(selectedAnalisis.paneles_nombres?.length || selectedAnalisis.origen_solicitud_display) && (
                      <Box sx={{ display: 'flex', gap: 4 }}>
                        {selectedAnalisis.origen_solicitud_display && (
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="subtitle2" color="textSecondary">Origen</Typography>
                            <Typography variant="body1">
                              {selectedAnalisis.origen_solicitud_display}
                            </Typography>
                          </Box>
                        )}
                        {!!selectedAnalisis.paneles_nombres?.length && (
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="subtitle2" color="textSecondary">Paneles</Typography>
                            <Typography variant="body1">
                              {selectedAnalisis.paneles_nombres.join(', ')}
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    )}
                  </Box>
                </CardContent>
              </Card>

              <Card sx={{ mb: 3 }}>
                <CardHeader
                  title="Resultados"
                  subheader="Agrupados por perfil (hemograma, EAB, ionograma, etc.)"
                />
                <CardContent>
                  {loadingResultados ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                      <CircularProgress />
                      <Typography variant="body2" sx={{ ml: 2 }}>
                        Cargando resultados...
                      </Typography>
                    </Box>
                  ) : selectedAnalisis.resultados_visibles === false ? (
                    <Alert severity="info">
                      Los valores se muestran cuando la orden está validada (FINALIZADO).
                    </Alert>
                  ) : resultadosDetallados.length > 0 ? (
                    <ResultadosOrdenLista
                      resultados={resultadosDetallados}
                      orden={selectedAnalisis}
                      observaciones={selectedAnalisis.observaciones}
                      modo="clinico"
                    />
                  ) : (
                    <Alert severity="info">
                      No hay resultados disponibles para esta solicitud.
                    </Alert>
                  )}
                </CardContent>
              </Card>
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
