import { parseClinics } from './clinics';
const development = __DEV__ && process.env.EXPO_PUBLIC_ALLOW_LOCAL_HTTP === 'true';
// Only the publisher configures endpoints. Codes never become arbitrary URLs.
export function catalogue() {
  const local = development && process.env.EXPO_PUBLIC_API_URL
    ? JSON.stringify([{code:'ICPL',name:'ICPL · Prueba local',apiUrl:process.env.EXPO_PUBLIC_API_URL}]) : '[]';
  return parseClinics(process.env.EXPO_PUBLIC_CLINICS_JSON || local, development);
}
