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
} from '@mui/material';
import toast from 'react-hot-toast';
import { apiService } from '../../services/api';
import { createMedico, getEspecialidades } from '../../services/apiService';
import { patchSolicitudExamenLims } from '../../services/limsApi';
import { useData } from '../../contexts/DataContext';
import type { Especialidad, Medico, Paciente } from '../../types';
import type { OrigenSolicitudLims, SolicitudExamenLims } from '../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { formatPacienteLabel } from '../../utils/pacienteFormat';
import { canCreateMedico, canCreatePaciente } from '../../utils/permissions';
import {
  ORIGEN_SOLICITUD_LIMS_OPTIONS,
  esOrigenAmbulatorioExterno,
} from '../../utils/limsOrigenSolicitud';

export interface EditarOrdenLimsDialogProps {
  open: boolean;
  orden: SolicitudExamenLims;
  onClose: () => void;
  onSaved: (orden: SolicitudExamenLims) => void;
}

const EditarOrdenLimsDialog: React.FC<EditarOrdenLimsDialogProps> = ({
  open,
  orden,
  onClose,
  onSaved,
}) => {
  const { currentUser } = useData();
  const puedeAltaPaciente = canCreatePaciente(currentUser);
  const puedeAltaMedico = canCreateMedico(currentUser);

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
  const [origen, setOrigen] = useState<OrigenSolicitudLims>(orden.origen_solicitud);
  const [fechaProgramada, setFechaProgramada] = useState(orden.fecha_programada_toma || '');
  const [fechaEntrega, setFechaEntrega] = useState(orden.fecha_entrega_prometida || '');
  const [observaciones, setObservaciones] = useState(orden.observaciones || '');

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
    setOrigen(orden.origen_solicitud);
    setFechaProgramada(orden.fecha_programada_toma || '');
    setFechaEntrega(orden.fecha_entrega_prometida || '');
    setObservaciones(orden.observaciones || '');
    setMedicoExterno(orden.medico_externo_nombre || '');
    const externo = Boolean(orden.medico_externo_nombre) && !orden.medico_interno;
    setMedicoExternoMode(externo || esOrigenAmbulatorioExterno(orden.origen_solicitud));

    if (orden.paciente) {
      void apiService
        .getPaciente(orden.paciente)
        .then((p) => {
          setPaciente(p);
          setPacienteQuery(formatPacienteLabel(p));
        })
        .catch(() => {
          setPaciente({ id: orden.paciente } as Paciente);
          setPacienteQuery(
            orden.paciente_nombre
              ? `${orden.paciente_nombre}${orden.paciente_dni ? ` · DNI ${orden.paciente_dni}` : ''}`
              : `Paciente #${orden.paciente}`
          );
        });
    } else {
      setPaciente(null);
      setPacienteQuery('');
    }

    if (orden.medico_interno) {
      void apiService
        .getMedico(orden.medico_interno)
        .then((m) => {
          setMedicoInterno(m);
          setMedicoQuery(`${m.apellido || ''} ${m.nombre || ''}`.trim());
        })
        .catch(() => {
          setMedicoInterno(null);
          setMedicoQuery(orden.medico_interno_nombre || '');
        });
    } else {
      setMedicoInterno(null);
      setMedicoQuery('');
    }
  }, [open, orden]);

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

  const handleSave = async () => {
    if (!paciente?.id) {
      setError('Seleccioná un paciente.');
      return;
    }
    if (!fechaProgramada) {
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
      const updated = await patchSolicitudExamenLims(orden.id, {
        paciente_id: paciente.id,
        medico_id: usarMedicoExterno ? null : medicoInterno?.id ?? null,
        medico_externo_nombre: usarMedicoExterno ? medicoExterno.trim() : '',
        origen_solicitud: origen,
        fecha_programada_toma: fechaProgramada,
        fecha_entrega_prometida: fechaEntrega || null,
        observaciones: observaciones.trim(),
      });
      toast.success('Orden actualizada.');
      onSaved(updated);
      onClose();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
        <DialogTitle>Editar orden {orden.numero || `#${orden.id}`}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <Alert severity="info" sx={{ py: 0.5 }}>
              Corregí datos de cabecera. Para ensayos usá Agregar/Quitar en la orden. No se puede
              editar si está finalizada.
            </Alert>
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
              <InputLabel id="edit-origen-label">Origen clínico</InputLabel>
              <Select
                labelId="edit-origen-label"
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
            <TextField
              size="small"
              type="date"
              label="Fecha extracción *"
              InputLabelProps={{ shrink: true }}
              value={fechaProgramada}
              onChange={(e) => setFechaProgramada(e.target.value)}
            />
            <TextField
              size="small"
              type="date"
              label="Fecha entrega prometida"
              InputLabelProps={{ shrink: true }}
              value={fechaEntrega}
              onChange={(e) => setFechaEntrega(e.target.value)}
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
          <Button disabled={saving} onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="contained" disabled={saving} onClick={() => void handleSave()}>
            {saving ? <CircularProgress size={20} color="inherit" /> : 'Guardar'}
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
              label="Apellido *"
              size="small"
              value={nuevoPacienteForm.apellido}
              onChange={(e) =>
                setNuevoPacienteForm((f) => ({ ...f, apellido: e.target.value }))
              }
            />
            <TextField
              label="Nombre *"
              size="small"
              value={nuevoPacienteForm.nombre}
              onChange={(e) =>
                setNuevoPacienteForm((f) => ({ ...f, nombre: e.target.value }))
              }
            />
            <TextField
              label="DNI *"
              size="small"
              value={nuevoPacienteForm.dni}
              onChange={(e) => setNuevoPacienteForm((f) => ({ ...f, dni: e.target.value }))}
            />
            <TextField
              label="Fecha de nacimiento *"
              size="small"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={nuevoPacienteForm.fecha_nacimiento}
              onChange={(e) =>
                setNuevoPacienteForm((f) => ({ ...f, fecha_nacimiento: e.target.value }))
              }
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button disabled={nuevoPacienteSaving} onClick={() => setOpenNuevoPaciente(false)}>
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
                  setPacienteOptions((prev) =>
                    prev.some((p) => p.id === created.id) ? prev : [created, ...prev]
                  );
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
              label="Apellido *"
              size="small"
              value={nuevoMedicoForm.apellido}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, apellido: e.target.value }))
              }
            />
            <TextField
              label="Nombre *"
              size="small"
              value={nuevoMedicoForm.nombre}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, nombre: e.target.value }))
              }
            />
            <TextField
              label="Matrícula *"
              size="small"
              value={nuevoMedicoForm.matricula}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, matricula: e.target.value }))
              }
            />
            <TextField
              select
              label="Especialidad"
              size="small"
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
          <Button disabled={nuevoMedicoSaving} onClick={() => setOpenNuevoMedico(false)}>
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
                  setMedicoOptions((prev) =>
                    prev.some((m) => m.id === created.id) ? prev : [created, ...prev]
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

export default EditarOrdenLimsDialog;
