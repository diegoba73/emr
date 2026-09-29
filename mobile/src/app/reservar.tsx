import React, { useEffect, useRef, useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { Alert, Text, View } from 'react-native';
import { allPages,api } from '../lib/api';
import { useSession } from '../lib/session';
import { Medico,Slot,Turno } from '../lib/types';
import { dateKey } from '../lib/calendar';
import Calendar from '../components/Calendar';
import { Action,Body,Card,colors,ErrorText,Field,Loading,Page,Title } from '../components/ui';
export default function Booking() {
  const { user,clinic } = useSession();const { turnoId } = useLocalSearchParams<{turnoId?:string}>();
  const [original,setOriginal]=useState<Turno|null>(null);const [medicos,setMedicos]=useState<Medico[]>([]);const [medico,setMedico]=useState<number|null>(null);
  const [busqueda,setBusqueda]=useState('');
  const normalizar=(texto:string)=>texto.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const palabras=normalizar(busqueda).trim().split(/\s+/).filter(Boolean);
  const coincidencias=palabras.length ? medicos.filter(m=>palabras.every(p=>normalizar(`${m.nombre_completo||''} ${m.nombre} ${m.apellido}`).includes(p))) : [];
  const seleccionado=medicos.find(m=>m.id===medico);
  const [tipo,setTipo]=useState<'CONSULTA'|'ESTUDIO'>('CONSULTA');const [fecha,setFecha]=useState(dateKey(new Date()));const [slots,setSlots]=useState<Slot[]>([]);
  const [loading,setLoading]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [motivo,setMotivo]=useState('');const [reload,setReload]=useState(0);const lock=useRef(false);
  useEffect(()=>{let active=true;(async()=>{try{ if(turnoId){const t=await api<Turno>(`/turnos/${turnoId}/`);if(active){setOriginal(t);setMedico(t.medico_id);setTipo(t.tipo);}} else {const m=await allPages<Medico>('/medicos/');if(active)setMedicos(m);} }catch(e){if(active)setError(e instanceof Error?e.message:'No se pudo cargar la agenda.');}})();return()=>{active=false;};},[turnoId]);
  useEffect(()=>{let active=true;
    // Reset the displayed availability whenever the server query changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSlots([]);if(!medico){setLoading(false);return;}setLoading(true);
    api<{slots:Slot[]}>(`/medicos/${medico}/slots/?fecha=${fecha}&tipo=${tipo}`).then(r=>{if(active)setSlots(r.slots);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};},[medico,fecha,tipo,reload]);
  const submit=async(slot:Slot)=>{if(lock.current)return;lock.current=true;setBusy(true);setError('');try{
    const t=await api<Turno>(turnoId?`/turnos/${turnoId}/reprogramar-horario/`:'/turnos/reservar-horario/','POST',{horario_id:slot.horario_id,inicio:slot.inicio,motivo});
    router.replace({pathname:'/turno/[id]',params:{id:t.id}});
  }catch(e){setError(e instanceof Error?e.message:'No se pudo guardar el turno.');setReload(v=>v+1);}finally{lock.current=false;setBusy(false);}};
  const choose=(slot:Slot)=>Alert.alert(turnoId?'Reprogramar turno':'Confirmar reserva',`${clinic?.name}\n${new Date(slot.inicio).toLocaleString('es-AR')} · 20 minutos`,[{text:'Volver',style:'cancel'},{text:'Confirmar',onPress:()=>submit(slot)}]);
  if(user?.rol==='medico'&&!turnoId)return <Page><Body>Seleccioná un turno de tu agenda para reprogramarlo.</Body></Page>;
  return <Page><Title>{turnoId?'Elegir otro horario':'Reservar un turno'}</Title><ErrorText text={error}/>
    {original?<Card><Body>{original.medico_nombre} · {tipo==='ESTUDIO'?'Estudio':'Consulta'}</Body></Card>:<>
      <Field label="Buscar médico" placeholder="Escribí nombre o apellido" value={busqueda} autoCorrect={false} editable={!busy} onChangeText={texto=>{setBusqueda(texto);setMedico(null);setSlots([]);setError('');}} />
      {seleccionado ? <Card><Body>Médico seleccionado: {seleccionado.nombre_completo||`${seleccionado.apellido}, ${seleccionado.nombre}`}</Body><Action secondary title="Cambiar médico" disabled={busy} onPress={()=>{setMedico(null);setSlots([]);setBusqueda('');}} /></Card> : <>
        {!palabras.length && <Body>Escribí para buscar y luego seleccioná un médico.</Body>}
        {palabras.length>0 && coincidencias.length===0 && <Body>No encontramos médicos con ese nombre o apellido.</Body>}
        {coincidencias.slice(0,8).map(m=><Action key={m.id} secondary title={m.nombre_completo||`${m.apellido}, ${m.nombre}`} disabled={busy} onPress={()=>{setMedico(m.id);setBusqueda(m.nombre_completo||`${m.apellido}, ${m.nombre}`);setError('');}}/>)}
        {coincidencias.length>8 && <Body>Hay más coincidencias. Escribí más letras para precisar la búsqueda.</Body>}
      </>}
      <View style={{flexDirection:'row',gap:12}}>{(['CONSULTA','ESTUDIO'] as const).map(t=><View key={t} style={{flex:1}}><Action secondary={tipo!==t} title={t==='CONSULTA'?'Consulta':'Estudio'} disabled={busy} onPress={()=>{setTipo(t);setError('');}}/></View>)}</View></>}
    <Card><Calendar value={fecha} onChange={d=>{if(!busy){setFecha(d);setError('');}}} futureOnly /></Card>
    <Field label={turnoId?'Motivo de reprogramación':'Motivo (opcional)'} value={motivo} onChangeText={setMotivo} maxLength={255} editable={!busy}/>
    {loading?<Loading/>:medico&&<Card><Text style={{fontSize:18,fontWeight:'700',color:colors.ink}}>Horarios disponibles · 20 minutos</Text>
      {!slots.length&&<Body>No hay horarios libres para este día. Probá otra fecha.</Body>}
      <View style={{flexDirection:'row',flexWrap:'wrap',gap:10}}>{slots.map(slot=><View key={slot.inicio} style={{width:'30%'}}><Action title={new Date(slot.inicio).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})} disabled={busy||(!!turnoId&&!motivo.trim())} onPress={()=>choose(slot)}/></View>)}</View>
    </Card>}
  </Page>;
}
