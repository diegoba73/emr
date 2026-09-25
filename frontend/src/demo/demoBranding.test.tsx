import React from 'react';
import { render, screen } from '@testing-library/react';
import Logo from '../components/Logo';
import {
  activateDemoSession, activateDemoTour, clearDemoTour,
  isDemoSessionForUser, DEMO_TOUR_ACTIVE_KEY,
} from './demoStorage';

const doctor = { id: 1, username: 'medico1' };
beforeEach(() => { sessionStorage.clear(); });

it('ignora marcas antiguas del tour sin una sesión demo identificada', () => {
  activateDemoTour('medico');
  expect(isDemoSessionForUser(doctor)).toBe(false);
  render(<Logo demo={isDemoSessionForUser(doctor)} />);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/synesis-logo.svg');
});

it('muestra la marca demo solo para el usuario de la sesión explícita', () => {
  activateDemoSession('medico', doctor);
  expect(isDemoSessionForUser(doctor)).toBe(true);
  expect(isDemoSessionForUser({ id: 2, username: 'otra-cuenta' })).toBe(false);
  expect(isDemoSessionForUser(null)).toBe(false);
  const view = render(<Logo demo={isDemoSessionForUser(doctor)} />);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/demo-logo-light.svg');
  view.rerender(<Logo demo={isDemoSessionForUser({ id: 2, username: 'otra-cuenta' })} />);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/synesis-logo.svg');
});

it('conserva la identidad demo al terminar la guía, hasta salir de esa sesión', () => {
  activateDemoSession('medico', doctor);
  sessionStorage.setItem(DEMO_TOUR_ACTIVE_KEY, '0');
  expect(isDemoSessionForUser(doctor)).toBe(true);
  clearDemoTour();
  expect(isDemoSessionForUser(doctor)).toBe(false);
});

it('no activa la sesión para una cuenta distinta de la del rol demo', () => {
  activateDemoSession('medico', { id: 2, username: 'clinica' });
  expect(isDemoSessionForUser({ id: 2, username: 'clinica' })).toBe(false);
});

it('permite que /demo muestre su logo sin cambiar el logo institucional por defecto', () => {
  activateDemoSession('medico', doctor);
  const view = render(<Logo demo />);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/demo-logo-light.svg');
  view.rerender(<Logo />);
  expect(screen.getByRole('img')).toHaveAttribute('src', '/synesis-logo.svg');
});
