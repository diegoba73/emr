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
import { TransferWithinAStation } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
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
import { Paciente } from '../../../types';
import { formatPacienteLabel } from '../../../utils/pacienteFormat';

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
  const navigate = useNavigate();
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
  const [motivoConsulta, setMotivoConsulta] = useState('');
  const [consultaHcId, setConsultaHcId] = useState<number | null>(null);
  const [preparingHc, setPreparingHc] = useState(false);
  const [saving, setSaving] = useState(false);

  const canEditPedidos = !isReadOnly;

  useEffect(() => {
    if (!open) return;
    if (isCreate) {
      clearGuardiaPendingDraft();
      setSelectedPaciente(null);
      setPacienteInputValue('');
      setMotivoConsulta('');
      setConsultaHcId(null);
      return;
    }
    if (!atencion) return;
    setSelectedPaciente(atencion.paciente ?? null);
    setPacienteInputValue(atencion.paciente ? formatPacienteLabel(atencion.paciente) : '');
    setMotivoConsulta(atencion.observaciones_generales ?? '');
    setConsultaHcId(atencion.consulta_hc_id ?? null);
  }, [open, isCreate, atencion]);

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

  const resolveMedicoId = (): number | undefined => {
    const fromUser =
      currentUser?.medico?.id ??
      (typeof currentUser?.medico === 'number' ? currentUser.medico : undefined);
    return fromUser;
  };

  const persistAtencion = async (): Promise<number> => {
    const medicoId = resolveMedicoId();
    if (!medicoId) {
      throw new Error('Tu usuario no tiene un médico asociado.');
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
    });

    await apiService.closeAtencion(targetAtencionId!);
    return targetAtencionId!;
  };

  const handleGuardar = async () => {
    setSaving(true);
    try {
      await persistAtencion();
      toast.success('Atención de guardia registrada.');
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

  const handleDerivarInternacion = async () => {
    setSaving(true);
    try {
      const savedId = await persistAtencion();
      const pacienteId = selectedPaciente?.id ?? atencion?.paciente?.id;
      onSaved();
      onClose();
      navigate('/internacion', {
        state: {
          derivarDesdeAtencionId: savedId,
          pacienteId,
          motivoIngreso: motivoConsulta.trim(),
        },
      });
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { error?: string; detail?: string } } };
      const message =
        ax.response?.data?.error ||
        ax.response?.data?.detail ||
        (err instanceof Error ? err.message : 'No se pudo guardar antes de derivar.');
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
                Completá paciente, motivo y pedidos en este formulario. Si el cuadro lo requiere, podés
                derivar a internación; si no, guardá y listo.
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
              color="warning"
              startIcon={<TransferWithinAStation />}
              onClick={handleDerivarInternacion}
              disabled={saving || (isCreate && !selectedPaciente)}
            >
              Guardar y derivar a internación
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={handleGuardar}
              disabled={saving || (isCreate && !selectedPaciente)}
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
