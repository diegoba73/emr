import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Stack,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  ThemeProvider,
} from '@mui/material';
import { CloudUpload, Download } from '@mui/icons-material';
import { useQueryClient } from '@tanstack/react-query';
import { ArchivoMedico } from '../../../types';
import {
  createArchivoMedico,
  downloadArchivoMedico,
  getArchivosPorAtencion,
  getArchivosPorConsulta,
  getTiposArchivo,
} from '../../../services/apiService';
import { getSafeApiErrorMessage } from '../../../utils/apiError';
import {
  clinicalDrawerDialogProps,
  clinicalDrawerDialogContentSx,
  useClinicalDrawerDialogTheme,
} from '../../../utils/layerZIndex';
import ArchivoMedicoPreviewDialog from '../../../components/archivos/ArchivoMedicoPreviewDialog';

interface DocumentosAdjuntosProps {
  atencionId: number;
  pacienteId: number;
  consultaHcId?: number | null;
  canEdit: boolean;
}

type CategoriaArchivo = {
  value: ArchivoMedico['tipo_archivo'];
  label: string;
};

const CATEGORIAS_ARCHIVO: CategoriaArchivo[] = [
  { value: 'PDF', label: 'Informe / PDF' },
  { value: 'FOTO_CLINICA', label: 'Imagen clínica' },
  { value: 'RAYOS_X', label: 'Rayos X' },
  { value: 'TOMOGRAFIA', label: 'Tomografía' },
  { value: 'RESONANCIA', label: 'Resonancia' },
  { value: 'ULTRASONIDO', label: 'Ultrasonido' },
  { value: 'OTRO', label: 'Otro' },
];

const DocumentosAdjuntos: React.FC<DocumentosAdjuntosProps> = ({
  atencionId,
  pacienteId,
  consultaHcId,
  canEdit,
}) => {
  const queryClient = useQueryClient();
  const dialogTheme = useClinicalDrawerDialogTheme();
  const [archivos, setArchivos] = useState<ArchivoMedico[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  const [tipoOptions, setTipoOptions] = useState<CategoriaArchivo[]>(CATEGORIAS_ARCHIVO);
  const [formState, setFormState] = useState({
    titulo: '',
    tipo_archivo: 'PDF' as ArchivoMedico['tipo_archivo'],
    descripcion: '',
    archivo: null as File | null,
  });
  const [previewArchivo, setPreviewArchivo] = useState<ArchivoMedico | null>(null);

  const reloadArchivos = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const items = consultaHcId
        ? await getArchivosPorConsulta(consultaHcId)
        : await getArchivosPorAtencion(atencionId);
      setArchivos(items);
    } catch (err) {
      setLoadError(getSafeApiErrorMessage(err, 'No se pudieron cargar los archivos.'));
      setArchivos([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reloadArchivos();
  }, [atencionId, consultaHcId]);

  useEffect(() => {
    void getTiposArchivo()
      .then((tipos) => {
        if (tipos?.length) {
          setTipoOptions(
            tipos.map((t: { value: string; label: string }) => ({
              value: t.value as ArchivoMedico['tipo_archivo'],
              label: t.label,
            }))
          );
        }
      })
      .catch(() => {
        /* categorías por defecto */
      });
  }, []);

  const tipoLabel = useMemo(() => {
    const map = new Map(tipoOptions.map((t) => [t.value, t.label]));
    return (tipo: string) => map.get(tipo as ArchivoMedico['tipo_archivo']) || tipo;
  }, [tipoOptions]);

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setUploadError('');
    setFormState({
      titulo: '',
      tipo_archivo: 'PDF',
      descripcion: '',
      archivo: null,
    });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setFormState((prev) => ({
      ...prev,
      archivo: file,
      titulo: prev.titulo || (file ? file.name.replace(/\.[^.]+$/, '') : ''),
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.archivo || !formState.titulo.trim()) {
      return;
    }
    setUploading(true);
    setUploadError('');
    try {
      const formData = new FormData();
      formData.append('paciente_id', String(pacienteId));
      formData.append('atencion_id', String(atencionId));
      if (consultaHcId) {
        formData.append('consulta_id', String(consultaHcId));
      }
      formData.append('titulo', formState.titulo.trim());
      formData.append('tipo_archivo', formState.tipo_archivo);
      if (formState.descripcion.trim()) {
        formData.append('descripcion', formState.descripcion.trim());
      }
      formData.append('archivo', formState.archivo);
      await createArchivoMedico(formData);
      await reloadArchivos();
      await queryClient.invalidateQueries({ queryKey: ['archivosMedicos'] });
      handleCloseDialog();
    } catch (err) {
      setUploadError(getSafeApiErrorMessage(err, 'No se pudo subir el archivo.'));
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (archivo: ArchivoMedico) => {
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
    } catch {
      /* sin log de detalle */
    }
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="subtitle1" fontWeight={600}>
            {consultaHcId ? 'Documentación de la consulta' : 'Archivos del paciente'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {consultaHcId
              ? 'Estudios previos u otra información que el paciente trae a la consulta.'
              : 'Los adjuntos de esta atención también aparecen en el menú Archivos.'}
          </Typography>
        </Box>
        {canEdit && (
          <Button
            variant="contained"
            size="small"
            startIcon={<CloudUpload />}
            onClick={handleOpenDialog}
          >
            Subir archivo
          </Button>
        )}
      </Stack>

      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {loadError}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" alignItems="center" gap={1} py={2}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Cargando archivos...
          </Typography>
        </Box>
      ) : archivos.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No hay archivos adjuntos a esta atención.
        </Typography>
      ) : (
        <List dense>
          {archivos.map((archivo) => (
            <ListItem
              key={archivo.id}
              divider
              onClick={() => setPreviewArchivo(archivo)}
              sx={{ cursor: 'pointer' }}
            >
              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                    <Chip label={tipoLabel(archivo.tipo_archivo)} size="small" />
                    <Typography variant="body2" fontWeight={600}>
                      {archivo.titulo}
                    </Typography>
                  </Stack>
                }
                secondary={
                  <Typography variant="caption" color="text.secondary">
                    {archivo.descripcion || 'Sin descripción'} ·{' '}
                    {new Date(archivo.fecha_subida).toLocaleString()}
                  </Typography>
                }
              />
              <ListItemSecondaryAction>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleDownload(archivo);
                  }}
                  title="Descargar"
                >
                  <Download fontSize="small" />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      )}

      <ArchivoMedicoPreviewDialog
        open={Boolean(previewArchivo)}
        archivo={previewArchivo}
        onClose={() => setPreviewArchivo(null)}
      />

      <ThemeProvider theme={dialogTheme}>
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        {...clinicalDrawerDialogProps}
      >
        <form onSubmit={handleSubmit}>
          <DialogTitle>Subir archivo del paciente</DialogTitle>
          <DialogContent dividers sx={clinicalDrawerDialogContentSx}>
            <Stack spacing={2} mt={0.5}>
              {uploadError && <Alert severity="error">{uploadError}</Alert>}
              <TextField
                label="Título"
                required
                value={formState.titulo}
                onChange={(e) => setFormState((prev) => ({ ...prev, titulo: e.target.value }))}
              />
              <TextField
                select
                label="Tipo de archivo"
                value={formState.tipo_archivo}
                onChange={(event) =>
                  setFormState((prev) => ({
                    ...prev,
                    tipo_archivo: event.target.value as ArchivoMedico['tipo_archivo'],
                  }))
                }
                SelectProps={{
                  MenuProps: {
                    sx: { zIndex: 2000 },
                    slotProps: { paper: { sx: { zIndex: 2000 } } },
                  },
                }}
              >
                {tipoOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Descripción"
                multiline
                minRows={2}
                value={formState.descripcion}
                onChange={(event) =>
                  setFormState((prev) => ({ ...prev, descripcion: event.target.value }))
                }
              />
              <Button variant="outlined" component="label">
                Seleccionar archivo
                <input type="file" hidden onChange={handleFileChange} />
              </Button>
              {formState.archivo && (
                <Typography variant="caption" color="text.secondary">
                  Archivo seleccionado: {formState.archivo.name}
                </Typography>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Cancelar</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!formState.archivo || !formState.titulo.trim() || uploading}
            >
              {uploading ? 'Subiendo...' : 'Subir'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      </ThemeProvider>
    </Box>
  );
};

export default DocumentosAdjuntos;
