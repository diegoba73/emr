import React, { useEffect, useMemo, useState } from 'react';
import { Box, Typography, Stack, TextField, MenuItem, Button } from '@mui/material';
import { RegistroProcedimientoRecord } from '../../../../types';
import {
  useProcedimientosCatalogoQuery,
  useSaveRegistroProcedimientoMutation,
} from '../../hooks';
import { useData } from '../../../../contexts/DataContext';

interface ProcedimientoFormProps {
  atencionId: number;
  registro?: RegistroProcedimientoRecord;
  canEdit: boolean;
  onSaveSuccess?: () => void;
}

const ProcedimientoForm: React.FC<ProcedimientoFormProps> = ({ atencionId, registro, canEdit, onSaveSuccess }) => {
  const { medicos } = useData();
  const procedimientosQuery = useProcedimientosCatalogoQuery();
  const saveMutation = useSaveRegistroProcedimientoMutation();

  const [formState, setFormState] = useState({
    procedimiento_id: '',
    descripcion_procedimiento: '',
    tipo_procedimiento: 'TERAPEUTICO',
    informe_medico: '',
    hallazgos: '',
    profesional_asistente_id: '',
    complicaciones: '',
  });
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (registro) {
      setFormState({
        procedimiento_id: registro.procedimiento_id ? String(registro.procedimiento_id) : '',
        descripcion_procedimiento: registro.descripcion_procedimiento ?? '',
        tipo_procedimiento: registro.tipo_procedimiento ?? 'TERAPEUTICO',
        informe_medico: registro.informe_medico ?? '',
        hallazgos: registro.hallazgos ?? '',
        profesional_asistente_id: registro.profesional_asistente_id ? String(registro.profesional_asistente_id) : '',
        complicaciones: registro.complicaciones ?? '',
      });
      setFile(null);
    }
  }, [registro]);

  const procedimientosOptions = useMemo(
    () => procedimientosQuery.data ?? [],
    [procedimientosQuery.data]
  );

  const medicosOptions = useMemo(
    () =>
      medicos
        .map((medico) => ({
          value: medico.id,
          label: `Dr. ${medico.nombre} ${medico.apellido}`,
        }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    [medicos]
  );

  const handleChange = (field: keyof typeof formState) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { value } = event.target;
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append('atencion_id', String(atencionId));
    if (formState.procedimiento_id) {
      formData.append('procedimiento_id', formState.procedimiento_id);
    }
    if (formState.descripcion_procedimiento) {
      formData.append('descripcion_procedimiento', formState.descripcion_procedimiento);
    }
    if (formState.tipo_procedimiento) {
      formData.append('tipo_procedimiento', formState.tipo_procedimiento);
    }
    if (formState.informe_medico) {
      formData.append('informe_medico', formState.informe_medico);
    }
    if (formState.hallazgos) {
      formData.append('hallazgos', formState.hallazgos);
    }
    if (formState.profesional_asistente_id) {
      formData.append('profesional_asistente_id', formState.profesional_asistente_id);
    }
    if (formState.complicaciones) {
      formData.append('complicaciones', formState.complicaciones);
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
      // handled in hook
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Typography variant="subtitle1" fontWeight={600} mb={2}>
        Procedimiento terapéutico
      </Typography>
      <Stack spacing={2}>
        <TextField
          select
          label="Procedimiento (catálogo)"
          value={formState.procedimiento_id}
          onChange={handleChange('procedimiento_id')}
          disabled={!canEdit || procedimientosQuery.isLoading}
        >
          <MenuItem value="">—</MenuItem>
          {procedimientosOptions.map((procedimiento) => (
            <MenuItem key={procedimiento.id} value={procedimiento.id}>
              {procedimiento.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Descripción del procedimiento"
          multiline
          minRows={2}
          value={formState.descripcion_procedimiento}
          onChange={handleChange('descripcion_procedimiento')}
          disabled={!canEdit}
        />
        <TextField
          select
          label="Tipo de procedimiento"
          value={formState.tipo_procedimiento}
          onChange={handleChange('tipo_procedimiento')}
          disabled={!canEdit}
        >
          <MenuItem value="TERAPEUTICO">Terapéutico</MenuItem>
          <MenuItem value="DIAGNOSTICO">Diagnóstico</MenuItem>
        </TextField>
        <TextField
          label="Profesional asistente"
          select
          value={formState.profesional_asistente_id}
          onChange={handleChange('profesional_asistente_id')}
          disabled={!canEdit}
        >
          <MenuItem value="">—</MenuItem>
          {medicosOptions.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Informe médico"
          multiline
          minRows={3}
          value={formState.informe_medico}
          onChange={handleChange('informe_medico')}
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
          label="Complicaciones"
          multiline
          minRows={2}
          value={formState.complicaciones}
          onChange={handleChange('complicaciones')}
          disabled={!canEdit}
        />
        {canEdit && (
          <Stack direction="row" spacing={1} alignItems="center">
            <Button variant="outlined" component="label">
              Adjuntar informe
              <input type="file" hidden onChange={handleFileChange} />
            </Button>
            <Typography variant="caption" color="text.secondary">
              {file ? file.name : registro?.adjunto_resultado ? 'Existe un archivo cargado' : 'Sin archivo'}
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
              Guardar procedimiento
            </Button>
          </Box>
        )}
      </Stack>
    </Box>
  );
};

export default ProcedimientoForm;

