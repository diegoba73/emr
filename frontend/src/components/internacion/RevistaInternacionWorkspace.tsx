import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
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
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import EvolucionInternacionForm from '../../modules/atenciones/components/forms/EvolucionInternacionForm';
import { canOpenDetalleOrdenLab, pathDetalleOrdenLab } from '../../utils/limsAccess';
import { withNavBack } from '../../utils/navBack';
import RevistaHcDiarioAccordions from './hc/RevistaHcDiarioAccordions';
import NuevaOrdenLimsDialog from '../lims/NuevaOrdenLimsDialog';
import {
  createEstudioComplementario,
  listTiposEstudioComplementario,
} from '../../services/estudiosComplementariosApi';
import { parseEstudiosApiError } from '../../modules/estudios/apiErrors';
import { MODALIDAD_OPTIONS } from '../../modules/estudios/constants';
import type {
  RevistaEstudioItem,
  RevistaInternacionContexto,
  RevistaLabItem,
  RevistaEvolucionItem,
} from '../../services/internacion';
import type { Paciente } from '../../types';
import type { TipoEstudioComplementario } from '../../types/estudios';

type PedidoPanel = 'lab' | 'estudios' | null;

type HistoriaEvento =
  | { key: string; kind: 'lab'; fecha: string; item: RevistaLabItem }
  | { key: string; kind: 'estudio'; fecha: string; item: RevistaEstudioItem }
  | { key: string; kind: 'evolucion'; fecha: string; item: RevistaEvolucionItem };

interface RevistaInternacionWorkspaceProps {
  internacionId: number;
  contexto: RevistaInternacionContexto | null;
  loading: boolean;
  error: string | null;
  canOperateClinica: boolean;
  canWriteSoap: boolean;
  canPedirLaboratorioEstudios: boolean;
  canWriteEnfermeria: boolean;
  canWriteKinesiologia: boolean;
  atencionHoyId: number | null;
  ensuringAtencion: boolean;
  paciente: Paciente | null;
  medicoId: number | null;
  onEnsureAtencion: () => Promise<number | null>;
  onRefresh: () => void;
  onIniciarInterconsulta?: () => void;
  iniciandoInterconsulta?: boolean;
  onAbrirAtencion?: (atencionId: number) => void;
}

const soapPreview = (evo: RevistaEvolucionItem) =>
  [evo.analisis, evo.objetivo, evo.subjetivo, evo.plan].find((t) => t && t.trim()) || 'Sin texto';

const formatFecha = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('es-AR') : '—';

const buildHistoria = (contexto: RevistaInternacionContexto | null): HistoriaEvento[] => {
  if (!contexto) return [];
  const eventos: HistoriaEvento[] = [];
  for (const lab of contexto.laboratorio) {
    eventos.push({
      key: `lab-${lab.id}`,
      kind: 'lab',
      fecha: lab.fecha_solicitud || '',
      item: lab,
    });
  }
  for (const est of contexto.estudios) {
    eventos.push({
      key: `estudio-${est.id}`,
      kind: 'estudio',
      fecha: est.fecha_solicitud || '',
      item: est,
    });
  }
  for (const evo of contexto.evoluciones) {
    eventos.push({
      key: `evo-${evo.atencion_id}`,
      kind: 'evolucion',
      fecha: evo.fecha_evolucion || evo.fecha_admision || '',
      item: evo,
    });
  }
  return eventos.sort((a, b) => (a.fecha < b.fecha ? 1 : a.fecha > b.fecha ? -1 : 0));
};

const RevistaInternacionWorkspace: React.FC<RevistaInternacionWorkspaceProps> = ({
  internacionId,
  contexto,
  loading,
  error,
  canOperateClinica,
  canWriteSoap,
  canPedirLaboratorioEstudios,
  canWriteEnfermeria,
  canWriteKinesiologia,
  atencionHoyId,
  ensuringAtencion,
  paciente,
  medicoId,
  onEnsureAtencion,
  onRefresh,
  onIniciarInterconsulta,
  iniciandoInterconsulta = false,
  onAbrirAtencion,
}) => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const puedeAbrirLab = canOpenDetalleOrdenLab(currentUser);
  const [pedidoPanel, setPedidoPanel] = useState<PedidoPanel>(null);
  const [soapOpen, setSoapOpen] = useState(false);
  const [pedidoError, setPedidoError] = useState<string | null>(null);
  const [localAtencionId, setLocalAtencionId] = useState<number | null>(null);
  const [eventoAbierto, setEventoAbierto] = useState<string | null>(null);

  const [estudioOpen, setEstudioOpen] = useState(false);
  const [estudioSaving, setEstudioSaving] = useState(false);
  const [tiposEstudio, setTiposEstudio] = useState<TipoEstudioComplementario[]>([]);
  const [selectedTipoEstudio, setSelectedTipoEstudio] = useState<TipoEstudioComplementario | null>(null);
  const [estudioDesc, setEstudioDesc] = useState('');
  const [estudioCatalogLoading, setEstudioCatalogLoading] = useState(false);

  const effectiveAtencionId = atencionHoyId ?? localAtencionId;
  const historia = useMemo(() => buildHistoria(contexto), [contexto]);
  const labSinFinalizar = contexto?.laboratorio.find((l) => l.estado !== 'FINALIZADO') ?? null;
  const showEnfermeria = canWriteEnfermeria;
  const showKinesiologia = canWriteKinesiologia;
  const showEvolucionMedica = canWriteSoap || (!showEnfermeria && !showKinesiologia);

  const ensureSoap = async () => {
    setPedidoError(null);
    let id = effectiveAtencionId;
    if (!id) {
      id = await onEnsureAtencion();
    }
    if (!id) {
      setPedidoError('No se pudo preparar la evolución de hoy.');
      setSoapOpen(false);
      return;
    }
    setLocalAtencionId(id);
    setSoapOpen(true);
  };

  const abrirPedidoLab = () => {
    setPedidoError(null);
    if (labSinFinalizar) {
      const numero = labSinFinalizar.numero || `#${labSinFinalizar.id}`;
      setPedidoError(
        `No se puede pedir un nuevo análisis: hay uno en proceso (${numero}, ${labSinFinalizar.estado}). ` +
          'Esperá a que el laboratorio lo finalice.',
      );
      setPedidoPanel(null);
      return;
    }
    if (!paciente?.id) {
      setPedidoError('No hay paciente cargado para solicitar laboratorio.');
      return;
    }
    setPedidoPanel('lab');
  };

  const abrirPedidoEstudios = async () => {
    setPedidoError(null);
    if (!paciente?.id) {
      setPedidoError('No hay paciente cargado para solicitar estudios.');
      return;
    }
    setPedidoPanel('estudios');
    setEstudioDesc('');
    setSelectedTipoEstudio(null);
    setEstudioCatalogLoading(true);
    setEstudioOpen(true);
    try {
      const catalog = await listTiposEstudioComplementario();
      setTiposEstudio(catalog.filter((t) => t.activo !== false));
    } catch (e) {
      setPedidoError(parseEstudiosApiError(e, 'No se pudo cargar el catálogo de estudios.'));
      setTiposEstudio([]);
    } finally {
      setEstudioCatalogLoading(false);
    }
  };

  const guardarEstudio = async () => {
    if (!paciente?.id || !selectedTipoEstudio) return;
    setEstudioSaving(true);
    try {
      await createEstudioComplementario({
        paciente_id: paciente.id,
        modalidad: selectedTipoEstudio.modalidad,
        tipo_estudio: selectedTipoEstudio.id > 0 ? selectedTipoEstudio.id : null,
        descripcion_clinica: estudioDesc.trim() || undefined,
        medico_solicitante: medicoId,
        origen: 'INTERNO',
      });
      toast.success('Estudio complementario solicitado.');
      setEstudioOpen(false);
      setPedidoPanel(null);
      onRefresh();
    } catch (e) {
      setPedidoError(parseEstudiosApiError(e, 'No se pudo solicitar el estudio.'));
    } finally {
      setEstudioSaving(false);
    }
  };

  useEffect(() => {
    if (atencionHoyId) setLocalAtencionId(atencionHoyId);
  }, [atencionHoyId]);

  if (loading && !contexto) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1}
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>
            Revista de sala
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Historial del episodio, pedidos independientes de la evolución, y nota de hoy si hace falta.
          </Typography>
        </Box>
        <Button size="small" onClick={onRefresh} disabled={loading}>
          Actualizar
        </Button>
      </Stack>

      {(contexto?.dias_internacion != null || contexto?.tipo_dieta) && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          {contexto.dias_internacion != null && (
            <Chip size="small" label={`${contexto.dias_internacion} día(s) de internación`} />
          )}
          {contexto.tipo_dieta && (
            <Chip size="small" variant="outlined" label={`Dieta: ${contexto.tipo_dieta}`} />
          )}
        </Stack>
      )}

      {canPedirLaboratorioEstudios && (
        <>
          <Typography variant="overline" color="text.secondary">
            Pedir
          </Typography>
          {pedidoError && (
            <Alert severity="error" sx={{ mb: 1 }} onClose={() => setPedidoError(null)}>
              {pedidoError}
            </Alert>
          )}
          <Stack spacing={1.5} sx={{ mb: 2 }}>
            {labSinFinalizar && (
              <Alert severity="warning">
                Hay un análisis en proceso
                {labSinFinalizar.numero ? ` (${labSinFinalizar.numero})` : ''}. No se puede pedir otro hasta que el laboratorio lo finalice.
              </Alert>
            )}
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button variant="outlined" onClick={abrirPedidoLab}>
                Pedir laboratorio
              </Button>
              <Button variant="outlined" onClick={() => void abrirPedidoEstudios()}>
                Pedir estudios complementarios
              </Button>
            </Stack>
          </Stack>
          <Divider sx={{ mb: 2 }} />
        </>
      )}

      <RevistaHcDiarioAccordions
        internacionId={internacionId}
        canWriteEnfermeria={canWriteEnfermeria}
        canWriteKinesiologia={canWriteKinesiologia}
        showEnfermeria={showEnfermeria}
        showKinesiologia={showKinesiologia}
      />

      {showEvolucionMedica && (
      <Accordion
        expanded={soapOpen}
        onChange={(_, expanded) => {
          if (expanded) {
            if (canWriteSoap) {
              void ensureSoap();
            } else {
              setSoapOpen(true);
            }
          } else {
            setSoapOpen(false);
          }
        }}
        disableGutters
        sx={{ border: 1, borderColor: 'divider', borderRadius: 1, mb: 2, '&:before': { display: 'none' } }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <Typography variant="subtitle2" fontWeight={700}>
                Evolución médica
              </Typography>
              {contexto?.evolucion_hoy && (
                <Chip size="small" label="Registrada hoy" color="success" variant="outlined" />
              )}
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block">
              Nota del médico tratante en la revista de sala. Una por día. No hace falta para pedir laboratorio o estudios.
            </Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {!canWriteSoap ? (
            <Alert severity="info">
              La evolución médica la carga el médico tratante. Podés leerla en el historial del episodio.
            </Alert>
          ) : ensuringAtencion || !effectiveAtencionId ? (
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={18} />
              <Typography variant="body2">Preparando evolución de hoy…</Typography>
            </Stack>
          ) : (
            <Stack spacing={2}>
              <EvolucionInternacionForm
                atencionId={effectiveAtencionId}
                canEdit={canWriteSoap}
                variant="revista"
                onSaveSuccess={onRefresh}
              />
              {onIniciarInterconsulta && (
                <Box sx={{ pt: 1, borderTop: 1, borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                    Si otro profesional o especialidad deja una nota adicional en este episodio:
                  </Typography>
                  <Button
                    variant="text"
                    size="small"
                    onClick={onIniciarInterconsulta}
                    disabled={iniciandoInterconsulta}
                  >
                    Interconsulta de especialista
                  </Button>
                </Box>
              )}
            </Stack>
          )}
        </AccordionDetails>
      </Accordion>
      )}

      <Typography variant="overline" color="text.secondary">
        Historial del episodio
      </Typography>
      {!historia.length ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Todavía no hay análisis, estudios ni evoluciones en esta internación.
        </Typography>
      ) : (
        <Stack spacing={1} sx={{ mb: 2 }}>
          {historia.map((ev) => {
            const abierto = eventoAbierto === ev.key;
            if (ev.kind === 'lab') {
              const lab = ev.item;
              return (
                <Box
                  key={ev.key}
                  sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.25 }}
                >
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                    <Chip size="small" label="Análisis" color="primary" variant="outlined" />
                    <Typography variant="body2" fontWeight={600}>
                      {formatFecha(ev.fecha)}
                    </Typography>
                    <Typography variant="body2">
                      {lab.numero || `Orden #${lab.id}`}
                    </Typography>
                    <Chip size="small" label={lab.estado} color={lab.tiene_resultados ? 'success' : 'default'} />
                    <Button size="small" onClick={() => setEventoAbierto(abierto ? null : ev.key)}>
                      {abierto ? 'Ocultar' : 'Ver'}
                    </Button>
                    {puedeAbrirLab && (
                      <Button
                        size="small"
                        onClick={() =>
                          navigate(
                            pathDetalleOrdenLab(currentUser, lab.id),
                            withNavBack('/internacion', '← Volver a internación')
                          )
                        }
                      >
                        Abrir en laboratorio
                      </Button>
                    )}
                  </Stack>
                  {abierto && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {[...lab.examenes, ...lab.paneles.map((p) => `Panel: ${p}`)].join(' · ') || '—'}
                      </Typography>
                      {lab.resultados.map((r) => (
                        <Typography
                          key={r.id}
                          variant="body2"
                          sx={{
                            color: r.es_patologico ? 'error.main' : 'text.primary',
                            fontWeight: r.es_patologico ? 600 : 400,
                          }}
                        >
                          {r.examen || 'Examen'}: {r.valor}
                          {r.unidad ? ` ${r.unidad}` : ''}
                          {r.es_patologico ? ' (fuera de rango)' : ''}
                        </Typography>
                      ))}
                      {!lab.resultados.length && (
                        <Typography variant="body2" color="text.secondary">
                          Sin resultados cargados todavía.
                        </Typography>
                      )}
                    </Box>
                  )}
                </Box>
              );
            }
            if (ev.kind === 'estudio') {
              const est = ev.item;
              return (
                <Box
                  key={ev.key}
                  sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.25 }}
                >
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                    <Chip size="small" label="Estudio" color="secondary" variant="outlined" />
                    <Typography variant="body2" fontWeight={600}>
                      {formatFecha(ev.fecha)}
                    </Typography>
                    <Typography variant="body2">
                      {est.tipo_nombre || est.modalidad}
                    </Typography>
                    <Chip size="small" label={est.estado} />
                    <Button
                      size="small"
                      onClick={() => navigate(`/estudios-complementarios/${est.id}`)}
                    >
                      Abrir estudio
                    </Button>
                  </Stack>
                </Box>
              );
            }
            const evo = ev.item;
            const esAtencionEditable =
              canOperateClinica
              && onAbrirAtencion
              && (evo.tipo_evolucion === 'INTERCONSULTA' || evo.tipo_evolucion === 'NOTA_ENFERMERIA');
            return (
              <Box
                key={ev.key}
                sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.25 }}
              >
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Chip size="small" label="Evolución" color="warning" variant="outlined" />
                  <Typography variant="body2" fontWeight={600}>
                    {formatFecha(ev.fecha)}
                  </Typography>
                  <Typography variant="body2">{evo.tipo_evolucion_display}</Typography>
                  <Chip size="small" label={evo.estado_clinico} />
                  <Button size="small" onClick={() => setEventoAbierto(abierto ? null : ev.key)}>
                    {abierto ? 'Ocultar' : 'Ver'}
                  </Button>
                  {esAtencionEditable && (
                    <Button size="small" onClick={() => onAbrirAtencion(evo.atencion_id)}>
                      Abrir
                    </Button>
                  )}
                </Stack>
                {abierto && (
                  <Box sx={{ mt: 1 }}>
                    {evo.medico_nombre && (
                      <Typography variant="caption" color="text.secondary" display="block">
                        {evo.medico_nombre}
                      </Typography>
                    )}
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {soapPreview(evo)}
                    </Typography>
                  </Box>
                )}
              </Box>
            );
          })}
        </Stack>
      )}

      {paciente && (
        <NuevaOrdenLimsDialog
          open={pedidoPanel === 'lab' && !labSinFinalizar}
          onClose={() => setPedidoPanel(null)}
          pacienteInicial={paciente}
          medicoId={medicoId}
          onCreated={() => {
            setPedidoPanel(null);
            onRefresh();
          }}
          onCreatedMicro={() => {
            setPedidoPanel(null);
            onRefresh();
          }}
        />
      )}

      <Dialog open={estudioOpen} onClose={() => setEstudioOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Solicitar estudio complementario</DialogTitle>
        <DialogContent>
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
                getOptionLabel={(t) => {
                  const mod = MODALIDAD_OPTIONS.find((m) => m.value === t.modalidad)?.label;
                  return mod ? `${t.nombre} (${mod})` : t.nombre;
                }}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                renderInput={(params) => (
                  <TextField {...params} label="Tipo de estudio" placeholder="Buscar…" />
                )}
              />
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Indicación clínica"
                value={estudioDesc}
                onChange={(e) => setEstudioDesc(e.target.value)}
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEstudioOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={() => void guardarEstudio()}
            disabled={estudioCatalogLoading || estudioSaving || !selectedTipoEstudio}
          >
            {estudioSaving ? <CircularProgress size={20} /> : 'Solicitar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RevistaInternacionWorkspace;
