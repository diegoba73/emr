import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
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
import toast from 'react-hot-toast';
import { useData } from '../../../contexts/DataContext';
import { useAtencionQuery } from '../../atenciones/hooks';
import ConsultaPedidosPanel from '../../atenciones/components/ConsultaPedidosPanel';
import {
  clearGuardiaPendingDraft,
  countGuardiaPendingDraftItems,
  flushConsultaPedidosDrafts,
  migrateGuardiaPendingDraftToConsulta,
} from '../../atenciones/consultaPedidosDraft';
import { apiService } from '../../../services/api';
import { imprimirPedidosPapel } from '../../../services/limsApi';
import type { Medico, Paciente } from '../../../types';
import { formatPacienteLabel } from '../../../utils/pacienteFormat';
import { normalizeRol } from '../../../utils/permissions';

export type GuardiaDialogMode = 'create' | 'edit' | 'view';

interface GuardiaAtencionDialogProps {
  open: boolean;
  mode: GuardiaDialogMode;
  atencionId?: number | null;
  onClose: () => void;
  onSaved: () => void;
}

const GuardiaAtencionDialog: React.FC<GuardiaAtencionDialogProps> = ({
  open,
  mode,
  atencionId,
  onClose,
  onSaved,
}) => {
  const { currentUser } = useData();
  const isReadOnly = mode === 'view';
  const isCreate = mode === 'create';

  const { data: atencion, isLoading: loadingAtencion } = useAtencionQuery(
    !isCreate && atencionId ? atencionId : null
  );

  const [selectedPaciente, setSelectedPaciente] = useState<Paciente | null>(null);
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [pacienteInputValue, setPacienteInputValue] = useState('');
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  const pacienteInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const [selectedMedico, setSelectedMedico] = useState<Medico | null>(null);
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [medicoInputValue, setMedicoInputValue] = useState('');
  const [searchingMedicos, setSearchingMedicos] = useState(false);
  const medicoInputReason = useRef<'input' | 'selection' | 'clear'>('input');
  const [motivoConsulta, setMotivoConsulta] = useState('');
  const [consultaHcId, setConsultaHcId] = useState<number | null>(null);
  const [preparingHc, setPreparingHc] = useState(false);
  const [saving, setSaving] = useState(false);

  const canEditPedidos = !isReadOnly;
  const medicoFromUser =
    currentUser?.medico && typeof currentUser.medico === 'object'
      ? (currentUser.medico as Medico)
      : null;
  const medicoFromUserId = medicoFromUser?.id ?? null;
  const needsMedicoPicker = !medicoFromUserId && normalizeRol(currentUser) !== 'medico';

  useEffect(() => {
    if (!open) return;
    if (isCreate) {
      clearGuardiaPendingDraft();
      setSelectedPaciente(null);
      setPacienteInputValue('');
      setMotivoConsulta('');
      setConsultaHcId(null);
      if (medicoFromUserId && medicoFromUser) {
        setSelectedMedico(medicoFromUser);
        setMedicoInputValue(
          `Dr. ${[medicoFromUser.apellido, medicoFromUser.nombre].filter(Boolean).join(', ')}`
        );
      } else {
        setSelectedMedico(null);
        setMedicoInputValue('');
      }
      return;
    }
    if (!atencion) return;
    setSelectedPaciente(atencion.paciente ?? null);
    setPacienteInputValue(atencion.paciente ? formatPacienteLabel(atencion.paciente) : '');
    setMotivoConsulta(atencion.observaciones_generales ?? '');
    setConsultaHcId(atencion.consulta_hc_id ?? null);
    const med = atencion.medico_principal;
    if (med && typeof med === 'object') {
      setSelectedMedico(med);
      setMedicoInputValue(`Dr. ${[med.apellido, med.nombre].filter(Boolean).join(', ')}`);
    } else if (medicoFromUserId && medicoFromUser) {
      setSelectedMedico(medicoFromUser);
      setMedicoInputValue(
        `Dr. ${[medicoFromUser.apellido, medicoFromUser.nombre].filter(Boolean).join(', ')}`
      );
    }
  }, [open, isCreate, atencion, medicoFromUserId, medicoFromUser]);

  useEffect(() => {
    if (!open || isCreate || !atencionId || consultaHcId) return;
    let cancelled = false;
    setPreparingHc(true);
    void (async () => {
      try {
        const hcId =
          atencion?.consulta_hc_id ?? (await apiService.ensureConsultaHc(atencionId));
        if (!cancelled) setConsultaHcId(hcId);
      } catch (err: unknown) {
        if (!cancelled) {
          const ax = err as { response?: { data?: { error?: string } } };
          toast.error(ax.response?.data?.error ?? 'No se pudo cargar los pedidos.');
        }
      } finally {
        if (!cancelled) setPreparingHc(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, isCreate, atencionId, consultaHcId, atencion?.consulta_hc_id]);

  useEffect(() => {
    if (!open || isReadOnly) return;
    if (pacienteInputReason.current !== 'input') {
      pacienteInputReason.current = 'input';
      return;
    }
    const query = pacienteInputValue.trim();
    if (query.length < 2) {
      setPacienteOptions([]);
      return;
    }
    const timeoutId = setTimeout(async () => {
      setSearchingPacientes(true);
      try {
        const results = await apiService.buscarPacientes(query);
        setPacienteOptions(results);
      } catch {
        setPacienteOptions([]);
      } finally {
        setSearchingPacientes(false);
      }
    }, 250);
    return () => clearTimeout(timeoutId);
  }, [pacienteInputValue, open, isReadOnly]);

  useEffect(() => {
    if (!open || isReadOnly || !needsMedicoPicker || !isCreate) return;
    if (medicoInputReason.current !== 'input') {
      medicoInputReason.current = 'input';
      return;
    }
    const query = medicoInputValue.trim();
    if (query.length < 2) {
      setMedicoOptions([]);
      return;
    }
    const timeoutId = setTimeout(async () => {
      setSearchingMedicos(true);
      try {
        const results = await apiService.buscarMedicos(query);
        setMedicoOptions(results);
      } catch {
        setMedicoOptions([]);
      } finally {
        setSearchingMedicos(false);
      }
    }, 250);
    return () => clearTimeout(timeoutId);
  }, [medicoInputValue, open, isReadOnly, needsMedicoPicker, isCreate]);

  const resolveMedicoId = (): number | undefined => {
    if (selectedMedico?.id) return selectedMedico.id;
    const fromUser =
      currentUser?.medico?.id ??
      (typeof currentUser?.medico === 'number' ? currentUser.medico : undefined);
    return fromUser;
  };

  const persistAtencion = async (): Promise<number> => {
    const medicoId = resolveMedicoId();
    if (!medicoId) {
      throw new Error(
        needsMedicoPicker
          ? 'Seleccioná el médico de guardia.'
          : 'Tu usuario no tiene un médico asociado.'
      );
    }

    let targetAtencionId = atencionId ?? null;
    const pacienteId = selectedPaciente?.id ?? atencion?.paciente?.id;

    if (!pacienteId) {
      throw new Error('Seleccioná un paciente.');
    }

    if (isCreate) {
      if (countGuardiaPendingDraftItems() === 0) {
        throw new Error('Agregá al menos un pedido de laboratorio o estudio complementario.');
      }
      const created = await apiService.iniciarAtencionGuardia({
        paciente_id: pacienteId,
        medico_id: medicoId,
        motivo_consulta: motivoConsulta.trim(),
        observaciones_generales: motivoConsulta.trim() || undefined,
      });
      targetAtencionId = created.id;
    } else if (motivoConsulta.trim() !== (atencion?.observaciones_generales ?? '')) {
      await apiService.updateAtencion(targetAtencionId!, {
        observaciones_generales: motivoConsulta.trim() || null,
      });
    }

    const hcId = await apiService.ensureConsultaHc(targetAtencionId!);
    setConsultaHcId(hcId);

    if (isCreate) {
      migrateGuardiaPendingDraftToConsulta(hcId);
    }

    await flushConsultaPedidosDrafts({
      consultaHcId: hcId,
      pacienteId,
      medicoId,
      origenSolicitud: 'GUARDIA',
    }).then(async ({ pedidosPapel }) => {
      if (pedidosPapel.length === 0) return;
      try {
        await imprimirPedidosPapel(pedidosPapel);
      } catch {
        toast.error(
          'Pedidos guardados, pero no se pudo abrir la impresión del pedido para firmar.'
        );
      }
    });

    // La atención queda ABIERTA: pedidos LIMS/estudios siguen su ciclo;
    // el cierre clínico es explícito (botón «Cerrar atención»).
    return targetAtencionId!;
  };

  const handleGuardar = async () => {
    setSaving(true);
    try {
      await persistAtencion();
      toast.success('Atención de guardia guardada (sigue abierta).');
      onSaved();
      onClose();
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { error?: string; detail?: string } } };
      const message =
        ax.response?.data?.error ||
        ax.response?.data?.detail ||
        (err instanceof Error ? err.message : 'No se pudo guardar la atención.');
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const handleCerrarAtencion = async () => {
    if (
      !window.confirm(
        '¿Cerrar esta atención de guardia? Podés seguir viendo los pedidos, pero no se podrán editar desde aquí.'
      )
    ) {
      return;
    }
    setSaving(true);
    try {
      let id = atencionId ?? null;
      if (isCreate || !id) {
        id = await persistAtencion();
      } else {
        // Persistir motivo/pedidos pendientes antes de cerrar
        await persistAtencion();
      }
      await apiService.closeAtencion(id!);
      toast.success('Atención de guardia cerrada.');
      onSaved();
      onClose();
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { error?: string; detail?: string } } };
      const message =
        ax.response?.data?.error ||
        ax.response?.data?.detail ||
        (err instanceof Error ? err.message : 'No se pudo cerrar la atención.');
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const title =
    mode === 'create'
      ? 'Nueva atención de guardia'
      : mode === 'edit'
        ? 'Continuar atención de guardia'
        : 'Detalle de guardia';

  const showPedidosEditor = canEditPedidos && (isCreate || consultaHcId);
  const showPedidosReadOnly = isReadOnly && consultaHcId;

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {loadingAtencion && !isCreate ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {!isReadOnly && (
              <Alert severity="info" variant="outlined">
                Al guardar, la atención queda <strong>abierta</strong>: podés seguir agregando
                pedidos y derivar a internación cuando haga falta. Los análisis y estudios se
                completan en sus módulos; cerrá la atención solo cuando el episodio de guardia
                termine.
              </Alert>
            )}

            <Autocomplete
              options={pacienteOptions}
              loading={searchingPacientes}
              disabled={!isCreate || isReadOnly}
              getOptionLabel={(option) => formatPacienteLabel(option)}
              value={selectedPaciente}
              inputValue={pacienteInputValue}
              onChange={(_, value) => {
                setSelectedPaciente(value);
                pacienteInputReason.current = 'selection';
                setPacienteInputValue(value ? formatPacienteLabel(value) : '');
              }}
              onInputChange={(_, newValue, reason) => {
                if (reason === 'input') {
                  pacienteInputReason.current = 'input';
                  setPacienteInputValue(newValue);
                } else if (reason === 'clear') {
                  pacienteInputReason.current = 'clear';
                  setPacienteInputValue('');
                  setSelectedPaciente(null);
                }
              }}
              filterOptions={(x) => x}
              noOptionsText={
                pacienteInputValue.trim().length < 2
                  ? 'Escribí al menos 2 caracteres (DNI o apellido)'
                  : 'Sin coincidencias'
              }
              renderInput={(params) => (
                <TextField {...params} label="Paciente *" required={isCreate} />
              )}
            />

            {needsMedicoPicker && (
              <Autocomplete
                options={medicoOptions}
                loading={searchingMedicos}
                disabled={!isCreate || isReadOnly}
                getOptionLabel={(m) =>
                  `Dr. ${[m.apellido, m.nombre].filter(Boolean).join(', ')}${
                    m.matricula ? ` — MP ${m.matricula}` : ''
                  }`
                }
                isOptionEqualToValue={(a, b) => a.id === b.id}
                value={selectedMedico}
                inputValue={medicoInputValue}
                onChange={(_, value) => {
                  setSelectedMedico(value);
                  medicoInputReason.current = 'selection';
                  setMedicoInputValue(
                    value
                      ? `Dr. ${[value.apellido, value.nombre].filter(Boolean).join(', ')}`
                      : ''
                  );
                }}
                onInputChange={(_, newValue, reason) => {
                  if (reason === 'input') {
                    medicoInputReason.current = 'input';
                    setMedicoInputValue(newValue);
                  } else if (reason === 'clear') {
                    medicoInputReason.current = 'clear';
                    setMedicoInputValue('');
                    setSelectedMedico(null);
                  }
                }}
                filterOptions={(x) => x}
                noOptionsText={
                  medicoInputValue.trim().length < 2
                    ? 'Escribí al menos 2 caracteres (apellido o matrícula)'
                    : 'Sin coincidencias'
                }
                renderInput={(params) => (
                  <TextField {...params} label="Médico de guardia *" required={isCreate} />
                )}
              />
            )}

            <TextField
              label="Motivo de consulta / triage"
              multiline
              minRows={2}
              value={motivoConsulta}
              onChange={(e) => setMotivoConsulta(e.target.value)}
              fullWidth
              disabled={isReadOnly}
            />

            <Divider />

            <Typography variant="subtitle2" fontWeight={600}>
              Pedidos clínicos
            </Typography>

            {preparingHc && !isCreate && (
              <Box display="flex" alignItems="center" gap={1}>
                <CircularProgress size={18} />
                <Typography variant="body2" color="text.secondary">
                  Preparando pedidos…
                </Typography>
              </Box>
            )}

            {showPedidosEditor && isCreate && (
              <ConsultaPedidosPanel canEdit variant="compact" usePendingDraft />
            )}

            {showPedidosEditor && !isCreate && consultaHcId && (
              <ConsultaPedidosPanel consultaHcId={consultaHcId} canEdit variant="compact" />
            )}

            {showPedidosReadOnly && consultaHcId && (
              <ConsultaPedidosPanel consultaHcId={consultaHcId} canEdit={false} variant="full" />
            )}
          </Stack>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Button onClick={onClose} disabled={saving}>
          {isReadOnly ? 'Cerrar' : 'Cancelar'}
        </Button>
        {!isReadOnly && (
          <>
            <Button
              variant="outlined"
              color="inherit"
              onClick={handleCerrarAtencion}
              disabled={
                saving ||
                (isCreate && (!selectedPaciente || (needsMedicoPicker && !selectedMedico)))
              }
            >
              Cerrar atención
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={handleGuardar}
              disabled={
                saving ||
                (isCreate && (!selectedPaciente || (needsMedicoPicker && !selectedMedico)))
              }
            >
              {saving ? <CircularProgress size={22} color="inherit" /> : 'Guardar atención'}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default GuardiaAtencionDialog;
