import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Stack,
  TextField,
  Button,
  CircularProgress,
  Tabs,
  Tab,
  Alert,
} from '@mui/material';
import { ConsultaAmbulatoriaRecord } from '../../../../types';
import toast from 'react-hot-toast';
import AtencionPedidosSection from '../AtencionPedidosSection';
import { useSaveConsultaAmbulatoriaMutation, useAtencionQuery, useCloseAtencionMutation } from '../../hooks';
import { flushConsultaPedidosDrafts } from '../../consultaPedidosDraft';

interface ConsultaAmbulatoriaFormProps {
  atencionId: number;
  canEdit: boolean;
  forceEdit?: boolean;
  onSaveSuccess?: () => void;
}

function ConsultaFormTabPanel(props: { value: number; index: number; children: React.ReactNode }) {
  const { value, index, children } = props;
  if (value !== index) return null;
  return <Box sx={{ pt: 2 }} role="tabpanel">{children}</Box>;
}

const ConsultaAmbulatoriaForm: React.FC<ConsultaAmbulatoriaFormProps> = ({ atencionId, canEdit, onSaveSuccess }) => {
  const { data: atencion, isLoading } = useAtencionQuery(atencionId);
  const [consulta, setConsulta] = useState<ConsultaAmbulatoriaRecord | null>(null);
  const initializedRef = useRef(false);
  const [tab, setTab] = useState(0);

  const [formState, setFormState] = useState({
    anamnesis: '',
    examen_fisico: '',
    diagnostico_presuntivo: '',
    plan_manejo: '',
    antecedentes_relevantes: '',
    alergias: '',
    medicacion_actual: '',
    diagnostico_definitivo: '',
    observaciones_medicas: '',
  });
  const saveMutation = useSaveConsultaAmbulatoriaMutation();
  const closeMutation = useCloseAtencionMutation();
  const draftKey = `consulta-amb-borrador-${atencionId}`;
  const formStateRef = useRef(formState);
  formStateRef.current = formState;

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
        /* lleno o privado */
      }
    },
    [draftKey]
  );

  useEffect(() => {
    initializedRef.current = false;
    setConsulta(null);
  }, [atencionId]);

  useEffect(() => {
    if (!atencion || initializedRef.current) return;

    const consultaData = atencion.consulta_ambulatoria;

    if (consultaData && typeof consultaData === 'object') {
      const hasFields = Object.keys(consultaData).length > 1 || 
        'anamnesis' in consultaData ||
        'diagnostico_presuntivo' in consultaData;

      const fromServer = {
        anamnesis: (consultaData as any).anamnesis ?? '',
        examen_fisico: (consultaData as any).examen_fisico ?? '',
        diagnostico_presuntivo: (consultaData as any).diagnostico_presuntivo ?? '',
        plan_manejo: (consultaData as any).plan_manejo ?? '',
        antecedentes_relevantes: (consultaData as any).antecedentes_relevantes ?? '',
        alergias: (consultaData as any).alergias ?? '',
        medicacion_actual: (consultaData as any).medicacion_actual ?? '',
        diagnostico_definitivo: (consultaData as any).diagnostico_definitivo ?? '',
        observaciones_medicas: (consultaData as any).observaciones_medicas ?? '',
      };
      const draft = readDraft();
      const merged = draft ? { ...fromServer, ...draft } : fromServer;

      if (hasFields) {
        setConsulta(consultaData as ConsultaAmbulatoriaRecord);
        setFormState(merged);
        initializedRef.current = true;
      } else {
        setConsulta({ id: (consultaData as any).id } as ConsultaAmbulatoriaRecord);
        setFormState((prev) => ({ ...prev, ...merged }));
        initializedRef.current = true;
      }
    } else {
      setConsulta(null);
      const draft = readDraft();
      if (draft) {
        setFormState((prev) => ({ ...prev, ...draft }));
      }
      initializedRef.current = true;
    }
  }, [atencion, atencionId, readDraft]);

  const atencionCerrada =
    atencion?.estado_clinico === 'FINALIZADA' || Boolean(atencion?.fecha_cierre);
  const isReadOnly = !canEdit || atencionCerrada;
  const canSave = canEdit && !atencionCerrada;

  useEffect(() => {
    if (!initializedRef.current || isReadOnly || !canSave) return;
    const t = setTimeout(() => {
      persistDraft(formState);
    }, 300);
    return () => clearTimeout(t);
  }, [formState, isReadOnly, canSave, persistDraft]);

  useEffect(() => {
    return () => {
      if (initializedRef.current && canSave) {
        persistDraft(formStateRef.current);
      }
    };
  }, [canSave, persistDraft]);

  const handleChange = useCallback(
    (field: keyof typeof formState) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { value } = event.target;
      setFormState((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  const textField = (field: keyof typeof formState, label: string, minRows: number) => (
    <TextField
      key={field}
      label={label}
      fullWidth
      multiline
      minRows={minRows}
      value={formState[field]}
      onChange={handleChange(field)}
      disabled={!canSave}
      InputProps={{ readOnly: isReadOnly }}
    />
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const payload = {
      anamnesis: formState.anamnesis,
      examen_fisico: formState.examen_fisico,
      diagnostico_presuntivo: formState.diagnostico_presuntivo,
      plan_manejo: formState.plan_manejo,
      antecedentes_relevantes: formState.antecedentes_relevantes,
      alergias: formState.alergias,
      medicacion_actual: formState.medicacion_actual,
      diagnostico_definitivo: formState.diagnostico_definitivo,
      observaciones_medicas: formState.observaciones_medicas,
    };
    try {
      const registroId = consulta?.id;
      await saveMutation.mutateAsync({
        atencionId,
        data: payload,
        exists: Boolean(registroId),
        registroId,
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
              : 'No se pudieron registrar los pedidos de la consulta.';
          toast.error(message);
          return;
        }
      }

      await closeMutation.mutateAsync(atencionId);
      try { sessionStorage.removeItem(draftKey); } catch { /* nada */ }
      if (onSaveSuccess) {
        onSaveSuccess();
      }
    } catch {
      // El hook muestra toast vía onError
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" py={4}>
        <CircularProgress size={32} />
        <Typography variant="body2" color="text.secondary" ml={2}>
          Cargando consulta...
        </Typography>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          {!consulta?.id ? 'Nueva consulta ambulatoria' : 'Consulta ambulatoria'}
        </Typography>
        {canSave && (
          <Typography variant="caption" color="text.secondary">
            Borrador local (sesión)
          </Typography>
        )}
      </Box>
      {atencionCerrada && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Atención finalizada: la consulta es de solo lectura.
        </Alert>
      )}
      {!canEdit && !atencionCerrada && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Tu rol no puede modificar el detalle clínico de esta atención.
        </Alert>
      )}

      <AtencionPedidosSection atencionId={atencionId} canEdit={canSave} />

      <Tabs
        value={tab}
        onChange={(_e, v) => setTab(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 0 }}
      >
        <Tab label="Anamnesis" id="ca-tab-0" aria-controls="ca-panel-0" />
        <Tab label="Examen físico" id="ca-tab-1" aria-controls="ca-panel-1" />
        <Tab label="Diagnóstico" id="ca-tab-2" aria-controls="ca-panel-2" />
        <Tab label="Plan" id="ca-tab-3" aria-controls="ca-panel-3" />
      </Tabs>

      <ConsultaFormTabPanel value={tab} index={0}>
        <Stack spacing={2}>
          {textField('anamnesis', 'Anamnesis *', 4)}
          {textField('antecedentes_relevantes', 'Antecedentes relevantes', 2)}
          {textField('alergias', 'Alergias', 2)}
          {textField('medicacion_actual', 'Medicación actual', 2)}
        </Stack>
      </ConsultaFormTabPanel>

      <ConsultaFormTabPanel value={tab} index={1}>
        <Stack spacing={2}>{textField('examen_fisico', 'Examen físico *', 4)}</Stack>
      </ConsultaFormTabPanel>

      <ConsultaFormTabPanel value={tab} index={2}>
        <Stack spacing={2}>
          {textField('diagnostico_presuntivo', 'Diagnóstico presuntivo', 3)}
          {textField('diagnostico_definitivo', 'Diagnóstico definitivo', 2)}
          {textField('observaciones_medicas', 'Observaciones médicas', 2)}
        </Stack>
      </ConsultaFormTabPanel>

      <ConsultaFormTabPanel value={tab} index={3}>
        <Stack spacing={2}>{textField('plan_manejo', 'Plan de manejo *', 3)}</Stack>
      </ConsultaFormTabPanel>

      {canSave && (
        <Box display="flex" justifyContent="flex-end" sx={{ mt: 2 }}>
          <Button
            type="submit"
            variant="contained"
            disabled={saveMutation.isPending || closeMutation.isPending}
          >
            {saveMutation.isPending || closeMutation.isPending ? 'Guardando…' : 'Guardar y cerrar consulta'}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default ConsultaAmbulatoriaForm;
