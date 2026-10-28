/**
 * Pedido Lab. Clínico por bloques de «material de pedido».
 * Sangre/orina: grillas legacy. Resto: grilla desde API materiales-pedido.
 * La selección sigue siendo paneles/examenes del catálogo (mismas APIs).
 */
import React, { useEffect, useMemo, useState } from 'react';
import {
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
  createFilterOptions,
} from '@mui/material';
import { Add, DeleteOutline } from '@mui/icons-material';
import type {
  LimsPanelExamen,
  LimsTipoExamen,
  MaterialPedidoLims,
  TipoCultivoMicrobiologia,
  TipoMuestraMicrobiologia,
} from '../../types/lims';
import {
  esExamenExcluidoDeLabClinico,
  ORINA_SOLICITUD_PAPEL_CODIGOS,
  SOLICITUD_ANALISIS_PAPEL_ROWS,
  type PapelItemRef,
} from '../../modules/laboratorio/solicitudAnalisisPapelLayout';
import { EXAMENES_CUBIERTOS_POR_PANEL } from '../../modules/laboratorio/solicitudAnalisisSelectionRules';
import type { MicroPedidoItem } from './SolicitudMicrobiologiaForm';
import { sugerirMuestraPorCultivo } from '../../utils/limsMicroUx';
import {
  agregarCatalogOptionsForMaterial,
  chipsAgregadosCatalogForMaterial,
  examenPerteneceAMaterial,
  modalidadDeCodigoOrina,
  panelPerteneceAMaterial,
  type CatalogAddItem,
  type OrinaModalidad,
} from '../../utils/limsCatalogoPedidoMaterial';

const ORINA_GRILLA_CODIGOS: readonly string[] = ORINA_SOLICITUD_PAPEL_CODIGOS;

const ORINA_EN_PAPEL = new Set<string>(ORINA_GRILLA_CODIGOS);

/** Códigos que se muestran al abrir el selector sin tipear (Sangre es el default). */
const MATERIALES_FRECUENTES_FALLBACK = [
  'ORINA',
  'MATERIA_FECAL',
  'ESPUTO',
  'HISOP_NAS',
  'HISOP_RECT',
  'HISOP_AMB',
] as const;

/** Fallback si la API aún no respondió. */
const MATERIALES_FALLBACK: MaterialPedidoLims[] = [
  {
    codigo: 'SANGRE',
    nombre: 'Sangre',
    ui_preset: 'sangre',
    tipo_muestra_codigos: [
      'SUERO',
      'SANGRE_EDTA',
      'PLASMA_CITRATO',
      'PLASMA_EDTA',
      'SANGRE_ERITRO',
      'SANGRE_CITRATO_VSG',
      'SANGRE_HEPARINA',
      'SANGRE_HEPARINA_ART',
      'SANGRE_HEPARINA_VEN',
      'PLASMA_HEPARINA',
    ],
    grilla_codigos: [],
    cultivo_micro_codigo: 'HEMOCULTIVO',
    muestra_micro_codigo: 'SANGRE',
  },
  {
    codigo: 'ORINA',
    nombre: 'Orina',
    ui_preset: 'orina',
    tipo_muestra_codigos: ['ORINA', 'ORINA_24_H'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'UROCULTIVO',
    muestra_micro_codigo: 'ORINA',
    frecuente: true,
  },
  {
    codigo: 'MATERIA_FECAL',
    nombre: 'Materia fecal',
    ui_preset: null,
    tipo_muestra_codigos: ['MATERIA_FECAL'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'COPROCULTIVO',
    muestra_micro_codigo: 'MATERIA_FECAL',
    frecuente: true,
  },
  {
    codigo: 'ESPUTO',
    nombre: 'Esputo',
    tipo_muestra_codigos: ['ESPUTO'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'ESPUTO',
    muestra_micro_codigo: 'ESPUTO',
    frecuente: true,
  },
  {
    codigo: 'HISOP_NAS',
    nombre: 'Hisopado nasal',
    tipo_muestra_codigos: ['HISOP_NAS'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'NASOFARINGEO',
    muestra_micro_codigo: 'EXUDADO_NASAL',
    frecuente: true,
  },
  {
    codigo: 'HISOP_RECT',
    nombre: 'Hisopado rectal',
    tipo_muestra_codigos: ['HISOP_RECT'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'HISOPADO_ANAL',
    muestra_micro_codigo: 'HISOPADO_VIGILANCIA',
    frecuente: true,
  },
  {
    codigo: 'HISOP_AMB',
    nombre: 'Hisopado ambiental',
    tipo_muestra_codigos: ['HISOP_AMB'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'AMBIENTAL',
    muestra_micro_codigo: 'HISOPADO_VIGILANCIA',
    frecuente: true,
  },
];

const filterMaterialesBase = createFilterOptions<MaterialPedidoLims>({
  stringify: (m) => `${m.codigo} ${m.nombre}`,
});

type CatalogItem = {
  kind: 'panel' | 'examen';
  id: number;
  codigo: string;
  nombre: string;
};

type CatalogGridRow = { left: CatalogItem | null; right: CatalogItem | null };

interface MaterialBlock {
  id: string;
  materialKey: string;
}

export interface SolicitudAnalisisMaterialesFormProps {
  examenes: LimsTipoExamen[];
  paneles: LimsPanelExamen[];
  /** Catálogo de materiales (API). Si vacío, usa fallback sangre/orina/fecal. */
  materialesPedido?: MaterialPedidoLims[];
  selectedPanelesIds: Set<number>;
  selectedExamenesIds: Set<number>;
  onTogglePanel: (id: number) => void;
  onToggleExamen: (id: number) => void;
  onDeselectMany?: (panelIds: number[], examenIds: number[]) => void;
  /** Códigos de materiales actualmente elegidos en bloques (para filtrar micro). */
  onSelectedMaterialsChange?: (codigos: string[]) => void;
  observaciones?: string;
  onObservacionesChange?: (value: string) => void;
  disabled?: boolean;
  /** Si false, no se muestra la sección Microbiología por material (p. ej. agregar a orden clínica). */
  showMicroPorMaterial?: boolean;
  cultivos?: TipoCultivoMicrobiologia[];
  tiposMuestraMicro?: TipoMuestraMicrobiologia[];
  microItems?: MicroPedidoItem[];
  onChangeMicroItems?: (items: MicroPedidoItem[]) => void;
  observacionesMicro?: string;
  onObservacionesMicroChange?: (value: string) => void;
}

function cultivoDeMaterial(
  mat: MaterialPedidoLims,
  cultivos: TipoCultivoMicrobiologia[]
): TipoCultivoMicrobiologia | null {
  const code = (mat.cultivo_micro_codigo || '').toUpperCase();
  if (!code) return null;
  return (
    cultivos.find((c) => c.activo !== false && (c.codigo || '').toUpperCase() === code) ||
    null
  );
}

function resolverMuestraMicro(
  cultivo: TipoCultivoMicrobiologia,
  tiposMuestra: TipoMuestraMicrobiologia[],
  preferidaCodigo?: string | null
): TipoMuestraMicrobiologia | null {
  if (preferidaCodigo) {
    const exact = tiposMuestra.find(
      (t) => (t.codigo || '').toUpperCase() === preferidaCodigo.toUpperCase()
    );
    if (exact) return exact;
  }
  return sugerirMuestraPorCultivo(cultivo.codigo, tiposMuestra) || tiposMuestra[0] || null;
}

function newBlockId(): string {
  return `mat-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function resolvePapelCatalogItem(
  ref: PapelItemRef | null | undefined,
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[],
  seen: Set<string>
): CatalogItem | null {
  if (!ref || ORINA_EN_PAPEL.has(ref.codigo) || seen.has(ref.codigo)) return null;
  if (ref.kind === 'panel') {
    const p = paneles.find((x) => x.codigo === ref.codigo && x.activo !== false);
    if (!p) return null;
    seen.add(p.codigo);
    return { kind: 'panel', id: p.id, codigo: p.codigo, nombre: p.nombre };
  }
  const e = examenes.find((x) => x.codigo === ref.codigo && x.activo !== false);
  if (!e || esExamenExcluidoDeLabClinico(e)) return null;
  seen.add(e.codigo);
  return { kind: 'examen', id: e.id, codigo: e.codigo, nombre: e.nombre };
}

/** Filas con columnas izquierda/derecha reales (no relleno flat i%2). */
function buildSangreRows(
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[]
): CatalogGridRow[] {
  const seen = new Set<string>();
  const rows: CatalogGridRow[] = [];
  for (const row of SOLICITUD_ANALISIS_PAPEL_ROWS) {
    const left = resolvePapelCatalogItem(row.left, paneles, examenes, seen);
    const right = resolvePapelCatalogItem(row.right, paneles, examenes, seen);
    if (left || right) rows.push({ left, right });
  }
  return rows;
}

function buildSangreGrid(
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[]
): CatalogItem[] {
  const items: CatalogItem[] = [];
  for (const row of buildSangreRows(paneles, examenes)) {
    if (row.left) items.push(row.left);
    if (row.right) items.push(row.right);
  }
  return items;
}

function buildOrinaGrid(
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[]
): CatalogItem[] {
  const items: CatalogItem[] = [];
  ORINA_GRILLA_CODIGOS.forEach((codigo) => {
    const p = paneles.find((x) => x.codigo === codigo && x.activo !== false);
    if (p) {
      items.push({ kind: 'panel', id: p.id, codigo: p.codigo, nombre: p.nombre });
      return;
    }
    const e = examenes.find((x) => x.codigo === codigo && x.activo !== false);
    if (e) {
      items.push({ kind: 'examen', id: e.id, codigo: e.codigo, nombre: e.nombre });
    }
  });
  return items;
}

function buildGrillaDesdeCodigos(
  codigos: string[],
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[]
): CatalogItem[] {
  const items: CatalogItem[] = [];
  codigos.forEach((codigo) => {
    const p = paneles.find((x) => x.codigo === codigo && x.activo !== false);
    if (p) {
      items.push({ kind: 'panel', id: p.id, codigo: p.codigo, nombre: p.nombre });
      return;
    }
    const e = examenes.find((x) => x.codigo === codigo && x.activo !== false);
    if (e && !esExamenExcluidoDeLabClinico(e)) {
      items.push({ kind: 'examen', id: e.id, codigo: e.codigo, nombre: e.nombre });
    }
  });
  return items;
}

function gridForMaterial(
  mat: MaterialPedidoLims,
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[]
): CatalogItem[] {
  if (mat.ui_preset === 'sangre') return buildSangreGrid(paneles, examenes);
  if (mat.ui_preset === 'orina') return buildOrinaGrid(paneles, examenes);
  if (mat.grilla_codigos?.length) {
    return buildGrillaDesdeCodigos(mat.grilla_codigos, paneles, examenes);
  }
  // Fallback: todos los exámenes de esas muestras (sin cultivos micro legados).
  return examenes
    .filter(
      (e) =>
        e.activo !== false &&
        !esExamenExcluidoDeLabClinico(e) &&
        examenPerteneceAMaterial(e, mat)
    )
    .map((e) => ({
      kind: 'examen' as const,
      id: e.id,
      codigo: e.codigo,
      nombre: e.nombre,
    }));
}

export function idsDeMaterial(
  mat: MaterialPedidoLims,
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[]
): { panelIds: number[]; examenIds: number[] } {
  const grid = gridForMaterial(mat, paneles, examenes);
  const panelIds = grid.filter((g) => g.kind === 'panel').map((g) => g.id);
  const examenIdsFromGrid = grid.filter((g) => g.kind === 'examen').map((g) => g.id);
  const examenIdsExtra = examenes
    .filter((e) => e.activo !== false && examenPerteneceAMaterial(e, mat))
    .map((e) => e.id);
  // Paneles de grilla_codigos + paneles del catálogo cuyos componentes son de este material
  // (p. ej. agregados vía «Agregar examen clínico»).
  const panelIdsExtra = paneles
    .filter(
      (p) =>
        p.activo !== false &&
        ((mat.grilla_codigos || []).includes(p.codigo) ||
          panelPerteneceAMaterial(p, mat, examenes))
    )
    .map((p) => p.id);
  return {
    panelIds: Array.from(new Set([...panelIds, ...panelIdsExtra])),
    examenIds: Array.from(new Set([...examenIdsFromGrid, ...examenIdsExtra])),
  };
}

export default function SolicitudAnalisisMaterialesForm({
  examenes,
  paneles,
  materialesPedido,
  selectedPanelesIds,
  selectedExamenesIds,
  onTogglePanel,
  onToggleExamen,
  onDeselectMany,
  onSelectedMaterialsChange,
  observaciones = '',
  onObservacionesChange,
  disabled = false,
  showMicroPorMaterial = false,
  cultivos = [],
  tiposMuestraMicro = [],
  microItems = [],
  onChangeMicroItems,
  observacionesMicro = '',
  onObservacionesMicroChange,
}: SolicitudAnalisisMaterialesFormProps) {
  const materiales = useMemo(
    () =>
      materialesPedido && materialesPedido.length > 0
        ? materialesPedido
        : MATERIALES_FALLBACK,
    [materialesPedido]
  );

  const [blocks, setBlocks] = useState<MaterialBlock[]>(() => [
    { id: newBlockId(), materialKey: 'SANGRE' },
  ]);
  const [agregarInput, setAgregarInput] = useState<Record<string, string>>({});
  const [materialInput, setMaterialInput] = useState<Record<string, string>>({});

  const panelIdByCodigo = useMemo(() => {
    const m = new Map<string, number>();
    paneles.forEach((p) => {
      if (p.activo !== false) m.set(p.codigo, p.id);
    });
    return m;
  }, [paneles]);

  const materialesUsados = useMemo(() => {
    const s = new Set<string>();
    blocks.forEach((b) => {
      if (b.materialKey) s.add(b.materialKey);
    });
    return s;
  }, [blocks]);

  useEffect(() => {
    onSelectedMaterialsChange?.(Array.from(materialesUsados));
  }, [materialesUsados, onSelectedMaterialsChange]);

  const orinaModalidad = useMemo((): OrinaModalidad => {
    let azar = false;
    let h24 = false;
    paneles.forEach((p) => {
      if (!selectedPanelesIds.has(p.id)) return;
      const mod = modalidadDeCodigoOrina(p.codigo);
      if (mod === 'azar') azar = true;
      if (mod === '24h') h24 = true;
    });
    examenes.forEach((e) => {
      if (!selectedExamenesIds.has(e.id)) return;
      const mod = modalidadDeCodigoOrina(e.codigo);
      if (mod === 'azar') azar = true;
      if (mod === '24h') h24 = true;
      const m = (e.tipo_muestra_codigo || '').toUpperCase();
      if (m === 'ORINA_24_H') h24 = true;
      else if (m === 'ORINA' && mod !== '24h') azar = true;
    });
    if (azar && !h24) return 'azar';
    if (h24 && !azar) return '24h';
    return null;
  }, [paneles, examenes, selectedPanelesIds, selectedExamenesIds]);

  const findMat = (key: string) => materiales.find((m) => m.codigo === key);

  const clearMaterialSelection = (key: string) => {
    const mat = findMat(key);
    if (!mat) return;
    const { panelIds, examenIds } = idsDeMaterial(mat, paneles, examenes);
    const panelsToClear = panelIds.filter((id) => selectedPanelesIds.has(id));
    const examsToClear = examenIds.filter((id) => selectedExamenesIds.has(id));
    if (onDeselectMany) {
      onDeselectMany(panelsToClear, examsToClear);
      return;
    }
    panelsToClear.forEach((id) => onTogglePanel(id));
    examsToClear.forEach((id) => onToggleExamen(id));
  };

  const setBlockMaterial = (blockId: string, key: string) => {
    const prev = blocks.find((b) => b.id === blockId);
    if (prev?.materialKey && prev.materialKey !== key) {
      clearMaterialSelection(prev.materialKey);
    }
    setBlocks((list) =>
      list.map((b) => (b.id === blockId ? { ...b, materialKey: key } : b))
    );
  };

  const removeBlock = (blockId: string) => {
    const prev = blocks.find((b) => b.id === blockId);
    if (prev?.materialKey) clearMaterialSelection(prev.materialKey);
    setBlocks((list) => {
      if (list.length <= 1) {
        return [{ id: newBlockId(), materialKey: 'SANGRE' }];
      }
      return list.filter((b) => b.id !== blockId);
    });
  };

  const addBlock = () => {
    const id = newBlockId();
    setBlocks((list) => [...list, { id, materialKey: '' }]);
    setMaterialInput((prev) => ({ ...prev, [id]: '' }));
  };

  const agregarOpciones = (materialKey: string): CatalogAddItem[] => {
    const mat = findMat(materialKey);
    if (!mat) return [];
    const gridCodigos = new Set(
      gridForMaterial(mat, paneles, examenes).map((g) => g.codigo)
    );
    return agregarCatalogOptionsForMaterial({
      mat,
      examenes,
      paneles,
      gridCodigos,
      selectedExamenesIds,
      selectedPanelesIds,
      orinaModalidad,
    });
  };

  const chipsAgregados = (materialKey: string): CatalogAddItem[] => {
    const mat = findMat(materialKey);
    if (!mat) return [];
    const gridCodigos = new Set(
      gridForMaterial(mat, paneles, examenes).map((g) => g.codigo)
    );
    return chipsAgregadosCatalogForMaterial({
      mat,
      examenes,
      paneles,
      gridCodigos,
      selectedExamenesIds,
      selectedPanelesIds,
    });
  };

  const totalClinico = selectedPanelesIds.size + selectedExamenesIds.size;
  const totalMicro = microItems.length;

  const esFrecuente = (m: MaterialPedidoLims) =>
    Boolean(m.frecuente) ||
    (MATERIALES_FRECUENTES_FALLBACK as readonly string[]).includes(m.codigo);

  const selectedCultivoIds = useMemo(
    () => new Set(microItems.map((i) => i.tipo_cultivo_id)),
    [microItems]
  );

  const toggleCultivoMaterial = (mat: MaterialPedidoLims) => {
    if (!onChangeMicroItems || disabled) return;
    const cultivo = cultivoDeMaterial(mat, cultivos);
    if (!cultivo) return;
    if (selectedCultivoIds.has(cultivo.id)) {
      onChangeMicroItems(microItems.filter((i) => i.tipo_cultivo_id !== cultivo.id));
      return;
    }
    const muestra = resolverMuestraMicro(
      cultivo,
      tiposMuestraMicro,
      mat.muestra_micro_codigo
    );
    if (!muestra) return;
    onChangeMicroItems([
      ...microItems,
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

  const sectionHeaderSx = {
    px: 1.25,
    py: 0.75,
    mb: 1.25,
    borderRadius: 1,
    bgcolor: 'action.hover',
  } as const;

  return (
    <Stack spacing={2.5}>
      <Typography variant="body2" color="text.secondary">
        Por cada material pedís Lab. Clínico y, si aplica, Microbiología en la misma tarjeta.
        Por defecto Sangre; al abrir el selector aparecen los frecuentes y el resto se busca tipando.
      </Typography>

      {blocks.map((block, index) => {
        const matDef = findMat(block.materialKey);
        const grid = matDef ? gridForMaterial(matDef, paneles, examenes) : [];
        const sangreRows =
          matDef?.ui_preset === 'sangre' ? buildSangreRows(paneles, examenes) : null;
        const opcionesMaterial = materiales.filter(
          (m) => m.codigo === block.materialKey || !materialesUsados.has(m.codigo)
        );
        const agregarOpts = block.materialKey ? agregarOpciones(block.materialKey) : [];
        const chips = block.materialKey ? chipsAgregados(block.materialKey) : [];
        const soloMicro = Boolean(
          matDef &&
            !matDef.ui_preset &&
            (matDef.grilla_codigos?.length || 0) === 0 &&
            grid.length === 0 &&
            matDef.cultivo_micro_codigo
        );
        const cultivoMat = matDef ? cultivoDeMaterial(matDef, cultivos) : null;
        const cultivoChecked = Boolean(
          cultivoMat && selectedCultivoIds.has(cultivoMat.id)
        );

        return (
          <Paper key={block.id} variant="outlined" sx={{ p: { xs: 2, sm: 2.5 } }}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              sx={{ mb: 2 }}
            >
              <Typography variant="subtitle1" fontWeight={600}>
                Material {index + 1}
                {matDef ? ` — ${matDef.nombre}` : ''}
              </Typography>
              <IconButton
                aria-label="Quitar material"
                size="small"
                onClick={() => removeBlock(block.id)}
                disabled={disabled || (blocks.length <= 1 && block.materialKey === 'SANGRE')}
              >
                <DeleteOutline fontSize="small" />
              </IconButton>
            </Stack>

            <Autocomplete
              size="small"
              sx={{ mb: 2.5, maxWidth: 560 }}
              options={opcionesMaterial}
              value={matDef || null}
              disabled={disabled}
              inputValue={materialInput[block.id] ?? matDef?.nombre ?? ''}
              onInputChange={(_e, v, reason) => {
                if (reason === 'reset' && matDef) {
                  setMaterialInput((prev) => ({ ...prev, [block.id]: matDef.nombre }));
                  return;
                }
                setMaterialInput((prev) => ({ ...prev, [block.id]: v }));
              }}
              onChange={(_e, value) => {
                setBlockMaterial(block.id, value?.codigo || '');
                setMaterialInput((prev) => ({
                  ...prev,
                  [block.id]: value?.nombre || '',
                }));
              }}
              getOptionLabel={(o) => o.nombre}
              isOptionEqualToValue={(a, b) => a.codigo === b.codigo}
              filterOptions={(opts, state) => {
                const q = (state.inputValue || '').trim();
                if (!q) {
                  // Al abrir sin texto: solo frecuentes (no Sangre: ya es el default).
                  return opts.filter(
                    (m) => esFrecuente(m) && m.codigo !== 'SANGRE'
                  );
                }
                return filterMaterialesBase(opts, state);
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Material de pedido"
                  placeholder="Orina, esputo… o tipiá para buscar"
                />
              )}
              noOptionsText={
                (materialInput[block.id] || '').trim()
                  ? 'Sin coincidencias'
                  : 'Tipiá para buscar más materiales'
              }
            />

            {!block.materialKey && (
              <Typography variant="body2" color="text.secondary">
                Elegí el material para ver Lab. Clínico y Microbiología.
              </Typography>
            )}

            {block.materialKey && (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" fontWeight={700} sx={sectionHeaderSx}>
                    Lab. Clínico — {matDef?.nombre || 'material'}
                  </Typography>
                  {soloMicro ? (
                    <Typography variant="body2" color="text.secondary">
                      Este material (p. ej. hisopo) no genera tubos de Lab. Clínico. Marcá el
                      cultivo en <strong>Microbiología</strong> (abajo) para pedirlo; la etiqueta
                      es de microbiología, no de tubo.
                    </Typography>
                  ) : null}
                  {(sangreRows ? sangreRows.length > 0 : grid.length > 0) && (
                    <>
                      {block.materialKey === 'ORINA' && orinaModalidad && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                          sx={{ mb: 1.25 }}
                        >
                          {orinaModalidad === '24h'
                            ? 'Seleccionaste orina 24 hs: las de al azar quedan bloqueadas. Orina completa sigue disponible.'
                            : 'Seleccionaste orina al azar: las de 24 hs quedan bloqueadas. Orina completa sigue disponible.'}
                        </Typography>
                      )}
                      <Box
                        sx={{
                          display: 'grid',
                          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
                          gap: 0,
                          border: 1,
                          borderColor: 'divider',
                          borderRadius: 1,
                          mb: 2,
                          maxHeight: { xs: '42vh', sm: '52vh' },
                          minHeight: { sm: 280 },
                          overflowY: 'auto',
                          overscrollBehavior: 'contain',
                        }}
                      >
                        {sangreRows
                          ? sangreRows.map((row, index) => {
                              const renderCell = (
                                item: CatalogItem | null,
                                side: 'left' | 'right'
                              ) => {
                                if (!item) {
                                  return (
                                    <Box
                                      key={`empty-${side}-${index}`}
                                      sx={{
                                        px: 1.25,
                                        py: 0.85,
                                        minHeight: 44,
                                        borderBottom:
                                          index < sangreRows.length - 1 ? 1 : 0,
                                        borderColor: 'divider',
                                        borderLeft: {
                                          sm: side === 'right' ? 1 : 0,
                                        },
                                      }}
                                    />
                                  );
                                }
                                let checked =
                                  item.kind === 'panel'
                                    ? selectedPanelesIds.has(item.id)
                                    : selectedExamenesIds.has(item.id);
                                let itemDisabled = disabled;
                                if (item.kind === 'examen') {
                                  const panelQueCubre =
                                    EXAMENES_CUBIERTOS_POR_PANEL[item.codigo];
                                  if (panelQueCubre) {
                                    const panId = panelIdByCodigo.get(panelQueCubre);
                                    if (panId != null && selectedPanelesIds.has(panId)) {
                                      checked = true;
                                      itemDisabled = true;
                                    }
                                  }
                                }
                                const onToggle =
                                  item.kind === 'panel' ? onTogglePanel : onToggleExamen;
                                return (
                                  <Box
                                    key={`${item.kind}-${item.id}`}
                                    sx={{
                                      px: 1.25,
                                      py: 0.85,
                                      borderBottom:
                                        index < sangreRows.length - 1 ? 1 : 0,
                                      borderColor: 'divider',
                                      borderLeft: {
                                        sm: side === 'right' ? 1 : 0,
                                      },
                                    }}
                                  >
                                    <FormControlLabel
                                      sx={{
                                        alignItems: 'flex-start',
                                        m: 0,
                                        width: '100%',
                                      }}
                                      control={
                                        <Checkbox
                                          size="small"
                                          checked={checked}
                                          disabled={itemDisabled}
                                          onChange={() => onToggle(item.id)}
                                          sx={{ pt: 0.35 }}
                                        />
                                      }
                                      label={
                                        <Typography
                                          variant="body2"
                                          sx={{ lineHeight: 1.4 }}
                                        >
                                          {item.nombre}{' '}
                                          <Typography
                                            component="span"
                                            variant="caption"
                                            color="text.secondary"
                                          >
                                            ({item.codigo})
                                          </Typography>
                                        </Typography>
                                      }
                                    />
                                  </Box>
                                );
                              };
                              return (
                                <React.Fragment key={`sangre-row-${index}`}>
                                  {renderCell(row.left, 'left')}
                                  {renderCell(row.right, 'right')}
                                </React.Fragment>
                              );
                            })
                          : grid.map((item, i) => {
                              let checked =
                                item.kind === 'panel'
                                  ? selectedPanelesIds.has(item.id)
                                  : selectedExamenesIds.has(item.id);
                              let itemDisabled = disabled;
                              if (item.kind === 'examen') {
                                const panelQueCubre =
                                  EXAMENES_CUBIERTOS_POR_PANEL[item.codigo];
                                if (panelQueCubre) {
                                  const panId = panelIdByCodigo.get(panelQueCubre);
                                  if (panId != null && selectedPanelesIds.has(panId)) {
                                    checked = true;
                                    itemDisabled = true;
                                  }
                                }
                              }
                              if (block.materialKey === 'ORINA' && !checked) {
                                const mod = modalidadDeCodigoOrina(item.codigo);
                                if (orinaModalidad === '24h' && mod === 'azar')
                                  itemDisabled = true;
                                if (orinaModalidad === 'azar' && mod === '24h')
                                  itemDisabled = true;
                              }
                              const onToggle =
                                item.kind === 'panel' ? onTogglePanel : onToggleExamen;
                              return (
                                <Box
                                  key={`${item.kind}-${item.id}`}
                                  sx={{
                                    px: 1.25,
                                    py: 0.85,
                                    borderBottom: 1,
                                    borderColor: 'divider',
                                    borderLeft: { sm: i % 2 === 1 ? 1 : 0 },
                                  }}
                                >
                                  <FormControlLabel
                                    sx={{
                                      alignItems: 'flex-start',
                                      m: 0,
                                      width: '100%',
                                    }}
                                    control={
                                      <Checkbox
                                        size="small"
                                        checked={checked}
                                        disabled={itemDisabled}
                                        onChange={() => onToggle(item.id)}
                                        sx={{ pt: 0.35 }}
                                      />
                                    }
                                    label={
                                      <Typography
                                        variant="body2"
                                        sx={{ lineHeight: 1.4 }}
                                      >
                                        {item.nombre}{' '}
                                        <Typography
                                          component="span"
                                          variant="caption"
                                          color="text.secondary"
                                        >
                                          ({item.codigo})
                                        </Typography>
                                      </Typography>
                                    }
                                  />
                                </Box>
                              );
                            })}
                      </Box>
                    </>
                  )}
                  {!soloMicro && (
                    <Box>
                      <Typography variant="body2" fontWeight={600} gutterBottom>
                        Agregar examen clínico
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                        sx={{ mb: 1 }}
                      >
                        {block.materialKey === 'ORINA'
                          ? 'Exámenes o paneles de orina que no están en la grilla frecuente.'
                          : `Buscá en el catálogo exámenes o paneles de ${matDef?.nombre || 'este material'}.`}
                      </Typography>
                      <Autocomplete
                        size="small"
                        options={agregarOpts}
                        getOptionLabel={(o) =>
                          o.kind === 'panel'
                            ? `Panel · ${o.codigo} — ${o.nombre}`
                            : `${o.codigo} — ${o.nombre}`
                        }
                        isOptionEqualToValue={(a, b) =>
                          a.kind === b.kind && a.id === b.id
                        }
                        inputValue={agregarInput[block.id] || ''}
                        onInputChange={(_e, v) =>
                          setAgregarInput((prev) => ({ ...prev, [block.id]: v }))
                        }
                        value={null}
                        disabled={disabled}
                        onChange={(_e, value) => {
                          if (!value) return;
                          if (value.kind === 'panel') onTogglePanel(value.id);
                          else onToggleExamen(value.id);
                          setAgregarInput((prev) => ({ ...prev, [block.id]: '' }));
                        }}
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            label="Agregar examen clínico"
                            placeholder="Código o nombre"
                          />
                        )}
                        noOptionsText={
                          (agregarInput[block.id] || '').trim().length < 1
                            ? 'Escribí para buscar'
                            : 'Sin coincidencias'
                        }
                      />
                      {chips.length > 0 && (
                        <Stack
                          direction="row"
                          flexWrap="wrap"
                          useFlexGap
                          spacing={0.5}
                          sx={{ mt: 1 }}
                        >
                          {chips.map((item) => (
                            <Chip
                              key={`${item.kind}-${item.id}`}
                              size="small"
                              label={
                                item.kind === 'panel' ? `Panel · ${item.codigo}` : item.codigo
                              }
                              onDelete={
                                disabled
                                  ? undefined
                                  : () =>
                                      item.kind === 'panel'
                                        ? onTogglePanel(item.id)
                                        : onToggleExamen(item.id)
                              }
                            />
                          ))}
                        </Stack>
                      )}
                    </Box>
                  )}
                </Box>

                {showMicroPorMaterial && (
                  <>
                    <Divider />
                    <Box>
                      <Typography variant="subtitle2" fontWeight={700} sx={sectionHeaderSx}>
                        Microbiología — {matDef?.nombre || 'material'}
                      </Typography>
                      {cultivoMat ? (
                        <>
                          {soloMicro && !cultivoChecked ? (
                            <Typography
                              variant="body2"
                              color="warning.main"
                              sx={{ mb: 1 }}
                            >
                              Marcá el cultivo para agregar el hisopo/pedido de microbiología.
                              No se selecciona solo.
                            </Typography>
                          ) : null}
                          <FormControlLabel
                            sx={{ alignItems: 'flex-start', m: 0 }}
                            control={
                              <Checkbox
                                size="small"
                                checked={cultivoChecked}
                                disabled={
                                  disabled ||
                                  !onChangeMicroItems ||
                                  tiposMuestraMicro.length === 0
                                }
                                onChange={() => toggleCultivoMaterial(matDef!)}
                                sx={{ pt: 0.25 }}
                              />
                            }
                            label={
                              <Box>
                                <Typography variant="body2" sx={{ lineHeight: 1.35 }}>
                                  {cultivoMat.nombre}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Cultivo de este material
                                  {matDef?.muestra_micro_codigo
                                    ? ` · muestra ${matDef.muestra_micro_codigo}`
                                    : ''}
                                </Typography>
                              </Box>
                            }
                          />
                          {tiposMuestraMicro.length === 0 && (
                            <Typography variant="caption" color="warning.main" display="block" sx={{ mt: 0.5 }}>
                              No hay tipos de muestra de microbiología cargados.
                            </Typography>
                          )}
                        </>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Este material no tiene cultivo de microbiología asociado.
                        </Typography>
                      )}
                    </Box>
                  </>
                )}
              </Stack>
            )}
          </Paper>
        );
      })}

      <Button
        startIcon={<Add />}
        variant="outlined"
        onClick={addBlock}
        disabled={disabled || materialesUsados.size >= materiales.length}
      >
        Agregar material
      </Button>

      {onObservacionesChange && (
        <TextField
          fullWidth
          multiline
          minRows={2}
          label="Observaciones (Lab. Clínico)"
          placeholder="Indicaciones adicionales, diagnóstico, etc."
          value={observaciones}
          onChange={(ev) => onObservacionesChange(ev.target.value)}
          disabled={disabled}
        />
      )}

      {showMicroPorMaterial && onObservacionesMicroChange && (
        <TextField
          fullWidth
          multiline
          minRows={2}
          label="Observaciones (Microbiología)"
          value={observacionesMicro}
          onChange={(ev) => onObservacionesMicroChange(ev.target.value)}
          disabled={disabled}
        />
      )}

      <Typography variant="caption" color="text.secondary">
        {totalClinico === 0 && totalMicro === 0
          ? 'Seleccioná al menos un análisis clínico o un cultivo de microbiología.'
          : [
              totalClinico > 0
                ? `${totalClinico} clínico${totalClinico === 1 ? '' : 's'}`
                : null,
              totalMicro > 0
                ? `${totalMicro} cultivo${totalMicro === 1 ? '' : 's'}`
                : null,
            ]
              .filter(Boolean)
              .join(' · ') + ' seleccionado(s).'}
      </Typography>
    </Stack>
  );
}
