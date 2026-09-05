/** Claves sessionStorage para la demo marketing (tour guiado). */

export const DEMO_TOUR_ACTIVE_KEY = 'demoTourActive';
export const DEMO_TOUR_ROLE_KEY = 'demoTourRole';
export const DEMO_PREFILL_USER_KEY = 'demoPrefillUsername';

export type DemoTourRole = 'medico' | 'laboratorio' | 'enfermeria' | 'paciente';

export const DEMO_ACCOUNTS: Record<
  DemoTourRole,
  { username: string; password: string; label: string; description: string }
> = {
  medico: {
    username: 'medico1',
    password: 'medico123',
    label: 'Médico',
    description: 'Agenda, historia clínica 360, internación y órdenes de laboratorio.',
  },
  laboratorio: {
    username: 'laboratorio1',
    password: 'laboratorio123',
    label: 'Laboratorio',
    description: 'Órdenes LIMS en proceso, resultados y consulta de muestras.',
  },
  enfermeria: {
    username: 'enfermeria1',
    password: 'enfermeria123',
    label: 'Enfermería',
    description: 'Tablero de camas e internaciones activas.',
  },
  paciente: {
    username: 'paciente1',
    password: 'paciente123',
    label: 'Paciente',
    description: 'Portal: turnos, resultados de laboratorio e historia.',
  },
};

export function isDemoTourRole(value: string | null): value is DemoTourRole {
  return value === 'medico' || value === 'laboratorio' || value === 'enfermeria' || value === 'paciente';
}

export function activateDemoTour(role: DemoTourRole): void {
  sessionStorage.setItem(DEMO_TOUR_ROLE_KEY, role);
  sessionStorage.setItem(DEMO_TOUR_ACTIVE_KEY, '1');
}

export function clearDemoTour(): void {
  sessionStorage.removeItem(DEMO_TOUR_ACTIVE_KEY);
  sessionStorage.removeItem(DEMO_TOUR_ROLE_KEY);
}

export function readDemoTourRole(): DemoTourRole | null {
  const role = sessionStorage.getItem(DEMO_TOUR_ROLE_KEY);
  return isDemoTourRole(role) ? role : null;
}

export function isDemoTourActive(): boolean {
  return sessionStorage.getItem(DEMO_TOUR_ACTIVE_KEY) === '1' && readDemoTourRole() != null;
}

export function consumeDemoPrefillUsername(): string {
  const u = sessionStorage.getItem(DEMO_PREFILL_USER_KEY) || '';
  sessionStorage.removeItem(DEMO_PREFILL_USER_KEY);
  return u;
}

export function setDemoPrefillUsername(username: string): void {
  sessionStorage.setItem(DEMO_PREFILL_USER_KEY, username);
}
