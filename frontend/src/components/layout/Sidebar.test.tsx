import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SidebarContent } from './Sidebar';
import type { User } from '../../types';

jest.mock('../../contexts/DataContext', () => ({
  useData: jest.fn(),
}));

const { useData } = jest.requireMock('../../contexts/DataContext');

function mockUser(overrides: Partial<User> & Pick<User, 'rol'>): User {
  return {
    id: 1,
    username: 'u',
    email: 'u@test.com',
    first_name: 'U',
    last_name: 'T',
    is_active: true,
    is_superuser: false,
    is_staff: false,
    ...overrides,
  };
}

describe('Sidebar Atenciones Clínicas (/atenciones)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('muestra Atenciones Clínicas para médico', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'MEDICO' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Atenciones Clínicas')).toBeInTheDocument();
  });

  it('no muestra Atenciones Clínicas para secretaría', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'SECRETARIA' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.queryByText('Atenciones Clínicas')).not.toBeInTheDocument();
  });

  it('muestra Atenciones Clínicas para enfermería (lectura)', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'ENFERMERIA' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Atenciones Clínicas')).toBeInTheDocument();
  });

  it('no muestra Atenciones Clínicas para laboratorio', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'LABORATORIO' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.queryByText('Atenciones Clínicas')).not.toBeInTheDocument();
  });

  it('no muestra Turnos para laboratorio', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'LABORATORIO' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.queryByText('Turnos')).not.toBeInTheDocument();
  });
});

describe('Sidebar paciente', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useData.mockReturnValue({
      currentUser: mockUser({ rol: 'PACIENTE', paciente: { id: 1, dni: '12345678' } }),
    });
  });

  it('muestra portal propio sin Pacientes ni módulos EMR generales', () => {
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getAllByText('Mi portal').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Mis turnos')).toBeInTheDocument();
    expect(screen.getByText('Mis resultados')).toBeInTheDocument();
    expect(screen.getByText('Mis documentos')).toBeInTheDocument();
    expect(screen.getByText('Mi historia')).toBeInTheDocument();
    expect(screen.queryByText('Pacientes')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Solicitudes')).not.toBeInTheDocument();
    expect(screen.queryByText('Atenciones Clínicas')).not.toBeInTheDocument();
  });
});

describe('Sidebar laboratorio + is_staff (PERM-FE-LAB-01)', () => {
  const labStaff = mockUser({ rol: 'LABORATORIO', is_staff: true });

  beforeEach(() => {
    jest.clearAllMocks();
    useData.mockReturnValue({ currentUser: labStaff });
  });

  it('no muestra enlaces EMR generales (salvo Pacientes)', () => {
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Pacientes')).toBeInTheDocument();
    expect(screen.queryByText('Atenciones Clínicas')).not.toBeInTheDocument();
    expect(screen.queryByText('Auditoría')).not.toBeInTheDocument();
    expect(screen.queryByText('Administración')).not.toBeInTheDocument();
    expect(screen.queryByText('Catálogos clínicos')).not.toBeInTheDocument();
    expect(screen.queryByText('Solicitudes')).not.toBeInTheDocument();
    // Portal clínico (duplicado de LIMS) y estudios: fuera del menú principal.
    expect(screen.queryByRole('button', { name: 'Laboratorio' })).not.toBeInTheDocument();
    expect(screen.queryByText('Estudios complementarios')).not.toBeInTheDocument();
  });

  it('muestra enlaces LIMS', () => {
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Laboratorio (LIMS)')).toBeInTheDocument();
    expect(screen.getByText('Órdenes LIMS')).toBeInTheDocument();
    expect(screen.getByText('Microbiología')).toBeInTheDocument();
    expect(screen.getByText('Catálogos LIMS')).toBeInTheDocument();
    expect(screen.getByText('Exámenes')).toBeInTheDocument();
  });

  it('no muestra Turnos ni agenda', () => {
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.queryByText('Turnos')).not.toBeInTheDocument();
  });
});

describe('Sidebar bioquímico: sin Laboratorio clínico ni Estudios', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'BIOQUIMICO', is_staff: true }) });
  });

  it('ve Pacientes y LIMS; oculta Estudios, Laboratorio clínico, Administración y catálogos clínicos', () => {
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Pacientes')).toBeInTheDocument();
    expect(screen.queryByText('Estudios complementarios')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Laboratorio' })).not.toBeInTheDocument();
    expect(screen.queryByText('Administración')).not.toBeInTheDocument();
    expect(screen.queryByText('Catálogos clínicos')).not.toBeInTheDocument();
    expect(screen.getByText('Laboratorio (LIMS)')).toBeInTheDocument();
    expect(screen.getByText('Órdenes LIMS')).toBeInTheDocument();
  });
});

describe('Sidebar Laboratorio (LIMS) solo admin/laboratorio', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('médico ve Laboratorio clínico y no el bloque LIMS', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'MEDICO' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Laboratorio')).toBeInTheDocument();
    expect(screen.queryByText('Laboratorio (LIMS)')).not.toBeInTheDocument();
    expect(screen.queryByText('Órdenes LIMS')).not.toBeInTheDocument();
    expect(screen.queryByText('Pendientes')).not.toBeInTheDocument();
  });

  it('secretaría ve Laboratorio clínico y no el bloque LIMS', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'SECRETARIA' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Laboratorio')).toBeInTheDocument();
    expect(screen.queryByText('Laboratorio (LIMS)')).not.toBeInTheDocument();
    expect(screen.queryByText('Órdenes LIMS')).not.toBeInTheDocument();
  });

  it('enfermería ve Laboratorio clínico y no el bloque LIMS', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'ENFERMERIA' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Laboratorio')).toBeInTheDocument();
    expect(screen.queryByText('Laboratorio (LIMS)')).not.toBeInTheDocument();
  });
});
