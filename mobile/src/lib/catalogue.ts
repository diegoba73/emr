import { parseClinics, Clinic } from './clinics';

const CLINIC_NAME_ICPL = 'Pueblo de Luis & CEHTA';

const development = __DEV__ && process.env.EXPO_PUBLIC_ALLOW_LOCAL_HTTP === 'true';

/** Catálogo autorizado. El código técnico sigue siendo ICPL; el nombre visible es el institucional. */
export function catalogue(): Clinic[] {
  const local =
    development && process.env.EXPO_PUBLIC_API_URL
      ? JSON.stringify([
          {
            code: 'ICPL',
            name: CLINIC_NAME_ICPL,
            apiUrl: process.env.EXPO_PUBLIC_API_URL,
          },
        ])
      : '[]';
  const clinics = parseClinics(process.env.EXPO_PUBLIC_CLINICS_JSON || local, development);
  return clinics.map((c) =>
    c.code === 'ICPL' ? { ...c, name: CLINIC_NAME_ICPL } : c
  );
}

export { CLINIC_NAME_ICPL };
