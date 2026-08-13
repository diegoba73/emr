import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Stack,
  Chip,
  Alert,
  CircularProgress,
  List,
  ListItemButton,
  ListItemText,
  Divider,
} from '@mui/material';
import { ArrowBack, Edit, PersonOutline, WarningAmber } from '@mui/icons-material';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import { listSolicitudesExamen } from '../../services/limsApi';
import { Atencion, ArchivoMedico, InternacionCama, Paciente, PacienteTimelineEvent } from '../../types';
import type { SolicitudExamenLims } from '../../types/lims';
import { getInternaciones } from '../../services/apiService';
import PatientIntegratedView from '../PatientIntegratedView';
import PacienteFormDialog from '../PacienteFormDialog';
import { canUpdatePacienteDemographics } from '../../utils/permissions';
import { pacienteFichaAnalisisPath, withNavBack } from '../../utils/navBack';
import SectionCard from './SectionCard';
import InfoCard from './InfoCard';
import Timeline, { TimelineItem, TimelineItemType } from './Timeline';
import { patientAgeYears } from './patientAge';

function mapTimelineEvent(
  ev: PacienteTimelineEvent,
  navigate: (path: string, opts?: { state?: unknown }) => void,
  pacienteId: number,
): TimelineItem | null {
  const date = ev.date ? new Date(ev.date) : new Date(0);
  if (Number.isNaN(date.getTime())) return null;
  const type = (ev.type || 'otro') as TimelineItemType;
  return {
    id: ev.id,
    type,
    title: ev.title,
    subtitle: ev.subtitle || undefined,
    date,
    critical: Boolean(ev.critical),
    nested: Boolean(ev.nested),
    episodeGroupId: ev.episode_group_id || undefined,
    episodeGroupTitle: ev.episode_group_title || undefined,
    onClick: () => {
      const path = ev.navigate_to || '/atenciones';
      const openId = ev.atencion_id || (ev.meta?.openAtencionId as number | undefined);
      if (openId) {
        navigate(path, { state: { openAtencionId: openId } });
        return;
      }
      if (path.startsWith('/solicitudes/')) {
        navigate(
          path,
          withNavBack(pacienteFichaAnalisisPath(pacienteId), '← Volver a la ficha')
        );
        return;
      }
      if (path.startsWith('/estudios-complementarios/')) {
        navigate(
          path,
          withNavBack(`/paciente/${pacienteId}`, '← Volver a la ficha')
        );
        return;
      }
      navigate(path);
    },
  };
}

const PatientDashboard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    pacientes,
    loadPacientes,
    loading,
    archivosMedicos,
    loadArchivosMedicos,
    currentUser,
  } = useData();

  const [atenciones, setAtenciones] = useState<Atencion[]>([]);
  const [internaciones, setInternaciones] = useState<InternacionCama[]>([]);
  const [ordenesLab, setOrdenesLab] = useState<SolicitudExamenLims[]>([]);
  const [timelineItems, setTimelineItems] = useState<TimelineItem[]>([]);
  const [loadingAte, setLoadingAte] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [showEditPaciente, setShowEditPaciente] = useState(false);

  const pid = Number(id);
  const fichaLabTab = searchParams.get('tab') === 'analisis' ? 2 : 0;
  const paciente: Paciente | undefined = useMemo(
    () => pacientes.find((p) => p.id === pid),
    [pacientes, pid]
  );

  useEffect(() => {
    if (!loading.pacientes && pacientes.length === 0) {
      loadPacientes();
    }
  }, [loadPacientes, loading.pacientes, pacientes.length]);

  useEffect(() => {
    if (paciente?.id) {
      loadArchivosMedicos();
    }
  }, [loadArchivosMedicos, paciente?.id]);

  const loadAtenciones = useCallback(async () => {
    if (!paciente?.id) return;
    setLoadingAte(true);
    try {
      const response = await apiService.getAtenciones({ paciente: paciente.id });
      setAtenciones(response.results || []);
    } catch {
      setAtenciones([]);
    } finally {
      setLoadingAte(false);
    }
  }, [paciente?.id]);

  const loadTimeline = useCallback(async () => {
    if (!paciente?.id) return;
    setLoadingTimeline(true);
    try {
      const events = await apiService.getPacienteTimeline(paciente.id);
      setTimelineItems(
        events
          .map((ev) => mapTimelineEvent(ev, navigate, pid))
          .filter((x): x is TimelineItem => Boolean(x)),
      );
    } catch {
      setTimelineItems([]);
    } finally {
      setLoadingTimeline(false);
    }
  }, [paciente?.id, navigate, pid]);

  useEffect(() => {
    loadAtenciones();
  }, [loadAtenciones]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  useEffect(() => {
    if (!paciente?.id) return;
    listSolicitudesExamen({ paciente: paciente.id })
      .then(setOrdenesLab)
      .catch(() => setOrdenesLab([]));
  }, [paciente?.id]);

  const ordenesLabPx = ordenesLab;
  const archivosPx: ArchivoMedico[] = useMemo(
    () => archivosMedicos.filter((a) => a.paciente_id === pid),
    [archivosMedicos, pid]
  );

  useEffect(() => {
    if (!paciente?.id) return;
    getInternaciones({ paciente: paciente.id, historico: true })
      .then(setInternaciones)
      .catch(() => setInternaciones([]));
  }, [paciente?.id]);

  const internacionActiva = useMemo(
    () => internaciones.find((i) => i.activo),
    [internaciones],
  );
  if (!id || Number.isNaN(pid)) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="warning">Identificador de paciente no válido.</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/pacientes')}>
          Volver a pacientes
        </Button>
      </Box>
    );
  }

  if (loading.pacientes && !paciente) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  if (!paciente) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="info">
          No tiene permisos para ver este paciente o el registro no está disponible.
        </Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/pacientes')}>
          Volver a pacientes
        </Button>
      </Box>
    );
  }

  const edad = patientAgeYears(paciente.fecha_nacimiento);
  const alergias = (paciente.alergias || '').trim();
  const riesgo = [paciente.grupo_sanguineo, paciente.antecedentes].filter(Boolean).join(' · ');
  const canEditDemographics = canUpdatePacienteDemographics(currentUser);

  return (
    <Box className="fade-in">
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" flexWrap="wrap" gap={2} sx={{ mb: 2 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/pacientes')} size="small" variant="text">
          Pacientes
        </Button>
      </Stack>

      <Box
        sx={{
          p: 2.5,
          borderRadius: 2,
          mb: 2,
          background: (t) => `linear-gradient(135deg, ${t.palette.primary.main} 0%, ${t.palette.secondary.main} 100%)`,
          color: 'common.white',
        }}
      >
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'flex-start', sm: 'center' }} justifyContent="space-between">
          <Box>
            <Typography variant="h5" fontWeight={800} sx={{ textShadow: '0 1px 2px rgba(0,0,0,0.15)' }}>
              {paciente.nombre} {paciente.apellido}
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1, alignItems: 'center' }}>
              <Chip
                size="small"
                icon={<PersonOutline sx={{ color: 'inherit !important' }} />}
                label={`DNI ${paciente.dni}`}
                sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }}
              />
              <Chip size="small" label={`${edad} años`} sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }} />
              {internacionActiva && (
                <Chip
                  size="small"
                  color="warning"
                  label={`Internado${internacionActiva.cama_nombre ? ` · ${internacionActiva.cama_nombre}` : ''}`}
                  sx={{ bgcolor: 'rgba(255,255,255,0.95)', color: 'warning.dark', fontWeight: 700 }}
                />
              )}
            </Stack>
          </Box>
          <Stack direction="row" spacing={1} alignItems="flex-start">
            {canEditDemographics && (
              <Button
                variant="contained"
                size="small"
                startIcon={<Edit />}
                onClick={() => setShowEditPaciente(true)}
                sx={{ bgcolor: 'rgba(255,255,255,0.95)', color: 'primary.main', '&:hover': { bgcolor: '#fff' } }}
              >
                Editar datos
              </Button>
            )}
          <Box sx={{ maxWidth: 480 }}>
            {alergias ? (
              <Alert
                icon={<WarningAmber />}
                severity="warning"
                sx={{ bgcolor: 'rgba(0,0,0,0.2)', color: 'common.white', '& .MuiAlert-icon': { color: 'common.white' } }}
              >
                Alergias: {alergias}
              </Alert>
            ) : (
              <Typography variant="body2" sx={{ opacity: 0.95 }}>
                Sin alergias registradas en ficha
              </Typography>
            )}
            {riesgo && (
              <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.9 }}>
                {riesgo}
              </Typography>
            )}
          </Box>
          </Stack>
        </Stack>
      </Box>

      <PacienteFormDialog
        open={showEditPaciente}
        mode="edit"
        paciente={paciente}
        onClose={() => setShowEditPaciente(false)}
        onSaved={loadPacientes}
      />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1fr 400px' },
          gap: 2,
          alignItems: 'stretch',
        }}
      >
        <Box>
          <SectionCard
            title="Línea de tiempo clínica"
            subtitle="Timeline unificada (Atención como eje; sin duplicar HC vinculada)"
            headerRight={
              loadingAte || loadingTimeline ? <CircularProgress size={18} color="inherit" /> : null
            }
          >
            <Timeline items={timelineItems} />
          </SectionCard>
        </Box>
        <Box>
          <Stack spacing={2} sx={{ height: '100%' }}>
            <InfoCard title="Últimos signos vitales" dense>
              {atenciones.some((a) => a.ultimo_signo_vital || (a.signos_vitales && a.signos_vitales.length > 0)) ? (
                <List dense disablePadding>
                  {atenciones
                    .filter((a) => a.ultimo_signo_vital || (a.signos_vitales && a.signos_vitales[0]))
                    .slice(0, 3)
                    .map((a) => {
                      const sv = a.ultimo_signo_vital || a.signos_vitales?.[0];
                      if (!sv) return null;
                      const parts = [
                        sv.tension_arterial && `TA ${sv.tension_arterial}`,
                        sv.frecuencia_cardiaca != null && `FC ${sv.frecuencia_cardiaca}`,
                        sv.temperatura != null && `T ${sv.temperatura}°C`,
                        sv.saturacion_oxigeno != null && `SpO₂ ${sv.saturacion_oxigeno}%`,
                      ].filter(Boolean);
                      return (
                        <ListItemButton
                          key={`sv-${a.id}`}
                          onClick={() => navigate('/atenciones', { state: { openAtencionId: a.id } })}
                          sx={{ borderRadius: 1 }}
                        >
                          <ListItemText
                            primary={parts.join(' · ') || 'Registro SV'}
                            secondary={
                              sv.fecha_registro
                                ? new Date(sv.fecha_registro).toLocaleString('es-AR')
                                : a.fecha_admision
                            }
                          />
                        </ListItemButton>
                      );
                    })}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Sin signos vitales recientes
                </Typography>
              )}
            </InfoCard>
            <InfoCard title="Últimas atenciones / consultas" dense>
              {atenciones.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Sin atenciones registradas
                </Typography>
              ) : (
                <List dense disablePadding>
                  {atenciones.slice(0, 5).map((a) => (
                    <ListItemButton
                      key={a.id}
                      onClick={() => navigate('/atenciones', { state: { openAtencionId: a.id } })}
                      sx={{ borderRadius: 1 }}
                    >
                      <ListItemText
                        primary={a.tipo_intervencion}
                        secondary={a.fecha_admision ? new Date(a.fecha_admision).toLocaleString('es-AR') : ''}
                      />
                    </ListItemButton>
                  ))}
                </List>
              )}
            </InfoCard>
            <InfoCard title="Archivos médicos" dense>
              {archivosPx.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Sin archivos
                </Typography>
              ) : (
                <List dense disablePadding>
                  {archivosPx.slice(0, 5).map((a) => (
                    <ListItemButton
                      key={a.id}
                      onClick={() => navigate('/archivos-medicos')}
                      sx={{ borderRadius: 1 }}
                    >
                      <ListItemText primary={a.titulo} secondary={a.tipo_archivo} />
                    </ListItemButton>
                  ))}
                </List>
              )}
            </InfoCard>
            <InfoCard
              title="Análisis de laboratorio"
              dense
              action={
                <Button
                  size="small"
                  onClick={() => {
                    setSearchParams({ tab: 'analisis' });
                    document.getElementById('ficha-paciente-detalle')?.scrollIntoView({
                      behavior: 'smooth',
                      block: 'start',
                    });
                  }}
                >
                  Ver
                </Button>
              }
            >
              {ordenesLabPx.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Sin órdenes de laboratorio
                </Typography>
              ) : (
                <Stack direction="row" flexWrap="wrap" gap={0.5}>
                  {ordenesLabPx.slice(0, 6).map((s) => (
                    <Chip
                      key={s.id}
                      size="small"
                      label={s.numero ? `${s.numero} · ${s.estado}` : s.estado}
                      variant="outlined"
                      onClick={() =>
                        navigate(
                          `/solicitudes/${s.id}`,
                          withNavBack(pacienteFichaAnalisisPath(pid), '← Volver a la ficha')
                        )
                      }
                    />
                  ))}
                </Stack>
              )}
            </InfoCard>
            <InfoCard title="Datos demográficos" dense>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {paciente.direccion || 'Sin domicilio'}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Tel: {paciente.telefono || '—'} · Email: {paciente.email || '—'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Obra social: {paciente.obra_social || '—'}
              </Typography>
            </InfoCard>
          </Stack>
        </Box>
      </Box>

      <Divider sx={{ my: 3 }} />

      <Box sx={{ mb: 1 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Ficha clínica detallada
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Información completa, atenciones y laboratorio
        </Typography>
      </Box>
      <Box id="ficha-paciente-detalle">
        <PatientIntegratedView
          paciente={paciente}
          variant="page"
          initialTab={fichaLabTab}
        />
      </Box>
    </Box>
  );
};

export default PatientDashboard;
