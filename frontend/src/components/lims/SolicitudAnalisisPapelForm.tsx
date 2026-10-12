import React, { useMemo, useState } from 'react';
import {
  Autocomplete,
  Box,
  Checkbox,
  Chip,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { LimsPanelExamen, LimsTipoExamen } from '../../types/lims';
import {
  buildCatalogMaps,
  countPapelSelection,
  EXAMENES_FUERA_DE_SOLICITUD,
  papelCodigosSet,
  resolvePapelItemId,
  resolvePapelItemLabel,
  SOLICITUD_ANALISIS_PAPEL_ROWS,
  type CatalogMaps,
  type PapelItemRef,
} from '../../modules/laboratorio/solicitudAnalisisPapelLayout';
import {
  CARTUCHO_CARDIACO_CODIGOS,
  CA_ION_INCLUYE_CODIGOS,
  EAB_INCLUYE_CODIGOS,
  EXAMENES_CUBIERTOS_POR_PANEL,
  esCodigoCartuchoCardiaco,
  esPanelEab,
} from '../../modules/laboratorio/solicitudAnalisisSelectionRules';

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
  /**
   * Códigos (panel o examen) a ocultar del grid papel y del buscador «Agregar».
   * Útil en prototipos / vistas por material (p. ej. sacar orina del bloque sangre).
   */
  omitCodigos?: ReadonlySet<string>;
  /**
   * Si se indica, el buscador «Agregar» solo ofrece exámenes cuyo
   * `tipo_muestra_codigo` esté en este set (p. ej. solo sangre).
   */
  agregarSoloMuestras?: ReadonlySet<string>;
  /** Etiqueta del buscador de catálogo (default: «Agregar examen del catálogo»). */
  agregarLabel?: string;
}

function DerivBadge({ exam }: { exam: LimsTipoExamen | undefined }) {
  const code = exam?.laboratorio_derivacion_codigo;
  if (!code) return null;
  return (
    <Chip
      size="small"
      label={code}
      color="warning"
      variant="outlined"
      sx={{ height: 20, ml: 0.5, fontSize: '0.65rem' }}
    />
  );
}

function PapelCheckbox({
  item,
  maps,
  examenesById,
  checked,
  onToggle,
  disabled,
}: {
  item: PapelItemRef;
  maps: CatalogMaps;
  examenesById: Map<number, LimsTipoExamen>;
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
  const exam = item.kind === 'examen' ? examenesById.get(id) : undefined;
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
        <Typography variant="body2" sx={{ lineHeight: 1.35, display: 'flex', alignItems: 'center' }}>
          {label}
          <DerivBadge exam={exam} />
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
  omitCodigos,
  agregarSoloMuestras,
  agregarLabel = 'Agregar examen del catálogo',
}) => {
  const maps = useMemo(() => buildCatalogMaps(paneles, examenes), [paneles, examenes]);
  const examenesById = useMemo(() => {
    const m = new Map<number, LimsTipoExamen>();
    for (const e of examenes) m.set(e.id, e);
    return m;
  }, [examenes]);

  const papelCodes = useMemo(() => papelCodigosSet(), []);

  const otrosOpciones = useMemo(() => {
    return examenes.filter((e) => {
      if (e.activo === false) return false;
      if (papelCodes.has(e.codigo)) return false;
      if (EXAMENES_FUERA_DE_SOLICITUD.has(e.codigo)) return false;
      if (omitCodigos?.has(e.codigo)) return false;
      if (selectedExamenesIds.has(e.id)) return false;
      if (agregarSoloMuestras) {
        const m = (e.tipo_muestra_codigo || '').toUpperCase();
        if (!agregarSoloMuestras.has(m)) return false;
      }
      return true;
    });
  }, [examenes, papelCodes, selectedExamenesIds, omitCodigos, agregarSoloMuestras]);

  const otrosSeleccionados = useMemo(() => {
    return examenes.filter((e) => {
      if (!selectedExamenesIds.has(e.id)) return false;
      if (papelCodes.has(e.codigo)) return false;
      if (omitCodigos?.has(e.codigo)) return false;
      if (agregarSoloMuestras) {
        const m = (e.tipo_muestra_codigo || '').toUpperCase();
        if (!agregarSoloMuestras.has(m)) return false;
      }
      return true;
    });
  }, [examenes, selectedExamenesIds, papelCodes, omitCodigos, agregarSoloMuestras]);

  const [otrosInput, setOtrosInput] = useState('');

  const total = countPapelSelection(selectedPanelesIds, selectedExamenesIds);

  const panelIdByCodigo = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of paneles) {
      if (p.activo !== false) m.set(p.codigo, p.id);
    }
    return m;
  }, [paneles]);

  const renderCell = (item: PapelItemRef | null | undefined) => {
    if (!item) {
      return <Box sx={{ minHeight: 42 }} />;
    }
    if (omitCodigos?.has(item.codigo)) {
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
    let checked =
      item.kind === 'panel' ? selectedPanelesIds.has(id) : selectedExamenesIds.has(id);
    let itemDisabled = disabled;
    if (item.kind === 'examen') {
      const panelQueCubre = EXAMENES_CUBIERTOS_POR_PANEL[item.codigo];
      if (panelQueCubre) {
        const panId = panelIdByCodigo.get(panelQueCubre);
        if (panId != null && selectedPanelesIds.has(panId)) {
          checked = true;
          // Cubierto por el panel: no se pide de nuevo como suelto.
          itemDisabled = true;
        }
      }
    }
    const onToggle = item.kind === 'panel' ? onTogglePanel : onToggleExamen;
    return (
      <PapelCheckbox
        item={item}
        maps={maps}
        examenesById={examenesById}
        checked={checked}
        onToggle={onToggle}
        disabled={itemDisabled}
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
          maxHeight: { xs: '36vh', sm: '40vh' },
          minHeight: 180,
          overflowY: 'auto',
          overscrollBehavior: 'contain',
        }}
      >
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

      <Box>
        <Typography variant="subtitle2" fontWeight={600} gutterBottom>
          Otros exámenes
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          Buscá en el catálogo análisis que no están en el formulario de papel.
        </Typography>
        <Autocomplete
          size="small"
          options={otrosOpciones}
          getOptionLabel={(o) => `${o.codigo} — ${o.nombre}`}
          inputValue={otrosInput}
          onInputChange={(_e, v) => setOtrosInput(v)}
          value={null}
          onChange={(_e, value) => {
            if (value) {
              onToggleExamen(value.id);
              setOtrosInput('');
            }
          }}
          disabled={disabled}
          renderInput={(params) => (
            <TextField {...params} label={agregarLabel} placeholder="Código o nombre" />
          )}
          noOptionsText={otrosInput.trim().length < 1 ? 'Escribí para buscar' : 'Sin coincidencias'}
        />
        {otrosSeleccionados.length > 0 && (
          <Stack direction="row" flexWrap="wrap" useFlexGap spacing={0.5} sx={{ mt: 1 }}>
            {otrosSeleccionados.map((ex) => (
              <Chip
                key={ex.id}
                size="small"
                label={`${ex.codigo}${ex.laboratorio_derivacion_codigo ? ` · ${ex.laboratorio_derivacion_codigo}` : ''}`}
                onDelete={disabled ? undefined : () => onToggleExamen(ex.id)}
              />
            ))}
          </Stack>
        )}
      </Box>

      {onObservacionesChange && (
        <TextField
          fullWidth
          multiline
          minRows={2}
          label="Observaciones"
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

export function useSolicitudAnalisisSelection(
  catalog?: {
    examenes: Array<{ id: number; codigo: string }>;
    paneles: Array<{ id: number; codigo: string }>;
  }
) {
  const [selectedPanelesIds, setSelectedPanelesIds] = React.useState<Set<number>>(
    () => new Set()
  );
  const [selectedExamenesIds, setSelectedExamenesIds] = React.useState<Set<number>>(
    () => new Set()
  );

  const examIdByCodigo = React.useMemo(() => {
    const m = new Map<string, number>();
    for (const e of catalog?.examenes || []) m.set(e.codigo, e.id);
    return m;
  }, [catalog?.examenes]);

  const panelIdByCodigo = React.useMemo(() => {
    const m = new Map<string, number>();
    for (const p of catalog?.paneles || []) m.set(p.codigo, p.id);
    return m;
  }, [catalog?.paneles]);

  const panelCodigoById = React.useMemo(() => {
    const m = new Map<number, string>();
    for (const p of catalog?.paneles || []) m.set(p.id, p.codigo);
    return m;
  }, [catalog?.paneles]);

  const examCodigoById = React.useMemo(() => {
    const m = new Map<number, string>();
    for (const e of catalog?.examenes || []) m.set(e.id, e.codigo);
    return m;
  }, [catalog?.examenes]);

  const addExamenesByCodigo = React.useCallback(
    (prev: Set<number>, codigos: readonly string[]) => {
      const next = new Set(prev);
      for (const codigo of codigos) {
        const id = examIdByCodigo.get(codigo);
        if (id != null) next.add(id);
      }
      return next;
    },
    [examIdByCodigo]
  );

  const togglePanel = React.useCallback(
    (id: number) => {
      const codigo = panelCodigoById.get(id);
      const selecting = !selectedPanelesIds.has(id);
      setSelectedPanelesIds((prev) => {
        const next = new Set(prev);
        if (selecting) {
          next.add(id);
          if (esPanelEab(codigo)) {
            for (const panCodigo of EAB_INCLUYE_CODIGOS.paneles) {
              const panId = panelIdByCodigo.get(panCodigo);
              if (panId != null) next.add(panId);
            }
          }
        } else {
          next.delete(id);
        }
        return next;
      });
      if (selecting && esPanelEab(codigo)) {
        setSelectedExamenesIds((prev) =>
          addExamenesByCodigo(prev, EAB_INCLUYE_CODIGOS.examenes)
        );
      }
    },
    [
      addExamenesByCodigo,
      panelCodigoById,
      panelIdByCodigo,
      selectedPanelesIds,
    ]
  );

  const toggleExamen = React.useCallback(
    (id: number) => {
      const codigo = examCodigoById.get(id);
      setSelectedExamenesIds((prev) => {
        const next = new Set(prev);
        const selecting = !next.has(id);
        if (esCodigoCartuchoCardiaco(codigo)) {
          const ids = CARTUCHO_CARDIACO_CODIGOS.map((c) => examIdByCodigo.get(c)).filter(
            (x): x is number => x != null
          );
          if (selecting) {
            for (const cartId of ids) next.add(cartId);
          } else {
            for (const cartId of ids) next.delete(cartId);
          }
          return next;
        }
        if (selecting) {
          next.add(id);
          if ((codigo || '').toUpperCase() === 'CA_ION') {
            return addExamenesByCodigo(next, CA_ION_INCLUYE_CODIGOS);
          }
        } else {
          next.delete(id);
        }
        return next;
      });
    },
    [addExamenesByCodigo, examCodigoById, examIdByCodigo]
  );

  const resetSelection = React.useCallback(() => {
    setSelectedPanelesIds(new Set());
    setSelectedExamenesIds(new Set());
  }, []);

  /** Quita paneles/exámenes por id sin toggles encadenados (evita estado stale). */
  const deselectMany = React.useCallback((panelIds: number[], examenIds: number[]) => {
    if (panelIds.length) {
      setSelectedPanelesIds((prev) => {
        const next = new Set(prev);
        panelIds.forEach((id) => next.delete(id));
        return next;
      });
    }
    if (examenIds.length) {
      setSelectedExamenesIds((prev) => {
        const next = new Set(prev);
        examenIds.forEach((id) => next.delete(id));
        return next;
      });
    }
  }, []);

  const getSelectionArrays = React.useCallback(() => {
    const panelesCodigos = new Set(
      Array.from(selectedPanelesIds)
        .map((id) => panelCodigoById.get(id))
        .filter((c): c is string => Boolean(c))
    );
    const examenes_ids = Array.from(selectedExamenesIds).filter((id) => {
      const codigo = examCodigoById.get(id);
      if (!codigo) return true;
      const panelQueCubre = EXAMENES_CUBIERTOS_POR_PANEL[codigo];
      if (panelQueCubre && panelesCodigos.has(panelQueCubre)) {
        // Ya va dentro del panel (p. ej. INR con coagulograma).
        return false;
      }
      return true;
    });
    return {
      paneles_ids: Array.from(selectedPanelesIds),
      examenes_ids,
    };
  }, [examCodigoById, panelCodigoById, selectedExamenesIds, selectedPanelesIds]);

  const hasSelection = selectedPanelesIds.size + selectedExamenesIds.size > 0;

  return {
    selectedPanelesIds,
    selectedExamenesIds,
    togglePanel,
    toggleExamen,
    resetSelection,
    deselectMany,
    getSelectionArrays,
    hasSelection,
  };
}
