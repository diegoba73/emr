import {
  canAccessInventarioLab,
  canAccessLimsModule,
} from '../../../utils/limsAccess';
import type { User } from '../../../types';
import {
  esReactivo,
  estadoCatalogoDisplay,
  existenciaDisplay,
  filterReactivosPorEquipo,
  labelTipoInsumoVista,
  refComercialDisplay,
  resumenReactivosVista,
  type InsumoVista,
} from './inventarioReactivosView';

const base: InsumoVista = {
  tipo: 'REACTIVO',
  codigo: 'R-1008149',
  nombre: 'Wiener Creatinina enzimática',
  ref_comercial: '1008149',
  equipo_codigo: 'CM260',
  stock_actual: 0,
  unidad: 'cartucho',
};

const productos: InsumoVista[] = [
  base,
  {
    ...base,
    codigo: 'R-W216',
    nombre: 'Finecare panel cTnI/Myoglobin/CK-MB',
    ref_comercial: 'W216',
    equipo_codigo: 'FINECARE',
    stock_actual: 0,
    unidad: 'test',
  },
  {
    ...base,
    codigo: 'CRE',
    nombre: 'Creatinina Pharmacorp',
    ref_comercial: '',
    equipo_codigo: 'CM260',
    stock_actual: 5,
    unidad: 'cartucho',
  },
  {
    tipo: 'TUBO',
    codigo: 'TUBO-EDTA',
    nombre: 'Tubo EDTA',
    ref_comercial: '',
    equipo_codigo: null,
    stock_actual: 100,
    unidad: 'tubo',
  },
  {
    tipo: 'MEDIO',
    codigo: 'MED-AGAR',
    nombre: 'Agar sangre',
    ref_comercial: null,
    equipo_codigo: null,
    stock_actual: 0,
    unidad: 'placa',
  },
];

describe('inventarioReactivosView (Ticket C)', () => {
  it('filtra reactivos por equipo y excluye otros tipos', () => {
    const cm260 = filterReactivosPorEquipo(productos, 'CM260');
    expect(cm260.map((r) => r.codigo)).toEqual(['R-1008149', 'CRE']);
    expect(cm260.every(esReactivo)).toBe(true);

    const finecare = filterReactivosPorEquipo(productos, 'FINECARE');
    expect(finecare.map((r) => r.codigo)).toEqual(['R-W216']);

    const todos = filterReactivosPorEquipo(productos, '');
    expect(todos).toHaveLength(3);
    expect(todos.some((p) => p.tipo === 'TUBO')).toBe(false);
  });

  it('muestra REF comercial y marca pendientes', () => {
    expect(refComercialDisplay('1008149')).toEqual({ text: '1008149', pendiente: false });
    expect(refComercialDisplay('')).toEqual({ text: 'Sin REF', pendiente: true });
    expect(refComercialDisplay('   ')).toEqual({ text: 'Sin REF', pendiente: true });
    expect(refComercialDisplay(null)).toEqual({ text: 'Sin REF', pendiente: true });
  });

  it('muestra stock cero como sin existencia (catalogado ≠ usable)', () => {
    const cero = existenciaDisplay(0, 'cartucho');
    expect(cero.sinExistencia).toBe(true);
    expect(cero.text).toBe('Sin existencia (0 cartucho)');
    expect(cero.cantidad).toBe(0);

    const con = existenciaDisplay(12, 'test');
    expect(con.sinExistencia).toBe(false);
    expect(con.text).toBe('12 test');
  });

  it('diferencia tipos de insumo', () => {
    expect(labelTipoInsumoVista('REACTIVO')).toBe('Reactivo');
    expect(labelTipoInsumoVista('TUBO')).toBe('Tubo / contenedor');
    expect(labelTipoInsumoVista('MEDIO')).toBe('Medio de cultivo');
    expect(labelTipoInsumoVista('OTRO')).toBe('Otro');
    expect(estadoCatalogoDisplay()).toBe('Catalogado');
  });

  it('resume REF y existencia sin mutar stock', () => {
    const lista = filterReactivosPorEquipo(productos, 'CM260');
    const resumen = resumenReactivosVista(lista);
    expect(resumen).toEqual({
      total: 2,
      conRef: 1,
      sinRef: 1,
      conExistencia: 1,
      sinExistencia: 1,
    });
    // Inputs inmutables
    expect(lista[0].stock_actual).toBe(0);
    expect(lista[1].stock_actual).toBe(5);
  });
});

describe('permisos Inventario (sin ampliación Ticket C)', () => {
  const labUser: User = {
    id: 1,
    username: 'lab',
    email: 'lab@test.com',
    first_name: 'Lab',
    last_name: 'User',
    rol: 'LABORATORIO',
    is_active: true,
    is_superuser: false,
  };
  const medUser: User = { ...labUser, id: 2, username: 'med', rol: 'MEDICO' };

  it('Inventario sigue el mismo gate que LIMS module', () => {
    expect(canAccessInventarioLab(labUser)).toBe(canAccessLimsModule(labUser));
    expect(canAccessInventarioLab(medUser)).toBe(canAccessLimsModule(medUser));
    expect(canAccessInventarioLab(labUser)).toBe(true);
    expect(canAccessInventarioLab(medUser)).toBe(false);
    expect(canAccessInventarioLab(null)).toBe(false);
  });
});
