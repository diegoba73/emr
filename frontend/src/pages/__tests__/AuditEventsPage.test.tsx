import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AuditEventsPage from '../AuditEventsPage';

jest.mock('../../services/auditoria', () => ({
  getAuditEvents: jest.fn(async () => ({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })),
  getAuditEvent: jest.fn(async () => ({})),
}));

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

test('renders audit events page', async () => {
  renderWithQuery(<AuditEventsPage />);
  expect(screen.getByText('Auditoría')).toBeInTheDocument();
  expect(screen.getByText('Refrescar')).toBeInTheDocument();
});

