import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MicrobiologiaEstudioDetalle from './MicrobiologiaEstudioDetalle';

const mockGetEstudio = jest.fn();
const mockListSiembras = jest.fn();
const mockListLecturas = jest.fn();
const mockListAislados = jest.fn();
const mockListIdentificaciones = jest.fn();
const mockListAntibiogramas = jest.fn();
const mockListResultados = jest.fn();
const mockListInformes = jest.fn();
const mockListMedios = jest.fn();
const mockListMicroorganismos = jest.fn();
const mockListAntibioticos = jest.fn();

jest.mock('../../services/limsApi', () => ({
  formatDrfError: (e: unknown) => String(e),
  getEstudioMicrobiologia: (...args: unknown[]) => mockGetEstudio(...args),
  listSiembrasMicrobiologia: (...args: unknown[]) => mockListSiembras(...args),
  listLecturasCultivo: (...args: unknown[]) => mockListLecturas(...args),
  listAisladosMicrobiologicos: (...args: unknown[]) => mockListAislados(...args),
  listIdentificacionesMicroorganismo: (...args: unknown[]) => mockListIdentificaciones(...args),
  listAntibiogramas: (...args: unknown[]) => mockListAntibiogramas(...args),
  listResultadosAntibiotico: (...args: unknown[]) => mockListResultados(...args),
  listInformesMicrobiologia: (...args: unknown[]) => mockListInformes(...args),
  listMediosCultivo: (...args: unknown[]) => mockListMedios(...args),
  listMicroorganismos: (...args: unknown[]) => mockListMicroorganismos(...args),
  listAntibioticos: (...args: unknown[]) => mockListAntibioticos(...args),
  cancelarEstudioMicrobiologia: jest.fn(),
  iniciarEstudioMicrobiologia: jest.fn(),
  marcarEstudioMicrobiologiaInformado: jest.fn(),
}));

jest.mock('../../contexts/DataContext', () => ({
  useData: () => ({
    currentUser: { rol: 'LABORATORIO', username: 'lab1' },
  }),
}));

jest.mock('../../utils/limsAccess', () => ({
  canAccessMicrobiologia: () => true,
  canAccessMicrobiologiaLectura: () => true,
  canOperateMicrobiologia: () => true,
  canValidarInformeMicro: () => false,
  canOperateMicroEstudioTecnico: () => true,
  canMarcarMicroEstudioInformado: () => false,
  isMicroEstudioCerrado: () => false,
}));

jest.mock('../../services/limsMicroApi', () => ({
  downloadEtiquetasEstudioMicro: jest.fn(),
}));

jest.mock('../../components/lims/micro/EstudioMicroPedidoRecepcionPanel', () => () => (
  <div>Pedido recepción</div>
));
jest.mock('../../components/lims/micro/EstudioMicroResumenTab', () => () => <div>Resumen</div>);
jest.mock('../../components/lims/micro/SiembrasLecturasPanel', () => () => <div>Siembras</div>);
jest.mock('../../components/lims/micro/AisladosIdentificacionPanel', () => () => <div>Aislados</div>);
jest.mock('../../components/lims/micro/AntibiogramaPanel', () => () => <div>Antibiograma</div>);
jest.mock('../../components/lims/micro/InformesMicrobiologiaPanel', () => () => <div>Informes</div>);
jest.mock('../../components/lims/micro/MotivoDialog', () => ({
  MotivoDialog: () => null,
  useMotivoDialog: () => ({ openMotivoDialog: jest.fn(), dialogProps: {} }),
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

const estudioMock = {
  id: 42,
  numero: 'EM-001',
  estado: 'PENDIENTE',
  solicitud: 1,
  muestra: 2,
  paciente: 3,
};

describe('MicrobiologiaEstudioDetalle', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetEstudio.mockResolvedValue(estudioMock);
    mockListSiembras.mockResolvedValue([]);
    mockListLecturas.mockResolvedValue([]);
    mockListAislados.mockResolvedValue([]);
    mockListIdentificaciones.mockResolvedValue([]);
    mockListAntibiogramas.mockResolvedValue([]);
    mockListResultados.mockResolvedValue([]);
    mockListInformes.mockResolvedValue([]);
    mockListMedios.mockResolvedValue([]);
    mockListMicroorganismos.mockResolvedValue([]);
    mockListAntibioticos.mockResolvedValue([]);
  });

  it('en PENDIENTE muestra vista de recepción y no carga listas técnicas', async () => {
    const { findByText } = render(
      <MemoryRouter initialEntries={['/laboratorio/microbiologia/estudios/42']}>
        <Routes>
          <Route
            path="/laboratorio/microbiologia/estudios/:id"
            element={<MicrobiologiaEstudioDetalle />}
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockGetEstudio).toHaveBeenCalledWith(42);
    });
    expect(await findByText('Pedido recepción')).toBeInTheDocument();
    expect(mockListSiembras).not.toHaveBeenCalled();
    expect(mockListMedios).not.toHaveBeenCalled();
  });

  it('pasa estudio_id a los listados micro filtrados cuando ya está recibido', async () => {
    mockGetEstudio.mockResolvedValue({ ...estudioMock, estado: 'RECIBIDO' });

    render(
      <MemoryRouter initialEntries={['/laboratorio/microbiologia/estudios/42']}>
        <Routes>
          <Route
            path="/laboratorio/microbiologia/estudios/:id"
            element={<MicrobiologiaEstudioDetalle />}
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockGetEstudio).toHaveBeenCalledWith(42);
    });

    const filterParams = { estudio_id: 42 };
    await waitFor(() => {
      expect(mockListSiembras).toHaveBeenCalledWith(filterParams);
    });
    expect(mockListLecturas).toHaveBeenCalledWith(filterParams);
    expect(mockListAislados).toHaveBeenCalledWith(filterParams);
    expect(mockListIdentificaciones).toHaveBeenCalledWith(filterParams);
    expect(mockListAntibiogramas).toHaveBeenCalledWith(filterParams);
    expect(mockListResultados).toHaveBeenCalledWith(filterParams);
    expect(mockListInformes).toHaveBeenCalledWith(filterParams);
    expect(mockListMedios).toHaveBeenCalledWith();
    expect(mockListMicroorganismos).toHaveBeenCalledWith();
    expect(mockListAntibioticos).toHaveBeenCalledWith();
  });
});
