import React, { useMemo } from 'react';
import {
  Box,
  Checkbox,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { LimsPanelExamen, LimsTipoExamen } from '../../types/lims';
import {
  buildCatalogMaps,
  countPapelSelection,
  resolvePapelItemId,
  resolvePapelItemLabel,
  SOLICITUD_ANALISIS_PAPEL_ROWS,
  type CatalogMaps,
  type PapelItemRef,
} from '../../modules/laboratorio/solicitudAnalisisPapelLayout';

export interface SolicitudAnalisisPapelFormProps {
  examenes: LimsTipoExamen[];
  paneles: LimsPanelExamen[];
  selectedPanelesIds: Set<number>;
  selectedExamenesIds: Set<number>;
  onTogglePanel: (id: number) => void;
  onToggleExamen: (id: number) => void;
  observaciones?: string;
  onObservacionesChange?: (value: string) => void;
  showHeader?: boolean;
  disabled?: boolean;
}

function PapelCheckbox({
  item,
  maps,
  checked,
  onToggle,
  disabled,
}: {
  item: PapelItemRef;
  maps: CatalogMaps;
  checked: boolean;
  onToggle: (id: number) => void;
  disabled?: boolean;
}) {
  const id = resolvePapelItemId(item, maps);
  const label = resolvePapelItemLabel(item, maps);
  if (id == null || !label) {
    return (
      <Typography variant="body2" color="text.disabled" sx={{ pl: 4, minHeight: 42 }}>
        {item.codigo} (no en catálogo)
      </Typography>
    );
  }
  return (
    <FormControlLabel
      sx={{ alignItems: 'flex-start', m: 0, width: '100%' }}
      control={
        <Checkbox
          size="small"
          checked={checked}
          disabled={disabled}
          onChange={() => onToggle(id)}
          sx={{ pt: 0.5 }}
        />
      }
      label={
        <Typography variant="body2" sx={{ lineHeight: 1.35 }}>
          {label}
        </Typography>
      }
    />
  );
}

const SolicitudAnalisisPapelForm: React.FC<SolicitudAnalisisPapelFormProps> = ({
  examenes,
  paneles,
  selectedPanelesIds,
  selectedExamenesIds,
  onTogglePanel,
  onToggleExamen,
  observaciones = '',
  onObservacionesChange,
  showHeader = true,
  disabled = false,
}) => {
  const maps = useMemo(
    () => buildCatalogMaps(paneles, examenes),
    [paneles, examenes]
  );

  const total = countPapelSelection(selectedPanelesIds, selectedExamenesIds);

  const renderCell = (item: PapelItemRef | null | undefined) => {
    if (!item) {
      return <Box sx={{ minHeight: 42 }} />;
    }
    const id = resolvePapelItemId(item, maps);
    if (id == null) {
      return (
        <Typography variant="body2" color="text.disabled" sx={{ pl: 4, minHeight: 42 }}>
          —
        </Typography>
      );
    }
    const checked =
      item.kind === 'panel'
        ? selectedPanelesIds.has(id)
        : selectedExamenesIds.has(id);
    const onToggle = item.kind === 'panel' ? onTogglePanel : onToggleExamen;
    return (
      <PapelCheckbox
        item={item}
        maps={maps}
        checked={checked}
        onToggle={onToggle}
        disabled={disabled}
      />
    );
  };

  return (
    <Stack spacing={2}>
      {showHeader && (
        <Box textAlign="center">
          <Typography variant="h6" fontWeight={700} letterSpacing={1}>
            LABORATORIO
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Solicitud de análisis
          </Typography>
        </Box>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 0,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          maxHeight: { xs: '48vh', sm: '52vh' },
          minHeight: 220,
          overflowY: 'auto',
          overscrollBehavior: 'contain',
        }}
      >
        <Box
          sx={{
            px: 1.5,
            py: 1,
            bgcolor: 'background.paper',
            borderBottom: 1,
            borderColor: 'divider',
            display: { xs: 'none', sm: 'block' },
            position: 'sticky',
            top: 0,
            zIndex: 1,
          }}
        >
          <Typography variant="caption" fontWeight={600}>
            Columna izquierda
          </Typography>
        </Box>
        <Box
          sx={{
            px: 1.5,
            py: 1,
            bgcolor: 'background.paper',
            borderBottom: 1,
            borderColor: 'divider',
            display: { xs: 'none', sm: 'block' },
            position: 'sticky',
            top: 0,
            zIndex: 1,
          }}
        >
          <Typography variant="caption" fontWeight={600}>
            Columna derecha
          </Typography>
        </Box>

        {SOLICITUD_ANALISIS_PAPEL_ROWS.map((row, index) => (
          <React.Fragment key={`row-${index}`}>
            <Box
              sx={{
                px: 1,
                py: 0.5,
                borderBottom: index < SOLICITUD_ANALISIS_PAPEL_ROWS.length - 1 ? 1 : 0,
                borderColor: 'divider',
              }}
            >
              {renderCell(row.left)}
            </Box>
            <Box
              sx={{
                px: 1,
                py: 0.5,
                borderBottom: index < SOLICITUD_ANALISIS_PAPEL_ROWS.length - 1 ? 1 : 0,
                borderColor: 'divider',
                borderLeft: { sm: 1 },
              }}
            >
              {renderCell(row.right)}
            </Box>
          </React.Fragment>
        ))}
      </Box>

      <Typography variant="caption" color="text.secondary" display="block" textAlign="center">
        Desplazá la lista para ver más análisis
      </Typography>

      {onObservacionesChange && (
        <TextField
          fullWidth
          multiline
          minRows={2}
          label="Otro / observaciones"
          placeholder="Indicaciones adicionales, diagnóstico, etc."
          value={observaciones}
          onChange={(ev) => onObservacionesChange(ev.target.value)}
          disabled={disabled}
        />
      )}

      <Typography variant="caption" color="text.secondary">
        {total === 0
          ? 'Seleccioná al menos un análisis o panel.'
          : `${total} ítem${total === 1 ? '' : 's'} seleccionado${total === 1 ? '' : 's'}.`}
      </Typography>
    </Stack>
  );
};

export default SolicitudAnalisisPapelForm;

export function useSolicitudAnalisisSelection() {
  const [selectedPanelesIds, setSelectedPanelesIds] = React.useState<Set<number>>(
    () => new Set()
  );
  const [selectedExamenesIds, setSelectedExamenesIds] = React.useState<Set<number>>(
    () => new Set()
  );

  const togglePanel = React.useCallback((id: number) => {
    setSelectedPanelesIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleExamen = React.useCallback((id: number) => {
    setSelectedExamenesIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const resetSelection = React.useCallback(() => {
    setSelectedPanelesIds(new Set());
    setSelectedExamenesIds(new Set());
  }, []);

  const getSelectionArrays = React.useCallback(
    () => ({
      paneles_ids: Array.from(selectedPanelesIds),
      examenes_ids: Array.from(selectedExamenesIds),
    }),
    [selectedPanelesIds, selectedExamenesIds]
  );

  const hasSelection = selectedPanelesIds.size + selectedExamenesIds.size > 0;

  return {
    selectedPanelesIds,
    selectedExamenesIds,
    togglePanel,
    toggleExamen,
    resetSelection,
    getSelectionArrays,
    hasSelection,
  };
}
