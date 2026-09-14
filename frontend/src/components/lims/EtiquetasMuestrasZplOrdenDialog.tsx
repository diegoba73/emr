import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { EtiquetaMuestraZpl, MuestraTransaccional } from '../../types/lims';
import {
  getMuestraEtiquetaZpl,
  listMuestrasPorSolicitud,
  printTalonOrden,
} from '../../services/limsApi';
import { imprimirEtiquetaMuestraLocal } from '../../services/labelPrintAgent';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import type { OrigenParaLugarExtraccion } from '../../utils/limsOrigenSolicitud';
import { printerErrorMessage } from './EtiquetaMuestraZplDialog';

export interface EtiquetasMuestrasZplOrdenDialogProps {
  open: boolean;
  solicitudId: number;
  solicitudNumero?: string | null;
  /** Reservado: el backend resuelve lugar desde origen de la solicitud. */
  origenOrden?: OrigenParaLugarExtraccion | null;
  onClose: () => void;
  /** Tras cerrar / refrescar muestras en el padre. */
  onUpdated?: () => void;
}

type RowState = {
  muestra: MuestraTransaccional;
  payload: EtiquetaMuestraZpl | null;
  loading: boolean;
  printing: boolean;
  error?: string;
};

function EtiquetaPreviewBlock({ payload }: { payload: EtiquetaMuestraZpl | null }) {
  const lines = payload?.lines ?? [];
  const errors = payload?.validation_errors ?? [];
  return (
    <>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Etiqueta 40 × 23 mm · Perfil 203 dpi
        {payload?.profile ? ` · ${payload.profile}` : ''}
      </Typography>
      {lines.length === 4 ? (
        <Box
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            px: 2,
            py: 1.5,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            bgcolor: 'background.paper',
          }}
        >
          <Typography sx={{ fontWeight: 700, fontSize: '1.05rem', lineHeight: 1.3 }}>
            {lines[0]}
          </Typography>
          <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.35 }}>{lines[1]}</Typography>
          <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.35 }}>{lines[2]}</Typography>
          <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.35 }}>{lines[3]}</Typography>
        </Box>
      ) : (
        <Typography color="text.secondary" variant="body2">
          No se puede generar la etiqueta completa todavía.
        </Typography>
      )}
      {errors.length > 0 && (
        <Box sx={{ mt: 1 }}>
          {errors.map((err) => (
            <Typography key={err} variant="body2" color="warning.main">
              {err}
            </Typography>
          ))}
        </Box>
      )}
    </>
  );
}

/**
 * Vista previa + impresión ZPL por tubo.
 * No registra toma ni avanza la orden: el tubo sigue pendiente de recepción.
 */
const EtiquetasMuestrasZplOrdenDialog: React.FC<EtiquetasMuestrasZplOrdenDialogProps> = ({
  open,
  solicitudId,
  solicitudNumero,
  onClose,
  onUpdated,
}) => {
  const [rows, setRows] = useState<RowState[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [downloadingTalon, setDownloadingTalon] = useState(false);
  const printLocks = useRef<Record<number, boolean>>({});

  const loadPreviews = useCallback(async (muestras: MuestraTransaccional[]) => {
    const initial: RowState[] = muestras.map((m) => ({
      muestra: m,
      payload: null,
      loading: true,
      printing: false,
    }));
    setRows(initial);
    await Promise.all(
      muestras.map(async (m, idx) => {
        try {
          const payload = await getMuestraEtiquetaZpl(m.id);
          setRows((prev) => {
            const next = [...prev];
            if (!next[idx] || next[idx].muestra.id !== m.id) {
              const i = next.findIndex((r) => r.muestra.id === m.id);
              if (i < 0) return prev;
              next[i] = { ...next[i], payload, loading: false, error: undefined };
              return next;
            }
            next[idx] = { ...next[idx], payload, loading: false, error: undefined };
            return next;
          });
        } catch (e) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarMuestra);
          setRows((prev) => {
            const next = [...prev];
            const i = next.findIndex((r) => r.muestra.id === m.id);
            if (i < 0) return prev;
            next[i] = { ...next[i], loading: false, error: msg };
            return next;
          });
        }
      })
    );
  }, []);

  const reload = useCallback(async () => {
    setLoadingList(true);
    try {
      const muestras = await listMuestrasPorSolicitud(solicitudId, solicitudNumero);
      if (muestras.length === 0) {
        setRows([]);
        return;
      }
      await loadPreviews(muestras);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarMuestras));
      setRows([]);
    } finally {
      setLoadingList(false);
    }
  }, [solicitudId, solicitudNumero, loadPreviews]);

  useEffect(() => {
    if (!open) {
      setRows([]);
      printLocks.current = {};
      return;
    }
    void reload();
  }, [open, reload]);

  const setRowPrinting = (muestraId: number, printing: boolean) => {
    setRows((prev) =>
      prev.map((r) => (r.muestra.id === muestraId ? { ...r, printing } : r))
    );
  };

  const handlePrint = async (row: RowState) => {
    const id = row.muestra.id;
    if (printLocks.current[id] || row.printing) return;
    printLocks.current[id] = true;
    setRowPrinting(id, true);
    try {
      await imprimirEtiquetaMuestraLocal(id);
      toast.success(
        `Etiqueta enviada a impresión${
          row.muestra.codigo_barra ? ` (${row.muestra.codigo_barra})` : ''
        }`
      );
      const payload = await getMuestraEtiquetaZpl(id);
      const muestras = await listMuestrasPorSolicitud(solicitudId, solicitudNumero);
      const fresh = muestras.find((m) => m.id === id) || row.muestra;
      setRows((prev) =>
        prev.map((r) =>
          r.muestra.id === id
            ? { ...r, muestra: fresh, payload, loading: false, error: undefined }
            : r
        )
      );
      onUpdated?.();
    } catch (e) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 400) {
        toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarMuestra));
      } else {
        toast.error(printerErrorMessage(e));
      }
    } finally {
      setRowPrinting(id, false);
      printLocks.current[id] = false;
    }
  };

  const anyPrinting = rows.some((r) => r.printing);

  const handleTalon = async () => {
    if (downloadingTalon || anyPrinting) return;
    setDownloadingTalon(true);
    try {
      await printTalonOrden(solicitudId);
      toast.success('Diálogo de impresión abierto — elegí una impresora común.');
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
    } finally {
      setDownloadingTalon(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => !anyPrinting && !downloadingTalon && onClose()}
      maxWidth="sm"
      fullWidth
      scroll="paper"
    >
      <DialogTitle>
        Imprimir etiquetas
        {solicitudNumero ? ` — orden ${solicitudNumero}` : ''}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Etiqueta = impresora USB de tubos en esta PC (agente ZPL). Talón = media hoja A4 por
          muestra (impresora común) si la etiquetadora falla. Ninguna opción recepciona la muestra.
        </Typography>
        {loadingList && rows.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography color="text.secondary">No hay tubos/muestras en esta orden.</Typography>
        ) : (
          <Stack spacing={2} divider={<Divider flexItem />}>
            {rows.map((row) => {
              const canPrint = Boolean(row.payload?.printable);
              return (
                <Box key={row.muestra.id}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    {row.muestra.codigo_barra || `Muestra #${row.muestra.id}`}
                    {row.muestra.estado === 'PENDIENTE_TOMA'
                      ? ' · pendiente de recepción'
                      : ''}
                  </Typography>
                  {row.loading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                      <CircularProgress size={24} />
                    </Box>
                  ) : row.error ? (
                    <Typography color="error" variant="body2">
                      {row.error}
                    </Typography>
                  ) : (
                    <EtiquetaPreviewBlock payload={row.payload} />
                  )}
                  {row.muestra.estado === 'PENDIENTE_TOMA' && canPrint && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                      Imprimir no recibe el tubo: queda en Pendientes «Esperando recepción» hasta el
                      escaneo en recepción.
                    </Typography>
                  )}
                  <Box sx={{ mt: 1.5, display: 'flex', justifyContent: 'flex-end' }}>
                    <Button
                      variant="contained"
                      size="small"
                      disabled={
                        row.loading ||
                        row.printing ||
                        !!row.error ||
                        !canPrint ||
                        downloadingTalon
                      }
                      onClick={() => void handlePrint(row)}
                    >
                      {row.printing ? 'Imprimiendo…' : 'Imprimir etiqueta'}
                    </Button>
                  </Box>
                </Box>
              );
            })}
          </Stack>
        )}
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Button
          variant="outlined"
          onClick={() => void handleTalon()}
          disabled={anyPrinting || downloadingTalon}
        >
          {downloadingTalon ? 'Abriendo impresión…' : 'Imprimir talón'}
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button onClick={onClose} disabled={anyPrinting || downloadingTalon}>
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EtiquetasMuestrasZplOrdenDialog;
