import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  ThemeProvider,
  Typography,
} from '@mui/material';
import { Add, Delete, OpenInNew } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { formatDrfError } from '../../../services/limsApi';
import { getConsultaDetalle } from '../../../services/apiService';
import { listTiposEstudioComplementario } from '../../../services/estudiosComplementariosApi';
import { parseEstudiosApiError } from '../../estudios/apiErrors';
import { MODALIDAD_OPTIONS } from '../../estudios/constants';
import type { ConsultaDetalle } from '../../../types';
import type { TipoEstudioComplementario } from '../../../types/estudios';
import NuevaOrdenLimsDialog from '../../../components/lims/NuevaOrdenLimsDialog';
import {
  loadConsultaPedidosDraft,
  loadGuardiaPendingDraft,
  newDraftId,
  saveConsultaPedidosDraft,
  saveGuardiaPendingDraft,
  type ConsultaPedidosDraft,
} from '../consultaPedidosDraft';
import {
  clinicalDrawerAutocompleteSlotProps,
  clinicalDrawerDialogProps,
  clinicalDrawerDialogContentSx,
  useClinicalDrawerDialogTheme,
} from '../../../utils/layerZIndex';

interface ConsultaPedidosPanelProps {
  /** Requerido salvo cuando ``usePendingDraft`` (formulario guardia antes de crear HC). */
  consultaHcId?: number;
  canEdit: boolean;
  /** `compact`: botones inline en el formulario clínico; `full`: pestaña Pedidos y resultados */
  variant?: 'full' | 'compact';
  /** Borrador local para guardia walk-in (sin consulta HC aún). */
  usePendingDraft?: boolean;
}

function buildEstudioCatalogOptions(catalog: TipoEstudioComplementario[]): TipoEstudioComplementario[] {
  if (catalog.length > 0) {
    return catalog.filter((t) => t.activo !== false);
  }
  return MODALIDAD_OPTIONS.map((m, index) => ({
    id: -(index + 1),
    nombre: m.label,
    modalidad: m.value,
    activo: true,
  }));
}

function filterCatalogOptions<T extends { nombre: string; codigo?: string | null }>(
  options: T[],
  inputValue: string
): T[] {
  const q = inputValue.trim().toLowerCase();
  if (!q) return options;
  return options.filter((o) => {
    const nombre = o.nombre.toLowerCase();
    const codigo = o.codigo ? o.codigo.toLowerCase() : '';
    return nombre.includes(q) || codigo.includes(q);
  });
}

function formatEstudioTipoLabel(t: TipoEstudioComplementario): string {
  const codigo = t.codigo ? `${t.codigo} — ` : '';
  const modLabel = MODALIDAD_OPTIONS.find((m) => m.value === t.modalidad)?.label;
  return modLabel ? `${codigo}${t.nombre} (${modLabel})` : `${codigo}${t.nombre}`;
}

const ConsultaPedidosPanel: React.FC<ConsultaPedidosPanelProps> = ({
  consultaHcId,
  canEdit,
  variant = 'full',
  usePendingDraft = false,
}) => {
  const navigate = useNavigate();
  const dialogTheme = useClinicalDrawerDialogTheme();
  const [detalle, setDetalle] = useState<ConsultaDetalle | null>(null);
  const [loading, setLoading] = useState(!canEdit && !usePendingDraft);
  const [error, setError] = useState('');

  const loadDraftFromStorage = useCallback((): ConsultaPedidosDraft => {
    if (usePendingDraft) {
      return loadGuardiaPendingDraft();
    }
    if (!consultaHcId) {
      return { solicitudesLab: [], estudios: [] };
    }
    return loadConsultaPedidosDraft(consultaHcId);
  }, [consultaHcId, usePendingDraft]);

  const persistDraftToStorage = useCallback(
    (draft: ConsultaPedidosDraft) => {
      if (usePendingDraft) {
        saveGuardiaPendingDraft(draft);
        return;
      }
      if (consultaHcId) {
        saveConsultaPedidosDraft(consultaHcId, draft);
      }
    },
    [consultaHcId, usePendingDraft]
  );

  const [labOpen, setLabOpen] = useState(false);
  const [estudioOpen, setEstudioOpen] = useState(false);
  const [actionError, setActionError] = useState('');

  const [tiposEstudio, setTiposEstudio] = useState<TipoEstudioComplementario[]>([]);
  const [selectedTipoEstudio, setSelectedTipoEstudio] = useState<TipoEstudioComplementario | null>(null);
  const [estudioCatalogLoading, setEstudioCatalogLoading] = useState(false);
  const [estudioDesc, setEstudioDesc] = useState('');
  const [draft, setDraft] = useState<ConsultaPedidosDraft>(() => loadDraftFromStorage());

  const persistDraft = useCallback(
    (updater: (prev: ConsultaPedidosDraft) => ConsultaPedidosDraft) => {
      setDraft((prev) => {
        const next = updater(prev);
        persistDraftToStorage(next);
        return next;
      });
    },
    [persistDraftToStorage]
  );

  useEffect(() => {
    setDraft(loadDraftFromStorage());
  }, [loadDraftFromStorage]);

  const load = useCallback(async () => {
    if (canEdit || usePendingDraft) {
      setLoading(false);
      setError('');
      return;
    }
    if (!consultaHcId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await getConsultaDetalle(consultaHcId);
      setDetalle(data);
    } catch (e) {
      setError(formatDrfError(e) || 'No se pudo cargar los pedidos de la consulta.');
      setDetalle(null);
    } finally {
      setLoading(false);
    }
  }, [consultaHcId, canEdit, usePendingDraft]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAddLabDraft = (payload: {
    examenes_ids: number[];
    paneles_ids: number[];
    examenes_labels: string[];
    paneles_labels: string[];
    observaciones?: string;
  }) => {
    persistDraft((prev) => ({
      ...prev,
      solicitudesLab: [
        ...prev.solicitudesLab,
        {
          id: newDraftId(),
          ...payload,
        },
      ],
    }));
    setActionError('');
  };

  const handleAgregarEstudioBorrador = () => {
    if (!selectedTipoEstudio) {
      setActionError('Seleccioná un tipo de estudio.');
      return;
    }
    persistDraft((prev) => ({
      ...prev,
      estudios: [
        ...prev.estudios,
        {
          id: newDraftId(),
          tipo_estudio_id: selectedTipoEstudio.id > 0 ? selectedTipoEstudio.id : undefined,
          modalidad: selectedTipoEstudio.modalidad,
          tipo_label: formatEstudioTipoLabel(selectedTipoEstudio),
          descripcion_clinica: estudioDesc.trim() || undefined,
        },
      ],
    }));
    setEstudioOpen(false);
    setActionError('');
  };

  const handleEliminarLabBorrador = (id: string) => {
    persistDraft((prev) => ({
      ...prev,
      solicitudesLab: prev.solicitudesLab.filter((s) => s.id !== id),
    }));
  };

  const handleEliminarEstudioBorrador = (id: string) => {
    persistDraft((prev) => ({
      ...prev,
      estudios: prev.estudios.filter((e) => e.id !== id),
    }));
  };

  const openEstudioDialog = async () => {
    setActionError('');
    setEstudioDesc('');
    setSelectedTipoEstudio(null);
    setEstudioCatalogLoading(true);
    setEstudioOpen(true);
    try {
      const catalog = await listTiposEstudioComplementario();
      setTiposEstudio(buildEstudioCatalogOptions(catalog));
    } catch (e) {
      setActionError(parseEstudiosApiError(e, 'No se pudo cargar el catálogo de estudios.'));
      setTiposEstudio(buildEstudioCatalogOptions([]));
    } finally {
      setEstudioCatalogLoading(false);
    }
  };

  const renderClinicalDialog = (
    open: boolean,
    onClose: () => void,
    title: string,
    children: React.ReactNode,
    actions: React.ReactNode
  ) => (
    <ThemeProvider theme={dialogTheme}>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="sm"
        fullWidth
        {...clinicalDrawerDialogProps}
      >
        <DialogTitle>{title}</DialogTitle>
        <DialogContent sx={clinicalDrawerDialogContentSx}>{children}</DialogContent>
        <DialogActions>{actions}</DialogActions>
      </Dialog>
    </ThemeProvider>
  );

  const solicitudesLab = detalle?.solicitudes_laboratorio ?? [];
  const estudios = detalle?.estudios_complementarios ?? [];
  const draftLab = draft.solicitudesLab;
  const draftEstudios = draft.estudios;

  const estudioTipoLabel = useCallback(
    (t: TipoEstudioComplementario) => formatEstudioTipoLabel(t),
    []
  );

  if (loading && variant !== 'compact') {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return (
      <Stack spacing={2}>
        <Alert severity="error">{error}</Alert>
        <Button variant="outlined" size="small" onClick={() => load()}>
          Reintentar
        </Button>
      </Stack>
    );
  }

  const pedidosDialogs = (
    <>
      <NuevaOrdenLimsDialog
        open={labOpen}
        onClose={() => setLabOpen(false)}
        draftMode
        consultaHcId={consultaHcId}
        onAddDraft={handleAddLabDraft}
      />

      {renderClinicalDialog(
        estudioOpen,
        () => setEstudioOpen(false),
        'Solicitar estudio complementario',
        <>
          {actionError && <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert>}
          {estudioCatalogLoading ? (
            <Box display="flex" justifyContent="center" py={3}>
              <CircularProgress size={28} />
            </Box>
          ) : (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Autocomplete
                options={tiposEstudio}
                value={selectedTipoEstudio}
                onChange={(_e, value) => setSelectedTipoEstudio(value)}
                getOptionLabel={estudioTipoLabel}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                filterOptions={(options, state) => filterCatalogOptions(options, state.inputValue)}
                noOptionsText="Sin coincidencias"
                slotProps={clinicalDrawerAutocompleteSlotProps}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Buscar tipo de estudio *"
                    placeholder="Nombre, código o modalidad"
                  />
                )}
              />
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Indicación clínica"
                value={estudioDesc}
                onChange={(e) => setEstudioDesc(e.target.value)}
                placeholder="Motivo del estudio, región anatómica, etc."
              />
            </Stack>
          )}
        </>,
        <>
          <Button onClick={() => setEstudioOpen(false)}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleAgregarEstudioBorrador}
            disabled={estudioCatalogLoading || !selectedTipoEstudio}
          >
            Agregar a la consulta
          </Button>
        </>
      )}
    </>
  );

  if (variant === 'compact') {
    if (loading) {
      return (
        <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="caption" color="text.secondary">
            Cargando pedidos…
          </Typography>
        </Box>
      );
    }

    const totalPendientes = draftLab.length + draftEstudios.length;

    return (
      <Box
        sx={{
          mt: 2,
          p: 2,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: 'background.default',
        }}
      >
        <Stack spacing={1.5}>
          <Typography variant="subtitle2" fontWeight={600}>
            Pedidos clínicos
          </Typography>

          {actionError && !labOpen && !estudioOpen && (
            <Alert severity="error" onClose={() => setActionError('')}>
              {actionError}
            </Alert>
          )}

          {canEdit && (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button
                size="small"
                variant="outlined"
                startIcon={<Add />}
                onClick={() => setLabOpen(true)}
              >
                Solicitar laboratorio
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={<Add />}
                onClick={openEstudioDialog}
              >
                Solicitar estudio
              </Button>
            </Stack>
          )}

          {totalPendientes > 0 && (
            <Stack spacing={1}>
              {draftLab.map((sol) => (
                <Stack
                  key={sol.id}
                  direction="row"
                  alignItems="flex-start"
                  justifyContent="space-between"
                  spacing={1}
                  sx={{ py: 0.5 }}
                >
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Typography variant="body2" fontWeight={500}>
                      Laboratorio
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {[
                        ...sol.examenes_labels,
                        ...sol.paneles_labels.map((p) => `Panel: ${p}`),
                      ].join(' · ') || '—'}
                    </Typography>
                  </Box>
                  {canEdit && (
                    <IconButton
                      size="small"
                      color="error"
                      aria-label="Quitar pedido de laboratorio"
                      onClick={() => handleEliminarLabBorrador(sol.id)}
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  )}
                </Stack>
              ))}
              {draftEstudios.map((est) => (
                <Stack
                  key={est.id}
                  direction="row"
                  alignItems="flex-start"
                  justifyContent="space-between"
                  spacing={1}
                  sx={{ py: 0.5 }}
                >
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Typography variant="body2" fontWeight={500}>
                      {est.tipo_label}
                    </Typography>
                    {est.descripcion_clinica && (
                      <Typography variant="caption" color="text.secondary" display="block">
                        {est.descripcion_clinica}
                      </Typography>
                    )}
                  </Box>
                  {canEdit && (
                    <IconButton
                      size="small"
                      color="error"
                      aria-label="Quitar estudio"
                      onClick={() => handleEliminarEstudioBorrador(est.id)}
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  )}
                </Stack>
              ))}
            </Stack>
          )}

          {canEdit && totalPendientes === 0 && (
            <Typography variant="caption" color="text.secondary">
              Opcional. Los pedidos se registran al guardar y cerrar la atención.
            </Typography>
          )}
        </Stack>
        {pedidosDialogs}
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      {canEdit && (
        <Alert severity="info">
          Los pedidos de laboratorio y estudios se registrarán al usar{' '}
          <strong>Guardar y cerrar consulta</strong> en el detalle clínico.
        </Alert>
      )}

      {actionError && !labOpen && !estudioOpen && (
        <Alert severity="error" onClose={() => setActionError('')}>
          {actionError}
        </Alert>
      )}

      <Box>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="subtitle1" fontWeight={600}>
            Análisis de laboratorio
          </Typography>
          {canEdit && (
            <Button size="small" startIcon={<Add />} onClick={() => setLabOpen(true)}>
              Solicitar análisis
            </Button>
          )}
        </Stack>
        {canEdit ? (
          draftLab.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No hay pedidos de laboratorio pendientes.
            </Typography>
          ) : (
            <Stack spacing={2}>
              {draftLab.map((sol) => (
                <Box key={sol.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" mb={1}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="body2" fontWeight={600}>
                        Pedido de laboratorio
                      </Typography>
                      <Chip label="Pendiente de guardar" size="small" color="warning" variant="outlined" />
                    </Stack>
                    <IconButton
                      size="small"
                      color="error"
                      aria-label="Eliminar pedido de laboratorio"
                      onClick={() => handleEliminarLabBorrador(sol.id)}
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  </Stack>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {[
                      ...sol.examenes_labels,
                      ...sol.paneles_labels.map((p) => `Panel: ${p}`),
                    ].join(' · ') || '—'}
                  </Typography>
                  {sol.observaciones && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {sol.observaciones}
                    </Typography>
                  )}
                </Box>
              ))}
            </Stack>
          )
        ) : solicitudesLab.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No hay pedidos de laboratorio en esta consulta.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {solicitudesLab.map((sol) => (
              <Box key={sol.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
                <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                  <Typography variant="body2" fontWeight={600}>
                    {sol.numero || `Orden #${sol.id}`}
                  </Typography>
                  <Chip label={sol.estado} size="small" />
                  <Typography variant="caption" color="text.secondary">
                    {new Date(sol.fecha_solicitud).toLocaleString()}
                  </Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                  {[...sol.tipos_examen_nombres, ...sol.paneles_nombres.map((p) => `Panel: ${p}`)].join(' · ') || '—'}
                </Typography>
                {sol.resultados.length > 0 ? (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Examen</TableCell>
                        <TableCell>Resultado</TableCell>
                        <TableCell>Estado</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sol.resultados.map((res) => (
                        <TableRow key={res.id}>
                          <TableCell>{res.tipo_examen_nombre || '—'}</TableCell>
                          <TableCell>
                            {res.valor_obtenido || '—'}
                            {res.unidad ? ` ${res.unidad}` : ''}
                            {res.es_patologico ? (
                              <Chip label="Patológico" size="small" color="warning" sx={{ ml: 1 }} />
                            ) : null}
                          </TableCell>
                          <TableCell>{res.estado || '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Resultados pendientes.
                  </Typography>
                )}
              </Box>
            ))}
          </Stack>
        )}
      </Box>

      <Box>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="subtitle1" fontWeight={600}>
            Estudios complementarios
          </Typography>
          {canEdit && (
            <Button size="small" startIcon={<Add />} onClick={openEstudioDialog}>
              Solicitar estudio
            </Button>
          )}
        </Stack>
        {canEdit ? (
          draftEstudios.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No hay estudios complementarios pendientes.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Estudio</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell align="right">Acción</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {draftEstudios.map((est) => (
                  <TableRow key={est.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {est.tipo_label}
                      </Typography>
                      {est.descripcion_clinica && (
                        <Typography variant="caption" color="text.secondary">
                          {est.descripcion_clinica}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip label="Pendiente de guardar" size="small" color="warning" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="error"
                        aria-label="Eliminar estudio complementario"
                        onClick={() => handleEliminarEstudioBorrador(est.id)}
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )
        ) : estudios.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No hay estudios solicitados en esta consulta.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Estudio</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell align="right">Acción</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {estudios.map((est) => (
                <TableRow key={est.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {est.tipo_estudio_nombre || est.modalidad}
                    </Typography>
                    {est.descripcion_clinica && (
                      <Typography variant="caption" color="text.secondary">
                        {est.descripcion_clinica}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip label={est.estado} size="small" />
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      endIcon={<OpenInNew fontSize="small" />}
                      onClick={() => navigate(`/estudios-complementarios/${est.id}`)}
                    >
                      Ver
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Box>

      {pedidosDialogs}
    </Stack>
  );
};

export default ConsultaPedidosPanel;
export { ConsultaPedidosPanel };
