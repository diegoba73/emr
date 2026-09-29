import React, { createContext, useCallback, useContext, useEffect, useState, PropsWithChildren } from 'react';
import * as SecureStore from 'expo-secure-store';
import { api, setToken, onUnauthorized, setInstitution } from './api';
import { Perfil } from './types';
import { Clinic, findClinic } from './clinics';
import { catalogue } from './catalogue';
const KEY = 'synesis.movil.institution';
const sessionKey = (c: Clinic) => 'synesis.movil.session.' + c.code;
const Session = createContext<{
  user: Perfil | null; clinic: Clinic | null; loading: boolean;
  link: (code: string) => Promise<void>; changeClinic: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>; logout: () => Promise<void>;
}>({ user:null, clinic:null, loading:true, link:async()=>{}, changeClinic:async()=>{}, login:async()=>{}, logout:async()=>{} });
async function verifyClinic(c: Clinic) {
  const identity = await api<{code:string}>('/institucion/');
  if (identity.code !== c.code) throw new Error('La institución no coincide con el servidor configurado. Contactá a soporte.');
}
export function SessionProvider({ children }: PropsWithChildren) {
  const [user,setUser] = useState<Perfil|null>(null);
  const [clinic,setClinic] = useState<Clinic|null>(null);
  const [loading,setLoading] = useState(true);
  const clear = useCallback(async () => {
    setToken(null); setUser(null);
    if (clinic) await SecureStore.deleteItemAsync(sessionKey(clinic));
  }, [clinic]);
  useEffect(() => {
    onUnauthorized(() => { void clear().catch(()=>{}); });
    return () => onUnauthorized(()=>{});
  }, [clear]);
  useEffect(() => {
    (async()=>{
      try {
        // Legacy tokens have no institution binding and must never be reused.
        await SecureStore.deleteItemAsync('synesis.movil.session');
        const code = await SecureStore.getItemAsync(KEY);
        const c = code ? findClinic(catalogue(),code) : null;
        if (!c) return;
        setInstitution(c.apiUrl); setClinic(c);
        await verifyClinic(c);
        const stored = await SecureStore.getItemAsync(sessionKey(c));
        if (stored) {
          const saved = JSON.parse(stored);
          if (saved.apiUrl === c.apiUrl && typeof saved.token === 'string') {
            setToken(saved.token);
            setUser(await api<Perfil>('/me/'));
          }
        }
      } catch { setToken(null); setUser(null); }
      finally { setLoading(false); }
    })();
  }, []);
  const link = async(code:string) => {
    if (user) throw new Error('Cerrá la sesión antes de cambiar de institución.');
    const c = findClinic(catalogue(),code);
    if (!c) throw new Error('Código de clínica no reconocido. Verificá el código con tu institución.');
    setInstitution(c.apiUrl);
    await verifyClinic(c);
    await SecureStore.setItemAsync(KEY,c.code);
    setClinic(c);
  };
  const login = async(username:string,password:string) => {
    if (!clinic) throw new Error('Primero vinculá tu clínica.');
    await verifyClinic(clinic);
    const data = await api<{token:string;user:Perfil}>('/login/','POST',{username:username.trim(),password});
    await SecureStore.setItemAsync(sessionKey(clinic),JSON.stringify({apiUrl:clinic.apiUrl,token:data.token}),{keychainAccessible:SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY});
    setToken(data.token); setUser(data.user);
  };
  const logout = async()=>{
    // Require server revocation before switching: old push subscriptions must stop.
    await api('/logout/','POST');
    await clear();
  };
  const changeClinic = async()=>{
    if (user) await logout();
    else await clear();
    await SecureStore.deleteItemAsync(KEY);
    setInstitution(''); setClinic(null);
  };
  return <Session.Provider value={{user,clinic,loading,link,changeClinic,login,logout}}>{children}</Session.Provider>;
}
export const useSession = () => useContext(Session);
