import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Stack,
  TextField,
  MenuItem,
  Button,
  IconButton,
  Checkbox,
  FormControlLabel,
  GridLegacy as Grid,
} from '@mui/material';
import { Delete } from '@mui/icons-material';
import { RegistroQuirurgicoRecord } from '../../../../types';
import {
  useProcedimientosCatalogoQuery,
  useSaveRegistroQuirurgicoMutation,
} from '../../hooks';
import { useData } from '../../../../contexts/DataContext';

interface CirugiaFormProps {
  atencionId: number;
  registro?: RegistroQuirurgicoRecord;
  canEdit: boolean;
  onSaveSuccess?: () => void;
}

interface EquipoItem {
  nombre: string;
  rol: string;
}

const CirugiaForm: React.FC<CirugiaFormProps> = ({ atencionId, registro, canEdit, onSaveSuccess }) => {
  const { medicos } = useData();
  const procedimientosQuery = useProcedimientosCatalogoQuery();
  const saveMutation = useSaveRegistroQuirurgicoMutation();

  const [formState, setFormState] = useState({
    procedimiento_id: '',
    anestesista_id: '',
    diagnostico_preoperatorio: '',
    diagnostico_postoperatorio: '',
    protocolo_quirurgico: '',
    hallazgos_operatorios: '',
    complicaciones: '',
    recuento_instrumental_ok: false,
  });
  const [equipo, setEquipo] = useState<EquipoItem[]>([{ nombre: '', rol: '' }]);
  const [consentFile, setConsentFile] = useState<File | null>(null);

  useEffect(() => {
    console.log('🔄 CirugiaForm useEffect - registro recibido:', registro);
    if (registro) {
      // Obtener anestesista_id: primero del campo directo, luego del objeto relacionado
      const anestesistaId = registro.anestesista_id 
        || (registro.anestesista && typeof registro.anestesista === 'object' && 'id' in registro.anestesista ? registro.anestesista.id : null)
        || null;
      
      // Obtener procedimiento_id: primero del campo directo, luego del objeto relacionado
      const procedimientoId = registro.procedimiento_id 
        || (registro.procedimiento && typeof registro.procedimiento === 'object' && 'id' in registro.procedimiento ? registro.procedimiento.id : null)
        || null;
      
      // Obtener el ID del registro
      const registroId = registro.id || (registro && typeof registro === 'object' && 'id' in registro ? (registro as any).id : undefined);
      console.log('📋 Registro quirúrgico detectado con ID:', registroId);
      
      setFormState({
        procedimiento_id: procedimientoId ? String(procedimientoId) : '',
        anestesista_id: anestesistaId ? String(anestesistaId) : '',
        diagnostico_preoperatorio: registro.diagnostico_preoperatorio ?? '',
        diagnostico_postoperatorio: registro.diagnostico_postoperatorio ?? '',
        protocolo_quirurgico: registro.protocolo_quirurgico ?? '',
        hallazgos_operatorios: registro.hallazgos_operatorios ?? '',
        complicaciones: registro.complicaciones ?? '',
        recuento_instrumental_ok: Boolean(registro.recuento_instrumental_ok),
      });
      if (registro.equipo_quirurgico && registro.equipo_quirurgico.length > 0) {
        setEquipo(
          registro.equipo_quirurgico.map((item) => ({
            nombre: item.nombre,
            rol: item.rol,
          }))
        );
      } else {
        setEquipo([{ nombre: '', rol: '' }]);
      }
      setConsentFile(null);
    } else {
      console.log('📋 No hay registro quirúrgico, formulario en modo creación');
      // Resetear el formulario cuando no hay registro
      setFormState({
        procedimiento_id: '',
        anestesista_id: '',
        diagnostico_preoperatorio: '',
        diagnostico_postoperatorio: '',
        protocolo_quirurgico: '',
        hallazgos_operatorios: '',
        complicaciones: '',
        recuento_instrumental_ok: false,
      });
      setEquipo([{ nombre: '', rol: '' }]);
      setConsentFile(null);
    }
  }, [registro?.id, registro?.procedimiento_id, registro?.anestesista_id, registro?.diagnostico_preoperatorio, registro?.protocolo_quirurgico]);

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
    const value = event.target.value;
    const isCheckbox = field === 'recuento_instrumental_ok';
    const checked = isCheckbox && 'checked' in event.currentTarget ? (event.currentTarget as HTMLInputElement).checked : undefined;
    setFormState((prev) => ({
      ...prev,
      [field]: isCheckbox ? checked : value,
    }));
  };

  const handleEquipoChange = (index: number, key: keyof EquipoItem) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setEquipo((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [key]: value };
      return next;
    });
  };

  const handleAddTeamMember = () => {
    setEquipo((prev) => [...prev, { nombre: '', rol: '' }]);
  };

  const handleRemoveTeamMember = (index: number) => {
    setEquipo((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleConsentChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setConsentFile(file);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    // Validar campos requeridos
    if (!formState.anestesista_id || !formState.diagnostico_preoperatorio || !formState.protocolo_quirurgico) {
      alert('Por favor complete todos los campos requeridos');
      return;
    }
    
    const formData = new FormData();
    formData.append('atencion_id', String(atencionId));
    formData.append('anestesista_id', formState.anestesista_id);
    if (formState.procedimiento_id) {
      formData.append('procedimiento_id', formState.procedimiento_id);
    }
    formData.append('diagnostico_preoperatorio', formState.diagnostico_preoperatorio);
    if (formState.diagnostico_postoperatorio) {
      formData.append('diagnostico_postoperatorio', formState.diagnostico_postoperatorio);
    }
    formData.append('protocolo_quirurgico', formState.protocolo_quirurgico);
    if (formState.hallazgos_operatorios) {
      formData.append('hallazgos_operatorios', formState.hallazgos_operatorios);
    }
    if (formState.complicaciones) {
      formData.append('complicaciones', formState.complicaciones);
    }
    formData.append('recuento_instrumental_ok', String(formState.recuento_instrumental_ok));
    const equipoFiltrado = equipo.filter((item) => item.nombre.trim());
    formData.append('equipo_quirurgico', JSON.stringify(equipoFiltrado));
    if (consentFile) {
      formData.append('consentimiento_informado', consentFile);
    }
    try {
      // Verificar si existe un registro con ID
      // El registro puede venir como objeto completo o como { id: number }
      let registroId: number | undefined = undefined;
      if (registro) {
        if (typeof registro === 'object') {
          // Intentar obtener el ID de diferentes formas
          registroId = (registro as any).id || 
                      (registro as RegistroQuirurgicoRecord).id ||
                      undefined;
        }
      }
      
      const exists = Boolean(registro && registroId);
      
      console.log('🔍 Guardando cirugía:', {
        atencionId,
        exists,
        registroId,
        tieneRegistro: Boolean(registro),
        tipoRegistro: typeof registro,
        registroKeys: registro ? Object.keys(registro) : [],
        registroCompleto: JSON.stringify(registro, null, 2)
      });
      
      const result = await saveMutation.mutateAsync({
        atencionId,
        formData,
        exists,
        registroId,
      });
      setConsentFile(null);
      // El hook ya invalida el query y muestra un toast de éxito
      // El formulario se actualizará automáticamente cuando el registro cambie en el useEffect
      console.log('✅ Cirugía guardada exitosamente:', result);
      // Llamar al callback de éxito para cerrar el modal
      if (onSaveSuccess) {
        onSaveSuccess();
      }
    } catch (error) {
      // El error ya se maneja en el hook con un toast
      console.error('❌ Error guardando cirugía:', error);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Typography variant="subtitle1" fontWeight={600} mb={2}>
        Registro quirúrgico
      </Typography>
      <Stack spacing={2}>
        <TextField
          select
          label="Procedimiento (catálogo)"
          value={formState.procedimiento_id || ''}
          onChange={handleChange('procedimiento_id')}
          disabled={!canEdit || procedimientosQuery.isLoading}
        >
          <MenuItem value="">—</MenuItem>
          {procedimientosOptions.map((procedimiento) => (
            <MenuItem key={procedimiento.id} value={String(procedimiento.id)}>
              {procedimiento.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Anestesista"
          value={formState.anestesista_id || ''}
          onChange={handleChange('anestesista_id')}
          disabled={!canEdit}
          required
        >
          <MenuItem value="">Seleccionar anestesista</MenuItem>
          {medicosOptions.map((option) => (
            <MenuItem key={option.value} value={String(option.value)}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Diagnóstico preoperatorio"
          multiline
          minRows={2}
          value={formState.diagnostico_preoperatorio}
          onChange={handleChange('diagnostico_preoperatorio')}
          disabled={!canEdit}
          required
        />
        <TextField
          label="Diagnóstico postoperatorio"
          multiline
          minRows={2}
          value={formState.diagnostico_postoperatorio}
          onChange={handleChange('diagnostico_postoperatorio')}
          disabled={!canEdit}
        />
        <TextField
          label="Protocolo quirúrgico"
          multiline
          minRows={3}
          value={formState.protocolo_quirurgico}
          onChange={handleChange('protocolo_quirurgico')}
          disabled={!canEdit}
          required
        />
        <TextField
          label="Hallazgos operatorios"
          multiline
          minRows={3}
          value={formState.hallazgos_operatorios}
          onChange={handleChange('hallazgos_operatorios')}
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
        <FormControlLabel
          control={
            <Checkbox
              checked={formState.recuento_instrumental_ok}
              onChange={(event) =>
                setFormState((prev) => ({
                  ...prev,
                  recuento_instrumental_ok: event.target.checked,
                }))
              }
              disabled={!canEdit}
            />
          }
          label="Recuento instrumental verificado"
        />

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Equipo quirúrgico
          </Typography>
          <Stack spacing={1}>
            {equipo.map((integrante, index) => (
              <Grid container spacing={1} key={index}>
                <Grid item xs={12} md={5}>
                  <TextField
                    label="Nombre completo"
                    value={integrante.nombre}
                    onChange={handleEquipoChange(index, 'nombre')}
                    disabled={!canEdit}
                  />
                </Grid>
                <Grid item xs={12} md={5}>
                  <TextField
                    label="Rol"
                    value={integrante.rol}
                    onChange={handleEquipoChange(index, 'rol')}
                    disabled={!canEdit}
                  />
                </Grid>
                <Grid item xs={12} md={2} sx={{ display: 'flex', alignItems: 'center' }}>
                  {canEdit && (
                    <IconButton onClick={() => handleRemoveTeamMember(index)} disabled={equipo.length === 1}>
                      <Delete />
                    </IconButton>
                  )}
                </Grid>
              </Grid>
            ))}
            {canEdit && (
              <Button variant="outlined" onClick={handleAddTeamMember}>
                Agregar integrante
              </Button>
            )}
          </Stack>
        </Box>

        {canEdit && (
          <Stack direction="row" spacing={1} alignItems="center">
            <Button variant="outlined" component="label">
              Adjuntar consentimiento
              <input type="file" hidden onChange={handleConsentChange} />
            </Button>
            <Typography variant="caption" color="text.secondary">
              {consentFile ? consentFile.name : registro?.consentimiento_informado ? 'Ya existe un consentimiento cargado' : 'Sin archivo'}
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
              {saveMutation.isPending ? 'Guardando...' : 'Guardar cirugía'}
            </Button>
          </Box>
        )}
      </Stack>
    </Box>
  );
};

export default CirugiaForm;

