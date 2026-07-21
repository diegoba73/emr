import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
import { Atencion, ArchivoMedico, Consulta, InternacionCama, Paciente, Turno } from '../../types';
import type { SolicitudExamenLims } from '../../types/lims';
import { getInternaciones } from '../../services/apiService';
import PatientIntegratedView from '../PatientIntegratedView';
import PacienteFormDialog from '../PacienteFormDialog';
import { canUpdatePacienteDemographics } from '../../utils/permissions';
import SectionCard from './SectionCard';
import InfoCard from './InfoCard';
import Timeline, { TimelineItem } from './Timeline';
import { patientAgeYears } from './patientAge';

const PatientDashboard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    pacientes,
    loadPacientes,
    loading,
    turnos,
    archivosMedicos,
    loadArchivosMedicos,
    consultas,
    loadConsultas,
    currentUser,
  } = useData();

  const [atenciones, setAtenciones] = useState<Atencion[]>([]);
  const [internaciones, setInternaciones] = useState<InternacionCama[]>([]);
  const [ordenesLab, setOrdenesLab] = useState<SolicitudExamenLims[]>([]);
  const [loadingAte, setLoadingAte] = useState(false);
  const [showEditPaciente, setShowEditPaciente] = useState(false);

  const pid = Number(id);
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
      loadConsultas();
    }
  }, [loadArchivosMedicos, loadConsultas, paciente?.id]);

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

  useEffect(() => {
    loadAtenciones();
  }, [loadAtenciones]);

  useEffect(() => {
    if (!paciente?.id) return;
    listSolicitudesExamen({ paciente: paciente.id })
      .then(setOrdenesLab)
      .catch(() => setOrdenesLab([]));
  }, [paciente?.id]);

  const turnosPx: Turno[] = useMemo(
    () => turnos.filter((t) => t.paciente?.id === pid || t.paciente_id === pid),
    [turnos, pid]
  );
  const ordenesLabPx = ordenesLab;
  const archivosPx: ArchivoMedico[] = useMemo(
    () => archivosMedicos.filter((a) => a.paciente_id === pid),
    [archivosMedicos, pid]
  );
  const consultasPx: Consulta[] = useMemo(
    () =>
      consultas.filter(
        (c) =>
          c.paciente_id === pid ||
          (c as any).paciente?.id === pid ||
          (c.historia_clinica?.paciente as Paciente | undefined)?.id === pid
      ),
    [consultas, pid]
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

  const timelineItems: TimelineItem[] = useMemo(() => {
    const out: TimelineItem[] = [];
    const internacionIds = new Set(internaciones.map((i) => i.id));

    for (const t of turnosPx) {
      const start = t.fecha_hora_inicio ? new Date(t.fecha_hora_inicio) : new Date(0);
      if (Number.isNaN(start.getTime())) continue;
      out.push({
        id: `turno-${t.id}`,
        type: 'turno',
        title: `Turno ambulatorio (${t.estado})`,
        subtitle: t.motivo_reserva || t.motivo_consulta || t.recurso?.nombre,
        date: start,
        critical: t.estado === 'CANCELADO',
        onClick: () => navigate('/turnos'),
      });
    }

    for (const internacion of internaciones) {
      const ingreso = internacion.fecha_ingreso ? new Date(internacion.fecha_ingreso) : new Date(0);
      const groupId = `internacion-${internacion.id}`;
      const sectorLabel = internacion.cama_nombre || `Internación #${internacion.id}`;
      if (!Number.isNaN(ingreso.getTime())) {
        out.push({
          id: `int-ingreso-${internacion.id}`,
          type: 'internacion_ingreso',
          title: `Ingreso — ${internacion.numero_internacion || groupId}`,
          subtitle: internacion.diagnostico_ingreso || internacion.motivo_ingreso || sectorLabel,
          date: ingreso,
          episodeGroupId: groupId,
          episodeGroupTitle: `Episodio de internación · ${sectorLabel}`,
          onClick: () => navigate('/internacion'),
        });
      }
      if (internacion.fecha_alta) {
        const alta = new Date(internacion.fecha_alta);
        if (!Number.isNaN(alta.getTime())) {
          out.push({
            id: `int-alta-${internacion.id}`,
            type: 'internacion_alta',
            title: 'Alta médica',
            subtitle: internacion.numero_internacion || undefined,
            date: alta,
            episodeGroupId: groupId,
            nested: true,
            onClick: () => navigate('/internacion'),
          });
        }
      }
    }

    for (const a of atenciones) {
      const d = a.fecha_admision ? new Date(a.fecha_admision) : new Date(0);
      if (Number.isNaN(d.getTime())) continue;
      const isInternacion = a.contexto_atencion === 'INTERNACION' || Boolean(a.internacion_id);
      if (isInternacion && a.internacion_id && internacionIds.has(a.internacion_id)) {
        const evo = a.evolucion_internacion;
        const tipoEvo = evo?.tipo_evolucion_display || evo?.tipo_evolucion || 'Evolución';
        out.push({
          id: `atencion-${a.id}`,
          type: 'internacion_evolucion',
          title: tipoEvo,
          subtitle: a.estado_clinico ? `Estado: ${a.estado_clinico}` : undefined,
          date: evo?.fecha_evolucion ? new Date(evo.fecha_evolucion) : d,
          episodeGroupId: `internacion-${a.internacion_id}`,
          nested: true,
          critical: a.estado_clinico === 'ABIERTA',
          onClick: () => navigate('/atenciones', { state: { openAtencionId: a.id } }),
        });
        continue;
      }
      const t = a.tipo_intervencion;
      const isGuardia = a.contexto_atencion === 'GUARDIA';
      out.push({
        id: `atencion-${a.id}`,
        type: isGuardia ? 'guardia' : t === 'ESTUDIO' ? 'estudio' : t === 'PROCEDIMIENTO' || t === 'CIRUGIA' ? 'procedimiento' : 'consulta',
        title: isGuardia
          ? 'Guardia cardiológica'
          : a.tipo_intervencion === 'CONSULTA'
            ? 'Consulta ambulatoria'
            : a.tipo_intervencion,
        subtitle: a.estado_clinico ? `Estado: ${a.estado_clinico}` : undefined,
        date: d,
        critical: a.estado_clinico === 'ABIERTA' && (t === 'CONSULTA' || isGuardia),
        onClick: () => {
          if (a.id) {
            navigate(isGuardia ? '/guardia' : '/atenciones', { state: { openAtencionId: a.id } });
          }
        },
      });
    }
    for (const s of ordenesLabPx) {
      const d = s.fecha_solicitud ? new Date(s.fecha_solicitud) : new Date(0);
      if (Number.isNaN(d.getTime())) continue;
      out.push({
        id: `sol-${s.id}`,
        type: 'solicitud',
        title: s.numero ? `Lab ${s.numero}` : 'Análisis de laboratorio',
        subtitle: s.estado,
        date: d,
        critical: s.estado === 'PENDIENTE',
        onClick: () => navigate(`/solicitudes/${s.id}`),
      });
    }
    for (const c of consultasPx) {
      const d = c.fecha_hora_consulta ? new Date(c.fecha_hora_consulta) : c.created_at ? new Date(c.created_at) : new Date(0);
      if (Number.isNaN(d.getTime())) continue;
      out.push({
        id: `con-${c.id}`,
        type: 'consulta',
        title: c.motivo_consulta_detalle?.slice(0, 80) || 'Consulta',
        date: d,
        onClick: () => navigate('/atenciones'),
      });
    }
    return out;
  }, [atenciones, consultasPx, internaciones, navigate, ordenesLabPx, turnosPx]);

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
            subtitle="Turnos, consultas, procedimientos y solicitudes (datos ya cargados en contexto o API de atenciones)"
            headerRight={
              loadingAte ? <CircularProgress size={18} color="inherit" /> : null
            }
          >
            <Timeline items={timelineItems} />
          </SectionCard>
        </Box>
        <Box>
          <Stack spacing={2} sx={{ height: '100%' }}>
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
                <Button size="small" onClick={() => navigate('/solicitudes')}>
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
                      onClick={() => navigate(`/solicitudes/${s.id}`)}
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
      <PatientIntegratedView paciente={paciente} variant="page" />
    </Box>
  );
};

export default PatientDashboard;
