import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemSecondaryAction,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  ArrowBack,
  CheckCircle,
  Download,
  Link as LinkIcon,
  Send,
  Undo,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { useData } from '../contexts/DataContext';
import { parseEstudiosApiError } from '../modules/estudios/apiErrors';
import {
  ARCHIVO_ROL_OPTIONS,
  ESTADO_CHIP_COLOR,
  ESTADO_LABELS,
  MODALIDAD_OPTIONS,
} from '../modules/estudios/constants';
import {
  canAccessEstudiosModule,
  canAnularEstudio,
  canAsociarArchivo,
  canCrearInforme,
  canDownloadArchivoEstudio,
  canEmitirInforme,
  canEntregarEstudio,
  canMarcarRealizado,
  canRectificarInforme,
  canValidarInformeUi,
  canWriteEstudio,
} from '../modules/estudios/permissions';
import { getArchivosPorPaciente } from '../services/apiService';
import {
  agregarArchivoEstudio,
  anularEstudio,
  crearInformeEstudio,
  downloadArchivoEstudio,
  emitirInformeEstudio,
  entregarEstudio,
  listArchivosEstudio,
  listInformesEstudio,
  marcarRealizadoEstudio,
  rectificarInformeEstudio,
  triggerBlobDownload,
  validarInformeEstudio,
  getEstudioComplementario,
} from '../services/estudiosComplementariosApi';
import type {
  ArchivoEstudioComplementario,
  EstudioComplementario,
  InformeEstudioComplementario,
} from '../types/estudios';
import { ArchivoMedico } from '../types';
import { formatPacienteLabel } from '../utils/pacienteFormat';

const EstudioComplementarioDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentUser, pacientes, loadPacientes } = useData();
  const estudioId = Number(id);

  const [estudio, setEstudio] = useState<EstudioComplementario | null>(null);
  const [archivos, setArchivos] = useState<ArchivoEstudioComplementario[]>([]);
  const [informes, setInformes] = useState<InformeEstudioComplementario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const [anularOpen, setAnularOpen] = useState(false);
  const [motivoAnulacion, setMotivoAnulacion] = useState('');
  const [informeTexto, setInformeTexto] = useState('');
  const [rectificarOpen, setRectificarOpen] = useState(false);
  const [rectificarInformeId, setRectificarInformeId] = useState<number | null>(null);
  const [motivoRectificacion, setMotivoRectificacion] = useState('');
  const [textoRectificacion, setTextoRectificacion] = useState('');
  const [archivoOpen, setArchivoOpen] = useState(false);
  const [archivosPaciente, setArchivosPaciente] = useState<ArchivoMedico[]>([]);
  const [archivoMedicoId, setArchivoMedicoId] = useState<number | ''>('');
  const [archivoRol, setArchivoRol] = useState('OTRO');

  const writeAccess = canWriteEstudio(currentUser);

  const refresh = useCallback(async () => {
    if (!estudioId || Number.isNaN(estudioId)) return;
    setLoading(true);
    setError(null);
    try {
      const [est, arch, inf] = await Promise.all([
        getEstudioComplementario(estudioId),
        listArchivosEstudio(estudioId),
        listInformesEstudio(estudioId),
      ]);
      setEstudio(est);
      setArchivos(arch);
      setInformes(inf);
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudo cargar el estudio.'));
    } finally {
      setLoading(false);
    }
  }, [estudioId]);

  useEffect(() => {
    if (!canAccessEstudiosModule(currentUser)) return;
    refresh();
    loadPacientes();
  }, [currentUser, refresh, loadPacientes]);

  const runAction = async (fn: () => Promise<void>, fallback: string) => {
    setActionLoading(true);
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(parseEstudiosApiError(e, fallback));
    } finally {
      setActionLoading(false);
    }
  };

  const pacienteLabel = estudio
    ? formatPacienteLabel(pacientes.find((p) => p.id === estudio.paciente_id))
    : '';

  const handleDownloadArchivo = async (arch: ArchivoEstudioComplementario) => {
    if (!estudio || !canDownloadArchivoEstudio(currentUser, estudio)) return;
    try {
      const blob = await downloadArchivoEstudio(estudio.id, arch.id);
      await triggerBlobDownload(blob, `archivo-estudio-${arch.id}`);
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudo descargar el archivo.'));
    }
  };

  const openAsociarArchivo = async () => {
    if (!estudio) return;
    setArchivoOpen(true);
    try {
      const list = await getArchivosPorPaciente(estudio.paciente_id);
      setArchivosPaciente(list);
    } catch {
      setArchivosPaciente([]);
    }
  };

  const handleAsociarArchivo = async () => {
    if (!archivoMedicoId || !estudio) return;
    await runAction(async () => {
      await agregarArchivoEstudio(estudio.id, {
        archivo_medico_id: Number(archivoMedicoId),
        tipo_rol: archivoRol,
      });
      setArchivoOpen(false);
      setArchivoMedicoId('');
    }, 'No se pudo asociar el archivo.');
  };

  if (!canAccessEstudiosModule(currentUser)) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tiene acceso a estudios complementarios.</Alert>
      </Box>
    );
  }

  if (loading && !estudio) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!estudio) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Estudio no encontrado.'}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/estudios-complementarios')}>
          Volver al listado
        </Button>
      </Box>
    );
  }

  const informeVigente = informes.find((i) => i.es_vigente && i.estado === 'VALIDADO');

  return (
    <Box sx={{ p: 3 }}>
      <Button startIcon={<ArrowBack />} onClick={() => navigate('/estudios-complementarios')} sx={{ mb: 2 }}>
        Volver
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
          <Box>
            <Typography variant="h5" fontWeight={600}>
              Estudio #{estudio.id}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Paciente: {pacienteLabel || `#${estudio.paciente_id}`}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Modalidad:{' '}
              {MODALIDAD_OPTIONS.find((m) => m.value === estudio.modalidad)?.label || estudio.modalidad}
              {estudio.tipo_estudio_nombre ? ` · ${estudio.tipo_estudio_nombre}` : ''}
            </Typography>
          </Box>
          <Chip
            label={ESTADO_LABELS[estudio.estado]}
            color={ESTADO_CHIP_COLOR[estudio.estado]}
            size="medium"
          />
        </Stack>

        <Divider sx={{ my: 2 }} />

        <Stack direction="row" flexWrap="wrap" gap={1}>
          {writeAccess && canMarcarRealizado(estudio) && (
            <Button
              variant="contained"
              size="small"
              disabled={actionLoading}
              onClick={() => runAction(async () => { await marcarRealizadoEstudio(estudio.id); }, 'No se pudo marcar como realizado.')}
            >
              Marcar realizado
            </Button>
          )}
          {writeAccess && canAnularEstudio(estudio) && (
            <Button
              variant="outlined"
              color="error"
              size="small"
              disabled={actionLoading}
              onClick={() => setAnularOpen(true)}
            >
              Anular
            </Button>
          )}
          {writeAccess && canEntregarEstudio(estudio) && (
            <Button
              variant="contained"
              color="success"
              size="small"
              startIcon={<Send />}
              disabled={actionLoading || !informeVigente}
              onClick={() =>
                runAction(async () => { await entregarEstudio(estudio.id); }, 'No se pudo entregar el estudio.')
              }
            >
              Entregar al paciente
            </Button>
          )}
        </Stack>

        {estudio.motivo_anulacion && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Motivo de anulación: {estudio.motivo_anulacion}
          </Alert>
        )}

        <Box sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Centro:</strong> {estudio.centro_realizador || '—'}
          </Typography>
          <Typography variant="body2">
            <strong>Descripción:</strong> {estudio.descripcion_clinica || '—'}
          </Typography>
          <Typography variant="body2">
            <strong>F. solicitud:</strong>{' '}
            {estudio.fecha_solicitud ? new Date(estudio.fecha_solicitud).toLocaleString() : '—'}
          </Typography>
          <Typography variant="body2">
            <strong>F. realización:</strong>{' '}
            {estudio.fecha_realizacion ? new Date(estudio.fecha_realizacion).toLocaleString() : '—'}
          </Typography>
        </Box>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6">Archivos asociados</Typography>
          {writeAccess && canAsociarArchivo(estudio) && (
            <Button size="small" startIcon={<LinkIcon />} onClick={openAsociarArchivo}>
              Asociar archivo existente
            </Button>
          )}
        </Stack>
        {archivos.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Sin archivos vinculados.
          </Typography>
        ) : (
          <List dense>
            {archivos.map((a) => (
              <ListItem key={a.id} divider>
                <ListItemText
                  primary={`Archivo médico #${a.archivo_medico_id} · ${a.tipo_rol}`}
                  secondary={a.descripcion || 'Sin descripción'}
                />
                {canDownloadArchivoEstudio(currentUser, estudio) && (
                  <ListItemSecondaryAction>
                    <Button
                      size="small"
                      startIcon={<Download />}
                      onClick={() => handleDownloadArchivo(a)}
                    >
                      Descargar
                    </Button>
                  </ListItemSecondaryAction>
                )}
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Informes
        </Typography>

        {writeAccess && canCrearInforme(estudio) && (
          <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <TextField
              size="small"
              label="Texto del informe (borrador)"
              value={informeTexto}
              onChange={(e) => setInformeTexto(e.target.value)}
              sx={{ flex: 1, minWidth: 240 }}
            />
            <Button
              variant="outlined"
              disabled={actionLoading}
              onClick={() =>
                runAction(async () => {
                  await crearInformeEstudio(estudio.id, { texto: informeTexto, tipo: 'FINAL' });
                  setInformeTexto('');
                }, 'No se pudo crear el informe.')
              }
            >
              Crear borrador
            </Button>
          </Box>
        )}

        {informes.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Sin informes registrados.
          </Typography>
        ) : (
          <List dense>
            {informes.map((inf) => (
              <ListItem key={inf.id} divider alignItems="flex-start">
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                      <Typography variant="body2" fontWeight={600}>
                        v{inf.version} · {inf.estado}
                      </Typography>
                      {inf.es_vigente && <Chip size="small" label="Vigente" color="success" />}
                    </Stack>
                  }
                  secondary={
                    <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                      {(inf.texto || '(sin texto)').slice(0, 500)}
                      {(inf.texto?.length || 0) > 500 ? '…' : ''}
                    </Typography>
                  }
                />
                <ListItemSecondaryAction sx={{ position: 'relative', transform: 'none', top: 0, right: 0 }}>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" justifyContent="flex-end">
                    {writeAccess && canEmitirInforme(estudio, inf) && (
                      <Button
                        size="small"
                        disabled={actionLoading}
                        onClick={() =>
                          runAction(async () => {
                            await emitirInformeEstudio(estudio.id, inf.id);
                          }, 'No se pudo emitir el informe.')
                        }
                      >
                        Emitir
                      </Button>
                    )}
                    {canValidarInformeUi(currentUser, estudio, inf) && (
                      <Button
                        size="small"
                        color="primary"
                        startIcon={<CheckCircle />}
                        disabled={actionLoading}
                        onClick={() =>
                          runAction(async () => {
                            await validarInformeEstudio(estudio.id, inf.id);
                          }, 'No se pudo validar el informe.')
                        }
                      >
                        Validar
                      </Button>
                    )}
                    {writeAccess && canRectificarInforme(estudio, inf) && (
                      <Button
                        size="small"
                        color="warning"
                        startIcon={<Undo />}
                        disabled={actionLoading}
                        onClick={() => {
                          setRectificarInformeId(inf.id);
                          setRectificarOpen(true);
                        }}
                      >
                        Rectificar
                      </Button>
                    )}
                  </Stack>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      <Dialog open={anularOpen} onClose={() => setAnularOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Anular estudio</DialogTitle>
        <DialogContent>
          <TextField
            label="Motivo de anulación *"
            value={motivoAnulacion}
            onChange={(e) => setMotivoAnulacion(e.target.value)}
            fullWidth
            multiline
            minRows={2}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAnularOpen(false)}>Cancelar</Button>
          <Button
            color="error"
            variant="contained"
            disabled={!motivoAnulacion.trim() || actionLoading}
            onClick={() =>
              runAction(async () => {
                await anularEstudio(estudio.id, motivoAnulacion.trim());
                setAnularOpen(false);
                setMotivoAnulacion('');
              }, 'No se pudo anular el estudio.')
            }
          >
            Confirmar anulación
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={rectificarOpen} onClose={() => setRectificarOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Rectificar informe</DialogTitle>
        <DialogContent>
          <TextField
            label="Motivo de rectificación *"
            value={motivoRectificacion}
            onChange={(e) => setMotivoRectificacion(e.target.value)}
            fullWidth
            multiline
            minRows={2}
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            label="Texto nueva versión"
            value={textoRectificacion}
            onChange={(e) => setTextoRectificacion(e.target.value)}
            fullWidth
            multiline
            minRows={4}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRectificarOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            disabled={!motivoRectificacion.trim() || !rectificarInformeId || actionLoading}
            onClick={() =>
              runAction(async () => {
                if (!rectificarInformeId) return;
                await rectificarInformeEstudio(estudio.id, rectificarInformeId, {
                  motivo_rectificacion: motivoRectificacion.trim(),
                  texto: textoRectificacion,
                });
                setRectificarOpen(false);
                setMotivoRectificacion('');
                setTextoRectificacion('');
              }, 'No se pudo rectificar el informe.')
            }
          >
            Crear rectificación
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={archivoOpen} onClose={() => setArchivoOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Asociar archivo médico existente</DialogTitle>
        <DialogContent>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
            Debe pertenecer al mismo paciente. Subida directa desde estudio: pendiente (C6.4.2 deuda).
          </Typography>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Archivo médico</InputLabel>
            <Select
              label="Archivo médico"
              value={archivoMedicoId}
              onChange={(e) => setArchivoMedicoId(e.target.value as number)}
            >
              {archivosPaciente.map((am) => (
                <MenuItem key={am.id} value={am.id}>
                  #{am.id} — {am.titulo || 'Sin título'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Rol en el estudio</InputLabel>
            <Select
              label="Rol en el estudio"
              value={archivoRol}
              onChange={(e) => setArchivoRol(e.target.value)}
            >
              {ARCHIVO_ROL_OPTIONS.map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setArchivoOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            disabled={!archivoMedicoId || actionLoading}
            onClick={handleAsociarArchivo}
          >
            Asociar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EstudioComplementarioDetalle;
