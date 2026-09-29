import React from 'react';
import { Image, Text, View } from 'react-native';
import { useSession } from '../lib/session';
export default function ClinicIdentity() {
  const {clinic} = useSession();
  if (!clinic) return null;
  const logo = clinic.logoUrl ? {uri:clinic.logoUrl} : clinic.code === 'ICPL' ? require('../../assets/icpl-logo.png') : null;
  return <View accessibilityLabel={'Institución: '+clinic.name} style={{padding:12,backgroundColor:'#e3eff2',borderRadius:12,flexDirection:'row',alignItems:'center',gap:12}}>
    {logo && <Image source={logo} accessibilityLabel={'Logo de '+clinic.name} style={{width:100,height:64}} resizeMode="contain"/>}
    <View style={{flex:1}}><Text style={{fontSize:12,color:'#547180'}}>Institución seleccionada</Text><Text style={{fontSize:18,fontWeight:'700',color:'#17364a'}}>{clinic.name}</Text></View>
  </View>;
}
