import React, { useEffect, useState } from 'react';
import { FormControl, InputLabel, MenuItem, Select, FormHelperText } from '@mui/material';
import { listObrasSociales, type ObraSocialCatalogo } from '../services/obrasSociales';

export interface ObraSocialSelectProps {
  value: string;
  onChange: (codigo: string) => void;
  required?: boolean;
  label?: string;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  size?: 'small' | 'medium';
}

const ObraSocialSelect: React.FC<ObraSocialSelectProps> = ({
  value,
  onChange,
  required = false,
  label = 'Obra social',
  disabled = false,
  error = false,
  helperText,
  fullWidth = true,
  size = 'medium',
}) => {
  const [options, setOptions] = useState<ObraSocialCatalogo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listObrasSociales(true)
      .then((rows) => {
        if (!cancelled) setOptions(rows);
      })
      .catch(() => {
        if (!cancelled) setOptions([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <FormControl fullWidth={fullWidth} required={required} error={error} size={size} disabled={disabled || loading}>
      <InputLabel>{required ? `${label} *` : label}</InputLabel>
      <Select
        label={required ? `${label} *` : label}
        value={value || ''}
        onChange={(e) => onChange(String(e.target.value))}
      >
        {!required && <MenuItem value="">—</MenuItem>}
        {options.map((o) => (
          <MenuItem key={o.id} value={o.codigo}>
            {o.nombre}
            {o.codigo === 'PARTICULAR' ? ' (sin cobertura)' : ''}
          </MenuItem>
        ))}
      </Select>
      {helperText ? <FormHelperText>{helperText}</FormHelperText> : null}
    </FormControl>
  );
};

export default ObraSocialSelect;
