import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

jest.mock('./services/auth', () => ({
  authService: {
    login: jest.fn(),
    logout: jest.fn(),
    getCurrentUser: jest.fn(),
  },
}));

test('muestra la pantalla de login en /login', async () => {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <App />
    </MemoryRouter>
  );

  await waitFor(() => {
    expect(screen.getByText(/Synesis EMR/i)).toBeInTheDocument();
  });
  expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument();
});
