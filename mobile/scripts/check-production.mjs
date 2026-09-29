// Read-only prerequisite before generating an APK connected to real appointments.
import {readFile} from 'node:fs/promises';
const profiles=JSON.parse(await readFile(new URL('../eas.json',import.meta.url),'utf8'));
const clinics=JSON.parse(profiles.build.preview.env.EXPO_PUBLIC_CLINICS_JSON);
let failed=false;
for(const clinic of clinics){
 try{
  const base=new URL(clinic.apiUrl);
  if(base.protocol!=='https:')throw new Error('La API debe usar HTTPS.');
  const options={signal:AbortSignal.timeout(15000),redirect:'error'};
  const identity=await fetch(clinic.apiUrl+'/institucion/',options);
  if(!identity.ok)throw new Error('Identidad institucional: HTTP '+identity.status);
  const body=await identity.json();
  if(body.code!==clinic.code)throw new Error('Código institucional inesperado.');
  const privateResponse=await fetch(clinic.apiUrl+'/me/',{...options,signal:AbortSignal.timeout(15000)});
  if(privateResponse.status!==401)throw new Error('La API privada sin sesión debe responder 401; respondió '+privateResponse.status);
  console.log(clinic.code+': HTTPS válido, identidad correcta y autenticación requerida.');
 }catch(error){
  failed=true;
  console.error(clinic.code+': '+error.message+(error.cause?.code?' ('+error.cause.code+')':''));
 }
}
if(!clinics.length){failed=true;console.error('No hay clínicas configuradas.');}
if(failed){console.error('No generar el APK conectado a producción hasta corregir estos puntos.');process.exitCode=1;}
