import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormLabel,
  ListItemText,
  Paper,
  Radio,
  RadioGroup,
  TextField,
  Typography,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import FilterListIcon from '@mui/icons-material/FilterList';
import { useData } from '../../contexts/DataContext';
import {
  downloadFiltrosAvanzadosExcel,
  listTiposExamenLims,
  postFiltrosAvanzadosPreview,
  type FiltrosAvanzadosPreview,
} from '../../services/limsApi';
import type { LimsTipoExamen } from '../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessFiltrosAvanzados } from '../../utils/limsAccess';

type ModoUi = 'all' | 'any';

const FiltrosAvanzadosPage: React.FC = () => {
  const { currentUser } = useData();
  const allowed = canAccessFiltrosAvanzados(currentUser);

  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [selected, setSelected] = useState<LimsTipoExamen[]>([]);
  const [obligatorios, setObligatorios] = useState<Set<string>>(new Set());
  const [modo, setModo] = useState<ModoUi>('all');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [loadingCat, setLoadingCat] = useState(true);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingExcel, setLoadingExcel] = useState(false);
  const [preview, setPreview] = useState<FiltrosAvanzadosPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    (async () => {
      setLoadingCat(true);
      try {
        const list = await listTiposExamenLims({ activo: true });
        if (!cancelled) setExamenes(list);
      } catch {
        if (!cancelled) setError('No se pudo cargar el catálogo de exámenes.');
      } finally {
        if (!cancelled) setLoadingCat(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [allowed]);

  const codigos = useMemo(
    () => selected.map((e) => (e.codigo || '').trim().toUpperCase()).filter(Boolean),
    [selected]
  );

  const body = useMemo(
    () => ({
      codigos,
      modo,
      obligatorios: modo === 'any' ? Array.from(obligatorios) : undefined,
      desde: desde || undefined,
      hasta: hasta || undefined,
    }),
    [codigos, desde, hasta, modo, obligatorios]
  );

  const toggleObligatorio = (codigo: string) => {
    const c = codigo.trim().toUpperCase();
    setObligatorios((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
    setPreview(null);
  };

  const consultar = useCallback(async () => {
    if (codigos.length === 0) {
      setError('Seleccioná al menos un examen.');
      return;
    }
    setLoadingPreview(true);
    setError(null);
    try {
      const data = await postFiltrosAvanzadosPreview(body);
      setPreview(data);
    } catch (e) {
      setPreview(null);
      setError(
        getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.genericClinicalAction)
      );
    } finally {
      setLoadingPreview(false);
    }
  }, [body, codigos.length]);

  const descargar = useCallback(async () => {
    if (codigos.length === 0) {
      setError('Seleccioná al menos un examen.');
      return;
    }
    setLoadingExcel(true);
    setError(null);
    try {
      await downloadFiltrosAvanzadosExcel(body);
    } catch (e) {
      setError(
        getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.genericClinicalAction)
      );
    } finally {
      setLoadingExcel(false);
    }
  }, [body, codigos.length]);

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tenés permiso para filtros avanzados.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 960 }}>
      <Typography variant="h5" gutterBottom>
        Filtros avanzados
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Definí los exámenes requeridos para armar el listado de pacientes del estudio. El sistema
        cuenta cuántos pacientes cumplen el criterio y permite descargar un Excel (una fila por
        orden; los exámenes elegidos van en columnas). Contiene DNI: uso local/estudio.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Autocomplete
          multiple
          loading={loadingCat}
          options={examenes}
          value={selected}
          onChange={(_, v) => {
            setSelected(v);
            const keep = new Set(
              v.map((e) => (e.codigo || '').trim().toUpperCase()).filter(Boolean)
            );
            setObligatorios((prev) => new Set(Array.from(prev).filter((c) => keep.has(c))));
            setPreview(null);
          }}
          getOptionLabel={(o) => `${o.codigo} — ${o.nombre}`}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          filterSelectedOptions
          renderTags={(value, getTagProps) =>
            value.map((option, index) => {
              const code = (option.codigo || '').trim().toUpperCase();
              const obl = modo === 'any' && obligatorios.has(code);
              return (
                <Chip
                  {...getTagProps({ index })}
                  key={option.id}
                  size="small"
                  color={obl ? 'primary' : 'default'}
                  label={obl ? `${code} · obligatorio` : code}
                />
              );
            })
          }
          renderInput={(params) => (
            <TextField
              {...params}
              label="Exámenes a incluir en el filtro"
              placeholder="Buscá por código o nombre…"
              helperText="Seleccioná uno o más exámenes del catálogo."
            />
          )}
        />

        <FormControl sx={{ mt: 2, display: 'block' }}>
          <FormLabel>Criterio entre exámenes</FormLabel>
          <RadioGroup
            row
            value={modo}
            onChange={(e) => {
              setModo(e.target.value as ModoUi);
              setPreview(null);
            }}
          >
            <FormControlLabel
              value="all"
              control={<Radio />}
              label="Todos (debe tener cada examen seleccionado)"
            />
            <FormControlLabel
              value="any"
              control={<Radio />}
              label="Algunos (obligatorios definen la cohorte; el resto solo columnas)"
            />
          </RadioGroup>
        </FormControl>

        {modo === 'any' && selected.length > 0 ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Obligatorios dentro de «Algunos»
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Los marcados definen quién entra (debe tener todos). Los no marcados no
              reducen la cantidad: en el Excel aparecen como columnas y se completan
              solo si esa orden también los tenía. Si no marcás ninguno, alcanza con
              cualquiera de los seleccionados (OR).
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {selected.map((ex) => {
                const code = (ex.codigo || '').trim().toUpperCase();
                return (
                  <FormControlLabel
                    key={ex.id}
                    control={
                      <Checkbox
                        checked={obligatorios.has(code)}
                        onChange={() => toggleObligatorio(code)}
                        size="small"
                      />
                    }
                    label={
                      <ListItemText
                        primary={`${code} — ${ex.nombre}`}
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    }
                  />
                );
              })}
            </Box>
          </Box>
        ) : null}

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 2 }}>
          <TextField
            size="small"
            type="date"
            label="Desde"
            InputLabelProps={{ shrink: true }}
            value={desde}
            onChange={(e) => {
              setDesde(e.target.value);
              setPreview(null);
            }}
          />
          <TextField
            size="small"
            type="date"
            label="Hasta"
            InputLabelProps={{ shrink: true }}
            value={hasta}
            onChange={(e) => {
              setHasta(e.target.value);
              setPreview(null);
            }}
          />
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mt: 2 }}>
          <Button
            variant="contained"
            startIcon={loadingPreview ? <CircularProgress size={16} /> : <FilterListIcon />}
            onClick={() => void consultar()}
            disabled={loadingPreview || loadingCat || codigos.length === 0}
          >
            Consultar cantidad
          </Button>
          <Button
            variant="outlined"
            startIcon={loadingExcel ? <CircularProgress size={16} /> : <DownloadIcon />}
            onClick={() => void descargar()}
            disabled={loadingExcel || loadingCat || codigos.length === 0}
          >
            Descargar Excel
          </Button>
        </Box>
      </Paper>

      {error ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {preview ? (
        <Alert severity="info">
          <Typography variant="body1" fontWeight={600}>
            {preview.pacientes} paciente{preview.pacientes === 1 ? '' : 's'} cumplen el criterio
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            Modo: {preview.modo === 'all' ? 'Todos' : 'Algunos'} · Exámenes:{' '}
            {(preview.codigos || []).join(', ') || '—'}
            {preview.modo === 'any' && (preview.obligatorios || []).length > 0
              ? ` · Obligatorios: ${(preview.obligatorios || []).join(', ')}`
              : ''}
            {preview.desde || preview.hasta
              ? ` · Ventana: ${preview.desde || '…'} → ${preview.hasta || '…'}`
              : ''}
          </Typography>
        </Alert>
      ) : null}
    </Box>
  );
};

export default FiltrosAvanzadosPage;
