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
import SignosVitalesPanel from '../../../../components/clinical/SignosVitalesPanel';

interface ConsultaAmbulatoriaFormProps {
  atencionId: number;
  canEdit: boolean;
  forceEdit?: boolean;
  onSaveSuccess?: () => void;
}

type ConsultaFormState = {
  anamnesis: string;
  examen_fisico: string;
  diagnostico_presuntivo: string;
  plan_manejo: string;
  antecedentes_relevantes: string;
  alergias: string;
  medicacion_actual: string;
  diagnostico_definitivo: string;
  observaciones_medicas: string;
};

const EMPTY_FORM: ConsultaFormState = {
  anamnesis: '',
  examen_fisico: '',
  diagnostico_presuntivo: '',
  plan_manejo: '',
  antecedentes_relevantes: '',
  alergias: '',
  medicacion_actual: '',
  diagnostico_definitivo: '',
  observaciones_medicas: '',
};

function ConsultaFormTabPanel(props: { value: number; index: number; children: React.ReactNode }) {
  const { value, index, children } = props;
  if (value !== index) return null;
  return <Box sx={{ pt: 2 }} role="tabpanel">{children}</Box>;
}

function formFromConsulta(
  consultaData: Partial<ConsultaAmbulatoriaRecord> | Record<string, unknown> | null | undefined
): ConsultaFormState {
  if (!consultaData || typeof consultaData !== 'object') return { ...EMPTY_FORM };
  const c = consultaData as Partial<ConsultaAmbulatoriaRecord>;
  return {
    anamnesis: String(c.anamnesis ?? ''),
    examen_fisico: String(c.examen_fisico ?? ''),
    diagnostico_presuntivo: String(c.diagnostico_presuntivo ?? ''),
    plan_manejo: String(c.plan_manejo ?? ''),
    antecedentes_relevantes: String(c.antecedentes_relevantes ?? ''),
    alergias: String(c.alergias ?? ''),
    medicacion_actual: String(c.medicacion_actual ?? ''),
    diagnostico_definitivo: String(c.diagnostico_definitivo ?? ''),
    observaciones_medicas: String(c.observaciones_medicas ?? ''),
  };
}

/** True si hay al menos un campo clínico con texto. */
function formHasContent(state: ConsultaFormState): boolean {
  return Object.values(state).some((v) => typeof v === 'string' && v.trim().length > 0);
}

/**
 * Une servidor + borrador sin que un draft vacío pise datos ya persistidos.
 * - Campos con texto en el draft (edición local) ganan.
 * - Campos vacíos en el draft no sobrescriben al servidor.
 */
function mergeServerAndDraft(
  server: ConsultaFormState,
  draft: Partial<ConsultaFormState> | null
): ConsultaFormState {
  if (!draft) return server;
  const merged = { ...server };
  (Object.keys(EMPTY_FORM) as (keyof ConsultaFormState)[]).forEach((key) => {
    const draftVal = draft[key];
    if (typeof draftVal === 'string' && draftVal.trim().length > 0) {
      merged[key] = draftVal;
    }
  });
  return merged;
}

function consultaRecordFromPayload(
  consultaData: Partial<ConsultaAmbulatoriaRecord> | null | undefined,
  atencionId: number,
  form: ConsultaFormState
): ConsultaAmbulatoriaRecord {
  const id = consultaData?.id || consultaData?.atencion_id || atencionId;
  return {
    id: Number(id),
    atencion_id: Number(consultaData?.atencion_id ?? atencionId),
    ...form,
  } as ConsultaAmbulatoriaRecord;
}

const ConsultaAmbulatoriaForm: React.FC<ConsultaAmbulatoriaFormProps> = ({
  atencionId,
  canEdit,
  onSaveSuccess,
}) => {
  const { data: atencion, isLoading, isFetching } = useAtencionQuery(atencionId);
  const [consulta, setConsulta] = useState<ConsultaAmbulatoriaRecord | null>(null);
  const initializedRef = useRef(false);
  const skipDraftPersistRef = useRef(false);
  const [tab, setTab] = useState(0);

  const [formState, setFormState] = useState<ConsultaFormState>({ ...EMPTY_FORM });
  const saveMutation = useSaveConsultaAmbulatoriaMutation();
  const closeMutation = useCloseAtencionMutation();
  const draftKey = `consulta-amb-borrador-${atencionId}`;
  const formStateRef = useRef(formState);
  formStateRef.current = formState;

  const readDraft = useCallback((): Partial<ConsultaFormState> | null => {
    try {
      const raw = sessionStorage.getItem(draftKey);
      if (!raw) return null;
      return JSON.parse(raw) as Partial<ConsultaFormState>;
    } catch {
      return null;
    }
  }, [draftKey]);

  const persistDraft = useCallback(
    (state: ConsultaFormState) => {
      if (skipDraftPersistRef.current) return;
      try {
        sessionStorage.setItem(draftKey, JSON.stringify(state));
      } catch {
        /* lleno o privado */
      }
    },
    [draftKey]
  );

  const clearDraft = useCallback(() => {
    skipDraftPersistRef.current = true;
    try {
      sessionStorage.removeItem(draftKey);
    } catch {
      /* nada */
    }
  }, [draftKey]);

  useEffect(() => {
    initializedRef.current = false;
    skipDraftPersistRef.current = false;
    setConsulta(null);
    setFormState({ ...EMPTY_FORM });
  }, [atencionId]);

  useEffect(() => {
    if (!atencion) return;

    const consultaData =
      atencion.consulta_ambulatoria && typeof atencion.consulta_ambulatoria === 'object'
        ? (atencion.consulta_ambulatoria as Partial<ConsultaAmbulatoriaRecord>)
        : null;
    const fromServer = formFromConsulta(consultaData);
    const serverHasContent = formHasContent(fromServer);

    if (!initializedRef.current) {
      // Evitar fijar el form con un cache incompleto mientras llega el GET detalle.
      if (isFetching && !consultaData && !readDraft()) {
        return;
      }
      const merged = mergeServerAndDraft(fromServer, readDraft());
      if (consultaData) {
        setConsulta(consultaRecordFromPayload(consultaData, atencionId, merged));
      } else {
        setConsulta(null);
      }
      setFormState(merged);
      initializedRef.current = true;
      return;
    }

    // Rehidratación: cache inicial sin campos clínicos → GET detalle con contenido.
    if (serverHasContent && !formHasContent(formStateRef.current)) {
      setFormState(fromServer);
      if (consultaData) {
        setConsulta(consultaRecordFromPayload(consultaData, atencionId, fromServer));
      }
      return;
    }

    // Si el servidor trae id y aún no lo teníamos (shell creado por pedidos).
    if (consultaData && !consulta?.id) {
      const id = Number(consultaData.id ?? consultaData.atencion_id ?? atencionId);
      setConsulta((prev) => ({
        ...(prev || ({} as ConsultaAmbulatoriaRecord)),
        ...consultaRecordFromPayload(consultaData, atencionId, formStateRef.current),
        id,
      }));
    }
  }, [atencion, atencionId, isFetching, readDraft, consulta?.id]);

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
      if (initializedRef.current && canSave && !skipDraftPersistRef.current) {
        persistDraft(formStateRef.current);
      }
    };
  }, [canSave, persistDraft]);

  const handleChange = useCallback(
    (field: keyof ConsultaFormState) =>
      (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { value } = event.target;
        setFormState((prev) => ({ ...prev, [field]: value }));
      },
    []
  );

  const textField = (field: keyof ConsultaFormState, label: string, minRows: number) => (
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
    const payload = { ...formState };
    try {
      const registroId = consulta?.id ?? atencionId;
      const saved = await saveMutation.mutateAsync({
        atencionId,
        data: payload,
        exists: Boolean(consulta?.id),
        registroId,
      });

      const savedId = saved.id ?? saved.atencion_id ?? atencionId;
      setConsulta({
        ...saved,
        id: savedId,
        atencion_id: saved.atencion_id ?? atencionId,
        ...payload,
      });

      const consultaHcId = atencion?.consulta_hc_id;
      const pacienteId =
        atencion?.paciente && typeof atencion.paciente === 'object'
          ? atencion.paciente.id
          : typeof atencion?.paciente === 'number'
            ? atencion.paciente
            : atencion?.paciente_id;
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
            origenSolicitud:
              atencion?.contexto_atencion === 'GUARDIA' ? 'GUARDIA' : undefined,
          });
        } catch (flushError) {
          const message =
            flushError instanceof Error
              ? flushError.message
              : 'No se pudieron registrar los pedidos de la consulta.';
          toast.error(
            `La consulta clínica se guardó, pero hubo un problema con los pedidos: ${message}. ` +
              'La atención sigue abierta: corregí o reintentá con «Guardar y cerrar».'
          );
          // No cerrar: el borrador de pedidos fallidos queda para reintentar.
          return;
        }
      }

      try {
        await closeMutation.mutateAsync(atencionId);
      } catch {
        // Toast del hook; la clínica ya está persistida.
        clearDraft();
        return;
      }

      clearDraft();
      if (onSaveSuccess) {
        onSaveSuccess();
      }
    } catch {
      // El hook muestra toast vía onError
    }
  };

  if (isLoading && !atencion) {
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
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          mb: 1,
        }}
      >
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

      <AtencionPedidosSection
        atencionId={atencionId}
        canEdit={canSave}
        pacienteId={
          (
            atencion?.paciente && typeof atencion.paciente === 'object'
              ? atencion.paciente.id
              : typeof atencion?.paciente === 'number'
                ? atencion.paciente
                : atencion?.paciente_id
          ) ?? undefined
        }
      />

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
        <Stack spacing={2}>
          <SignosVitalesPanel
            atencionId={atencionId}
            canEdit={canSave}
            initialItems={atencion?.signos_vitales}
          />
          {textField('examen_fisico', 'Examen físico *', 4)}
        </Stack>
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
            {saveMutation.isPending || closeMutation.isPending
              ? 'Guardando…'
              : 'Guardar y cerrar consulta'}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default ConsultaAmbulatoriaForm;
