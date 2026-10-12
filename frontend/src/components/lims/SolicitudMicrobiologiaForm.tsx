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
  /**
   * Si hay códigos, solo se muestran esos cultivos.
   * Mapa cultivo → muestra micro preferida (desde materiales de pedido).
   */
  cultivosPermitidos?: string[] | null;
  muestraPreferidaPorCultivo?: Record<string, string>;
}

function resolverMuestra(
  cultivo: TipoCultivoMicrobiologia,
  tiposMuestra: TipoMuestraMicrobiologia[],
  preferidaCodigo?: string
): TipoMuestraMicrobiologia | null {
  if (preferidaCodigo) {
    const exact = tiposMuestra.find(
      (t) => (t.codigo || '').toUpperCase() === preferidaCodigo.toUpperCase()
    );
    if (exact) return exact;
  }
  return sugerirMuestraPorCultivo(cultivo.codigo, tiposMuestra) || tiposMuestra[0] || null;
}

export default function SolicitudMicrobiologiaForm({
  cultivos,
  tiposMuestra,
  items,
  onChangeItems,
  disabled,
  cultivosPermitidos,
  muestraPreferidaPorCultivo,
}: SolicitudMicrobiologiaFormProps) {
  const selectedCultivoIds = useMemo(
    () => new Set(items.map((i) => i.tipo_cultivo_id)),
    [items]
  );

  const cultivosVisibles = useMemo(() => {
    if (!cultivosPermitidos || cultivosPermitidos.length === 0) {
      return cultivos.filter((c) => c.activo !== false);
    }
    const allow = new Set(cultivosPermitidos.map((c) => c.toUpperCase()));
    return cultivos.filter(
      (c) => c.activo !== false && allow.has((c.codigo || '').toUpperCase())
    );
  }, [cultivos, cultivosPermitidos]);

  const toggleCultivo = (cultivo: TipoCultivoMicrobiologia) => {
    if (disabled) return;
    if (selectedCultivoIds.has(cultivo.id)) {
      onChangeItems(items.filter((i) => i.tipo_cultivo_id !== cultivo.id));
      return;
    }
    const preferida = muestraPreferidaPorCultivo?.[cultivo.codigo];
    const muestra = resolverMuestra(cultivo, tiposMuestra, preferida);
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

  const filtrado = Boolean(cultivosPermitidos && cultivosPermitidos.length > 0);

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle2">Tipos de cultivo</Typography>
      <Typography variant="caption" color="text.secondary">
        {filtrado
          ? 'Solo se muestran los cultivos del material elegido en Lab. Clínico (evita seleccionar otro por error).'
          : 'Cada cultivo seleccionado genera una muestra y una etiqueta. El tipo de muestra se asigna automáticamente según el cultivo.'}
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
        {cultivosVisibles.map((c) => (
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

      {filtrado && cultivosVisibles.length === 0 && (
        <Typography variant="body2" color="warning.main">
          No hay cultivos mapeados para el material elegido, o aún no están cargados en el
          catálogo. Corré el seed de materiales de pedido.
        </Typography>
      )}

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
}
