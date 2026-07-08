import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { LimsTipoMuestra } from '../../types/lims';
import { createTipoMuestraLims, listTiposMuestraLims, patchTipoMuestraLims } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsModule, canEditLimsCatalogos } from '../../utils/limsAccess';

const TiposMuestraCatalogo: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<LimsTipoMuestra[]>([]);
  const [loading, setLoading] = useState(true);
  const [codigo, setCodigo] = useState('');
  const [nombre, setNombre] = useState('');
  const [colorTubo, setColorTubo] = useState('');
  const [saving, setSaving] = useState(false);

  const allowed = canAccessLimsModule(currentUser);
  const canEdit = canEditLimsCatalogos(currentUser);

  const load = async () => {
    setLoading(true);
    try {
      const list = await listTiposMuestraLims();
      setRows(list);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (allowed) load();
  }, [allowed]);

  const handleCrear = async () => {
    if (!codigo.trim() || !nombre.trim()) {
      toast.error('Código y nombre son obligatorios');
      return;
    }
    setSaving(true);
    try {
      await createTipoMuestraLims({
        codigo: codigo.trim().toUpperCase(),
        nombre: nombre.trim(),
        color_tubo: colorTubo.trim() || undefined,
        activo: true,
      });
      toast.success('Tipo de muestra agregado');
      setCodigo('');
      setNombre('');
      setColorTubo('');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const toggleActivo = async (row: LimsTipoMuestra) => {
    if (!canEdit) return;
    try {
      await patchTipoMuestraLims(row.id, { activo: row.activo === false });
      toast.success(row.activo === false ? 'Tipo reactivado' : 'Tipo desactivado');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    }
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso al módulo LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/ordenes')} sx={{ mb: 1 }}>
        ← Órdenes LIMS
      </Button>
      <Typography variant="h5" gutterBottom>
        Tipos de muestra
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Catálogo de muestras biológicas (sangre, orina, etc.). Aparecen al tomar muestras en una orden. Podés agregar
        nuevos tipos cuando el laboratorio los incorpore.
      </Typography>

      {rows.length === 0 && !loading && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No hay tipos de muestra cargados. Agregá al menos sangre y orina, o ejecutá{' '}
          <code>python manage.py seed_catalogo_solicitud_papel</code> en el servidor.
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Color / tubo</TableCell>
              <TableCell>Estado</TableCell>
              {canEdit && <TableCell align="right">Acción</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 5 : 4}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 5 : 4}>
                  <Typography color="text.secondary">Sin registros.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.color_tubo || '—'}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={r.activo === false ? 'Inactivo' : 'Activo'}
                      color={r.activo === false ? 'default' : 'success'}
                      variant="outlined"
                    />
                  </TableCell>
                  {canEdit && (
                    <TableCell align="right">
                      <Button size="small" onClick={() => toggleActivo(r)}>
                        {r.activo === false ? 'Reactivar' : 'Desactivar'}
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {canEdit && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Agregar tipo de muestra
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-start' }}>
            <TextField
              size="small"
              label="Código"
              value={codigo}
              onChange={(ev) => setCodigo(ev.target.value.toUpperCase())}
              inputProps={{ maxLength: 10 }}
              helperText="Máx. 10 caracteres (ej. SANGRE, ORINA)"
            />
            <TextField
              size="small"
              label="Nombre"
              value={nombre}
              onChange={(ev) => setNombre(ev.target.value)}
              helperText="Ej. Sangre (Suero), Orina"
            />
            <TextField
              size="small"
              label="Color / tubo (opcional)"
              value={colorTubo}
              onChange={(ev) => setColorTubo(ev.target.value)}
            />
            <Button variant="contained" onClick={handleCrear} disabled={saving}>
              {saving ? 'Guardando…' : 'Agregar'}
            </Button>
          </Box>
        </Paper>
      )}

      {!canEdit && (
        <Typography variant="caption" color="text.secondary">
          Solo lectura: la carga de tipos requiere rol laboratorio o administrador.
        </Typography>
      )}
    </Box>
  );
};

export default TiposMuestraCatalogo;
