import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { Paciente, PacienteAfiliacion } from '../../types';
import { formatPacienteObraSocial } from '../../utils/pacienteFormat';

export type ObraSocialPedidoValue = {
  afiliacionId: number | null;
  obra_social: string;
  numero_afiliado: string;
};

type Props = {
  paciente: Paciente | null | undefined;
  value: ObraSocialPedidoValue;
  onChange: (next: ObraSocialPedidoValue) => void;
  disabled?: boolean;
};

function afiliacionesActivas(paciente: Paciente | null | undefined): PacienteAfiliacion[] {
  const list = paciente?.afiliaciones;
  if (Array.isArray(list) && list.length > 0) {
    return list.filter((a) => a.activo !== false);
  }
  const os = (paciente?.obra_social || '').trim();
  if (!os) return [];
  return [
    {
      id: 0,
      obra_social: os,
      numero_afiliado: (paciente?.numero_afiliado || '').trim(),
      es_principal: true,
      activo: true,
    },
  ];
}

/**
 * Selector + edición de OS/afiliado para el diálogo de nueva orden.
 * No persiste solo: el padre envía el snapshot al crear la orden.
 */
const ObraSocialPedidoFields: React.FC<Props> = ({
  paciente,
  value,
  onChange,
  disabled = false,
}) => {
  const afils = useMemo(() => afiliacionesActivas(paciente), [paciente]);
  const [modoNueva, setModoNueva] = useState(false);

  useEffect(() => {
    if (!paciente) {
      onChange({ afiliacionId: null, obra_social: '', numero_afiliado: '' });
      setModoNueva(false);
      return;
    }
    const principal =
      afils.find((a) => a.es_principal) || afils[0] || null;
    if (principal) {
      onChange({
        afiliacionId: principal.id > 0 ? principal.id : null,
        obra_social: principal.obra_social || '',
        numero_afiliado: principal.numero_afiliado || '',
      });
      setModoNueva(false);
    } else {
      onChange({
        afiliacionId: null,
        obra_social: paciente.obra_social || '',
        numero_afiliado: paciente.numero_afiliado || '',
      });
      setModoNueva(true);
    }
    // Solo al cambiar de paciente
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paciente?.id]);

  const selectValue = modoNueva
    ? '__nueva__'
    : value.afiliacionId != null
      ? String(value.afiliacionId)
      : afils.length
        ? String(afils[0].id)
        : '__nueva__';

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        p: 1.5,
      }}
    >
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Obra social del pedido
      </Typography>
      <Stack spacing={1.25}>
        {afils.length > 0 && (
          <FormControl size="small" fullWidth disabled={disabled}>
            <InputLabel id="os-pedido-label">Afiliación</InputLabel>
            <Select
              labelId="os-pedido-label"
              label="Afiliación"
              value={selectValue}
              onChange={(e) => {
                const v = e.target.value;
                if (v === '__nueva__') {
                  setModoNueva(true);
                  onChange({ afiliacionId: null, obra_social: '', numero_afiliado: '' });
                  return;
                }
                setModoNueva(false);
                const afil = afils.find((a) => String(a.id) === v);
                if (!afil) return;
                onChange({
                  afiliacionId: afil.id > 0 ? afil.id : null,
                  obra_social: afil.obra_social || '',
                  numero_afiliado: afil.numero_afiliado || '',
                });
              }}
            >
              {afils.map((a) => (
                <MenuItem key={a.id || a.obra_social} value={String(a.id)}>
                  {formatPacienteObraSocial({
                    obra_social: a.obra_social,
                    numero_afiliado: a.numero_afiliado,
                  } as Paciente)}
                  {a.es_principal ? ' (principal)' : ''}
                </MenuItem>
              ))}
              <MenuItem value="__nueva__">Otra obra social…</MenuItem>
            </Select>
          </FormControl>
        )}
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <TextField
            size="small"
            label="Obra social"
            value={value.obra_social}
            onChange={(e) =>
              onChange({
                ...value,
                afiliacionId: null,
                obra_social: e.target.value,
              })
            }
            disabled={disabled}
            fullWidth
            sx={{ flex: 2 }}
          />
          <TextField
            size="small"
            label="N° afiliado"
            value={value.numero_afiliado}
            onChange={(e) =>
              onChange({
                ...value,
                afiliacionId: null,
                numero_afiliado: e.target.value,
              })
            }
            disabled={disabled}
            fullWidth
            sx={{ flex: 1 }}
          />
        </Stack>
        {afils.length === 0 && !value.obra_social.trim() && (
          <Typography variant="caption" color="text.secondary">
            Sin obra social cargada. Completá los campos para registrarla en este pedido.
          </Typography>
        )}
        {modoNueva && afils.length > 0 && (
          <Button
            size="small"
            onClick={() => {
              const principal = afils.find((a) => a.es_principal) || afils[0];
              if (!principal) return;
              setModoNueva(false);
              onChange({
                afiliacionId: principal.id > 0 ? principal.id : null,
                obra_social: principal.obra_social || '',
                numero_afiliado: principal.numero_afiliado || '',
              });
            }}
          >
            Usar afiliación existente
          </Button>
        )}
      </Stack>
    </Box>
  );
};

export default ObraSocialPedidoFields;
