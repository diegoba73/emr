import React, { useMemo, useRef } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { EstudioMicrobiologia } from '../../../types/lims';
import { updateEstudioMicrobiologia } from '../../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import {
  type ExamenFrescoMicro,
  normalizarExamenFresco,
  seccionesExamenDirecto,
  TITULO_APARTADO_UI,
} from '../../../utils/limsExamenFrescoMicro';
import {
  handleLimsEnterNext,
  LIMS_ENTER_FOCUS_ATTR,
} from '../../../utils/limsEnterFocusNext';

export interface EstudioMicroExamenFrescoTabProps {
  estudio: EstudioMicrobiologia;
  canOperate: boolean;
  onSaved: (estudio: EstudioMicrobiologia) => void;
}

const EstudioMicroExamenFrescoTab: React.FC<EstudioMicroExamenFrescoTabProps> = ({
  estudio,
  canOperate,
  onSaved,
}) => {
  const [form, setForm] = React.useState<ExamenFrescoMicro>(() =>
    normalizarExamenFresco(estudio.examen_fresco)
  );
  const [saving, setSaving] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const saveBtnRef = useRef<HTMLButtonElement>(null);

  const secciones = useMemo(() => seccionesExamenDirecto(estudio), [estudio.tipo_estudio]);
  const focusOrder = useMemo(
    () => secciones.flatMap((s) => s.campos.map((c) => c.codigo)),
    [secciones]
  );

  React.useEffect(() => {
    setForm(normalizarExamenFresco(estudio.examen_fresco));
    setDirty(false);
  }, [estudio.id, estudio.examen_fresco, estudio.updated_at]);

  const setCampo = (codigo: string, value: string) => {
    setForm((prev) => ({ ...prev, [codigo]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateEstudioMicrobiologia(estudio.id, {
        examen_fresco: form,
      });
      toast.success(`${TITULO_APARTADO_UI} guardado.`);
      setDirty(false);
      onSaved(updated);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Alert severity="info" sx={{ py: 0.5 }}>
        <strong>{TITULO_APARTADO_UI}</strong> de la misma muestra del cultivo. Se informan por
        separado las técnicas cargadas (fresco, Gram, micológico con KOH u parasitológico). Solo
        figura en el informe lo que tenga datos.
      </Alert>

      {secciones.map((sec) => (
        <Box
          key={sec.tecnica}
          sx={{
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            p: 2,
          }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            {sec.tituloUi}
          </Typography>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
              gap: 1.5,
            }}
          >
            {sec.campos.map((c) => {
              const fullWidth =
                sec.tecnica === 'gram' ||
                sec.tecnica === 'koh' ||
                c.codigo === 'EXF_PAR_MICRO' ||
                c.codigo === 'EXF_PAR_MACRO';
              const isSoloValor = sec.tecnica === 'gram' || sec.tecnica === 'koh';
              return (
                <TextField
                  key={c.codigo}
                  size="small"
                  label={isSoloValor ? 'Resultado' : c.label}
                  value={form[c.codigo] || ''}
                  onChange={(e) => setCampo(c.codigo, e.target.value)}
                  disabled={!canOperate || saving}
                  multiline={fullWidth}
                  minRows={fullWidth ? 2 : undefined}
                  placeholder={
                    sec.tecnica === 'koh'
                      ? 'p. ej. No se observan elementos fúngicos / Se observan hifas'
                      : sec.tecnica === 'gram'
                        ? 'p. ej. Bacilos Gram negativos / Cocos Gram positivos en racimos'
                        : undefined
                  }
                  onKeyDown={
                    canOperate
                      ? handleLimsEnterNext(focusOrder, c.codigo, {
                          onAfterLast: () => saveBtnRef.current?.focus(),
                        })
                      : undefined
                  }
                  inputProps={{ [LIMS_ENTER_FOCUS_ATTR]: c.codigo }}
                  helperText={
                    canOperate
                      ? fullWidth
                        ? 'Enter → siguiente · Shift+Enter → nueva línea'
                        : 'Enter → siguiente'
                      : undefined
                  }
                  sx={fullWidth ? { gridColumn: '1 / -1' } : undefined}
                />
              );
            })}
          </Box>
        </Box>
      ))}

      {canOperate && (
        <Box display="flex" justifyContent="flex-end" gap={1}>
          <Button
            ref={saveBtnRef}
            variant="contained"
            onClick={() => void handleSave()}
            disabled={saving || !dirty}
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            Guardar examen directo
          </Button>
        </Box>
      )}
      {!canOperate && (
        <Typography variant="caption" color="text.secondary">
          Solo lectura: el estudio no admite edición técnica en este estado o rol.
        </Typography>
      )}
    </Stack>
  );
};

export default EstudioMicroExamenFrescoTab;
