import { AxiosResponse } from 'axios';
import { apiClient } from './apiClient';

export interface AuditEvent {
  id: number;
  timestamp: string;
  actor: number | null;
  actor_username?: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  entity_repr: string;
  before_state: any | null;
  after_state: any | null;
  request_id: string;
  ip_address: string | null;
  user_agent: string;
  module: string;
  metadata: any | null;
  success: boolean;
  error_message: string | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type AuditEventFilters = {
  entity_type?: string;
  entity_id?: string;
  actor?: number;
  action?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
};

export async function getAuditEvents(params: AuditEventFilters & { page?: number; page_size?: number }): Promise<Paginated<AuditEvent>> {
  const res: AxiosResponse<Paginated<AuditEvent>> = await apiClient.get('/auditoria/events/', { params });
  return res.data;
}

export async function getAuditEvent(id: number): Promise<AuditEvent> {
  const res: AxiosResponse<AuditEvent> = await apiClient.get(`/auditoria/events/${id}/`);
  return res.data;
}

