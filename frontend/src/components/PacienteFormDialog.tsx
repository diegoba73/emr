import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from '@mui/material';
import { Close } from '@mui/icons-material';
import type { Paciente } from '../types';
import { createPaciente, updatePaciente } from '../services/apiService';
import { getSafeApiErrorMessage } from '../utils/apiError';
import PacienteDemographicsForm, {
  emptyPacienteFormValues,
  type PacienteDemographicsFormValues,
} from './PacienteDemographicsForm';

function pacienteToFormValues(p: Paciente): PacienteDemographicsFormValues {
  const fecha = p.fecha_nacimiento;
  return {
    nombre: p.nombre || '',
    apellido: p.apellido || '',
    dni: p.dni || '',
    fecha_nacimiento: fecha ? String(fecha).slice(0, 10) : '',
    sexo: (p.sexo as 'M' | 'F') || '',
    telefono: p.telefono || '',
    email: p.email || '',
    direccion: p.direccion || '',
    obra_social: p.obra_social || '',
    numero_afiliado: p.numero_afiliado || '',
    observaciones: p.observaciones || '',
  };
}

function formToPayload(values: PacienteDemographicsFormValues): Record<string, string> {
  const payload: Record<string, string> = {
    nombre: values.nombre.trim(),
    apellido: values.apellido.trim(),
    dni: values.dni.trim(),
    telefono: values.telefono.trim(),
    email: values.email.trim(),
    direccion: values.direccion.trim(),
    obra_social: values.obra_social.trim(),
    numero_afiliado: values.numero_afiliado.trim(),
    observaciones: values.observaciones.trim(),
  };
  if (values.fecha_nacimiento) payload.fecha_nacimiento = values.fecha_nacimiento;
  if (values.sexo) payload.sexo = values.sexo;
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

  useEffect(() => {
    if (!open) return;
    setError('');
    if (mode === 'edit' && paciente) {
      setValues(pacienteToFormValues(paciente));
    } else {
      setValues(emptyPacienteFormValues());
    }
  }, [open, mode, paciente]);

  const handleSave = async () => {
    setError('');
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
        <PacienteDemographicsForm
          values={values}
          onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
          dniReadOnly={mode === 'edit'}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button variant="contained" disabled={saving} onClick={handleSave}>
          {saving ? 'Guardando…' : mode === 'create' ? 'Crear Paciente' : 'Guardar Cambios'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PacienteFormDialog;
