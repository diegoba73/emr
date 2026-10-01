import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import {
  getPedidosPapelPdfBlob,
  getResenasSugeridas,
  type ItemImpresionOrden,
  type ResenaSugerida,
} from '../../services/limsApi';
import { triggerBlobDownload } from '../../services/estudiosComplementariosApi';
import { formatLimsPdfDownloadError, printPdfBlob } from '../../utils/limsDownload';
import type { PendientePedidoRow } from '../../utils/limsPendientesUnificados';

export interface ImprimirPedidosDialogProps {
  open: boolean;
  onClose: () => void;
  rows: PendientePedidoRow[];
  diaLabel: string;
}

type Modo = 'imprimir' | 'descargar';

const ImprimirPedidosDialog: React.FC<ImprimirPedidosDialogProps> = ({
  open,
  onClose,
  rows,
  diaLabel,
}) => {
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set());
  const [desde, setDesde] = useState('1');
  const [hasta, setHasta] = useState('');
  const [generando, setGenerando] = useState(false);
  const [paso, setPaso] = useState<'seleccion' | 'resenas'>('seleccion');
  const [resenas, setResenas] = useState<ResenaSugerida[]>([]);
  /** Textos editados por el operador (por solicitud), se conservan mientras el diálogo esté abierto. */
  const editadas = useRef<Map<number, string>>(new Map());

  useEffect(() => {
    if (!open) return;
    setSeleccion(new Set(rows.map((r) => r.key)));
    setDesde('1');
    setHasta(String(rows.length || 1));
    setPaso('seleccion');
    setResenas([]);
    editadas.current = new Map();
  }, [open, rows]);

  const seleccionadas = useMemo(
    () => rows.filter((r) => seleccion.has(r.key)),
    [rows, seleccion]
  );

  const toggle = (key: string) => {
    setSeleccion((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const aplicarRango = () => {
    const d = Math.max(1, parseInt(desde, 10) || 1);
    const h = Math.min(rows.length, parseInt(hasta, 10) || rows.length);
    if (d > h) {
      toast.error('El número «desde» debe ser menor o igual a «hasta».');
      return;
    }
    setSeleccion(new Set(rows.slice(d - 1, h).map((r) => r.key)));
  };

  const itemsSeleccionados = (): ItemImpresionOrden[] =>
    seleccionadas.map((r) => ({ tipo: r.tipo, id: r.id }));

  const generarPdf = async (modo: Modo, items: ItemImpresionOrden[], lista: ResenaSugerida[]) => {
    const blob = await getPedidosPapelPdfBlob(
      items,
      lista.map((r) => ({ solicitud_id: r.solicitud_id, texto: r.texto }))
    );
    if (modo === 'imprimir') {
      await printPdfBlob(blob);
    } else {
      await triggerBlobDownload(blob, 'pedidos-laboratorio.pdf');
    }
  };

  const continuar = async (modo: Modo) => {
    const items = itemsSeleccionados();
    if (!items.length) {
      toast.error('Seleccioná al menos un pedido.');
      return;
    }
    setGenerando(true);
    try {
      let sugeridas: ResenaSugerida[];
      try {
        sugeridas = await getResenasSugeridas(items);
      } catch {
        toast.error('No se pudieron preparar las reseñas. Intentá de nuevo.');
        return;
      }
      if (sugeridas.length) {
        setResenas(
          sugeridas.map((s) => ({
            ...s,
            texto: editadas.current.get(s.solicitud_id) ?? s.texto,
          }))
        );
        setPaso('resenas');
        return;
      }
      await generarPdf(modo, items, []);
    } catch (e) {
      toast.error(formatLimsPdfDownloadError(e));
    } finally {
      setGenerando(false);
    }
  };

  const imprimirConResenas = async (modo: Modo) => {
    setGenerando(true);
    try {
      await generarPdf(modo, itemsSeleccionados(), resenas);
    } catch (e) {
      toast.error(formatLimsPdfDownloadError(e));
    } finally {
      setGenerando(false);
    }
  };

  const editarResena = (solicitudId: number, texto: string) => {
    editadas.current.set(solicitudId, texto);
    setResenas((prev) => prev.map((r) => (r.solicitud_id === solicitudId ? { ...r, texto } : r)));
  };

  const botonesGenerar = (onGenerar: (m: Modo) => void, etiquetaImprimir: string) => (
    <>
      <Button onClick={() => onGenerar('descargar')} disabled={generando || !seleccionadas.length}>
        Descargar PDF
      </Button>
      <Button
        variant="contained"
        onClick={() => onGenerar('imprimir')}
        disabled={generando || !seleccionadas.length}
        startIcon={generando ? <CircularProgress size={16} color="inherit" /> : undefined}
      >
        {etiquetaImprimir}
      </Button>
    </>
  );

  return (
    <Dialog open={open} onClose={generando ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {paso === 'seleccion' ? `Imprimir pedidos — ${diaLabel}` : 'Revisar reseñas antes de imprimir'}
      </DialogTitle>
      {paso === 'seleccion' ? (
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            2 formularios por hoja apaisada. Si la orden incluye Pro-BNP se agregan sus 2 formularios
            en una misma hoja; si incluye exámenes fuera del listado básico se agrega una reseña que
            vas a poder revisar antes de imprimir.
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
            <Button size="small" onClick={() => setSeleccion(new Set(rows.map((r) => r.key)))}>
              Todos
            </Button>
            <Button size="small" onClick={() => setSeleccion(new Set())}>
              Ninguno
            </Button>
            <TextField
              size="small"
              type="number"
              label="Desde"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              inputProps={{ min: 1, max: rows.length }}
              sx={{ width: 90 }}
            />
            <TextField
              size="small"
              type="number"
              label="Hasta"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              inputProps={{ min: 1, max: rows.length }}
              sx={{ width: 90 }}
            />
            <Button size="small" variant="outlined" onClick={aplicarRango}>
              Seleccionar rango
            </Button>
            <Chip size="small" label={`${seleccionadas.length} de ${rows.length}`} />
          </Stack>
          {rows.length === 0 ? (
            <Typography variant="body2">No hay pedidos en el listado.</Typography>
          ) : (
            <List dense sx={{ maxHeight: 380, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
              {rows.map((r, idx) => (
                <ListItemButton key={r.key} onClick={() => toggle(r.key)} dense>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <Checkbox edge="start" size="small" checked={seleccion.has(r.key)} tabIndex={-1} disableRipple />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box component="span">
                        <strong>{idx + 1}.</strong> {r.paciente_nombre || '—'}
                        {r.paciente_dni ? ` · DNI ${r.paciente_dni}` : ''}
                      </Box>
                    }
                    secondary={`${r.numero || `#${r.id}`} · ${
                      r.tipo === 'MICROBIOLOGIA'
                        ? `Microbiología${r.cultivo_nombre ? ` (${r.cultivo_nombre})` : ''}`
                        : 'Clínico'
                    }`}
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </DialogContent>
      ) : (
        <DialogContent dividers>
          <Alert severity="info" sx={{ mb: 2 }}>
            Texto sugerido automáticamente a partir del diagnóstico, sexo, edad y antecedentes.
            Revisalo y corregilo si hace falta; se imprime tal como quede acá.
          </Alert>
          <Stack spacing={2}>
            {resenas.map((r) => (
              <Paper key={r.solicitud_id} variant="outlined" sx={{ p: 1.5 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                  <Typography variant="subtitle2">{r.paciente || '—'}</Typography>
                  {r.numero && (
                    <Typography variant="caption" color="text.secondary">
                      {r.numero}
                    </Typography>
                  )}
                  <Chip
                    size="small"
                    variant="outlined"
                    color="warning"
                    label={r.fuente === 'medgemma' ? 'Sugerencia IA (MedGemma)' : 'Sugerencia automática'}
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
                  Estudios a justificar: {r.examenes.join(', ')}
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  minRows={3}
                  maxRows={10}
                  value={r.texto}
                  onChange={(e) => editarResena(r.solicitud_id, e.target.value)}
                  inputProps={{ maxLength: 2000 }}
                  placeholder="Dejalo vacío para que el médico la escriba a mano."
                />
              </Paper>
            ))}
          </Stack>
        </DialogContent>
      )}
      <DialogActions>
        {paso === 'seleccion' ? (
          <>
            <Button onClick={onClose} disabled={generando}>
              Cancelar
            </Button>
            {botonesGenerar(continuar, `Imprimir (${seleccionadas.length})`)}
          </>
        ) : (
          <>
            <Button onClick={() => setPaso('seleccion')} disabled={generando}>
              Volver
            </Button>
            {botonesGenerar(imprimirConResenas, `Imprimir (${seleccionadas.length})`)}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ImprimirPedidosDialog;
