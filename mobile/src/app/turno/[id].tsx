import React, { useCallback, useRef, useState } from 'react';
import { router,useFocusEffect,useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';
import { api } from '../../lib/api';
import { Turno } from '../../lib/types';
import { useSession } from '../../lib/session';
import { Action,Body,Card,ErrorText,Field,Loading,Page,Title } from '../../components/ui';
export default function Detail(){
  const [now,setNow] = useState(() => Date.now());
  const {id}=useLocalSearchParams<{id:string}>();const {user}=useSession();
  const [turno,setTurno]=useState<Turno|null>(null);const [loading,setLoading]=useState(true);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [cancel,setCancel]=useState(false);const [motivo,setMotivo]=useState('');const lock=useRef(false);
  const refresh=useCallback(async()=>{setNow(Date.now());setLoading(true);setError('');try{setTurno(await api<Turno>(`/turnos/${id}/`));}catch(e){setTurno(null);setError(e instanceof Error?e.message:'No se pudo cargar el turno.');}finally{setLoading(false);}},[id]);
  useFocusEffect(useCallback(()=>{void refresh();},[refresh]));
  const action=async(path:string,body:unknown={})=>{if(lock.current)return;lock.current=true;setBusy(true);setError('');try{await api(`/turnos/${id}/${path}/`,'POST',body);setCancel(false);await refresh();}catch(e){setError(e instanceof Error?e.message:'No se pudo actualizar el turno.');}finally{lock.current=false;setBusy(false);}};
  const activo=turno&&['RESERVADO','CONFIRMADO'].includes(turno.estado)&&new Date(turno.fecha_hora_inicio).getTime()>now;
  return <Page><ErrorText text={error}/>{loading?<Loading/>:turno&&<>
    <Title>{turno.tipo==='ESTUDIO'?'Estudio':'Consulta'}</Title><Card><Title>{new Date(turno.fecha_hora_inicio).toLocaleDateString('es-AR',{weekday:'long',day:'numeric',month:'long'})}</Title><Body>{new Date(turno.fecha_hora_inicio).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})} · {turno.medico_nombre}</Body>{user?.rol==='medico'&&<Body>{turno.paciente_nombre}</Body>}<Body>Estado: {turno.estado}</Body><Body>{turno.asistencia_confirmada_en?'El paciente confirmó su asistencia.':'La asistencia todavía no fue confirmada por el paciente.'}</Body></Card>
    {activo&&<>
      {user?.rol==='paciente'&&!turno.asistencia_confirmada_en&&<Action title="Confirmar mi asistencia" disabled={busy} onPress={()=>Alert.alert('Confirmar asistencia','¿Vas a asistir a este turno?',[{text:'Volver',style:'cancel'},{text:'Sí, voy a asistir',onPress:()=>action('asistencia')}])}/>}
      {user?.rol==='medico'&&turno.estado==='RESERVADO'&&<Action title="Confirmar turno en agenda" disabled={busy} onPress={()=>action('confirmar')}/>}
      <Action title="Reprogramar" secondary disabled={busy} onPress={()=>router.push({pathname:'/reservar',params:{turnoId:id}})}/>
      <Action title="Cancelar turno" secondary disabled={busy} onPress={()=>setCancel(true)}/>
      {cancel&&<Card><Body>Al cancelar, el horario quedará disponible para otra persona.</Body><Field label="Motivo de cancelación" value={motivo} onChangeText={setMotivo} maxLength={255} editable={!busy}/><Action title="Sí, cancelar el turno" disabled={busy||!motivo.trim()} onPress={()=>action('cancelar',{motivo:motivo.trim()})}/><Action title="Conservar mi turno" secondary disabled={busy} onPress={()=>setCancel(false)}/></Card>}
    </>}
  </>}<Action title="Actualizar" secondary disabled={busy||loading} onPress={refresh}/><Action title="Volver a mi agenda" secondary disabled={busy} onPress={()=>router.replace('/')}/></Page>;
}
