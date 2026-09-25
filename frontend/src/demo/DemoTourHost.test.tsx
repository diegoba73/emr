import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import DemoTourHost from './DemoTourHost';
import { getTourSteps } from './tourSteps';
import { activateDemoSession, DEMO_TOUR_ACTIVE_KEY } from './demoStorage';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }));
jest.mock('../contexts/DataContext', () => ({ useData: () => ({ isAuthenticated: true, currentUser: { id: 1, username: 'medico1' }, logout: jest.fn().mockResolvedValue(undefined) }) }));
jest.mock('./tourSteps', () => ({ getTourSteps: jest.fn() }));

async function tick(ms: number) {
  await act(async () => { jest.advanceTimersByTime(ms); });
}

beforeEach(() => {
  jest.useFakeTimers();
  sessionStorage.clear();
  mockNavigate.mockClear();
  Element.prototype.scrollIntoView = jest.fn();
  activateDemoSession('medico', { id: 1, username: 'medico1' });
  (getTourSteps as jest.Mock).mockReturnValue([
    { route: '/first', element: '[data-demo="test"]', popover: { title: 'Primero', description: 'Inicio' } },
    { route: '/second', element: '[data-demo="test"]', popover: { title: 'Segundo', description: 'Detalle' } },
    { route: '/third', element: '[data-demo="test"]', popover: { title: 'Tercero', description: 'Cierre' } },
  ]);
});
afterEach(() => { jest.useRealTimers(); });

it('permite avanzar, volver y finalizar usando los controles reales de Driver', async () => {
  render(<><div data-demo="test" /><DemoTourHost /></>);
  await tick(500); await tick(400);
  expect(screen.getByText('Primero')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
  await tick(0); await tick(400);
  expect(screen.getByText('Segundo')).toBeInTheDocument();
  expect(screen.getByText('2 de 3')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Anterior' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Anterior' }));
  await tick(0); await tick(400);
  expect(screen.getByText('Primero')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
  await tick(0); await tick(400);
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
  await tick(0); await tick(400);
  fireEvent.click(screen.getByRole('button', { name: 'Listo' }));
  expect(screen.queryByText('Tercero')).not.toBeInTheDocument();
  expect(sessionStorage.getItem(DEMO_TOUR_ACTIVE_KEY)).toBe('0');
});

it('explica la ausencia del registro sin presentar el contenido de un detalle inexistente', async () => {
  (getTourSteps as jest.Mock).mockReturnValue([{
    route: '/pacientes', resolveRoute: async () => null,
    element: '[data-demo="missing"]', popover: { title: 'Paciente demo', description: 'Contenido incorrecto' },
  }]);
  render(<DemoTourHost />);
  await tick(500); await tick(400);
  expect(mockNavigate).toHaveBeenCalledWith('/pacientes');
  expect(screen.getByText(/No encontramos el registro demo/)).toBeInTheDocument();
  expect(screen.queryByText('Contenido incorrecto')).not.toBeInTheDocument();
});

it('no navega ni reabre la guía si se desmonta mientras resuelve un registro', async () => {
  let resolve!: (route: string) => void;
  (getTourSteps as jest.Mock).mockReturnValue([{
    resolveRoute: () => new Promise<string>((done) => { resolve = done; }),
    popover: { title: 'Paso tardío' },
  }]);
  const view = render(<DemoTourHost />);
  await tick(500);
  view.unmount();
  await act(async () => { resolve('/paciente/1'); });
  await tick(1000);
  expect(mockNavigate).not.toHaveBeenCalled();
  expect(screen.queryByText('Paso tardío')).not.toBeInTheDocument();
});

it('prepara la pestaña antes de mostrar su explicación', async () => {
  const prepare = jest.fn();
  (getTourSteps as jest.Mock).mockReturnValue([{
    route: '/orden', element: '[data-demo="test"]', prepare,
    popover: { title: 'Resultados' },
  }]);
  render(<><div data-demo="test" /><DemoTourHost /></>);
  await tick(500); await tick(400); await tick(50);
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Resultados')).toBeInTheDocument();
});

it('arranca también con el montaje doble de StrictMode', async () => {
  render(<React.StrictMode><div data-demo="test" /><DemoTourHost /></React.StrictMode>);
  await tick(500); await tick(400);
  expect(screen.getByText('Primero')).toBeInTheDocument();
});

it('permite continuar cuando una pantalla no llega a mostrar el elemento esperado', async () => {
  render(<DemoTourHost />);
  await tick(500); await tick(400); await tick(7000);
  expect(screen.getByText(/Esta sección no está disponible/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Siguiente' })).toBeEnabled();
});
