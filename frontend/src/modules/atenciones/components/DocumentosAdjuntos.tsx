import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import { CloudUpload, Download } from '@mui/icons-material';
import { Documento, TipoDocumento } from '../../../types';
import { useUploadDocumentoMutation } from '../hooks';
import { getTiposDocumento } from '../../../services/apiService';
import { apiService } from '../../../services/api';

interface DocumentosAdjuntosProps {
  atencionId: number;
  documentos: Documento[] | { results: Documento[] } | null | undefined;
  canEdit: boolean;
}

interface TipoDocumentoOption {
  value: TipoDocumento;
  label: string;
}

const DocumentosAdjuntos: React.FC<DocumentosAdjuntosProps> = ({ atencionId, documentos, canEdit }) => {
  const [openDialog, setOpenDialog] = useState(false);
  const [tipoDocumentoOptions, setTipoDocumentoOptions] = useState<TipoDocumentoOption[]>([
    { value: 'INFORME', label: 'Informe' },
    { value: 'ESTUDIO', label: 'Estudio' },
    { value: 'ANALISIS', label: 'Análisis' },
    { value: 'DIAGNOSTICO', label: 'Diagnóstico' },
    { value: 'IMAGEN', label: 'Imagen' },
    { value: 'CONSENTIMIENTO', label: 'Consentimiento informado' },
    { value: 'OTRO', label: 'Otro' },
  ]);
  const [formState, setFormState] = useState({
    tipo_documento: 'INFORME' as TipoDocumento,
    descripcion: '',
    archivo: null as File | null,
  });

  const uploadDocumento = useUploadDocumentoMutation();

  // Cargar tipos de documento dinámicamente desde el backend
  useEffect(() => {
    const loadTiposDocumento = async () => {
      try {
        const tipos = await getTiposDocumento();
        if (tipos && Array.isArray(tipos) && tipos.length > 0) {
          setTipoDocumentoOptions(tipos as TipoDocumentoOption[]);
        }
      } catch {
        /* tipos por defecto */
      }
    };
    loadTiposDocumento();
  }, []);

  // OPTIMIZACIÓN: Validar que documentos sea un array antes de iterar
  const documentosArray = React.useMemo((): Documento[] => {
    if (!documentos) {
      return [];
    }
    if (Array.isArray(documentos)) {
      return documentos;
    }
    if (typeof documentos === 'object' && documentos !== null && 'results' in documentos) {
      const results = (documentos as { results?: Documento[] }).results;
      if (Array.isArray(results)) {
        return results;
      }
    }
    return [];
  }, [documentos]);

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormState({
      tipo_documento: 'INFORME',
      descripcion: '',
      archivo: null,
    });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setFormState((prev) => ({ ...prev, archivo: file }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.archivo) {
      return;
    }
    const formData = new FormData();
    formData.append('atencion_id', String(atencionId));
    formData.append('tipo_documento', formState.tipo_documento);
    if (formState.descripcion) {
      formData.append('descripcion', formState.descripcion);
    }
    formData.append('archivo', formState.archivo);
    try {
      await uploadDocumento.mutateAsync(formData);
      handleCloseDialog();
    } catch {
      /* toast en hook */
    }
  };

  const handleDownload = async (documento: Documento) => {
    try {
      const blob = await apiService.downloadDocumento(documento.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = documento.archivo_nombre || 'documento';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      /* sin log de detalle (C6.2) */
    }
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="subtitle1" fontWeight={600}>
          Documentos adjuntos
        </Typography>
        {canEdit && (
          <Button
            variant="contained"
            size="small"
            startIcon={<CloudUpload />}
            onClick={handleOpenDialog}
          >
            Subir documento
          </Button>
        )}
      </Stack>

      {documentosArray.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No se adjuntaron documentos a esta atención.
        </Typography>
      ) : (
        <List dense>
          {documentosArray.map((documento) => (
            <ListItem key={documento.id} divider>
              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip
                      label={tipoDocumentoOptions.find((opt) => opt.value === documento.tipo_documento)?.label ?? documento.tipo_documento}
                      size="small"
                      color={documento.tipo_documento === 'CONSENTIMIENTO' ? 'warning' : 'default'}
                    />
                    <Typography variant="body2" fontWeight={600}>
                      {documento.descripcion || 'Sin descripción'}
                    </Typography>
                  </Stack>
                }
                secondary={
                  <Typography variant="caption" color="text.secondary">
                    Subido el {new Date(documento.fecha_subida).toLocaleString()} por {documento.usuario_cargador_nombre ?? 'Usuario desconocido'}
                  </Typography>
                }
              />
              <ListItemSecondaryAction>
                <IconButton size="small" onClick={() => handleDownload(documento)} title="Descargar">
                  <Download fontSize="small" />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      )}

      <Dialog 
        open={openDialog} 
        onClose={handleCloseDialog} 
        maxWidth="sm" 
        fullWidth
        sx={{ zIndex: 1500 }}
        PaperProps={{ sx: { zIndex: 1500 } }}
        slotProps={{ backdrop: { sx: { zIndex: 1500 } } }}
      >
        <form onSubmit={handleSubmit}>
          <DialogTitle>Subir documento clínico</DialogTitle>
          <DialogContent dividers>
            <Stack spacing={2} mt={0.5}>
              <TextField
                select
                label="Tipo de documento"
                value={formState.tipo_documento}
                onChange={(event) =>
                  setFormState((prev) => ({
                    ...prev,
                    tipo_documento: event.target.value as TipoDocumento,
                  }))
                }
                SelectProps={{
                  MenuProps: {
                    sx: { zIndex: 2000 },
                    slotProps: { paper: { sx: { zIndex: 2000 } } },
                  },
                }}
              >
                {tipoDocumentoOptions.map((option) => (
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
                <input
                  type="file"
                  hidden
                  onChange={handleFileChange}
                />
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
              disabled={!formState.archivo || uploadDocumento.isPending}
            >
              Subir
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default DocumentosAdjuntos;

