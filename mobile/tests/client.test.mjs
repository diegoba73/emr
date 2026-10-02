import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
async function source(path) {
 const text = await readFile(new URL(path, import.meta.url), 'utf8');
 const { outputText } = ts.transpileModule(text, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
 return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}
const { createClient, ApiError } = await source('../src/lib/client.ts');
const { monthCells, notificationTurnoId } = await source('../src/lib/calendar.ts');
test('calendar Monday first and leap day',()=>{
 const cells=monthCells(new Date(2024,1,1));
 assert.equal(cells[0],null);assert.equal(cells[3],'2024-02-01');
 assert.ok(cells.includes('2024-02-29'));assert.equal(cells.length%7,0);
});
test('notification cannot supply arbitrary routes',()=>{
 for(const id of ['https://host','../admin',0,-1,{},'1/2']) assert.equal(notificationTurnoId({turno_id:id}),null);
 assert.equal(notificationTurnoId({turno_id:12}),'12');
});
test('credentials only go to configured HTTPS API',async()=>{
 let calls=0;
 const fetcher=async(url,options)=>{
  calls++;assert.equal(url,'https://example.test/api/movil/me/');
  assert.equal(options?.headers.Authorization,'Bearer token');
  return new Response(JSON.stringify({id:1}),{status:200});
 };
 const client=createClient('https://example.test/api/movil',()=> 'token',()=>{},fetcher);
 assert.deepEqual(await client('/me/'),{id:1});
 await assert.rejects(client('//evil.test'),ApiError);assert.equal(calls,1);
 await assert.rejects(createClient('http://example.test',()=>null,()=>{},fetcher)('/me/'),ApiError);
});
test('401 invalidates session without retrying mutations',async()=>{
 let calls=0;let expired=false;
 const client=createClient('https://example.test',()=> 'token',()=>{expired=true;},async()=>{
  calls++;return new Response('{}',{status:401});
 });
 await assert.rejects(client('/turnos/','POST',{}),ApiError);
 assert.equal(calls,1);assert.equal(expired,true);
});
test('transport failure asks to retry without turnos-specific copy',async()=>{
 let calls=0;
 const client=createClient('https://example.test',()=>null,()=>{},async()=>{calls++;throw new Error('offline');});
 await assert.rejects(client('/turnos/','POST',{}),/Verificá tu conexión/);
 await assert.rejects(client('/informes/1/pdf/'),/Verificá tu conexión/);
 assert.equal(calls,2);
});
test('404 prefers API detail and stays resource-agnostic',async()=>{
 const client=createClient('https://example.test',()=>null,()=>{},async(url)=>{
  if(String(url).includes('/informes/')) {
   return new Response(JSON.stringify({detail:'Informe no encontrado.'}),{status:404});
  }
  return new Response('{}',{status:404});
 });
 await assert.rejects(client('/informes/9/pdf/?format=base64'),/Informe no encontrado/);
 await assert.rejects(client('/turnos/9/'),/No se encontró lo solicitado/);
});
test('local HTTP requires explicit opt-in and only accepts private IPv4',async()=>{
 const fetcher=async()=>new Response('{}',{status:200});
 for(const base of ['http://192.168.1.94:8000/api/movil','http://10.0.0.2:8000/api/movil']) {
  await assert.rejects(createClient(base,()=>null,()=>{},fetcher)('/me/'),ApiError);
  assert.deepEqual(await createClient(base,()=>null,()=>{},fetcher,true)('/me/'),{});
 }
 for(const base of ['http://example.com/api','http://8.8.8.8/api','http://192.168.1.94.evil.test/api']) {
  await assert.rejects(createClient(base,()=>null,()=>{},fetcher,true)('/me/'),ApiError);
 }
});
const {parseClinics,findClinic}=await source('../src/lib/clinics.ts');
test('clinic codes resolve only registered HTTPS endpoints',()=>{
 const list=parseClinics(JSON.stringify([{code:'ICPL',name:'ICPL',apiUrl:'https://clinic.test/api/movil/'}]));
 assert.equal(findClinic(list,' icpl ').apiUrl,'https://clinic.test/api/movil');
 assert.equal(findClinic(list,'https://evil.test'),null);
 assert.throws(()=>parseClinics(JSON.stringify([{code:'A1',name:'A',apiUrl:'http://clinic.test/api'}])));
 assert.throws(()=>parseClinics(JSON.stringify([...list,...list])));
 assert.throws(()=>parseClinics(JSON.stringify([{code:'A1',name:'A',apiUrl:'https://user:pass@clinic.test/api'}])));
});
test('local clinic endpoints require explicit development mode',()=>{
 const raw=JSON.stringify([{code:'ICPL',name:'Local',apiUrl:'http://192.168.1.94:8000/api/movil'}]);
 assert.throws(()=>parseClinics(raw));
 assert.equal(parseClinics(raw,true).length,1);
});
test('institution switch never sends the previous bearer to the new endpoint',async()=>{
 const encode=(text)=>'data:text/javascript;base64,'+Buffer.from(text).toString('base64');
 const compile=(text)=>ts.transpileModule(text,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
 const clientModule=encode(compile(await readFile(new URL('../src/lib/client.ts',import.meta.url),'utf8')));
 const apiText=compile(await readFile(new URL('../src/lib/api.ts',import.meta.url),'utf8')).replace("'./client'",JSON.stringify(clientModule));
 const originalFetch=globalThis.fetch;
 globalThis.__DEV__=false;
 const calls=[];let finish;
 globalThis.fetch=async(url,options)=>{
  calls.push({url,headers:options.headers});
  if(url.includes('/slow/')) return new Promise(resolve=>{finish=resolve;});
  return new Response('{}',{status:200});
 };
 try {
  const module=await import(encode(apiText));
  let unauthorized=0;module.onUnauthorized(()=>{unauthorized++;});
  module.setInstitution('https://a.test/api');module.setToken('token-A');
  const stale=module.api('/slow/');
  module.setInstitution('https://b.test/api');
  await module.api('/login/','POST',{});
  assert.equal(calls[1].headers.Authorization,undefined);
  module.setToken('token-B');
  finish(new Response('{}',{status:401}));
  await assert.rejects(stale);
  assert.equal(unauthorized,0);
  await module.api('/me/');
  assert.equal(calls[2].headers.Authorization,'Bearer token-B');
  assert.equal(calls[2].url,'https://b.test/api/me/');
 } finally {globalThis.fetch=originalFetch;delete globalThis.__DEV__;}
});
