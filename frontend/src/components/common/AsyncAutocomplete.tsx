import React, { useState, useEffect, useMemo } from 'react';
import { Autocomplete, TextField, CircularProgress } from '@mui/material';
import { debounce } from '@mui/material/utils';
import { api } from '../../services/apiService';

interface AsyncAutocompleteProps<T> {
  label: string;
  endpoint: string; // Ej: '/pacientes/' o '/medicos/'
  value: T | null;
  onChange: (value: T | null) => void;
  getOptionLabel: (option: T) => string;
  renderOption?: (props: React.HTMLAttributes<HTMLLIElement>, option: T) => React.ReactNode;
  placeholder?: string;
  minChars?: number; // Mínimo de caracteres para buscar (alias de minSearchLength)
  minSearchLength?: number; // Mínimo de caracteres para buscar
  debounceMs?: number; // Tiempo de debounce en milisegundos
  required?: boolean;
  helperText?: string;
  error?: boolean;
  disabled?: boolean;
  sx?: any;
}

/**
 * Componente reutilizable para búsqueda asíncrona con Autocomplete de Material UI.
 * 
 * Características:
 * - Búsqueda en servidor con debounce (400ms)
 * - Manejo correcto de inputValue separado del value
 * - Soporte para valores seleccionados que no están en la lista actual
 * - Optimizado para rendimiento
 */
export default function AsyncAutocomplete<T extends { id: any }>({
  label,
  endpoint,
  value,
  onChange,
  getOptionLabel,
  renderOption,
  placeholder = "Escriba para buscar...",
  minChars,
  minSearchLength,
  debounceMs = 300,
  required = false,
  helperText,
  error = false,
  disabled = false,
  sx,
}: AsyncAutocompleteProps<T>) {
  // Usar minSearchLength si está definido, sino minChars, sino 2 por defecto
  const minCharsToUse = minSearchLength ?? minChars ?? 2;
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Estado para lo que el usuario escribe (CRÍTICO: separado del value)
  const [inputValue, setInputValue] = useState('');

  // Inicializar inputValue cuando cambia el value (al editar)
  useEffect(() => {
    if (value) {
      setInputValue(getOptionLabel(value));
    } else {
      setInputValue('');
    }
  }, [value, getOptionLabel]);

  // Debounce para no saturar el servidor
  const fetchOptions = useMemo(
    () =>
      debounce(async (request: { input: string }, callback: (results?: T[]) => void) => {
        try {
          // Construir URL con parámetro search para búsqueda remota eficiente
          // El backend aplica límite de 20 resultados automáticamente cuando hay búsqueda
          const searchParams = new URLSearchParams();
          if (request.input && request.input.length >= minCharsToUse) {
            searchParams.append('search', request.input);
          }
          
          // Para pacientes, los médicos necesitan ?all=true para ver todos en selects (modales de turnos)
          // Según DOC_REGLAS_NEGOCIO: médicos solo ven pacientes con turnos/consultas por defecto
          // pero en contextos de selección (modales) necesitan ver todos
          const isPacientesEndpoint = endpoint.includes('/pacientes');
          if (isPacientesEndpoint) {
            // Agregar ?all=true para que los médicos vean todos los pacientes en selects
            // El backend aplica este filtro correctamente según DOC_REGLAS_NEGOCIO.md
            searchParams.append('all', 'true');
          }
          
          const url = searchParams.toString() 
            ? `${endpoint}?${searchParams.toString()}`
            : endpoint;
          
          // Usar la instancia de api configurada
          const response = await api.get<{ results?: T[] } | T[]>(url);
          
          // Soporte para paginación de DRF: busca en 'results' si existe, sino usa data directo
          let data = response.data;
          if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
            data = data.results;
          } else if (!Array.isArray(data)) {
            data = [];
          }
          
          callback(data as T[]);
        } catch (error) {
          console.error(`Error fetching options from ${endpoint}:`, error);
          callback([]);
        }
      }, debounceMs),
    [endpoint, debounceMs, minCharsToUse]
  );

  useEffect(() => {
    let active = true;

    if (inputValue.length < minCharsToUse) {
      setOptions(value ? [value] : []);
      setLoading(false);
      return () => {
        active = false;
      };
    }

    setLoading(true);

    fetchOptions({ input: inputValue }, (results?: T[]) => {
      if (active) {
        let newOptions: T[] = [];
        
        // Si hay un valor seleccionado, incluirlo en las opciones
        if (value) {
          newOptions = [value];
        }
        
        // Agregar resultados de la búsqueda
        if (results) {
          newOptions = [...newOptions, ...results];
        }
        
        // Eliminar duplicados por ID
        const uniqueOptions = Array.from(
          new Map(newOptions.map(item => [item.id, item])).values()
        );
        
        setOptions(uniqueOptions);
        setLoading(false);
      }
    });

    return () => {
      active = false;
    };
  }, [value, inputValue, fetchOptions, minCharsToUse]);

  return (
    <Autocomplete
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      
      // Control de Valor Seleccionado
      value={value}
      onChange={(event, newValue) => {
        onChange(newValue);
      }}

      // Control de Texto Escrito (CRÍTICO PARA QUE FUNCIONE EL TECLADO)
      inputValue={inputValue}
      onInputChange={(event, newInputValue) => {
        setInputValue(newInputValue);
      }}

      // Opciones
      options={options}
      loading={loading}
      getOptionLabel={getOptionLabel}
      renderOption={renderOption}
      
      // Desactivar filtro cliente (el servidor ya filtra)
      filterOptions={(x) => x}
      
      // Comparación de igualdad
      isOptionEqualToValue={(option, value) => {
        if (!value) return false;
        return option.id === value.id;
      }}

      // Deshabilitado
      disabled={disabled}

      // Mensaje cuando no hay opciones
      noOptionsText={
        loading
          ? 'Buscando...'
          : inputValue.length < minCharsToUse
          ? `Escriba al menos ${minCharsToUse} caracteres para buscar`
          : 'No se encontraron resultados'
      }

      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          required={required}
          helperText={helperText}
          error={error}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <React.Fragment>
                {loading ? <CircularProgress color="inherit" size={20} /> : null}
                {params.InputProps.endAdornment}
              </React.Fragment>
            ),
          }}
        />
      )}
      fullWidth
      sx={sx}
    />
  );
}
