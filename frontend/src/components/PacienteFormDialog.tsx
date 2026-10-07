import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from '@mui/material';
import { Close } from '@mui/icons-material';
import { pacientesService } from '../services/pacientes';
import type { Paciente } from '../types';
import { createPaciente, updatePaciente } from '../services/apiService';
import { getSafeApiErrorMessage } from '../utils/apiError';
import PacienteDemographicsForm, {
  emptyPacienteFormValues,
  type PacienteDemographicsFormValues,
} from './PacienteDemographicsForm';
import PacienteAfiliacionesEditor from './PacienteAfiliacionesEditor';

function pacienteToFormValues(p: Paciente): PacienteDemographicsFormValues {
  const fecha = p.fecha_nacimiento;
  return {
    nombre: p.nombre || '',
    apellido: p.apellido || '',
    dni: p.dni || '',
    fecha_nacimiento: fecha ? String(fecha).slice(0, 10) : '',
    sexo: (p.sexo as 'M' | 'F' | 'O') || '',
    telefono: p.telefono || '',
    email: p.email || '',
    direccion: p.direccion || '',
    obra_social: p.obra_social || '',
    numero_afiliado: p.numero_afiliado || '',
    estado_civil: p.estado_civil || '',
    familiar_nombre: p.familiar_nombre || '',
    familiar_telefono: p.familiar_telefono || '',
    antecedentes_personales: p.antecedentes_personales || '',
    antecedentes_familiares: p.antecedentes_familiares || '',
    observaciones: p.observaciones || '',
  };
}

function formToPayload(values: PacienteDemographicsFormValues): Record<string, string | null> {
  const upper = (s: string) => s.trim().toUpperCase();
  const payload: Record<string, string | null> = {
    nombre: upper(values.nombre),
    apellido: upper(values.apellido),
    dni: values.dni.trim(),
    telefono: values.telefono.trim(),
    email: values.email.trim(),
    direccion: upper(values.direccion),
    obra_social: upper(values.obra_social),
    numero_afiliado: upper(values.numero_afiliado),
    estado_civil: values.estado_civil.trim(),
    familiar_nombre: values.familiar_nombre.trim(),
    familiar_telefono: values.familiar_telefono.trim(),
    antecedentes_personales: values.antecedentes_personales.trim(),
    antecedentes_familiares: values.antecedentes_familiares.trim(),
    observaciones: values.observaciones.trim(),
  };
  payload.fecha_nacimiento = values.fecha_nacimiento || null;
  payload.sexo = values.sexo || '';
  return payload;
}

export interface PacienteFormDialogProps {
  open: boolean;
  mode: 'create' | 'edit';
  paciente?: Paciente | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}

const PacienteFormDialog: React.FC<PacienteFormDialogProps> = ({
  open,
  mode,
  paciente,
  onClose,
  onSaved,
}) => {
  const [values, setValues] = useState<PacienteDemographicsFormValues>(emptyPacienteFormValues());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsReady, setDetailsReady] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError('');
    setDetailsReady(mode === 'create');
    setValues(emptyPacienteFormValues());
    setLoadingDetails(mode === 'edit');
    if (mode === 'edit' && paciente) {
      // El listado usa un serializer reducido: leer la ficha evita borrar datos omitidos.
      pacientesService.getById(paciente.id).then((full) => {
        if (cancelled) return;
        setValues(pacienteToFormValues(full));
        setDetailsReady(true);
      }).catch((e: unknown) => {
        if (!cancelled) setError(getSafeApiErrorMessage(e, 'No se pudo cargar la ficha completa. Cerrá y volvé a intentar.'));
      }).finally(() => { if (!cancelled) setLoadingDetails(false); });
    }
    return () => { cancelled = true; };
  }, [open, mode, paciente]);

  const handlePrincipalChange = useCallback((obra_social: string, numero_afiliado: string) => {
    setValues((prev) => ({ ...prev, obra_social, numero_afiliado }));
  }, []);

  const handleSave = async () => {
    if (!detailsReady || loadingDetails) return;
    setError('');
    if (mode === 'create' && !values.fecha_nacimiento) {
      setError('La fecha de nacimiento es obligatoria para crear el paciente');
      return;
    }
    if (!values.nombre.trim() || !values.apellido.trim() || !values.dni.trim()) {
      setError('Nombre, apellido y DNI son obligatorios');
      return;
    }
    setSaving(true);
    try {
      const payload = formToPayload(values);
      if (mode === 'create') {
        await createPaciente(payload as Partial<Paciente>);
      } else if (paciente) {
        await updatePaciente(paciente.id, payload as Partial<Paciente>);
      }
      await onSaved();
      onClose();
    } catch (e: unknown) {
      setError(getSafeApiErrorMessage(e, mode === 'create' ? 'Error al crear el paciente' : 'Error al guardar los cambios'));
    } finally {
      setSaving(false);
    }
  };

  const title = mode === 'create' ? 'Nuevo Paciente' : 'Editar Paciente';

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">{title}</Typography>
          <IconButton onClick={onClose} disabled={saving} sx={{ color: 'grey.500' }}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {mode === 'edit' && paciente && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {paciente.nombre} {paciente.apellido} — ID {paciente.id}
          </Typography>
        )}
        {loadingDetails && <CircularProgress aria-label="Cargando ficha" size={24} />}
        {detailsReady && (
          <>
            <PacienteDemographicsForm
              values={values}
              onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
              requireBirthDate={mode === 'create'}
              hideObraSocial={mode === 'edit'}
            />
            {mode === 'edit' && paciente && (
              <PacienteAfiliacionesEditor
                pacienteId={paciente.id}
                obraSocialForm={values.obra_social}
                numeroAfiliadoForm={values.numero_afiliado}
                onPrincipalChange={handlePrincipalChange}
                disabled={saving}
              />
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button variant="contained" disabled={saving || loadingDetails || !detailsReady} onClick={handleSave}>
          {saving ? 'Guardando…' : mode === 'create' ? 'Crear Paciente' : 'Guardar Cambios'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PacienteFormDialog;
