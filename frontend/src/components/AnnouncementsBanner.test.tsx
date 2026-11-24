import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AnnouncementsBanner from './AnnouncementsBanner';

const mockGetActive = jest.fn();

jest.mock('../data/announcements', () => ({
  getActiveAnnouncements: (...args: unknown[]) => mockGetActive(...args),
}));

describe('AnnouncementsBanner', () => {
  beforeEach(() => {
    mockGetActive.mockReset();
    mockGetActive.mockReturnValue([]);
  });

  it('muestra varios anuncios en el home de staff', () => {
    mockGetActive.mockReturnValue([
      {
        id: 'staff-1',
        title: 'Aviso staff',
        body: 'Mensaje para el dashboard.',
        date: '2026-11-02',
        active: true,
      },
      {
        id: 'staff-2',
        title: 'Segundo aviso',
        body: 'Otro ítem.',
        active: true,
      },
    ]);
    render(<AnnouncementsBanner audience="staff" />);
    expect(mockGetActive).toHaveBeenCalledWith('staff');
    expect(screen.getByTestId('announcements-banner')).toBeInTheDocument();
    expect(screen.getByText('Aviso staff')).toBeInTheDocument();
    expect(screen.getByText('Segundo aviso')).toBeInTheDocument();
  });

  it('muestra anuncios del portal paciente', () => {
    mockGetActive.mockReturnValue([
      {
        id: 'pac-1',
        title: 'Aviso pacientes',
        body: 'Mensaje para el portal.',
        date: '2026-11-01',
        active: true,
      },
    ]);
    render(<AnnouncementsBanner audience="paciente" heading="Avisos" />);
    expect(mockGetActive).toHaveBeenCalledWith('paciente');
    expect(screen.getByText('Avisos')).toBeInTheDocument();
    expect(screen.getByText('Aviso pacientes')).toBeInTheDocument();
  });

  it('se puede ocultar en la sesión', async () => {
    mockGetActive.mockReturnValue([
      {
        id: 'staff-1',
        title: 'Aviso staff',
        body: 'Mensaje para el dashboard.',
        active: true,
      },
    ]);
    render(<AnnouncementsBanner audience="staff" />);
    expect(screen.getByTestId('announcements-banner')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Ocultar novedades' }));
    await waitFor(() => {
      expect(screen.queryByTestId('announcements-banner')).not.toBeInTheDocument();
    });
  });

  it('no renderiza si no hay anuncios activos', () => {
    mockGetActive.mockReturnValue([]);
    const { container } = render(<AnnouncementsBanner audience="staff" />);
    expect(container).toBeEmptyDOMElement();
  });
});
