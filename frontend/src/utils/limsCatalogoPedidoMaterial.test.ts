import {
  agregarCatalogOptionsForMaterial,
  chipsAgregadosCatalogForMaterial,
  codigosCubiertosPorGrilla,
  panelPerteneceAMaterial,
} from './limsCatalogoPedidoMaterial';
import type { LimsPanelExamen, LimsTipoExamen, MaterialPedidoLims } from '../types/lims';

const sangre: MaterialPedidoLims = {
  codigo: 'SANGRE',
  nombre: 'Sangre',
  ui_preset: 'sangre',
  tipo_muestra_codigos: ['SUERO', 'SANGRE_EDTA'],
  grilla_codigos: [],
};

const orina: MaterialPedidoLims = {
  codigo: 'ORINA',
  nombre: 'Orina',
  ui_preset: 'orina',
  tipo_muestra_codigos: ['ORINA', 'ORINA_24_H'],
  grilla_codigos: [],
};

const examenes: LimsTipoExamen[] = [
  {
    id: 1,
    codigo: 'GLU',
    nombre: 'Glucemia',
    tipo_muestra_requerida: 10,
    tipo_muestra_codigo: 'SUERO',
    activo: true,
  },
  {
    id: 2,
    codigo: 'CREATI',
    nombre: 'Creatinina',
    tipo_muestra_requerida: 10,
    tipo_muestra_codigo: 'SUERO',
    activo: true,
  },
  {
    id: 3,
    codigo: 'PROT_U_AZ',
    nombre: 'Proteínas orina azar',
    tipo_muestra_requerida: 20,
    tipo_muestra_codigo: 'ORINA',
    activo: true,
  },
  {
    id: 4,
    codigo: 'OMCULT',
    nombre: 'Urocultivo',
    tipo_muestra_requerida: 20,
    tipo_muestra_codigo: 'ORINA',
    activo: true,
  },
];

const panMetfra: LimsPanelExamen = {
  id: 200,
  codigo: 'METFRA',
  nombre: 'Metformina / fracciones',
  tipos_examen: [1, 2],
  activo: true,
};

const panMixto: LimsPanelExamen = {
  id: 201,
  codigo: 'PAN_MIX',
  nombre: 'Mixto sangre+orina',
  tipos_examen: [1, 3],
  activo: true,
};

const panVacio: LimsPanelExamen = {
  id: 202,
  codigo: 'PAN_EMPTY',
  nombre: 'Vacío',
  tipos_examen: [],
  activo: true,
};

const panSoloMicro: LimsPanelExamen = {
  id: 203,
  codigo: 'PAN_URO',
  nombre: 'Solo micro',
  tipos_examen: [4],
  activo: true,
};

describe('panelPerteneceAMaterial', () => {
  it('panel sangre solo en SANGRE', () => {
    expect(panelPerteneceAMaterial(panMetfra, sangre, examenes)).toBe(true);
    expect(panelPerteneceAMaterial(panMetfra, orina, examenes)).toBe(false);
  });

  it('panel mixto en cada material con componente', () => {
    expect(panelPerteneceAMaterial(panMixto, sangre, examenes)).toBe(true);
    expect(panelPerteneceAMaterial(panMixto, orina, examenes)).toBe(true);
  });

  it('panel vacío o solo micro no pertenece', () => {
    expect(panelPerteneceAMaterial(panVacio, sangre, examenes)).toBe(false);
    expect(panelPerteneceAMaterial(panSoloMicro, orina, examenes)).toBe(false);
  });
});

describe('agregarCatalogOptionsForMaterial', () => {
  const gridCodigos = new Set(['GLU', 'PAN_HEMO']);

  it('incluye panel METFRA en sangre y no en orina', () => {
    const sangreOpts = agregarCatalogOptionsForMaterial({
      mat: sangre,
      examenes,
      paneles: [panMetfra, panMixto, panVacio, panSoloMicro],
      gridCodigos,
      selectedExamenesIds: new Set(),
      selectedPanelesIds: new Set(),
      orinaModalidad: null,
    });
    expect(sangreOpts.some((o) => o.kind === 'panel' && o.codigo === 'METFRA')).toBe(
      true
    );
    expect(sangreOpts.some((o) => o.kind === 'panel' && o.codigo === 'PAN_MIX')).toBe(
      true
    );
    expect(sangreOpts.some((o) => o.codigo === 'PAN_EMPTY')).toBe(false);
    expect(sangreOpts.some((o) => o.codigo === 'GLU')).toBe(false); // en grilla

    const orinaOpts = agregarCatalogOptionsForMaterial({
      mat: orina,
      examenes,
      paneles: [panMetfra, panMixto],
      gridCodigos: new Set(),
      selectedExamenesIds: new Set(),
      selectedPanelesIds: new Set(),
      orinaModalidad: 'azar',
    });
    expect(orinaOpts.some((o) => o.codigo === 'METFRA')).toBe(false);
    expect(orinaOpts.some((o) => o.kind === 'panel' && o.codigo === 'PAN_MIX')).toBe(
      true
    );
  });

  it('omite paneles ya seleccionados', () => {
    const opts = agregarCatalogOptionsForMaterial({
      mat: sangre,
      examenes,
      paneles: [panMetfra],
      gridCodigos: new Set(),
      selectedExamenesIds: new Set(),
      selectedPanelesIds: new Set([200]),
      orinaModalidad: null,
    });
    expect(opts.some((o) => o.codigo === 'METFRA')).toBe(false);
  });

  it('omite componentes e IACA de paneles ya en grilla (uricuria/calcio 24h)', () => {
    const auU: LimsTipoExamen = {
      id: 10,
      codigo: 'AU_U',
      nombre: 'Ácido úrico urinario (concentración)',
      tipo_muestra_requerida: 30,
      tipo_muestra_codigo: 'ORINA_24_H',
      activo: true,
    };
    const auU24: LimsTipoExamen = {
      id: 11,
      codigo: 'AU_U24',
      nombre: 'Uricuria 24 hs',
      tipo_muestra_requerida: 30,
      tipo_muestra_codigo: 'ORINA_24_H',
      modo_entrada: 'CALCULADO',
      activo: true,
    };
    const diur: LimsTipoExamen = {
      id: 12,
      codigo: 'DIUR',
      nombre: 'Diuresis 24 hs',
      tipo_muestra_requerida: 30,
      tipo_muestra_codigo: 'ORINA_24_H',
      activo: true,
    };
    const uri24: LimsTipoExamen = {
      id: 13,
      codigo: 'URI24',
      nombre: 'Acido Urico',
      tipo_muestra_requerida: 30,
      tipo_muestra_codigo: 'ORINA_24_H',
      panel_equivalente: 'PAN_AU_U24',
      activo: true,
    };
    const suelto: LimsTipoExamen = {
      id: 14,
      codigo: 'OXA_U',
      nombre: 'Oxalato urinario',
      tipo_muestra_requerida: 30,
      tipo_muestra_codigo: 'ORINA_24_H',
      activo: true,
    };
    const panAu: LimsPanelExamen = {
      id: 300,
      codigo: 'PAN_AU_U24',
      nombre: 'Uricuria 24 hs',
      tipos_examen: [10, 12, 11],
      activo: true,
    };
    const examenesOrina = [...examenes, auU, auU24, diur, uri24, suelto];
    const opts = agregarCatalogOptionsForMaterial({
      mat: orina,
      examenes: examenesOrina,
      paneles: [panAu],
      gridCodigos: new Set(['PAN_AU_U24']),
      selectedExamenesIds: new Set(),
      selectedPanelesIds: new Set(),
      orinaModalidad: '24h',
    });
    const codes = opts.map((o) => o.codigo);
    expect(codes).not.toContain('AU_U');
    expect(codes).not.toContain('AU_U24');
    expect(codes).not.toContain('DIUR');
    expect(codes).not.toContain('URI24');
    expect(codes).not.toContain('PAN_AU_U24');
    expect(codes).toContain('OXA_U');
  });
});

describe('codigosCubiertosPorGrilla', () => {
  it('incluye componentes del panel de grilla', () => {
    const comps: LimsTipoExamen[] = [
      {
        id: 1,
        codigo: 'CA_U',
        nombre: 'Ca u',
        tipo_muestra_requerida: 1,
        tipo_muestra_codigo: 'ORINA_24_H',
        activo: true,
      },
      {
        id: 2,
        codigo: 'CA_U24',
        nombre: 'Ca 24',
        tipo_muestra_requerida: 1,
        tipo_muestra_codigo: 'ORINA_24_H',
        activo: true,
      },
    ];
    const pan: LimsPanelExamen = {
      id: 1,
      codigo: 'PAN_CA_U24',
      nombre: 'Calciuria 24 hs',
      tipos_examen: [1, 2],
      activo: true,
    };
    const covered = codigosCubiertosPorGrilla(
      new Set(['PAN_CA_U24']),
      [pan],
      comps
    );
    expect(covered.has('PAN_CA_U24')).toBe(true);
    expect(covered.has('CA_U')).toBe(true);
    expect(covered.has('CA_U24')).toBe(true);
  });
});

describe('chipsAgregadosCatalogForMaterial', () => {
  it('muestra panel seleccionado fuera de grilla', () => {
    const chips = chipsAgregadosCatalogForMaterial({
      mat: sangre,
      examenes,
      paneles: [panMetfra],
      gridCodigos: new Set(['PAN_HEMO']),
      selectedExamenesIds: new Set(),
      selectedPanelesIds: new Set([200]),
    });
    expect(chips).toEqual([
      { kind: 'panel', id: 200, codigo: 'METFRA', nombre: panMetfra.nombre },
    ]);
  });
});
