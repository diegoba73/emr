import React, { useMemo } from 'react';
import {
  Box,
  Checkbox,
  Chip,
  FormControlLabel,
  Stack,
  Typography,
} from '@mui/material';
import type { TipoCultivoMicrobiologia, TipoMuestraMicrobiologia } from '../../types/lims';
import { sugerirMuestraPorCultivo } from '../../utils/limsMicroUx';

export interface MicroPedidoItem {
  key: string;
  tipo_cultivo_id: number;
  tipo_muestra_micro_id: number;
  cultivo_codigo: string;
  cultivo_nombre: string;
  muestra_nombre: string;
}

export interface SolicitudMicrobiologiaFormProps {
  cultivos: TipoCultivoMicrobiologia[];
  tiposMuestra: TipoMuestraMicrobiologia[];
  items: MicroPedidoItem[];
  onChangeItems: (items: MicroPedidoItem[]) => void;
  disabled?: boolean;
}

function resolverMuestra(
  cultivo: TipoCultivoMicrobiologia,
  tiposMuestra: TipoMuestraMicrobiologia[]
): TipoMuestraMicrobiologia | null {
  return sugerirMuestraPorCultivo(cultivo.codigo, tiposMuestra) || tiposMuestra[0] || null;
}

const SolicitudMicrobiologiaForm: React.FC<SolicitudMicrobiologiaFormProps> = ({
  cultivos,
  tiposMuestra,
  items,
  onChangeItems,
  disabled,
}) => {
  const selectedCultivoIds = useMemo(
    () => new Set(items.map((i) => i.tipo_cultivo_id)),
    [items]
  );

  const toggleCultivo = (cultivo: TipoCultivoMicrobiologia) => {
    if (disabled) return;
    if (selectedCultivoIds.has(cultivo.id)) {
      onChangeItems(items.filter((i) => i.tipo_cultivo_id !== cultivo.id));
      return;
    }
    const muestra = resolverMuestra(cultivo, tiposMuestra);
    if (!muestra) return;
    onChangeItems([
      ...items,
      {
        key: `${cultivo.id}:${muestra.id}`,
        tipo_cultivo_id: cultivo.id,
        tipo_muestra_micro_id: muestra.id,
        cultivo_codigo: cultivo.codigo,
        cultivo_nombre: cultivo.nombre,
        muestra_nombre: muestra.nombre,
      },
    ]);
  };

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle2">Tipos de cultivo</Typography>
      <Typography variant="caption" color="text.secondary">
        Cada cultivo seleccionado genera una muestra y una etiqueta. El tipo de muestra se
        asigna automáticamente según el cultivo.
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 0.5,
          maxHeight: 320,
          overflow: 'auto',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          p: 1,
        }}
      >
        {cultivos.map((c) => (
          <FormControlLabel
            key={c.id}
            sx={{ m: 0, alignItems: 'flex-start' }}
            control={
              <Checkbox
                size="small"
                checked={selectedCultivoIds.has(c.id)}
                disabled={disabled || tiposMuestra.length === 0}
                onChange={() => toggleCultivo(c)}
                sx={{ pt: 0.25 }}
              />
            }
            label={
              <Typography variant="body2" sx={{ lineHeight: 1.35 }}>
                {c.nombre}
              </Typography>
            }
          />
        ))}
      </Box>

      {items.length > 0 && (
        <Stack direction="row" flexWrap="wrap" useFlexGap spacing={0.75}>
          {items.map((item) => (
            <Chip
              key={item.key}
              label={item.cultivo_nombre}
              onDelete={
                disabled
                  ? undefined
                  : () =>
                      onChangeItems(items.filter((i) => i.tipo_cultivo_id !== item.tipo_cultivo_id))
              }
              size="small"
            />
          ))}
        </Stack>
      )}

      {tiposMuestra.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No hay tipos de muestra de microbiología cargados.
        </Typography>
      )}
    </Stack>
  );
};

export default SolicitudMicrobiologiaForm;
