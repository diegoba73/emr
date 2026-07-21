import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Stack,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import { EvolucionInternacionRecord } from '../../../../types';
import toast from 'react-hot-toast';
import {
  useSaveEvolucionInternacionMutation,
  useAtencionQuery,
  useCloseAtencionMutation,
} from '../../hooks';
import { flushConsultaPedidosDrafts } from '../../consultaPedidosDraft';
import AtencionPedidosSection from '../AtencionPedidosSection';

interface EvolucionInternacionFormProps {
  atencionId: number;
  canEdit: boolean;
  onSaveSuccess?: () => void;
}

const EvolucionInternacionForm: React.FC<EvolucionInternacionFormProps> = ({
  atencionId,
  canEdit,
  onSaveSuccess,
}) => {
  const { data: atencion, isLoading } = useAtencionQuery(atencionId);
  const [evolucion, setEvolucion] = useState<EvolucionInternacionRecord | null>(null);
  const initializedRef = useRef(false);
  const [formState, setFormState] = useState({
    subjetivo: '',
    objetivo: '',
    analisis: '',
    plan: '',
    signos_vitales_resumen: '',
    diagnostico_actualizado: '',
    plan_manejo: '',
    observaciones: '',
  });
  const saveMutation = useSaveEvolucionInternacionMutation();
  const closeMutation = useCloseAtencionMutation();
  const draftKey = `evolucion-intern-borrador-${atencionId}`;

  const readDraft = useCallback((): Partial<typeof formState> | null => {
    try {
      const raw = sessionStorage.getItem(draftKey);
      if (!raw) return null;
      return JSON.parse(raw) as Partial<typeof formState>;
    } catch {
      return null;
    }
  }, [draftKey]);

  const persistDraft = useCallback(
    (state: typeof formState) => {
      try {
        sessionStorage.setItem(draftKey, JSON.stringify(state));
      } catch {
        /* ignore */
      }
    },
    [draftKey],
  );

  useEffect(() => {
    initializedRef.current = false;
    setEvolucion(null);
  }, [atencionId]);

  useEffect(() => {
    if (!atencion?.evolucion_internacion || initializedRef.current) return;
    const evo = atencion.evolucion_internacion;
    setEvolucion(evo);
    const draft = readDraft();
    setFormState({
      subjetivo: draft?.subjetivo ?? evo.subjetivo ?? '',
      objetivo: draft?.objetivo ?? evo.objetivo ?? '',
      analisis: draft?.analisis ?? evo.analisis ?? '',
      plan: draft?.plan ?? evo.plan ?? '',
      signos_vitales_resumen: draft?.signos_vitales_resumen ?? evo.signos_vitales_resumen ?? '',
      diagnostico_actualizado: draft?.diagnostico_actualizado ?? evo.diagnostico_actualizado ?? '',
      plan_manejo: draft?.plan_manejo ?? evo.plan_manejo ?? '',
      observaciones: draft?.observaciones ?? evo.observaciones ?? '',
    });
    initializedRef.current = true;
  }, [atencion, readDraft]);

  useEffect(() => {
    if (!canEdit || atencion?.fecha_cierre) return;
    persistDraft(formState);
  }, [formState, canEdit, atencion?.fecha_cierre, persistDraft]);

  const atencionCerrada = Boolean(atencion?.fecha_cierre || atencion?.estado_clinico === 'FINALIZADA');
  const canSave = canEdit && !atencionCerrada;

  const handleChange = (field: keyof typeof formState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setFormState((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSave) return;
    try {
      await saveMutation.mutateAsync({
        atencionId,
        data: formState,
        registroId: evolucion?.id,
      });

      const consultaHcId = atencion?.consulta_hc_id;
      const pacienteId =
        atencion?.paciente && typeof atencion.paciente === 'object'
          ? atencion.paciente.id
          : typeof atencion?.paciente === 'number'
            ? atencion.paciente
            : undefined;
      const medicoId =
        atencion?.medico_principal && typeof atencion.medico_principal === 'object'
          ? atencion.medico_principal.id
          : atencion?.medico_principal_id;

      if (consultaHcId && pacienteId) {
        try {
          await flushConsultaPedidosDrafts({
            consultaHcId,
            pacienteId,
            medicoId,
          });
        } catch (flushError) {
          const message =
            flushError instanceof Error
              ? flushError.message
              : 'No se pudieron registrar los pedidos de la evolución.';
          toast.error(message);
          return;
        }
      }

      await closeMutation.mutateAsync(atencionId);
      try {
        sessionStorage.removeItem(draftKey);
      } catch {
        /* ignore */
      }
      onSaveSuccess?.();
    } catch {
      /* toast via hook */
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" py={4}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  const tipoLabel = evolucion?.tipo_evolucion_display || evolucion?.tipo_evolucion || 'Evolución';

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          {tipoLabel}
        </Typography>
        <Chip label="Internación" size="small" color="warning" variant="outlined" />
      </Stack>

      {atencionCerrada && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Atención finalizada: la evolución es de solo lectura.
        </Alert>
      )}

      <AtencionPedidosSection atencionId={atencionId} canEdit={canSave} />

      <Stack spacing={2}>
        <TextField
          label="Subjetivo (S)"
          multiline
          minRows={3}
          value={formState.subjetivo}
          onChange={handleChange('subjetivo')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Objetivo (O)"
          multiline
          minRows={3}
          value={formState.objetivo}
          onChange={handleChange('objetivo')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Signos vitales (resumen)"
          multiline
          minRows={2}
          value={formState.signos_vitales_resumen}
          onChange={handleChange('signos_vitales_resumen')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Análisis (A)"
          multiline
          minRows={3}
          value={formState.analisis}
          onChange={handleChange('analisis')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Diagnóstico actualizado"
          multiline
          minRows={2}
          value={formState.diagnostico_actualizado}
          onChange={handleChange('diagnostico_actualizado')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Plan (P)"
          multiline
          minRows={3}
          value={formState.plan}
          onChange={handleChange('plan')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Plan de manejo"
          multiline
          minRows={2}
          value={formState.plan_manejo}
          onChange={handleChange('plan_manejo')}
          disabled={!canSave}
          fullWidth
        />
        <TextField
          label="Observaciones"
          multiline
          minRows={2}
          value={formState.observaciones}
          onChange={handleChange('observaciones')}
          disabled={!canSave}
          fullWidth
        />
      </Stack>

      {canSave && (
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            type="submit"
            variant="contained"
            disabled={saveMutation.isPending || closeMutation.isPending}
          >
            {saveMutation.isPending || closeMutation.isPending ? (
              <CircularProgress size={22} color="inherit" />
            ) : (
              'Guardar y cerrar evolución'
            )}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default EvolucionInternacionForm;
