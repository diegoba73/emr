import React, { useCallback, useEffect, useRef } from 'react';
import { TextField, TextFieldProps } from '@mui/material';

export interface BarcodeScanInputProps extends Omit<TextFieldProps, 'onChange' | 'value'> {
  onScan: (codigo: string) => void;
  /** Si true, limpia el campo tras cada escaneo exitoso. */
  clearOnScan?: boolean;
  disabled?: boolean;
}

/**
 * Input optimizado para lectores USB tipo teclado.
 * Al presionar Enter emite el código escaneado (trim).
 */
const BarcodeScanInput: React.FC<BarcodeScanInputProps> = ({
  onScan,
  clearOnScan = true,
  disabled = false,
  autoFocus = true,
  placeholder = 'Escanear código de barras…',
  ...textFieldProps
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const valueRef = useRef('');

  const refocus = useCallback(() => {
    if (disabled) return;
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [disabled]);

  useEffect(() => {
    refocus();
  }, [refocus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const codigo = valueRef.current.trim();
    if (!codigo) return;
    onScan(codigo);
    if (clearOnScan) {
      valueRef.current = '';
      if (inputRef.current) inputRef.current.value = '';
    }
    refocus();
  };

  return (
    <TextField
      {...textFieldProps}
      inputRef={inputRef}
      fullWidth
      autoFocus={autoFocus}
      disabled={disabled}
      placeholder={placeholder}
      onKeyDown={handleKeyDown}
      onChange={(e) => {
        valueRef.current = e.target.value;
      }}
      onBlur={refocus}
      inputProps={{
        ...textFieldProps.inputProps,
        autoComplete: 'off',
        spellCheck: false,
      }}
    />
  );
};

export default BarcodeScanInput;
