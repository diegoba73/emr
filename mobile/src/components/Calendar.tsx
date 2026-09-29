import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { dateKey, monthCells } from '../lib/calendar';
import { colors } from './ui';
export default function Calendar({ value, onChange, futureOnly = false }: { value: string; onChange: (date: string) => void; futureOnly?: boolean }) {
  const [month, setMonth] = useState(new Date(`${value}T12:00:00`));
  return <View style={{ gap: 14 }}>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
      <Pressable accessibilityLabel="Mes anterior" onPress={() => setMonth(new Date(month.getFullYear(),month.getMonth()-1,1))} style={{ padding: 14 }}><Text style={{ color: colors.primary }}>◀</Text></Pressable>
      <Text style={{ fontSize: 17, fontWeight: '700', color: colors.ink }}>{month.toLocaleDateString('es-AR',{month:'long',year:'numeric'})}</Text>
      <Pressable accessibilityLabel="Mes siguiente" onPress={() => setMonth(new Date(month.getFullYear(),month.getMonth()+1,1))} style={{ padding: 14 }}><Text style={{ color: colors.primary }}>▶</Text></Pressable>
    </View>
    <View style={{ flexDirection: 'row' }}>{['L','M','X','J','V','S','D'].map(d => <Text key={d} style={{ width:'14.2857%',textAlign:'center',color:colors.muted }}>{d}</Text>)}</View>
    <View style={{ flexDirection:'row',flexWrap:'wrap' }}>{monthCells(month).map((day,i) => {
      const disabled = !day || (futureOnly && day<dateKey(new Date()));
      return <Pressable key={day || `blank-${i}`} disabled={disabled} accessibilityRole="button" accessibilityLabel={day || 'Sin día'} accessibilityState={{ selected:day===value,disabled }} onPress={() => day && onChange(day)} style={{ width:'14.2857%',minHeight:46,justifyContent:'center',borderRadius:12,backgroundColor:day===value?colors.primary:'transparent',opacity:disabled?.35:1 }}><Text style={{textAlign:'center',color:day===value?'white':colors.ink}}>{day?Number(day.slice(-2)):''}</Text></Pressable>;
    })}</View>
  </View>;
}
