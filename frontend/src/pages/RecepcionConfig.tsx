import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import {
  deleteReglaRecepcion,
  listPuestosRecepcion,
  listReglasRecepcion,
  savePuestoRecepcion,
  saveReglaRecepcion,
} from '../services/recepcionApi';
import type { PuestoRecepcion, ReglaRuteoRecepcion } from '../types/recepcion';
import { getSafeClinicalActionMessage } from '../utils/apiError';

const TIPOS = [
  { value: '', label: '(Cualquier tipo)' },
  { value: 'CONSULTA', label: 'Consulta médica' },
  { value: 'ESTUDIO', label: 'Estudio' },
  { value: 'PROCEDIMIENTO', label: 'Procedimiento' },
  { value: 'CIRUGIA', label: 'Cirugía' },
  { value: 'EXTRACCION', label: 'Extracción' },
  { value: 'SIN_TURNO', label: 'Sin turno' },
];

const RecepcionConfig: React.FC = () => {
  const [puestos, setPuestos] = useState<PuestoRecepcion[]>([]);
  const [reglas, setReglas] = useState<ReglaRuteoRecepcion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [nuevaRegla, setNuevaRegla] = useState({
    puesto: 0,
    nombre: '',
    tipo_actividad: 'CONSULTA',
    prioridad: 50,
  });

  const reload = async () => {
    const [p, r] = await Promise.all([listPuestosRecepcion(), listReglasRecepcion()]);
    setPuestos(p);
    setReglas(r);
    if (!nuevaRegla.puesto && p[0]) setNuevaRegla((n) => ({ ...n, puesto: p[0].id }));
  };

  useEffect(() => {
    reload().catch((e) => setError(getSafeClinicalActionMessage(e, 'No se pudo cargar.')));
  }, []);

  const togglePuesto = async (p: PuestoRecepcion, patch: Partial<PuestoRecepcion>) => {
    setError(null);
    try {
      await savePuestoRecepcion({ ...p, ...patch, codigo: p.codigo, nombre: p.nombre }, p.id);
      setOk('Puesto actualizado.');
      await reload();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo guardar el puesto.'));
    }
  };

  const crearRegla = async () => {
    if (!nuevaRegla.puesto) return;
    setError(null);
    try {
      await saveReglaRecepcion({
        puesto: nuevaRegla.puesto,
        nombre: nuevaRegla.nombre || undefined,
        tipo_actividad: nuevaRegla.tipo_actividad as any,
        prioridad: nuevaRegla.prioridad,
        activo: true,
      });
      setOk('Regla creada.');
      await reload();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo crear la regla.'));
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Configuración de recepción
      </Typography>
      <Button
        href="/recepcion/qr-anuncio"
        variant="outlined"
        sx={{ mb: 2 }}
      >
        Imprimir QR de anuncio
      </Button>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Puestos físicos neutrales (Puesto 1 / Puesto 2 / Sala de extracción). Qué atiende cada
        secretaria (T/S/E/P) se configura en el tablero como <strong>cobertura del día</strong>. Las
        reglas tipo→puesto quedan solo para laboratorio (EXTRACCION → Sala de extracción).
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {ok && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setOk(null)}>
          {ok}
        </Alert>
      )}

      <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
        Puestos
      </Typography>
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre / etiqueta paciente</TableCell>
              <TableCell>Modo</TableCell>
              <TableCell>Activo</TableCell>
              <TableCell>Fallback</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {puestos.map((p) => (
              <TableRow key={p.id}>
                <TableCell>{p.codigo}</TableCell>
                <TableCell>
                  <TextField
                    size="small"
                    label="Nombre"
                    value={p.nombre}
                    onBlur={(e) => {
                      if (e.target.value !== p.nombre)
                        void togglePuesto(p, { nombre: e.target.value });
                    }}
                    onChange={(e) =>
                      setPuestos((rows) =>
                        rows.map((x) => (x.id === p.id ? { ...x, nombre: e.target.value } : x))
                      )
                    }
                    sx={{ mb: 1, mr: 1, minWidth: 160 }}
                  />
                  <TextField
                    size="small"
                    label="Etiqueta paciente"
                    value={p.etiqueta_paciente || ''}
                    onBlur={(e) => {
                      if (e.target.value !== (p.etiqueta_paciente || ''))
                        void togglePuesto(p, { etiqueta_paciente: e.target.value });
                    }}
                    onChange={(e) =>
                      setPuestos((rows) =>
                        rows.map((x) =>
                          x.id === p.id ? { ...x, etiqueta_paciente: e.target.value } : x
                        )
                      )
                    }
                    sx={{ minWidth: 220 }}
                  />
                </TableCell>
                <TableCell>
                  <Select
                    size="small"
                    value={p.modo}
                    onChange={(e) => void togglePuesto(p, { modo: e.target.value as any })}
                  >
                    <MenuItem value="REGLAS">Por reglas</MenuItem>
                    <MenuItem value="TODO">Todo</MenuItem>
                  </Select>
                </TableCell>
                <TableCell>
                  <Checkbox
                    checked={p.activo}
                    onChange={(e) => void togglePuesto(p, { activo: e.target.checked })}
                  />
                </TableCell>
                <TableCell>
                  <Checkbox
                    checked={p.es_fallback}
                    onChange={(e) => void togglePuesto(p, { es_fallback: e.target.checked })}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Reglas de ruteo (legacy / laboratorio)
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        Deprecado para secretaría: el ruteo T/S/E/P es por cobertura del día. Mantener solo la regla{' '}
        <strong>EXTRACCION → Sala de extracción</strong>.
      </Alert>
      <Paper sx={{ p: 2, mb: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Puesto</InputLabel>
          <Select
            label="Puesto"
            value={nuevaRegla.puesto || ''}
            onChange={(e) => setNuevaRegla((n) => ({ ...n, puesto: Number(e.target.value) }))}
          >
            {puestos.map((p) => (
              <MenuItem key={p.id} value={p.id}>
                {p.nombre}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Tipo</InputLabel>
          <Select
            label="Tipo"
            value={nuevaRegla.tipo_actividad}
            onChange={(e) => setNuevaRegla((n) => ({ ...n, tipo_actividad: e.target.value }))}
          >
            {TIPOS.filter((t) => t.value).map((t) => (
              <MenuItem key={t.value} value={t.value}>
                {t.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          size="small"
          label="Prioridad"
          type="number"
          value={nuevaRegla.prioridad}
          onChange={(e) =>
            setNuevaRegla((n) => ({ ...n, prioridad: Number(e.target.value) || 50 }))
          }
          sx={{ width: 110 }}
        />
        <TextField
          size="small"
          label="Nombre (opcional)"
          value={nuevaRegla.nombre}
          onChange={(e) => setNuevaRegla((n) => ({ ...n, nombre: e.target.value }))}
        />
        <Button variant="contained" onClick={() => void crearRegla()}>
          Agregar regla
        </Button>
      </Paper>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Prioridad</TableCell>
              <TableCell>Puesto</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Activa</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {reglas.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.prioridad}</TableCell>
                <TableCell>{r.puesto_nombre}</TableCell>
                <TableCell>{r.tipo_actividad || '(cualquiera)'}</TableCell>
                <TableCell>{r.nombre || '—'}</TableCell>
                <TableCell>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={r.activo}
                        onChange={async (e) => {
                          await saveReglaRecepcion(
                            { puesto: r.puesto, activo: e.target.checked },
                            r.id
                          );
                          await reload();
                        }}
                      />
                    }
                    label=""
                  />
                </TableCell>
                <TableCell>
                  <Button
                    size="small"
                    color="error"
                    onClick={async () => {
                      await deleteReglaRecepcion(r.id);
                      await reload();
                    }}
                  >
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default RecepcionConfig;
