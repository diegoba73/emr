/**
 * Navegación "volver" contextual: al abrir un detalle desde una sección,
 * guardar ``from`` / ``fromLabel`` en ``location.state`` para no perder el origen.
 */
export type NavBackState = {
  from?: string;
  fromLabel?: string;
};

export function withNavBack(from: string, fromLabel?: string): { state: NavBackState } {
  return {
    state: {
      from,
      ...(fromLabel ? { fromLabel } : {}),
    },
  };
}

export function readNavBackState(locationState: unknown): NavBackState {
  if (!locationState || typeof locationState !== 'object') return {};
  const s = locationState as Record<string, unknown>;
  const from = typeof s.from === 'string' ? s.from : undefined;
  const fromLabel = typeof s.fromLabel === 'string' ? s.fromLabel : undefined;
  if (from && from.startsWith('/') && !from.startsWith('//')) {
    return { from, fromLabel };
  }
  return {};
}

export function resolveNavBack(
  locationState: unknown,
  fallback: { path: string; label: string }
): { path: string; label: string } {
  const { from, fromLabel } = readNavBackState(locationState);
  if (from) {
    return {
      path: from,
      label: fromLabel || '← Volver',
    };
  }
  return fallback;
}

/** Query de ficha paciente para abrir la pestaña de análisis LIMS. */
export function pacienteFichaAnalisisPath(pacienteId: number | string): string {
  return `/paciente/${pacienteId}?tab=analisis`;
}
