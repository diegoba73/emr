import React, { useEffect, useMemo, useState } from 'react';
import { Box, Typography, Stack, TextField, MenuItem, Button } from '@mui/material';
import { RegistroProcedimientoRecord } from '../../../../types';
import {
  useEstudiosDiagnosticoQuery,
  useProcedimientosCatalogoQuery,
  useSaveRegistroProcedimientoMutation,
} from '../../hooks';

interface EstudioDiagnosticoFormProps {
  atencionId: number;
  registro?: RegistroProcedimientoRecord;
  canEdit: boolean;
  onSaveSuccess?: () => void;
}

const EstudioDiagnosticoForm: React.FC<EstudioDiagnosticoFormProps> = ({ atencionId, registro, canEdit, onSaveSuccess }) => {
  const estudiosQuery = useEstudiosDiagnosticoQuery();
  const procedimientosQuery = useProcedimientosCatalogoQuery();
  const saveMutation = useSaveRegistroProcedimientoMutation();

  const [formState, setFormState] = useState({
    estudio_id: '',
    procedimiento_id: '',
    descripcion_procedimiento: '',
    informe_medico: '',
    hallazgos: '',
  });
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (registro) {
      // Obtener estudio_id: primero del campo directo, luego del objeto relacionado
      const estudioId = (registro as any).estudio_id 
        || (registro.estudio && typeof registro.estudio === 'object' && 'id' in registro.estudio ? registro.estudio.id : null)
        || null;
      
      // Obtener procedimiento_id: primero del campo directo, luego del objeto relacionado
      const procedimientoId = registro.procedimiento_id 
        || (registro.procedimiento && typeof registro.procedimiento === 'object' && 'id' in registro.procedimiento ? registro.procedimiento.id : null)
        || null;
      
      setFormState({
        estudio_id: estudioId ? String(estudioId) : '',
        procedimiento_id: procedimientoId ? String(procedimientoId) : '',
        descripcion_procedimiento: registro.descripcion_procedimiento ?? '',
        informe_medico: registro.informe_medico ?? '',
        hallazgos: registro.hallazgos ?? '',
      });
      setFile(null);
    } else {
      // Resetear el formulario cuando no hay registro
      setFormState({
        estudio_id: '',
        procedimiento_id: '',
        descripcion_procedimiento: '',
        informe_medico: '',
        hallazgos: '',
      });
      setFile(null);
    }
  }, [registro?.id, registro?.estudio_id, registro?.procedimiento_id]);

  const estudiosOptions = useMemo(
    () => estudiosQuery.data ?? [],
    [estudiosQuery.data]
  );

  const procedimientosOptions = useMemo(
    () => procedimientosQuery.data ?? [],
    [procedimientosQuery.data]
  );

  const handleChange = (field: keyof typeof formState) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { value } = event.target;
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const handleEstudioSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const estudioId = event.target.value;
    const selected = estudiosOptions.find((estudio) => estudio.id === Number(estudioId));
    setFormState((prev) => ({
      ...prev,
      estudio_id: estudioId,
      descripcion_procedimiento: selected ? selected.nombre : prev.descripcion_procedimiento,
    }));
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append('atencion_id', String(atencionId));
    formData.append('tipo_procedimiento', 'DIAGNOSTICO');
    if (formState.estudio_id) {
      formData.append('estudio_id', formState.estudio_id);
    }
    if (formState.procedimiento_id) {
      formData.append('procedimiento_id', formState.procedimiento_id);
    }
    if (formState.descripcion_procedimiento) {
      formData.append('descripcion_procedimiento', formState.descripcion_procedimiento);
    }
    if (formState.informe_medico) {
      formData.append('informe_medico', formState.informe_medico);
    }
    if (formState.hallazgos) {
      formData.append('hallazgos', formState.hallazgos);
    }
    if (file) {
      formData.append('adjunto_resultado', file);
    }
    try {
      await saveMutation.mutateAsync({
        atencionId,
        formData,
        exists: Boolean(registro && registro.id),
        registroId: registro?.id,
      });
      setFile(null);
      // Llamar al callback de éxito para cerrar el modal
      if (onSaveSuccess) {
        onSaveSuccess();
      }
    } catch (error) {
      // handled by hook
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Typography variant="subtitle1" fontWeight={600} mb={2}>
        Estudio diagnóstico
      </Typography>
      <Stack spacing={2}>
        <TextField
          select
          label="Estudio (catálogo)"
          value={formState.estudio_id}
          onChange={handleEstudioSelect}
          helperText="Selecciona un estudio para completar automáticamente la descripción"
          disabled={!canEdit || estudiosQuery.isLoading}
        >
          <MenuItem value="">—</MenuItem>
          {estudiosOptions.map((estudio) => (
            <MenuItem key={estudio.id} value={String(estudio.id)}>
              {estudio.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Procedimiento asociado"
          value={formState.procedimiento_id}
          onChange={handleChange('procedimiento_id')}
          disabled={!canEdit || procedimientosQuery.isLoading}
          helperText="Opcional: vincula un procedimiento del catálogo"
        >
          <MenuItem value="">—</MenuItem>
          {procedimientosOptions.map((procedimiento) => (
            <MenuItem key={procedimiento.id} value={String(procedimiento.id)}>
              {procedimiento.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Descripción del estudio"
          multiline
          minRows={2}
          value={formState.descripcion_procedimiento}
          onChange={handleChange('descripcion_procedimiento')}
          disabled={!canEdit}
        />
        <TextField
          label="Hallazgos"
          multiline
          minRows={3}
          value={formState.hallazgos}
          onChange={handleChange('hallazgos')}
          disabled={!canEdit}
        />
        <TextField
          label="Informe médico"
          multiline
          minRows={3}
          value={formState.informe_medico}
          onChange={handleChange('informe_medico')}
          disabled={!canEdit}
        />
        {canEdit && (
          <Stack direction="row" spacing={1} alignItems="center">
            <Button variant="outlined" component="label">
              Adjuntar resultado
              <input type="file" hidden onChange={handleFileChange} />
            </Button>
            <Typography variant="caption" color="text.secondary">
              {file ? file.name : registro?.adjunto_resultado ? 'Ya existe un archivo adjunto' : 'Sin archivo'}
            </Typography>
          </Stack>
        )}
        {canEdit && (
          <Box display="flex" justifyContent="flex-end">
            <Button
              type="submit"
              variant="contained"
              disabled={saveMutation.isPending}
            >
              Guardar estudio
            </Button>
          </Box>
        )}
      </Stack>
    </Box>
  );
};

export default EstudioDiagnosticoForm;

