import { apiClient as api } from './apiClient';

export interface ObraSocialCatalogo {
  id: number;
  codigo: string;
  nombre: string;
  activo: boolean;
}

export async function listObrasSociales(activo = true): Promise<ObraSocialCatalogo[]> {
  const { data } = await api.get('/obras-sociales/', {
    params: { activo: activo ? 1 : 0 },
  });
  return Array.isArray(data) ? data : data.results || [];
}
