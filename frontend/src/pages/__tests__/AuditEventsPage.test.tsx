import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AuditEventsPage from '../AuditEventsPage';
import type { AuditEvent, Paginated } from '../../services/auditoria';

const mockGetAuditEvents = jest.fn<
  Promise<Paginated<AuditEvent>>,
  [Record<string, string | number>]
>();
const mockGetAuditEvent = jest.fn<Promise<AuditEvent>, [number]>();

jest.mock('../../services/auditoria', () => ({
  getAuditEvents: (params: Record<string, string | number>) => mockGetAuditEvents(params),
  getAuditEvent: (id: number) => mockGetAuditEvent(id),
}));

const emptyAuditPage: Paginated<AuditEvent> = {
  count: 0,
  next: null,
  previous: null,
  results: [],
};

const mockAuditEvent: AuditEvent = {
  id: 1,
  timestamp: '2026-01-01T00:00:00Z',
  actor: null,
  action: 'create',
  entity_type: 'TestEntity',
  entity_id: '1',
  entity_repr: 'Test',
  before_state: null,
  after_state: null,
  request_id: 'req-test-1',
  ip_address: null,
  user_agent: 'jest',
  module: 'test',
  metadata: null,
  success: true,
  error_message: null,
};

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  mockGetAuditEvents.mockReset();
  mockGetAuditEvent.mockReset();
  mockGetAuditEvents.mockResolvedValue(emptyAuditPage);
  mockGetAuditEvent.mockResolvedValue(mockAuditEvent);
});

test('renders audit events page', async () => {
  renderWithQuery(<AuditEventsPage />);
  expect(screen.getByText('Auditoría')).toBeInTheDocument();
  expect(screen.getByText('Refrescar')).toBeInTheDocument();
  await waitFor(() => {
    expect(mockGetAuditEvents).toHaveBeenCalled();
  });
  await waitFor(() => {
    expect(screen.getByText('Sin registros')).toBeInTheDocument();
  });
});
