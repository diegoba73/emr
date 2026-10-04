// Read-only prerequisite before generating an APK connected to real appointments.
import {readFile} from 'node:fs/promises';
import {get} from 'node:https';

// Allow slow WSL DNS resolution without fetch's shorter connection deadline.
// TLS verification stays enabled; redirects are never followed.
function request(url) {
 return new Promise((resolve,reject)=>{
  const req=get(url,{signal:AbortSignal.timeout(30000)},res=>{
   let body='';
   res.setEncoding('utf8');
   res.on('data',chunk=>{
    body+=chunk;
    if(body.length>1048576)res.destroy(new Error('Respuesta demasiado grande.'));
   });
   res.on('error',reject);
   res.on('end',()=>resolve({status:res.statusCode,body}));
  });
  req.on('error',reject);
 });
}
const profiles=JSON.parse(await readFile(new URL('../eas.json',import.meta.url),'utf8'));
// Pacientes: perfil production (misma URL pública que preview clínico).
const clinics=JSON.parse(profiles.build.production.env.EXPO_PUBLIC_CLINICS_JSON);
let failed=false;
for(const clinic of clinics){
 try{
  const base=new URL(clinic.apiUrl);
  if(base.protocol!=='https:')throw new Error('La API debe usar HTTPS.');
  const identity=await request(clinic.apiUrl+'/institucion/');
  if(identity.status!==200)throw new Error('Identidad institucional: HTTP '+identity.status);
  const body=JSON.parse(identity.body);
  if(body.code!==clinic.code)throw new Error('Código institucional inesperado.');
  const privateResponse=await request(clinic.apiUrl+'/me/');
  if(privateResponse.status!==401)throw new Error('La API privada sin sesión debe responder 401; respondió '+privateResponse.status);
  console.log(clinic.code+': HTTPS válido, identidad correcta y autenticación requerida.');
 }catch(error){
  failed=true;
  console.error(clinic.code+': '+error.message+(error.cause?.code?' ('+error.cause.code+')':''));
 }
}
if(!clinics.length){failed=true;console.error('No hay clínicas configuradas.');}
if(failed){console.error('No generar el APK conectado a producción hasta corregir estos puntos.');process.exitCode=1;}
