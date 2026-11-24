import React, { useCallback, useMemo, useState } from 'react';
import { Alert, Box, Button } from '@mui/material';
import AsyncAutocomplete from '../common/AsyncAutocomplete';
import PacienteFormDialog from '../PacienteFormDialog';
import type { Paciente } from '../../types';
import { formatPacienteLabel } from '../../utils/pacienteFormat';

/** DNI típico AR: solo dígitos, 7–8 (acepta 6–10 por margen). */
export function looksLikeDniQuery(raw: string): boolean {
  const q = raw.trim().replace(/[.\s-]/g, '');
  return /^\d{6,10}$/.test(q);
}

export function normalizeDniQuery(raw: string): string {
  return raw.trim().replace(/[.\s-]/g, '');
}

export interface PacienteAgendaSelectProps {
  value: Paciente | null;
  onChange: (paciente: Paciente | null) => void;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  helperText?: string;
  placeholder?: string;
  sx?: object;
  /** Permite alta inline cuando el DNI buscado no existe. Default true. */
  allowCreateIfMissing?: boolean;
  /** Override debounce de búsqueda (tests). */
  debounceMs?: number;
}

/**
 * Búsqueda de paciente para agenda/turno.
 * Si se busca un DNI sin resultados, ofrece crear la ficha y seguir con el turno.
 */
const PacienteAgendaSelect: React.FC<PacienteAgendaSelectProps> = ({
  value,
  onChange,
  label = 'Paciente',
  required = false,
  disabled = false,
  helperText,
  placeholder = 'Buscar por nombre, apellido o DNI…',
  sx,
  allowCreateIfMissing = true,
  debounceMs = 300,
}) => {
  const [searchMeta, setSearchMeta] = useState({
    inputValue: '',
    options: [] as Paciente[],
    loading: false,
  });
  const [altaOpen, setAltaOpen] = useState(false);
  const [dniInicial, setDniInicial] = useState('');
  /** DNI sin ficha (persiste aunque el Autocomplete limpie el input al blur). */
  const [dniSinFicha, setDniSinFicha] = useState('');

  const onSearchMetaChange = useCallback(
    (meta: { inputValue: string; options: Paciente[]; loading: boolean }) => {
      setSearchMeta(meta);
      if (meta.loading) return;
      if (!looksLikeDniQuery(meta.inputValue)) {
        if (!altaOpen) setDniSinFicha('');
        return;
      }
      const dni = normalizeDniQuery(meta.inputValue);
      const hayMatch = meta.options.some(
        (p) => normalizeDniQuery(p.dni || '') === dni,
      );
      setDniSinFicha(hayMatch ? '' : dni);
    },
    [altaOpen],
  );

  const mostrarAlta = Boolean(
    allowCreateIfMissing && !disabled && !value && dniSinFicha,
  );

  const abrirAlta = () => {
    setDniInicial(dniSinFicha);
    setAltaOpen(true);
  };

  const seleccionar = (p: Paciente | null) => {
    onChange(p);
  };

  return (
    <Box sx={sx}>
      <AsyncAutocomplete<Paciente>
        label={label}
        endpoint="/pacientes/"
        value={value}
        onChange={seleccionar}
        getOptionLabel={formatPacienteLabel}
        required={required}
        disabled={disabled}
        helperText={helperText}
        placeholder={placeholder}
        debounceMs={debounceMs}
        minSearchLength={2}
        onSearchMetaChange={onSearchMetaChange}
        noOptionsTextOverride={
          mostrarAlta ? `No hay paciente con DNI ${dniSinFicha}` : undefined
        }
      />
      {mostrarAlta && (
        <Alert
          severity="info"
          sx={{ mt: 1 }}
          action={
            <Button
              color="inherit"
              size="small"
              type="button"
              // Evita blur del Autocomplete que limpia el input antes del click.
              onMouseDown={(e) => e.preventDefault()}
              onClick={abrirAlta}
            >
              Crear paciente
            </Button>
          }
        >
          No existe un paciente con DNI {dniSinFicha}. Podés darlo de alta y
          continuar con el turno.
        </Alert>
      )}
      <PacienteFormDialog
        open={altaOpen}
        mode="create"
        initialValues={{ dni: dniInicial }}
        onClose={() => setAltaOpen(false)}
        onSaved={async (creado) => {
          if (creado) {
            setDniSinFicha('');
            seleccionar(creado);
          }
        }}
        onUseExisting={(existente) => {
          setDniSinFicha('');
          seleccionar(existente);
        }}
      />
    </Box>
  );
};

export default PacienteAgendaSelect;
