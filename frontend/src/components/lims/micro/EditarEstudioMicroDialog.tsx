import React, { useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import { apiService } from '../../../services/api';
import { createMedico, getEspecialidades } from '../../../services/apiService';
import {
  listTiposCultivoMicro,
  listTiposMuestraMicro,
  updateEstudioMicrobiologia,
} from '../../../services/limsMicroApi';
import { useData } from '../../../contexts/DataContext';
import type { Especialidad, Medico, Paciente } from '../../../types';
import type {
  EstudioMicrobiologia,
  OrigenSolicitudLims,
  TipoCultivoMicrobiologia,
  TipoMuestraMicrobiologia,
} from '../../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import { formatPacienteLabel } from '../../../utils/pacienteFormat';
import { canCreateMedico, canCreatePaciente } from '../../../utils/permissions';
import {
  ORIGEN_SOLICITUD_LIMS_OPTIONS,
  esOrigenAmbulatorioExterno,
} from '../../../utils/limsOrigenSolicitud';
import { sugerirMuestraPorCultivo } from '../../../utils/limsMicroUx';

export interface EditarEstudioMicroDialogProps {
  open: boolean;
  estudio: EstudioMicrobiologia;
  onClose: () => void;
  onSaved: (estudio: EstudioMicrobiologia) => void;
}

const EditarEstudioMicroDialog: React.FC<EditarEstudioMicroDialogProps> = ({
  open,
  estudio,
  onClose,
  onSaved,
}) => {
  const { currentUser } = useData();
  const puedeAltaPaciente = canCreatePaciente(currentUser);
  const puedeAltaMedico = canCreateMedico(currentUser);
  const fechaEditable = estudio.estado === 'PENDIENTE';

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [paciente, setPaciente] = useState<Paciente | null>(null);
  const [pacienteQuery, setPacienteQuery] = useState('');
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [searchingPaciente, setSearchingPaciente] = useState(false);
  const [medicoInterno, setMedicoInterno] = useState<Medico | null>(null);
  const [medicoQuery, setMedicoQuery] = useState('');
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [searchingMedico, setSearchingMedico] = useState(false);
  const [medicoExternoMode, setMedicoExternoMode] = useState(false);
  const [medicoExterno, setMedicoExterno] = useState('');
  const [origen, setOrigen] = useState<OrigenSolicitudLims>(
    (estudio.origen_solicitud as OrigenSolicitudLims) || 'AMBULATORIO_CEHTA'
  );
  const [fechaProgramada, setFechaProgramada] = useState(estudio.fecha_programada_toma || '');
  const [observaciones, setObservaciones] = useState(estudio.observaciones || '');
  const [tiposCultivo, setTiposCultivo] = useState<TipoCultivoMicrobiologia[]>([]);
  const [tiposMuestra, setTiposMuestra] = useState<TipoMuestraMicrobiologia[]>([]);
  const [tipoCultivoId, setTipoCultivoId] = useState<number | ''>('');
  const [tipoMuestraId, setTipoMuestraId] = useState<number | ''>('');
  const [loadingCatalogos, setLoadingCatalogos] = useState(false);

  const [openNuevoPaciente, setOpenNuevoPaciente] = useState(false);
  const [nuevoPacienteSaving, setNuevoPacienteSaving] = useState(false);
  const [nuevoPacienteError, setNuevoPacienteError] = useState('');
  const [nuevoPacienteForm, setNuevoPacienteForm] = useState({
    apellido: '',
    nombre: '',
    dni: '',
    fecha_nacimiento: '',
  });

  const [openNuevoMedico, setOpenNuevoMedico] = useState(false);
  const [nuevoMedicoSaving, setNuevoMedicoSaving] = useState(false);
  const [nuevoMedicoError, setNuevoMedicoError] = useState('');
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [nuevoMedicoForm, setNuevoMedicoForm] = useState({
    apellido: '',
    nombre: '',
    matricula: '',
    especialidad_id: '',
  });

  const usarMedicoExterno = medicoExternoMode || esOrigenAmbulatorioExterno(origen);

  useEffect(() => {
    if (!open) return;
    setError('');
    setOrigen((estudio.origen_solicitud as OrigenSolicitudLims) || 'AMBULATORIO_CEHTA');
    setFechaProgramada(estudio.fecha_programada_toma || '');
    setObservaciones(estudio.observaciones || '');
    setMedicoExterno(estudio.medico_externo_nombre || '');
    const externo = Boolean(estudio.medico_externo_nombre) && !estudio.medico_interno;
    setMedicoExternoMode(externo || esOrigenAmbulatorioExterno(estudio.origen_solicitud || ''));
    setTipoCultivoId(estudio.tipo_cultivo ?? '');
    setTipoMuestraId(estudio.tipo_muestra_micro ?? '');

    setLoadingCatalogos(true);
    void Promise.all([listTiposCultivoMicro(), listTiposMuestraMicro()])
      .then(([cultivos, muestras]) => {
        setTiposCultivo(cultivos);
        setTiposMuestra(muestras);
      })
      .catch(() => {
        setTiposCultivo([]);
        setTiposMuestra([]);
      })
      .finally(() => setLoadingCatalogos(false));

    if (estudio.paciente) {
      void apiService
        .getPaciente(estudio.paciente)
        .then((p) => {
          setPaciente(p);
          setPacienteQuery(formatPacienteLabel(p));
        })
        .catch(() => {
          setPaciente({ id: estudio.paciente } as Paciente);
          setPacienteQuery(
            estudio.paciente_nombre
              ? `${estudio.paciente_nombre}${estudio.paciente_dni ? ` · DNI ${estudio.paciente_dni}` : ''}`
              : `Paciente #${estudio.paciente}`
          );
        });
    } else {
      setPaciente(null);
      setPacienteQuery('');
    }

    if (estudio.medico_interno) {
      void apiService
        .getMedico(estudio.medico_interno)
        .then((m) => {
          setMedicoInterno(m);
          setMedicoQuery(`${m.apellido || ''} ${m.nombre || ''}`.trim());
        })
        .catch(() => {
          setMedicoInterno(null);
          setMedicoQuery(estudio.medico_display || '');
        });
    } else {
      setMedicoInterno(null);
      setMedicoQuery('');
    }
  }, [open, estudio]);

  useEffect(() => {
    if (!open) return;
    const q = pacienteQuery.trim();
    if (q.length < 2) {
      setPacienteOptions([]);
      return;
    }
    const tmr = window.setTimeout(() => {
      setSearchingPaciente(true);
      void apiService
        .buscarPacientes(q)
        .then(setPacienteOptions)
        .catch(() => setPacienteOptions([]))
        .finally(() => setSearchingPaciente(false));
    }, 250);
    return () => window.clearTimeout(tmr);
  }, [pacienteQuery, open]);

  useEffect(() => {
    if (!open || usarMedicoExterno) return;
    const q = medicoQuery.trim();
    if (q.length < 2) {
      setMedicoOptions([]);
      return;
    }
    const tmr = window.setTimeout(() => {
      setSearchingMedico(true);
      void apiService
        .buscarMedicos(q)
        .then(setMedicoOptions)
        .catch(() => setMedicoOptions([]))
        .finally(() => setSearchingMedico(false));
    }, 250);
    return () => window.clearTimeout(tmr);
  }, [medicoQuery, open, usarMedicoExterno]);

  const handleCultivoChange = (nextId: number | '') => {
    setTipoCultivoId(nextId);
    if (!nextId || !tiposCultivo.length || !tiposMuestra.length) return;
    const cultivo = tiposCultivo.find((c) => c.id === nextId);
    if (!cultivo) return;
    const sugerida = sugerirMuestraPorCultivo(cultivo.codigo, tiposMuestra);
    if (sugerida) setTipoMuestraId(sugerida.id);
  };

  const handleSave = async () => {
    if (!paciente?.id) {
      setError('Seleccioná un paciente.');
      return;
    }
    if (!tipoCultivoId) {
      setError('Seleccioná el tipo de cultivo.');
      return;
    }
    if (!tipoMuestraId) {
      setError('Seleccioná el tipo de muestra.');
      return;
    }
    if (fechaEditable && !fechaProgramada) {
      setError('Indicá el día de la extracción.');
      return;
    }
    if (usarMedicoExterno && !medicoExterno.trim()) {
      setError('Indicá el médico solicitante externo.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const body: Parameters<typeof updateEstudioMicrobiologia>[1] = {
        paciente_id: paciente.id,
        medico_id: usarMedicoExterno ? null : medicoInterno?.id ?? null,
        medico_externo_nombre: usarMedicoExterno ? medicoExterno.trim() : '',
        origen_solicitud: origen,
        tipo_cultivo_id: Number(tipoCultivoId),
        tipo_muestra_micro_id: Number(tipoMuestraId),
        observaciones: observaciones.trim(),
      };
      if (fechaEditable && fechaProgramada) {
        body.fecha_programada_toma = fechaProgramada;
      }
      const updated = await updateEstudioMicrobiologia(estudio.id, body);
      toast.success('Pedido actualizado.');
      onSaved(updated);
      onClose();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarEstudioMicro));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
        <DialogTitle>Editar pedido {estudio.numero || `#${estudio.id}`}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <Alert severity="info" sx={{ py: 0.5 }}>
              Corregí datos del pedido. No se puede editar si el estudio está validado o informado
              (reabrí primero).
            </Alert>
            {loadingCatalogos && (
              <Stack direction="row" spacing={1} alignItems="center">
                <CircularProgress size={18} />
                <Typography variant="body2" color="text.secondary">
                  Cargando catálogos…
                </Typography>
              </Stack>
            )}
            <Stack spacing={1}>
              <Autocomplete
                options={pacienteOptions}
                value={paciente}
                onChange={(_e, value) => setPaciente(value)}
                inputValue={pacienteQuery}
                onInputChange={(_e, value) => setPacienteQuery(value)}
                getOptionLabel={(p) => formatPacienteLabel(p)}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                loading={searchingPaciente}
                renderInput={(params) => (
                  <TextField {...params} label="Paciente *" size="small" />
                )}
              />
              {puedeAltaPaciente && (
                <Button
                  size="small"
                  variant="outlined"
                  sx={{ alignSelf: 'flex-start' }}
                  onClick={() => {
                    setNuevoPacienteError('');
                    setNuevoPacienteForm({
                      apellido: '',
                      nombre: '',
                      dni: '',
                      fecha_nacimiento: '',
                    });
                    setOpenNuevoPaciente(true);
                  }}
                >
                  Nuevo paciente
                </Button>
              )}
            </Stack>
            <FormControl fullWidth size="small">
              <InputLabel id="edit-micro-origen-label">Origen clínico</InputLabel>
              <Select
                labelId="edit-micro-origen-label"
                label="Origen clínico"
                value={origen}
                onChange={(e) => {
                  const next = e.target.value as OrigenSolicitudLims;
                  setOrigen(next);
                  if (esOrigenAmbulatorioExterno(next)) {
                    setMedicoExternoMode(true);
                    setMedicoInterno(null);
                  }
                }}
              >
                {ORIGEN_SOLICITUD_LIMS_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {!esOrigenAmbulatorioExterno(origen) && (
              <Button
                size="small"
                onClick={() => {
                  setMedicoExternoMode((v) => !v);
                  setMedicoInterno(null);
                  setMedicoExterno('');
                }}
                sx={{ alignSelf: 'flex-start' }}
              >
                {medicoExternoMode
                  ? 'Usar médico interno del sistema'
                  : 'Médico externo (texto libre)'}
              </Button>
            )}
            {usarMedicoExterno ? (
              <TextField
                size="small"
                fullWidth
                label="Médico externo *"
                value={medicoExterno}
                onChange={(e) => setMedicoExterno(e.target.value)}
              />
            ) : (
              <Stack spacing={1}>
                <Autocomplete
                  options={medicoOptions}
                  value={medicoInterno}
                  onChange={(_e, value) => setMedicoInterno(value)}
                  inputValue={medicoQuery}
                  onInputChange={(_e, value) => setMedicoQuery(value)}
                  getOptionLabel={(m) =>
                    `Dr. ${[m.apellido, m.nombre].filter(Boolean).join(', ')}${
                      m.matricula ? ` — MP ${m.matricula}` : ''
                    }`
                  }
                  isOptionEqualToValue={(a, b) => a.id === b.id}
                  loading={searchingMedico}
                  renderInput={(params) => (
                    <TextField {...params} label="Médico solicitante" size="small" />
                  )}
                />
                {puedeAltaMedico && (
                  <Button
                    size="small"
                    variant="outlined"
                    sx={{ alignSelf: 'flex-start' }}
                    onClick={() => {
                      setNuevoMedicoError('');
                      setNuevoMedicoForm({
                        nombre: '',
                        apellido: '',
                        matricula: '',
                        especialidad_id: '',
                      });
                      setOpenNuevoMedico(true);
                      void getEspecialidades()
                        .then(setEspecialidades)
                        .catch(() => setEspecialidades([]));
                    }}
                  >
                    Nuevo médico
                  </Button>
                )}
              </Stack>
            )}
            <FormControl fullWidth size="small">
              <InputLabel id="edit-micro-cultivo-label">Tipo de cultivo *</InputLabel>
              <Select
                labelId="edit-micro-cultivo-label"
                label="Tipo de cultivo *"
                value={tipoCultivoId === '' ? '' : String(tipoCultivoId)}
                onChange={(e) => {
                  const v = e.target.value;
                  handleCultivoChange(v === '' ? '' : Number(v));
                }}
              >
                {tiposCultivo.map((c) => (
                  <MenuItem key={c.id} value={String(c.id)}>
                    {c.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel id="edit-micro-muestra-label">Tipo de muestra *</InputLabel>
              <Select
                labelId="edit-micro-muestra-label"
                label="Tipo de muestra *"
                value={tipoMuestraId === '' ? '' : String(tipoMuestraId)}
                onChange={(e) => {
                  const v = e.target.value;
                  setTipoMuestraId(v === '' ? '' : Number(v));
                }}
              >
                {tiposMuestra.map((m) => (
                  <MenuItem key={m.id} value={String(m.id)}>
                    {m.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              type="date"
              label="Fecha extracción *"
              InputLabelProps={{ shrink: true }}
              value={fechaProgramada}
              disabled={!fechaEditable}
              helperText={
                fechaEditable
                  ? undefined
                  : 'La fecha solo se puede cambiar mientras el pedido está pendiente.'
              }
              onChange={(e) => setFechaProgramada(e.target.value)}
            />
            <TextField
              size="small"
              fullWidth
              multiline
              minRows={2}
              label="Observaciones"
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving || loadingCatalogos}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={openNuevoPaciente}
        onClose={nuevoPacienteSaving ? undefined : () => setOpenNuevoPaciente(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Nuevo paciente</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {nuevoPacienteError && <Alert severity="error">{nuevoPacienteError}</Alert>}
            <TextField
              size="small"
              label="Apellido *"
              value={nuevoPacienteForm.apellido}
              onChange={(e) => setNuevoPacienteForm((f) => ({ ...f, apellido: e.target.value }))}
            />
            <TextField
              size="small"
              label="Nombre *"
              value={nuevoPacienteForm.nombre}
              onChange={(e) => setNuevoPacienteForm((f) => ({ ...f, nombre: e.target.value }))}
            />
            <TextField
              size="small"
              label="DNI *"
              value={nuevoPacienteForm.dni}
              onChange={(e) => setNuevoPacienteForm((f) => ({ ...f, dni: e.target.value }))}
            />
            <TextField
              size="small"
              type="date"
              label="Fecha de nacimiento *"
              InputLabelProps={{ shrink: true }}
              value={nuevoPacienteForm.fecha_nacimiento}
              onChange={(e) =>
                setNuevoPacienteForm((f) => ({ ...f, fecha_nacimiento: e.target.value }))
              }
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenNuevoPaciente(false)} disabled={nuevoPacienteSaving}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            disabled={nuevoPacienteSaving}
            onClick={() => {
              void (async () => {
                const apellido = nuevoPacienteForm.apellido.trim();
                const nombre = nuevoPacienteForm.nombre.trim();
                const dni = nuevoPacienteForm.dni.trim();
                const fecha_nacimiento = nuevoPacienteForm.fecha_nacimiento;
                if (!apellido || !nombre || !dni || !fecha_nacimiento) {
                  setNuevoPacienteError('Completá apellido, nombre, DNI y fecha de nacimiento.');
                  return;
                }
                setNuevoPacienteSaving(true);
                setNuevoPacienteError('');
                try {
                  const created = await apiService.createPaciente({
                    apellido,
                    nombre,
                    dni,
                    fecha_nacimiento,
                  });
                  setPaciente(created);
                  setPacienteQuery(formatPacienteLabel(created));
                  setOpenNuevoPaciente(false);
                  toast.success('Paciente dado de alta.');
                } catch (e) {
                  setNuevoPacienteError(
                    getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.genericClinicalAction)
                  );
                } finally {
                  setNuevoPacienteSaving(false);
                }
              })();
            }}
          >
            {nuevoPacienteSaving ? <CircularProgress size={20} color="inherit" /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={openNuevoMedico}
        onClose={nuevoMedicoSaving ? undefined : () => setOpenNuevoMedico(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Nuevo médico</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {nuevoMedicoError && <Alert severity="error">{nuevoMedicoError}</Alert>}
            <TextField
              size="small"
              label="Apellido *"
              value={nuevoMedicoForm.apellido}
              onChange={(e) => setNuevoMedicoForm((f) => ({ ...f, apellido: e.target.value }))}
            />
            <TextField
              size="small"
              label="Nombre *"
              value={nuevoMedicoForm.nombre}
              onChange={(e) => setNuevoMedicoForm((f) => ({ ...f, nombre: e.target.value }))}
            />
            <TextField
              size="small"
              label="Matrícula *"
              value={nuevoMedicoForm.matricula}
              onChange={(e) => setNuevoMedicoForm((f) => ({ ...f, matricula: e.target.value }))}
            />
            <TextField
              select
              size="small"
              label="Especialidad"
              value={nuevoMedicoForm.especialidad_id}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, especialidad_id: e.target.value }))
              }
            >
              <MenuItem value="">Sin especialidad</MenuItem>
              {especialidades.map((esp) => (
                <MenuItem key={esp.id} value={String(esp.id)}>
                  {esp.nombre}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenNuevoMedico(false)} disabled={nuevoMedicoSaving}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            disabled={nuevoMedicoSaving}
            onClick={() => {
              void (async () => {
                const nombre = nuevoMedicoForm.nombre.trim();
                const apellido = nuevoMedicoForm.apellido.trim();
                const matricula = nuevoMedicoForm.matricula.trim();
                if (!nombre || !apellido || !matricula) {
                  setNuevoMedicoError('Completá nombre, apellido y matrícula.');
                  return;
                }
                setNuevoMedicoSaving(true);
                setNuevoMedicoError('');
                try {
                  const created = await createMedico({
                    nombre,
                    apellido,
                    matricula,
                    especialidad_id: nuevoMedicoForm.especialidad_id
                      ? Number(nuevoMedicoForm.especialidad_id)
                      : undefined,
                  } as Partial<Medico>);
                  setMedicoInterno(created);
                  setMedicoQuery(
                    `Dr. ${[created.apellido, created.nombre].filter(Boolean).join(', ')}`
                  );
                  setOpenNuevoMedico(false);
                  toast.success('Médico dado de alta.');
                } catch (e) {
                  setNuevoMedicoError(
                    getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.genericClinicalAction)
                  );
                } finally {
                  setNuevoMedicoSaving(false);
                }
              })();
            }}
          >
            {nuevoMedicoSaving ? <CircularProgress size={20} color="inherit" /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default EditarEstudioMicroDialog;
