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

describe('Sidebar Consultas (/atenciones)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('muestra Consultas para médico', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'MEDICO' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Consultas')).toBeInTheDocument();
  });

  it('no muestra Consultas para secretaría', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'SECRETARIA' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.queryByText('Consultas')).not.toBeInTheDocument();
  });

  it('muestra Consultas para enfermería (lectura)', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'ENFERMERIA' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.getByText('Consultas')).toBeInTheDocument();
  });

  it('no muestra Consultas para laboratorio', () => {
    useData.mockReturnValue({ currentUser: mockUser({ rol: 'LABORATORIO' }) });
    render(
      <MemoryRouter>
        <SidebarContent />
      </MemoryRouter>
    );
    expect(screen.queryByText('Consultas')).not.toBeInTheDocument();
  });
});
