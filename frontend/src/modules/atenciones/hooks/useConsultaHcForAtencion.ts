import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAtencionQuery } from '../hooks';
import { apiService } from '../../../services/api';

function extractApiError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { error?: string; detail?: string } } }).response?.data;
    if (typeof data?.error === 'string') return data.error;
    if (typeof data?.detail === 'string') return data.detail;
  }
  if (err instanceof Error) return err.message;
  return 'No se pudo preparar la consulta HC para pedidos.';
}

/**
 * Resuelve consulta_hc_id para pedidos LIMS/estudios (ambulatorio, guardia, internación).
 */
export function useConsultaHcForAtencion(atencionId: number, enabled: boolean) {
  const queryClient = useQueryClient();
  const { data: atencion, refetch, isFetching } = useAtencionQuery(atencionId);
  const [resolvedHcId, setResolvedHcId] = useState<number | null>(null);
  const [ensuring, setEnsuring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  const consultaHcId = resolvedHcId ?? atencion?.consulta_hc_id ?? null;

  const retry = useCallback(() => {
    setError(null);
    setRetryToken((n) => n + 1);
  }, []);

  useEffect(() => {
    setResolvedHcId(null);
    setError(null);
  }, [atencionId]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    if (consultaHcId) {
      setError(null);
      return;
    }

    let cancelled = false;

    const resolveHc = async () => {
      setEnsuring(true);
      setError(null);
      try {
        const refreshed = await refetch();
        const fromGet = refreshed.data?.consulta_hc_id;
        if (cancelled) return;
        if (fromGet) {
          setResolvedHcId(fromGet);
          return;
        }

        const hcId = await apiService.ensureConsultaHc(atencionId);
        if (cancelled) return;
        setResolvedHcId(hcId);
        queryClient.setQueryData(['atencion', atencionId], (prev: typeof atencion) =>
          prev ? { ...prev, consulta_hc_id: hcId } : prev
        );
      } catch (err: unknown) {
        if (!cancelled) {
          setError(extractApiError(err));
        }
      } finally {
        if (!cancelled) {
          setEnsuring(false);
        }
      }
    };

    void resolveHc();

    return () => {
      cancelled = true;
    };
  }, [atencionId, enabled, consultaHcId, queryClient, refetch, retryToken]);

  return {
    consultaHcId,
    ensuring: ensuring || isFetching,
    error,
    retry,
  };
}
