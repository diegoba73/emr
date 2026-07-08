import React from 'react';
import { Box, MenuItem, TextField } from '@mui/material';

export interface PacienteDemographicsFormValues {
  nombre: string;
  apellido: string;
  dni: string;
  fecha_nacimiento: string;
  sexo: 'M' | 'F' | '';
  telefono: string;
  email: string;
  direccion: string;
  obra_social: string;
  numero_afiliado: string;
  observaciones: string;
}

export const emptyPacienteFormValues = (): PacienteDemographicsFormValues => ({
  nombre: '',
  apellido: '',
  dni: '',
  fecha_nacimiento: '',
  sexo: '',
  telefono: '',
  email: '',
  direccion: '',
  obra_social: '',
  numero_afiliado: '',
  observaciones: '',
});

export interface PacienteDemographicsFormProps {
  values: PacienteDemographicsFormValues;
  onChange: (patch: Partial<PacienteDemographicsFormValues>) => void;
  dniReadOnly?: boolean;
}

const PacienteDemographicsForm: React.FC<PacienteDemographicsFormProps> = ({
  values,
  onChange,
  dniReadOnly = false,
}) => (
  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 1 }}>
    <TextField
      label="Nombre *"
      value={values.nombre}
      onChange={(e) => onChange({ nombre: e.target.value })}
      required
      sx={{ flex: '1 1 200px' }}
    />
    <TextField
      label="Apellido *"
      value={values.apellido}
      onChange={(e) => onChange({ apellido: e.target.value })}
      required
      sx={{ flex: '1 1 200px' }}
    />
    <TextField
      label="DNI *"
      value={values.dni}
      onChange={(e) => onChange({ dni: e.target.value })}
      required
      disabled={dniReadOnly}
      helperText={dniReadOnly ? 'El DNI no se modifica desde aquí' : undefined}
      sx={{ flex: '1 1 150px' }}
    />
    <TextField
      label="Fecha de Nacimiento"
      type="date"
      value={values.fecha_nacimiento}
      onChange={(e) => onChange({ fecha_nacimiento: e.target.value })}
      InputLabelProps={{ shrink: true }}
      sx={{ flex: '1 1 180px' }}
    />
    <TextField
      select
      label="Sexo"
      value={values.sexo}
      onChange={(e) => onChange({ sexo: e.target.value as 'M' | 'F' | '' })}
      sx={{ flex: '1 1 150px' }}
    >
      <MenuItem value="">Seleccionar</MenuItem>
      <MenuItem value="M">Masculino</MenuItem>
      <MenuItem value="F">Femenino</MenuItem>
    </TextField>
    <TextField
      label="Teléfono"
      value={values.telefono}
      onChange={(e) => onChange({ telefono: e.target.value })}
      sx={{ flex: '1 1 180px' }}
    />
    <TextField
      label="Email"
      type="email"
      value={values.email}
      onChange={(e) => onChange({ email: e.target.value })}
      sx={{ flex: '1 1 260px' }}
    />
    <TextField
      label="Dirección"
      value={values.direccion}
      onChange={(e) => onChange({ direccion: e.target.value })}
      fullWidth
    />
    <TextField
      label="Obra Social"
      value={values.obra_social}
      onChange={(e) => onChange({ obra_social: e.target.value })}
      sx={{ flex: '1 1 260px' }}
    />
    <TextField
      label="N° Afiliado"
      value={values.numero_afiliado}
      onChange={(e) => onChange({ numero_afiliado: e.target.value })}
      sx={{ flex: '1 1 180px' }}
    />
    <TextField
      label="Observaciones"
      value={values.observaciones}
      onChange={(e) => onChange({ observaciones: e.target.value })}
      fullWidth
      multiline
      minRows={2}
    />
  </Box>
);

export default PacienteDemographicsForm;
