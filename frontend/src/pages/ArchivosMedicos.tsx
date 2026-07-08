import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,

  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Chip,
  Avatar,
  Tooltip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Alert,
} from '@mui/material';
import {
  Edit,
  Download,
  Folder,
  Description,
  Image,
  PictureAsPdf,
  Close,
} from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import { ArchivoMedico, Paciente } from '../types';
import SearchAndFilters from '../components/SearchAndFilters';
import AsyncAutocomplete from '../components/common/AsyncAutocomplete';
import { formatPacienteLabel } from '../utils/pacienteFormat';
import {
  canDownloadArchivoMedico,
  canWriteArchivoMedico,
} from '../utils/permissions';
import { getSafeApiErrorMessage } from '../utils/apiError';
import { 
  createArchivoMedico, 
  updateArchivoMedico, 
  downloadArchivoMedico,
  getTiposArchivo,
  getConsultas 
} from '../services/apiService';
import ArchivoMedicoPreviewDialog from '../components/archivos/ArchivoMedicoPreviewDialog';

const ArchivosMedicos: React.FC = () => {
  const { archivosMedicos, loadArchivosMedicos, pacientes, loadPacientes, currentUser } = useData();
  const canWrite = canWriteArchivoMedico(currentUser);
  const canDownload = canDownloadArchivoMedico(currentUser);
  const [downloadError, setDownloadError] = useState('');
  const [consultas, setConsultas] = useState<any[]>([]);
  const [tiposArchivo, setTiposArchivo] = useState<{value: string, label: string}[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingArchivo, setEditingArchivo] = useState<ArchivoMedico | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPaciente, setSelectedPaciente] = useState<Paciente | null>(null);
  const [formData, setFormData] = useState({
    titulo: '',
    descripcion: '',
    tipo_archivo: 'OTRO',
    paciente_id: '',
    consulta_id: '',
    fecha_estudio: '',
    es_urgente: false
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [existingFileName, setExistingFileName] = useState<string | null>(null);
  const [previewArchivo, setPreviewArchivo] = useState<ArchivoMedico | null>(null);

  useEffect(() => {
    loadArchivosMedicos();
    loadPacientes();
    loadTiposArchivo();
    loadConsultasData();
  }, []);

  const loadConsultasData = async () => {
    try {
      const consultasData = await getConsultas();
      // getConsultas ahora retorna { results, count, next, previous }
      setConsultas(consultasData.results || []);
    } catch {
      setConsultas([]);
    }
  };

  const loadTiposArchivo = async () => {
    try {
      const tipos = await getTiposArchivo();
      setTiposArchivo(tipos);
    } catch {
      /* tipos opcionales */
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload: any = {
        titulo: formData.titulo,
        descripcion: formData.descripcion,
        tipo_archivo: formData.tipo_archivo as any,
        paciente_id: parseInt(formData.paciente_id),
        consulta_id: formData.consulta_id ? parseInt(formData.consulta_id) : null,
        fecha_estudio: formData.fecha_estudio || null,
        es_urgente: formData.es_urgente
      };

      if (selectedFile) {
        const data = new FormData();
        Object.entries(payload).forEach(([k, v]) => {
          if (v !== undefined && v !== null) data.append(k, String(v));
        });
        data.append('archivo', selectedFile);

        if (editingArchivo) {
          await updateArchivoMedico(editingArchivo.id, data as any);
        } else {
          await createArchivoMedico(data as any);
        }
      } else {
        if (editingArchivo) {
          await updateArchivoMedico(editingArchivo.id, payload);
        } else {
          await createArchivoMedico(payload);
        }
      }

      setShowForm(false);
      setEditingArchivo(null);
      resetForm();
      loadArchivosMedicos();
    } catch (err: unknown) {
      setDownloadError(getSafeApiErrorMessage(err, 'No se pudo guardar el archivo.'));
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      titulo: '',
      descripcion: '',
      tipo_archivo: 'OTRO',
      paciente_id: '',
      consulta_id: '',
      fecha_estudio: '',
      es_urgente: false
    });
    setSelectedPaciente(null);
    setSelectedFile(null);
    setExistingFileName(null);
  };

  const handleEdit = (archivo: ArchivoMedico) => {
    setEditingArchivo(archivo);
    setFormData({
      titulo: archivo.titulo,
      descripcion: archivo.descripcion || '',
      tipo_archivo: archivo.tipo_archivo,
      paciente_id: archivo.paciente_id.toString(),
      consulta_id: archivo.consulta_id?.toString() || '',
      fecha_estudio: archivo.fecha_estudio || '',
      es_urgente: archivo.es_urgente || false
    });
    setExistingFileName(archivo.archivo_nombre || null);
    setShowForm(true);
  };

  const handleView = (archivo: ArchivoMedico) => {
    if (!canDownload) return;
    setPreviewArchivo(archivo);
  };

  const handleDownload = async (archivo: ArchivoMedico) => {
    setDownloadError('');
    try {
      const blob = await downloadArchivoMedico(archivo.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = archivo.archivo_nombre || archivo.titulo || 'archivo';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setDownloadError(getSafeApiErrorMessage(err, 'No se pudo descargar el archivo.'));
    }
  };

  const getPacienteNombre = (pacienteId: number) => {
    const paciente = pacientes.find(p => p.id === pacienteId);
    return paciente ? `${paciente.nombre} ${paciente.apellido}` : 'N/A';
  };

  const getTipoIcon = (tipo: string) => {
    switch (tipo) {
      case 'FOTO_CLINICA':
      case 'RAYOS_X':
      case 'TOMOGRAFIA':
      case 'RESONANCIA':
      case 'ULTRASONIDO':
      case 'PATOLOGIA':
        return <Image />;
      case 'PDF':
        return <PictureAsPdf />;
      case 'DICOM':
      case 'NIFTI':
        return <Description />;
      default:
        return <Folder />;
    }
  };

  const getTipoColor = (tipo: string) => {
    switch (tipo) {
      case 'FOTO_CLINICA':
      case 'RAYOS_X':
      case 'TOMOGRAFIA':
      case 'RESONANCIA':
      case 'ULTRASONIDO':
      case 'PATOLOGIA':
        return 'success';
      case 'PDF':
        return 'error';
      case 'DICOM':
      case 'NIFTI':
        return 'primary';
      default:
        return 'default';
    }
  };

  // Filtrar archivos
  const filteredArchivos = archivosMedicos.filter(archivo => {
    const matchesSearch = 
      archivo.titulo?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      archivo.descripcion?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      getPacienteNombre(archivo.paciente_id).toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesSearch;
  });

  const paginatedArchivos = filteredArchivos.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Box sx={{ p: 3 }} className="fade-in">
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Archivos
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Repositorio unificado de archivos del paciente (incluye adjuntos de atenciones, estudios e imágenes).
        </Typography>
      </Box>

      {downloadError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setDownloadError('')}>
          {downloadError}
        </Alert>
      )}

      {/* Search and Actions */}
      <SearchAndFilters
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        searchPlaceholder="Buscar por título, descripción o paciente..."
        onRefresh={loadArchivosMedicos}
        onAdd={canWrite ? () => {
          setShowForm(true);
          setEditingArchivo(null);
          resetForm();
        } : undefined}
        addButtonText="Nuevo Archivo"
        totalItems={archivosMedicos.length}
        filteredItems={filteredArchivos.length}
      />

      {/* Files Table */}
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Archivo</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Tipo</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Paciente</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Fecha</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Estado</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedArchivos.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      {searchTerm ? 'No se encontraron archivos con los filtros aplicados' : 'No hay archivos médicos registrados'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedArchivos.map((archivo) => (
                  <TableRow
                    key={archivo.id}
                    hover
                    onClick={() => handleView(archivo)}
                    sx={{ cursor: canDownload ? 'pointer' : 'default' }}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                          {getTipoIcon(archivo.tipo_archivo)}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {archivo.titulo}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {archivo.descripcion && typeof archivo.descripcion === 'string' 
                              ? (archivo.descripcion.length > 50 ? archivo.descripcion.substring(0, 50) + '...' : archivo.descripcion)
                              : archivo.descripcion}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={getTipoIcon(archivo.tipo_archivo)}
                        label={archivo.tipo_archivo}
                        color={getTipoColor(archivo.tipo_archivo) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {getPacienteNombre(archivo.paciente_id)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {archivo.fecha_subida ? new Date(archivo.fecha_subida).toLocaleDateString('es-ES') : 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={archivo.es_urgente ? 'Urgente' : 'Normal'}
                        color={archivo.es_urgente ? 'error' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {canDownload && (
                          <Tooltip title="Descargar">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleDownload(archivo)}
                            >
                              <Download />
                            </IconButton>
                          </Tooltip>
                        )}
                        {canWrite && (
                          <Tooltip title="Editar">
                            <IconButton
                              size="small"
                              onClick={() => handleEdit(archivo)}
                              color="warning"
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={filteredArchivos.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Filas por página:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
        />
      </Paper>

      {/* Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => setShowForm(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6">{editingArchivo ? 'Editar Archivo Médico' : 'Nuevo Archivo Médico'}</Typography>
            <IconButton onClick={() => setShowForm(false)} sx={{ color: 'grey.500' }}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <TextField
                fullWidth
                label="Título *"
                value={formData.titulo}
                onChange={(e) => setFormData({...formData, titulo: e.target.value})}
                required
              />
              
              <TextField
                fullWidth
                label="Descripción"
                value={formData.descripcion}
                onChange={(e) => setFormData({...formData, descripcion: e.target.value})}
                multiline
                rows={3}
              />
              
              <FormControl fullWidth>
                <InputLabel>Tipo de Archivo *</InputLabel>
                <Select
                  value={formData.tipo_archivo}
                  label="Tipo de Archivo *"
                  onChange={(e) => setFormData({...formData, tipo_archivo: e.target.value})}
                  required
                >
                  {tiposArchivo.map(tipo => (
                    <MenuItem key={tipo.value} value={tipo.value}>
                      {tipo.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <AsyncAutocomplete<Paciente>
                label="👤 Paciente"
                endpoint="/pacientes/"
                getOptionLabel={(option) => formatPacienteLabel(option)}
                onChange={(newValue) => {
                  setSelectedPaciente(newValue);
                  setFormData({ 
                    ...formData, 
                    paciente_id: newValue ? String(newValue.id) : '' 
                  });
                }}
                value={selectedPaciente}
                required
                placeholder="Escriba al menos 2 caracteres para buscar por nombre, apellido o DNI..."
                helperText="Búsqueda asíncrona en servidor"
                debounceMs={500}
                minSearchLength={2}
                sx={{ mb: 2 }}
              />
              
              <FormControl fullWidth>
                <InputLabel>Consulta Asociada (Opcional)</InputLabel>
                <Select
                  value={formData.consulta_id}
                  label="Consulta Asociada (Opcional)"
                  onChange={(e) => setFormData({...formData, consulta_id: e.target.value})}
                >
                  <MenuItem value="">Sin consulta asociada</MenuItem>
                  {consultas.map(consulta => (
                    <MenuItem key={consulta.id} value={consulta.id}>
                      {consulta.motivo_consulta_detalle || consulta.motivo} - {new Date(consulta.fecha_hora_consulta || consulta.fecha_consulta).toLocaleDateString()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <TextField
                fullWidth
                label="Fecha de Estudio"
                type="date"
                value={formData.fecha_estudio}
                onChange={(e) => setFormData({...formData, fecha_estudio: e.target.value})}
                InputLabelProps={{ shrink: true }}
              />
              
              <Box sx={{ width: '100%' }}>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  required={!editingArchivo}
                  style={{ marginBottom: 16 }}
                />
                {editingArchivo && existingFileName && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Archivo actual: <strong>{existingFileName}</strong>
                  </Typography>
                )}
              </Box>
              
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.es_urgente}
                    onChange={(e) => setFormData({...formData, es_urgente: e.target.checked})}
                  />
                }
                label="Marcar como urgente"
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowForm(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? 'Guardando...' : (editingArchivo ? 'Actualizar' : 'Crear')}
          </Button>
        </DialogActions>
      </Dialog>

      <ArchivoMedicoPreviewDialog
        open={Boolean(previewArchivo)}
        archivo={previewArchivo}
        onClose={() => setPreviewArchivo(null)}
      />
    </Box>
  );
};

export default ArchivosMedicos;
