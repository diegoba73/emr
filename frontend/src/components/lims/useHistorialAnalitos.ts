import { useCallback, useEffect, useState } from 'react';
import { getHistorialAnalitos } from '../../services/limsApi';
import type { HistorialAnalitoPrevioLims } from '../../types/lims';

/** Distingue ausencia de antecedentes de una consulta fallida y descarta respuestas viejas. */
export function useHistorialAnalitos(ordenId: number, tiposKey: string) {
  const key = `${ordenId}:${tiposKey}`;
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({
    key: '', loading: true, error: '',
    previos: new Map<number, HistorialAnalitoPrevioLims[]>(),
  });
  const actualizar = useCallback(() => setRevision((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setState({ key, loading: true, error: '', previos: new Map() });
    getHistorialAnalitos(ordenId, 10).then((data) => {
      if (cancelled) return;
      setState({ key, loading: false, error: '', previos: new Map(
        data.analitos.map((a) => [a.tipo_examen_id, a.previos])
      ) });
    }).catch(() => {
      if (cancelled) return;
      setState({ key, loading: false,
        error: 'No se pudo consultar el historial. Reintentá antes de validar; esto no significa que el paciente no tenga resultados anteriores.',
        previos: new Map() });
    });
    return () => { cancelled = true; };
  }, [ordenId, key, revision]);

  return {
    previosPorTipo: state.key === key ? state.previos : new Map<number, HistorialAnalitoPrevioLims[]>(),
    loading: state.key !== key || state.loading,
    error: state.key === key ? state.error : '',
    actualizar,
  };
}
