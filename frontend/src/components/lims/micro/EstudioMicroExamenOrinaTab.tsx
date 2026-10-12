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
  CAMPOS_SEDIMENTO_ORINA,
  CAMPOS_TIRA_ORINA,
  type CodigoExamenOrinaMicro,
  type ExamenOrinaMicro,
  normalizarExamenOrina,
} from '../../../utils/limsExamenOrinaMicro';
import {
  handleLimsEnterNext,
  LIMS_ENTER_FOCUS_ATTR,
} from '../../../utils/limsEnterFocusNext';

export interface EstudioMicroExamenOrinaTabProps {
  estudio: EstudioMicrobiologia;
  canOperate: boolean;
  onSaved: (estudio: EstudioMicrobiologia) => void;
}

const EstudioMicroExamenOrinaTab: React.FC<EstudioMicroExamenOrinaTabProps> = ({
  estudio,
  canOperate,
  onSaved,
}) => {
  const [form, setForm] = React.useState<ExamenOrinaMicro>(() =>
    normalizarExamenOrina(estudio.examen_orina)
  );
  const [saving, setSaving] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const saveBtnRef = useRef<HTMLButtonElement>(null);

  const focusOrder = useMemo(
    () => [
      ...CAMPOS_TIRA_ORINA.map((c) => c.codigo),
      ...CAMPOS_SEDIMENTO_ORINA.map((c) => c.codigo),
    ],
    []
  );

  React.useEffect(() => {
    setForm(normalizarExamenOrina(estudio.examen_orina));
    setDirty(false);
  }, [estudio.id, estudio.examen_orina, estudio.updated_at]);

  const setCampo = (codigo: CodigoExamenOrinaMicro, value: string) => {
    setForm((prev) => ({ ...prev, [codigo]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateEstudioMicrobiologia(estudio.id, {
        examen_orina: form,
      });
      toast.success('Examen de orina guardado.');
      setDirty(false);
      onSaved(updated);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setSaving(false);
    }
  };

  const renderCampos = (
    campos: readonly { codigo: CodigoExamenOrinaMicro; label: string }[],
    multilinea?: CodigoExamenOrinaMicro
  ) => (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
        gap: 1.5,
      }}
    >
      {campos.map((c) => {
        const fullWidth = c.codigo === multilinea;
        return (
          <TextField
            key={c.codigo}
            size="small"
            label={c.label}
            value={form[c.codigo] || ''}
            onChange={(e) => setCampo(c.codigo, e.target.value)}
            disabled={!canOperate || saving}
            multiline={fullWidth}
            minRows={fullWidth ? 2 : undefined}
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
  );

  return (
    <Stack spacing={2}>
      <Alert severity="info" sx={{ py: 0.5 }}>
        Tira reactiva y sedimento de la <strong>misma muestra</strong> del urocultivo. No genera un
        pedido separado de orina completa en lab. clínico.
      </Alert>

      <PaperSection title="Tira reactiva">
        {renderCampos(CAMPOS_TIRA_ORINA)}
      </PaperSection>

      <PaperSection title="Sedimento">
        {renderCampos(CAMPOS_SEDIMENTO_ORINA, 'ORI_CONC')}
      </PaperSection>

      {canOperate && (
        <Box display="flex" justifyContent="flex-end" gap={1}>
          <Button
            ref={saveBtnRef}
            variant="contained"
            onClick={() => void handleSave()}
            disabled={saving || !dirty}
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            Guardar examen de orina
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

function PaperSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        p: 2,
      }}
    >
      <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}

export default EstudioMicroExamenOrinaTab;
