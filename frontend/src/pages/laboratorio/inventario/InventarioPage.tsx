import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import {
  createConsumoInsumoExamen,
  createInsumoLab,
  createLoteInsumo,
  deleteConsumoInsumoExamen,
  deleteInsumoLab,
  deleteLoteInsumo,
  getInventarioAlertas,
  listConsumosInsumoExamen,
  listEquiposQc,
  listInsumosLab,
  listLotesInsumo,
  listMovimientosStock,
  listTiposExamenLims,
  patchConsumoInsumoExamen,
  patchInsumoLab,
  patchLoteInsumo,
  type ConsumoInsumoExamen,
  type EquipoAnalizador,
  type InsumoLab,
  type InventarioAlertas,
  type LoteInsumo,
  type MovimientoStock,
} from '../../../services/limsApi';
import type { LimsTipoExamen } from '../../../types/lims';
import { getSafeApiErrorMessage, isProtectedDeleteError } from '../../../utils/apiError';

type ProductoTipo = InsumoLab['tipo'];

const UNIDADES_COMUNES = ['cartucho', 'ml', 'test', 'pack'] as const;

const emptyReactivoForm = {
  codigo: '',
  nombre: '',
  unidad: 'cartucho',
  stock_min: '10',
  proveedor: '',
  volumen_por_unidad: '',
  composicion: '' as InsumoLab['composicion'],
  canal_analizador: '' as InsumoLab['canal_analizador'],
  equipo: '',
};

const emptyInsumoForm = {
  codigo: '',
  nombre: '',
  tipo: 'TUBO' as Exclude<ProductoTipo, 'REACTIVO'>,
  unidad: 'tubo',
  stock_min: '20',
  proveedor: '',
};

const labelComposicion = (c: string) => {
  if (c === 'SOLO_A') return 'Solo A';
  if (c === 'A_B') return 'A+B';
  if (c === 'OTRO') return 'Otro';
  return '—';
};

const labelCanal = (c: string) => {
  if (c === 'DEDICADO') return 'Dedicada';
  if (c === 'ABIERTO') return 'Abierta';
  return '—';
};

/**
 * Inventario LIMS
 * - Reactivos: químicos/kits (se descuentan al cargar resultados).
 * - Insumos: tubos, medios, otros.
 * - Consumo por ensayo: qué reactivo baja cada determinación.
 */
const InventarioPage: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [productos, setProductos] = useState<InsumoLab[]>([]);
  const [lotes, setLotes] = useState<LoteInsumo[]>([]);
  const [movimientos, setMovimientos] = useState<MovimientoStock[]>([]);
  const [consumos, setConsumos] = useState<ConsumoInsumoExamen[]>([]);
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [equipos, setEquipos] = useState<EquipoAnalizador[]>([]);
  const [alertas, setAlertas] = useState<InventarioAlertas | null>(null);
  const [loading, setLoading] = useState(true);
  const [filtroEquipo, setFiltroEquipo] = useState('');
  const [examenId, setExamenId] = useState('');

  const [reactivoForm, setReactivoForm] = useState(emptyReactivoForm);
  const [insumoForm, setInsumoForm] = useState(emptyInsumoForm);
  const [loteForm, setLoteForm] = useState({
    producto: '',
    codigo_lote: '',
    cantidad: '',
    fecha_vencimiento: '',
  });
  const [consumoForm, setConsumoForm] = useState({
    reactivo: '',
    cantidad: '1',
    etiqueta: '',
  });
  const [editingReactivoId, setEditingReactivoId] = useState<number | null>(null);
  const [editingInsumoId, setEditingInsumoId] = useState<number | null>(null);
  const [editingLoteId, setEditingLoteId] = useState<number | null>(null);
  const [editingConsumoId, setEditingConsumoId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [i, l, m, a, c, ex, eq] = await Promise.all([
        listInsumosLab({ activo: true }),
        listLotesInsumo(),
        listMovimientosStock(),
        getInventarioAlertas(),
        listConsumosInsumoExamen({
          equipo: filtroEquipo || undefined,
          activo: true,
        }),
        listTiposExamenLims({ activo: true }),
        listEquiposQc(),
      ]);
      setProductos(i);
      setLotes(l.filter((x) => x.activo));
      setMovimientos(m);
      setAlertas(a);
      setConsumos(c);
      setExamenes(ex);
      setEquipos(eq.filter((e) => e.activo));
    } catch (e) {
      toast.error(getSafeApiErrorMessage(e, 'Error cargando inventario'));
    } finally {
      setLoading(false);
    }
  }, [filtroEquipo]);

  useEffect(() => {
    load();
  }, [load]);

  const reactivos = useMemo(
    () => productos.filter((p) => p.tipo === 'REACTIVO'),
    [productos]
  );
  const insumos = useMemo(
    () => productos.filter((p) => p.tipo !== 'REACTIVO'),
    [productos]
  );

  const examenesFiltrados = useMemo(() => {
    let list = examenes;
    if (filtroEquipo) {
      list = list.filter((e) => e.equipo_analizador_codigo === filtroEquipo);
    }
    return list.slice().sort((a, b) => a.codigo.localeCompare(b.codigo));
  }, [examenes, filtroEquipo]);

  const consumosVisibles = useMemo(() => {
    if (!examenId) return consumos;
    const id = Number(examenId);
    return consumos.filter((c) => c.tipo_examen === id);
  }, [consumos, examenId]);

  const pedidosReactivos = useMemo(
    () => (alertas?.pedidos || []).filter((p) => p.tipo === 'REACTIVO'),
    [alertas]
  );
  const pedidosInsumos = useMemo(
    () => (alertas?.pedidos || []).filter((p) => p.tipo !== 'REACTIVO'),
    [alertas]
  );

  const productoLote = useMemo(
    () => productos.find((p) => String(p.id) === loteForm.producto),
    [productos, loteForm.producto]
  );

  const submitReactivo = async () => {
    try {
      const body = {
        codigo: reactivoForm.codigo.trim(),
        nombre: reactivoForm.nombre.trim(),
        tipo: 'REACTIVO' as const,
        unidad: reactivoForm.unidad.trim() || 'u',
        stock_min: Number(reactivoForm.stock_min) || 0,
        proveedor: reactivoForm.proveedor.trim(),
        volumen_por_unidad: reactivoForm.volumen_por_unidad
          ? reactivoForm.volumen_por_unidad
          : null,
        composicion: reactivoForm.composicion,
        canal_analizador: reactivoForm.canal_analizador,
        equipo: reactivoForm.equipo ? Number(reactivoForm.equipo) : null,
        activo: true,
      };
      if (editingReactivoId) {
        await patchInsumoLab(editingReactivoId, body);
        toast.success('Reactivo actualizado');
      } else {
        await createInsumoLab(body);
        toast.success('Reactivo creado');
      }
      setReactivoForm(emptyReactivoForm);
      setEditingReactivoId(null);
      load();
    } catch (e) {
      toast.error(getSafeApiErrorMessage(e, 'No se pudo guardar el reactivo'));
    }
  };

  const submitInsumo = async () => {
    try {
      const body = {
        codigo: insumoForm.codigo.trim(),
        nombre: insumoForm.nombre.trim(),
        tipo: insumoForm.tipo,
        unidad: insumoForm.unidad.trim() || 'u',
        stock_min: Number(insumoForm.stock_min) || 0,
        proveedor: insumoForm.proveedor.trim(),
        activo: true,
      };
      if (editingInsumoId) {
        await patchInsumoLab(editingInsumoId, body);
        toast.success('Insumo actualizado');
      } else {
        await createInsumoLab(body);
        toast.success('Insumo creado');
      }
      setInsumoForm(emptyInsumoForm);
      setEditingInsumoId(null);
      load();
    } catch (e) {
      toast.error(getSafeApiErrorMessage(e, 'No se pudo guardar el insumo'));
    }
  };

  const submitLote = async () => {
    const cantidad = Number(loteForm.cantidad) || 0;
    if (!loteForm.producto || !loteForm.codigo_lote.trim() || cantidad <= 0) {
      toast.error('Completá producto, lote y cantidad');
      return;
    }
    try {
      const body = {
        insumo: Number(loteForm.producto),
        codigo_lote: loteForm.codigo_lote.trim(),
        cantidad,
        fecha_vencimiento: loteForm.fecha_vencimiento || null,
      };
      if (editingLoteId) {
        await patchLoteInsumo(editingLoteId, body);
        toast.success('Lote actualizado');
      } else {
        await createLoteInsumo(body);
        toast.success('Lote cargado');
      }
      setLoteForm({ producto: '', codigo_lote: '', cantidad: '', fecha_vencimiento: '' });
      setEditingLoteId(null);
      load();
    } catch (e) {
      toast.error(getSafeApiErrorMessage(e, 'No se pudo guardar el lote'));
    }
  };

  const submitConsumo = async () => {
    if (!examenId || !consumoForm.reactivo) {
      toast.error('Elegí el ensayo y el reactivo a descontar');
      return;
    }
    try {
      if (editingConsumoId) {
        await patchConsumoInsumoExamen(editingConsumoId, {
          tipo_examen: Number(examenId),
          insumo: Number(consumoForm.reactivo),
          cantidad_por_determinacion: Number(consumoForm.cantidad) || 1,
          rol: consumoForm.etiqueta.trim(),
        });
        toast.success('Consumo actualizado');
      } else {
        await createConsumoInsumoExamen({
          tipo_examen: Number(examenId),
          insumo: Number(consumoForm.reactivo),
          cantidad_por_determinacion: Number(consumoForm.cantidad) || 1,
          rol: consumoForm.etiqueta.trim(),
          activo: true,
        });
        toast.success('Consumo vinculado al ensayo');
      }
      setConsumoForm({ reactivo: '', cantidad: '1', etiqueta: '' });
      setEditingConsumoId(null);
      load();
    } catch (e) {
      toast.error(getSafeApiErrorMessage(e, 'No se pudo guardar'));
    }
  };

  const deleteWithFallback = async (
    label: string,
    doDelete: () => Promise<unknown>,
    doDeactivate?: () => Promise<unknown>
  ) => {
    if (!window.confirm(`¿Eliminar ${label}?`)) return;
    try {
      await doDelete();
      toast.success('Eliminado');
      load();
    } catch (e) {
      if (doDeactivate && isProtectedDeleteError(e)) {
        if (
          window.confirm(
            'No se puede borrar porque tiene registros relacionados. ¿Desactivar en su lugar?'
          )
        ) {
          try {
            await doDeactivate();
            toast.success('Desactivado');
            load();
          } catch (e2) {
            toast.error(getSafeApiErrorMessage(e2, 'No se pudo desactivar'));
          }
        }
        return;
      }
      toast.error(getSafeApiErrorMessage(e, 'No se pudo eliminar'));
    }
  };

  const quitarConsumo = async (id: number) => {
    if (!window.confirm('¿Quitar este vínculo de consumo?')) return;
    try {
      await deleteConsumoInsumoExamen(id);
      toast.success('Vínculo quitado');
      if (editingConsumoId === id) {
        setEditingConsumoId(null);
        setConsumoForm({ reactivo: '', cantidad: '1', etiqueta: '' });
      }
      load();
    } catch (e) {
      toast.error(getSafeApiErrorMessage(e, 'No se pudo quitar'));
    }
  };

  const startEditReactivo = (r: InsumoLab) => {
    setEditingReactivoId(r.id);
    setReactivoForm({
      codigo: r.codigo,
      nombre: r.nombre,
      unidad: r.unidad || 'cartucho',
      stock_min: String(r.stock_min ?? 0),
      proveedor: r.proveedor || '',
      volumen_por_unidad: r.volumen_por_unidad != null ? String(r.volumen_por_unidad) : '',
      composicion: r.composicion || '',
      canal_analizador: r.canal_analizador || '',
      equipo: r.equipo != null ? String(r.equipo) : '',
    });
  };

  const startEditInsumo = (i: InsumoLab) => {
    setEditingInsumoId(i.id);
    setInsumoForm({
      codigo: i.codigo,
      nombre: i.nombre,
      tipo: (i.tipo === 'REACTIVO' ? 'TUBO' : i.tipo) as typeof emptyInsumoForm.tipo,
      unidad: i.unidad || 'tubo',
      stock_min: String(i.stock_min ?? 0),
      proveedor: i.proveedor || '',
    });
  };

  const startEditLote = (l: LoteInsumo) => {
    setEditingLoteId(l.id);
    setLoteForm({
      producto: String(l.insumo),
      codigo_lote: l.codigo_lote,
      cantidad: String(l.cantidad),
      fecha_vencimiento: l.fecha_vencimiento || '',
    });
  };

  const startEditConsumo = (c: ConsumoInsumoExamen) => {
    setEditingConsumoId(c.id);
    setExamenId(String(c.tipo_examen));
    setConsumoForm({
      reactivo: String(c.insumo),
      cantidad: String(c.cantidad_por_determinacion),
      etiqueta: c.rol || '',
    });
  };

  const labelTipoInsumo = (t: string) => {
    if (t === 'TUBO') return 'Tubo / contenedor';
    if (t === 'MEDIO') return 'Medio de cultivo';
    return 'Otro';
  };

  return (
    <Box sx={{ p: 2, maxWidth: 1200 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Inventario de laboratorio
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Reactivos (determinaciones) e insumos (tubos/medios). El stock se carga por lote; los
        reactivos vinculados a un ensayo se descuentan al cargar el primer resultado.
      </Typography>

      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable">
        <Tab label="Reactivos" />
        <Tab label="Insumos" />
        <Tab label="Lotes" />
        <Tab label="Consumo por ensayo" />
        <Tab label="Movimientos" />
        <Tab label="Pedidos / alertas" />
      </Tabs>
      {loading && <CircularProgress size={24} sx={{ mb: 2 }} />}

      {tab === 0 && (
        <Box>
          <Stack spacing={1.5} sx={{ mb: 2 }}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} flexWrap="wrap" useFlexGap>
              <TextField
                size="small"
                label="Código"
                value={reactivoForm.codigo}
                onChange={(e) => setReactivoForm((p) => ({ ...p, codigo: e.target.value }))}
                sx={{ width: 130 }}
              />
              <TextField
                size="small"
                label="Nombre"
                value={reactivoForm.nombre}
                onChange={(e) => setReactivoForm((p) => ({ ...p, nombre: e.target.value }))}
                sx={{ flex: 1, minWidth: 180 }}
              />
              <FormControl size="small" sx={{ width: 130 }}>
                <InputLabel>Unidad</InputLabel>
                <Select
                  label="Unidad"
                  value={reactivoForm.unidad}
                  onChange={(e) => setReactivoForm((p) => ({ ...p, unidad: e.target.value }))}
                >
                  {UNIDADES_COMUNES.map((u) => (
                    <MenuItem key={u} value={u}>
                      {u}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                size="small"
                label="ml / envase"
                type="number"
                value={reactivoForm.volumen_por_unidad}
                onChange={(e) =>
                  setReactivoForm((p) => ({ ...p, volumen_por_unidad: e.target.value }))
                }
                sx={{ width: 120 }}
              />
              <TextField
                size="small"
                label="Stock mín."
                type="number"
                value={reactivoForm.stock_min}
                onChange={(e) => setReactivoForm((p) => ({ ...p, stock_min: e.target.value }))}
                sx={{ width: 100 }}
              />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} flexWrap="wrap" useFlexGap>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Contenido</InputLabel>
                <Select
                  label="Contenido"
                  value={reactivoForm.composicion}
                  onChange={(e) =>
                    setReactivoForm((p) => ({
                      ...p,
                      composicion: e.target.value as InsumoLab['composicion'],
                    }))
                  }
                >
                  <MenuItem value="">—</MenuItem>
                  <MenuItem value="SOLO_A">Solo A</MenuItem>
                  <MenuItem value="A_B">A+B mismo envase</MenuItem>
                  <MenuItem value="OTRO">Otro</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Línea</InputLabel>
                <Select
                  label="Línea"
                  value={reactivoForm.canal_analizador}
                  onChange={(e) =>
                    setReactivoForm((p) => ({
                      ...p,
                      canal_analizador: e.target.value as InsumoLab['canal_analizador'],
                    }))
                  }
                >
                  <MenuItem value="">—</MenuItem>
                  <MenuItem value="DEDICADO">Dedicada</MenuItem>
                  <MenuItem value="ABIERTO">Abierta</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Equipo</InputLabel>
                <Select
                  label="Equipo"
                  value={reactivoForm.equipo}
                  onChange={(e) => setReactivoForm((p) => ({ ...p, equipo: e.target.value }))}
                >
                  <MenuItem value="">—</MenuItem>
                  {equipos.map((eq) => (
                    <MenuItem key={eq.id} value={String(eq.id)}>
                      {eq.codigo}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                size="small"
                label="Proveedor"
                value={reactivoForm.proveedor}
                onChange={(e) => setReactivoForm((p) => ({ ...p, proveedor: e.target.value }))}
                sx={{ minWidth: 160 }}
              />
              <Button variant="contained" onClick={submitReactivo}>
                {editingReactivoId ? 'Guardar' : 'Alta reactivo'}
              </Button>
              {editingReactivoId && (
                <Button
                  variant="outlined"
                  onClick={() => {
                    setEditingReactivoId(null);
                    setReactivoForm(emptyReactivoForm);
                  }}
                >
                  Cancelar
                </Button>
              )}
            </Stack>
          </Stack>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Código</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Unidad</TableCell>
                <TableCell align="right">ml/env.</TableCell>
                <TableCell>Contenido</TableCell>
                <TableCell>Línea</TableCell>
                <TableCell>Equipo</TableCell>
                <TableCell align="right">Stock</TableCell>
                <TableCell align="right">Mín.</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reactivos.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.unidad}</TableCell>
                  <TableCell align="right">{r.volumen_por_unidad ?? '—'}</TableCell>
                  <TableCell>{labelComposicion(r.composicion)}</TableCell>
                  <TableCell>{labelCanal(r.canal_analizador)}</TableCell>
                  <TableCell>{r.equipo_codigo || '—'}</TableCell>
                  <TableCell align="right">{r.stock_actual}</TableCell>
                  <TableCell align="right">{r.stock_min}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => startEditReactivo(r)}>
                      Editar
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={() =>
                        void deleteWithFallback(
                          `reactivo ${r.codigo}`,
                          () => deleteInsumoLab(r.id),
                          () => patchInsumoLab(r.id, { activo: false })
                        )
                      }
                    >
                      Eliminar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {reactivos.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10}>
                    <Typography variant="body2" color="text.secondary">
                      Sin reactivos aún.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 1 && (
        <Box>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            sx={{ mb: 2 }}
            flexWrap="wrap"
            useFlexGap
          >
            <TextField
              size="small"
              label="Código"
              value={insumoForm.codigo}
              onChange={(e) => setInsumoForm((p) => ({ ...p, codigo: e.target.value }))}
            />
            <TextField
              size="small"
              label="Nombre"
              value={insumoForm.nombre}
              onChange={(e) => setInsumoForm((p) => ({ ...p, nombre: e.target.value }))}
              sx={{ minWidth: 180 }}
            />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Tipo</InputLabel>
              <Select
                label="Tipo"
                value={insumoForm.tipo}
                onChange={(e) =>
                  setInsumoForm((p) => ({
                    ...p,
                    tipo: e.target.value as typeof p.tipo,
                    unidad:
                      e.target.value === 'TUBO'
                        ? 'tubo'
                        : e.target.value === 'MEDIO'
                          ? 'placa'
                          : p.unidad,
                  }))
                }
              >
                <MenuItem value="TUBO">Tubo</MenuItem>
                <MenuItem value="MEDIO">Medio</MenuItem>
                <MenuItem value="OTRO">Otro</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Unidad"
              value={insumoForm.unidad}
              onChange={(e) => setInsumoForm((p) => ({ ...p, unidad: e.target.value }))}
              sx={{ width: 100 }}
            />
            <TextField
              size="small"
              label="Stock mín."
              type="number"
              value={insumoForm.stock_min}
              onChange={(e) => setInsumoForm((p) => ({ ...p, stock_min: e.target.value }))}
              sx={{ width: 100 }}
            />
            <TextField
              size="small"
              label="Proveedor"
              value={insumoForm.proveedor}
              onChange={(e) => setInsumoForm((p) => ({ ...p, proveedor: e.target.value }))}
            />
            <Button variant="contained" onClick={submitInsumo}>
              {editingInsumoId ? 'Guardar' : 'Alta insumo'}
            </Button>
            {editingInsumoId && (
              <Button
                variant="outlined"
                onClick={() => {
                  setEditingInsumoId(null);
                  setInsumoForm(emptyInsumoForm);
                }}
              >
                Cancelar
              </Button>
            )}
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Código</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Unidad</TableCell>
                <TableCell align="right">Stock</TableCell>
                <TableCell align="right">Mín.</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {insumos.map((i) => (
                <TableRow key={i.id}>
                  <TableCell>{i.codigo}</TableCell>
                  <TableCell>{i.nombre}</TableCell>
                  <TableCell>{labelTipoInsumo(i.tipo)}</TableCell>
                  <TableCell>{i.unidad}</TableCell>
                  <TableCell align="right">{i.stock_actual}</TableCell>
                  <TableCell align="right">{i.stock_min}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => startEditInsumo(i)}>
                      Editar
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={() =>
                        void deleteWithFallback(
                          `insumo ${i.codigo}`,
                          () => deleteInsumoLab(i.id),
                          () => patchInsumoLab(i.id, { activo: false })
                        )
                      }
                    >
                      Eliminar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 2 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Cantidad en la unidad del producto (cartuchos, ml, tests…).
            {productoLote
              ? ` Seleccionado: ${productoLote.codigo} → unidad “${productoLote.unidad}”${
                  productoLote.volumen_por_unidad
                    ? `, ${productoLote.volumen_por_unidad} ml/envase`
                    : ''
                }.`
              : ''}
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
            <FormControl size="small" sx={{ minWidth: 260 }}>
              <InputLabel>Producto</InputLabel>
              <Select
                label="Producto"
                value={loteForm.producto}
                onChange={(e) => setLoteForm((p) => ({ ...p, producto: e.target.value }))}
              >
                <MenuItem disabled value="">
                  — Reactivos —
                </MenuItem>
                {reactivos.map((r) => (
                  <MenuItem key={r.id} value={String(r.id)}>
                    {r.codigo} ({r.unidad})
                  </MenuItem>
                ))}
                <MenuItem disabled value=" ">
                  — Insumos —
                </MenuItem>
                {insumos.map((i) => (
                  <MenuItem key={i.id} value={String(i.id)}>
                    {i.codigo} ({i.unidad})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Lote"
              value={loteForm.codigo_lote}
              onChange={(e) => setLoteForm((p) => ({ ...p, codigo_lote: e.target.value }))}
            />
            <TextField
              size="small"
              label={productoLote ? `Cantidad (${productoLote.unidad})` : 'Cantidad'}
              type="number"
              value={loteForm.cantidad}
              onChange={(e) => setLoteForm((p) => ({ ...p, cantidad: e.target.value }))}
              sx={{ width: 140 }}
            />
            <TextField
              size="small"
              type="date"
              label="Vence"
              InputLabelProps={{ shrink: true }}
              value={loteForm.fecha_vencimiento}
              onChange={(e) => setLoteForm((p) => ({ ...p, fecha_vencimiento: e.target.value }))}
            />
            <Button variant="contained" onClick={submitLote}>
              {editingLoteId ? 'Guardar lote' : 'Cargar lote'}
            </Button>
            {editingLoteId && (
              <Button
                variant="outlined"
                onClick={() => {
                  setEditingLoteId(null);
                  setLoteForm({ producto: '', codigo_lote: '', cantidad: '', fecha_vencimiento: '' });
                }}
              >
                Cancelar
              </Button>
            )}
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Producto</TableCell>
                <TableCell>Lote</TableCell>
                <TableCell align="right">Cantidad</TableCell>
                <TableCell>Vence</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lotes.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>
                    {l.insumo_codigo} — {l.insumo_nombre}
                  </TableCell>
                  <TableCell>{l.codigo_lote}</TableCell>
                  <TableCell align="right">{l.cantidad}</TableCell>
                  <TableCell>{l.fecha_vencimiento || '—'}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => startEditLote(l)}>
                      Editar
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={() =>
                        void deleteWithFallback(
                          `lote ${l.codigo_lote}`,
                          () => deleteLoteInsumo(l.id),
                          () => patchLoteInsumo(l.id, { activo: false })
                        )
                      }
                    >
                      Eliminar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 3 && (
        <Box>
          <Alert severity="info" sx={{ mb: 2 }}>
            Definí qué reactivo se descuenta al cargar el resultado de cada ensayo (ej. Glucosa → 1
            cartucho). Sin vínculo, la carga no mueve stock.
          </Alert>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Equipo</InputLabel>
              <Select
                label="Equipo"
                value={filtroEquipo}
                onChange={(e) => {
                  setFiltroEquipo(e.target.value);
                  setExamenId('');
                }}
              >
                <MenuItem value="">Todos</MenuItem>
                {equipos.map((eq) => (
                  <MenuItem key={eq.id} value={eq.codigo}>
                    {eq.codigo}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 260 }}>
              <InputLabel>Ensayo</InputLabel>
              <Select
                label="Ensayo"
                value={examenId}
                onChange={(e) => setExamenId(e.target.value)}
              >
                <MenuItem value="">—</MenuItem>
                {examenesFiltrados.map((ex) => (
                  <MenuItem key={ex.id} value={String(ex.id)}>
                    {ex.codigo} — {ex.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Reactivo</InputLabel>
              <Select
                label="Reactivo"
                value={consumoForm.reactivo}
                onChange={(e) => setConsumoForm((p) => ({ ...p, reactivo: e.target.value }))}
              >
                {reactivos.map((r) => (
                  <MenuItem key={r.id} value={String(r.id)}>
                    {r.codigo} ({r.unidad})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Cant. / det."
              type="number"
              value={consumoForm.cantidad}
              onChange={(e) => setConsumoForm((p) => ({ ...p, cantidad: e.target.value }))}
              sx={{ width: 110 }}
            />
            <Button variant="contained" onClick={submitConsumo} disabled={!examenId}>
              {editingConsumoId ? 'Guardar' : 'Vincular'}
            </Button>
            {editingConsumoId && (
              <Button
                variant="outlined"
                onClick={() => {
                  setEditingConsumoId(null);
                  setConsumoForm({ reactivo: '', cantidad: '1', etiqueta: '' });
                }}
              >
                Cancelar
              </Button>
            )}
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Ensayo</TableCell>
                <TableCell>Reactivo que se descuenta</TableCell>
                <TableCell align="right">Cant. / det.</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {consumosVisibles.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    {c.tipo_examen_codigo} — {c.tipo_examen_nombre}
                  </TableCell>
                  <TableCell>
                    {c.insumo_codigo} ({c.insumo_unidad})
                  </TableCell>
                  <TableCell align="right">{c.cantidad_por_determinacion}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => startEditConsumo(c)}>
                      Editar
                    </Button>
                    <Button size="small" color="error" onClick={() => void quitarConsumo(c.id)}>
                      Quitar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {consumosVisibles.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography variant="body2" color="text.secondary">
                      Sin vínculos{examenId ? ' para este ensayo' : ''}.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 4 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Fecha</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>Producto</TableCell>
              <TableCell>Lote</TableCell>
              <TableCell align="right">Cant.</TableCell>
              <TableCell>Motivo</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {movimientos.map((m) => (
              <TableRow key={m.id}>
                <TableCell>{new Date(m.created_at).toLocaleString('es-AR')}</TableCell>
                <TableCell>{m.tipo}</TableCell>
                <TableCell>{m.insumo_codigo}</TableCell>
                <TableCell>{m.lote_codigo}</TableCell>
                <TableCell align="right">{m.cantidad}</TableCell>
                <TableCell>{m.motivo}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {tab === 5 && alertas && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Reactivos a pedir
          </Typography>
          {pedidosReactivos.length === 0 ? (
            <Alert severity="success" sx={{ mb: 2 }}>
              Sin pedidos de reactivos.
            </Alert>
          ) : (
            <Table size="small" sx={{ mb: 3 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Reactivo</TableCell>
                  <TableCell>Proveedor</TableCell>
                  <TableCell align="right">Stock</TableCell>
                  <TableCell align="right">Mín.</TableCell>
                  <TableCell align="right">Sugerido</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pedidosReactivos.map((p) => (
                  <TableRow key={p.insumo_id}>
                    <TableCell>
                      {p.codigo} — {p.nombre}
                    </TableCell>
                    <TableCell>{p.proveedor || '—'}</TableCell>
                    <TableCell align="right">
                      {p.stock_actual} {p.unidad}
                    </TableCell>
                    <TableCell align="right">{p.stock_min}</TableCell>
                    <TableCell align="right">{p.cantidad_sugerida}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Insumos a pedir
          </Typography>
          {pedidosInsumos.length === 0 ? (
            <Alert severity="success" sx={{ mb: 2 }}>
              Sin pedidos de insumos.
            </Alert>
          ) : (
            <Table size="small" sx={{ mb: 3 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Insumo</TableCell>
                  <TableCell align="right">Stock</TableCell>
                  <TableCell align="right">Mín.</TableCell>
                  <TableCell align="right">Sugerido</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pedidosInsumos.map((p) => (
                  <TableRow key={p.insumo_id}>
                    <TableCell>
                      {p.codigo} — {p.nombre}
                    </TableCell>
                    <TableCell align="right">
                      {p.stock_actual} {p.unidad}
                    </TableCell>
                    <TableCell align="right">{p.stock_min}</TableCell>
                    <TableCell align="right">{p.cantidad_sugerida}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {alertas.bajo_minimo.map((a) => (
            <Alert key={`min-${a.insumo_id}`} severity="warning" sx={{ mb: 1 }}>
              Bajo mínimo: {a.codigo} ({a.stock_actual}/{a.stock_min} {a.unidad})
            </Alert>
          ))}
          {alertas.por_vencer.map((a) => (
            <Alert key={`v-${a.lote_id}`} severity="error" sx={{ mb: 1 }}>
              Por vencer: {a.insumo_codigo}/{a.codigo_lote} en {a.dias_restantes} días
            </Alert>
          ))}
          {alertas.bajo_minimo.length === 0 && alertas.por_vencer.length === 0 && (
            <Alert severity="success">Sin alertas de stock.</Alert>
          )}
        </Box>
      )}
    </Box>
  );
};

export default InventarioPage;
