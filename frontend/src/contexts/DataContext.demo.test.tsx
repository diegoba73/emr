import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DataProvider, useData } from './DataContext';
import { authService } from '../services/auth';
import { activateDemoSession, isDemoSessionForUser } from '../demo/demoStorage';

jest.mock('../services/auth', () => ({ authService: {
  login: jest.fn(), logout: jest.fn(), getCurrentUser: jest.fn(),
} }));
const doctor = { id: 1, username: 'medico1', rol: 'MEDICO' };
function Harness() {
  const { login, logout, currentUser } = useData();
  return <>
    <span>{isDemoSessionForUser(currentUser) ? 'demo' : 'clinica'}</span>
    <button onClick={() => void login({ username: 'medico1', password: 'test' }, { demoRole: 'medico' }).catch(() => {})}>Demo</button>
    <button onClick={() => void login({ username: 'medico1', password: 'test' }).catch(() => {})}>Normal</button>
    <button onClick={() => void logout()}>Salir</button>
  </>;
}
beforeEach(() => {
  sessionStorage.clear();
  jest.clearAllMocks();
  (authService.login as jest.Mock).mockResolvedValue(undefined);
  (authService.logout as jest.Mock).mockResolvedValue(undefined);
  (authService.getCurrentUser as jest.Mock).mockResolvedValue(doctor);
});
it('activa la marca demo al autenticar desde demo y la elimina al ingresar normalmente con la misma cuenta', async () => {
  render(<DataProvider><Harness /></DataProvider>);
  fireEvent.click(screen.getByText('Demo'));
  await waitFor(() => expect(screen.getByText('demo')).toBeInTheDocument());
  fireEvent.click(screen.getByText('Normal'));
  await waitFor(() => expect(screen.getByText('clinica')).toBeInTheDocument());
  expect(isDemoSessionForUser(doctor)).toBe(false);
});
it('elimina la identidad demo incluso si el cierre de sesión remoto falla', async () => {
  (authService.logout as jest.Mock).mockRejectedValue(new Error('Offline'));
  render(<DataProvider><Harness /></DataProvider>);
  fireEvent.click(screen.getByText('Demo'));
  await waitFor(() => expect(screen.getByText('demo')).toBeInTheDocument());
  fireEvent.click(screen.getByText('Salir'));
  await waitFor(() => expect(screen.getByText('clinica')).toBeInTheDocument());
  expect(isDemoSessionForUser(doctor)).toBe(false);
});
it('un ingreso fallido no deja una identidad demo activa', async () => {
  activateDemoSession('medico', doctor);
  (authService.login as jest.Mock).mockRejectedValue(new Error('Login failed'));
  render(<DataProvider><Harness /></DataProvider>);
  fireEvent.click(screen.getByText('Demo'));
  await waitFor(() => expect(authService.login).toHaveBeenCalled());
  expect(isDemoSessionForUser(doctor)).toBe(false);
});
