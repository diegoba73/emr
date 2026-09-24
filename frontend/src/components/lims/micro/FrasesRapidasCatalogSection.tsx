import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Paper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import toast from 'react-hot-toast';
import type { FraseRapidaMicrobiologia } from '../../../types/lims';
import {
  createFraseRapidaMicro,
  listFrasesRapidasMicro,
  updateFraseRapidaMicro,
} from '../../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';

type FraseForm = {
  abreviatura: string;
  texto: string;
  categoria: string;
  activo: boolean;
};

const emptyForm = (): FraseForm => ({
  abreviatura: '',
  texto: '',
  categoria: 'GENERAL',
  activo: true,
});

export interface FrasesRapidasCatalogSectionProps {
  search: string;
  canEdit: boolean;
}

const FrasesRapidasCatalogSection: React.FC<FrasesRapidasCatalogSectionProps> = ({
  search,
  canEdit,
}) => {
  const [rows, setRows] = useState<FraseRapidaMicrobiologia[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FraseForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listFrasesRapidasMicro({ search: search.trim() || undefined });
      setRows(data);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (row: FraseRapidaMicrobiologia) => {
    setEditingId(row.id);
    setForm({
      abreviatura: row.abreviatura,
      texto: row.texto,
      categoria: row.categoria || 'GENERAL',
      activo: row.activo !== false,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.abreviatura.trim() || !form.texto.trim()) {
      toast.error('Abreviatura y texto son obligatorios');
      return;
    }
    setSaving(true);
    try {
      const body = {
        abreviatura: form.abreviatura.trim(),
        texto: form.texto.trim(),
        categoria: form.categoria.trim() || 'GENERAL',
        activo: form.activo,
      };
      if (editingId) {
        await updateFraseRapidaMicro(editingId, body);
        toast.success('Frase actualizada');
      } else {
        await createFraseRapidaMicro(body);
        toast.success('Frase creada');
      }
      setDialogOpen(false);
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async (row: FraseRapidaMicrobiologia) => {
    try {
      await updateFraseRapidaMicro(row.id, { activo: false });
      toast.success('Frase desactivada');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    }
  };

  return (
    <Box>
      {canEdit && (
        <Button startIcon={<AddIcon />} variant="contained" size="small" sx={{ mb: 1 }} onClick={openCreate}>
          Nueva frase
        </Button>
      )}
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Abreviatura</TableCell>
              <TableCell>Texto</TableCell>
              <TableCell>Categoría</TableCell>
              <TableCell>Origen</TableCell>
              <TableCell>Estado</TableCell>
              {canEdit && <TableCell align="right" />}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 6 : 5}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 6 : 5}>
                  <Typography color="text.secondary">Sin frases.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.abreviatura}</TableCell>
                  <TableCell sx={{ maxWidth: 360 }}>
                    {(r.texto || '').slice(0, 120)}
                    {(r.texto || '').length > 120 ? '…' : ''}
                    {r.requiere_revision ? (
                      <Chip size="small" label="Revisión" color="warning" sx={{ ml: 1 }} />
                    ) : null}
                  </TableCell>
                  <TableCell>{r.categoria || '—'}</TableCell>
                  <TableCell>{r.origen || '—'}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={r.activo === false ? 'Inactivo' : 'Activo'}
                      color={r.activo === false ? 'default' : 'success'}
                      variant="outlined"
                    />
                  </TableCell>
                  {canEdit && (
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton size="small" onClick={() => openEdit(r)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        disabled={r.activo === false}
                        onClick={() => void deactivate(r)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? 'Editar frase' : 'Nueva frase rápida'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField
            label="Abreviatura"
            value={form.abreviatura}
            onChange={(e) => setForm((f) => ({ ...f, abreviatura: e.target.value }))}
            disabled={Boolean(editingId)}
            fullWidth
          />
          <TextField
            label="Texto para mostrar"
            value={form.texto}
            onChange={(e) => setForm((f) => ({ ...f, texto: e.target.value }))}
            multiline
            minRows={3}
            fullWidth
          />
          <TextField
            label="Categoría"
            value={form.categoria}
            onChange={(e) => setForm((f) => ({ ...f, categoria: e.target.value }))}
            helperText="GENERAL, HALLAZGO, INTERPRETACION, UMBRAL, FENOTIPO…"
            fullWidth
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.activo}
                onChange={(e) => setForm((f) => ({ ...f, activo: e.target.checked }))}
              />
            }
            label="Activo"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button variant="contained" disabled={saving} onClick={() => void handleSave()}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default FrasesRapidasCatalogSection;
