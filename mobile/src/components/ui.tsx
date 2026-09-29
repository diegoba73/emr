import ClinicIdentity from './ClinicIdentity';
import React, { PropsWithChildren } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, TextInput, TextInputProps } from 'react-native';
export const colors = { bg: '#f1f6f8', ink: '#17364a', primary: '#087e8b', muted: '#547180', border: '#d2e2e8', danger: '#a12736' };
export function Page({ children }: PropsWithChildren) { return <ScrollView style={{ flex: 1, backgroundColor: colors.bg }} contentContainerStyle={s.page} keyboardShouldPersistTaps="handled"><ClinicIdentity/>{children}</ScrollView>; }
export function Card({ children }: PropsWithChildren) { return <View style={s.card}>{children}</View>; }
export function Title({ children }: PropsWithChildren) { return <Text accessibilityRole="header" style={s.title}>{children}</Text>; }
export function Body({ children }: PropsWithChildren) { return <Text style={s.body}>{children}</Text>; }
export function ErrorText({ text }: { text: string }) { return text ? <Text accessibilityRole="alert" style={s.error}>{text}</Text> : null; }
export function Action({ title, onPress, disabled = false, secondary = false }: { title: string; onPress: () => void; disabled?: boolean; secondary?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [s.button, { backgroundColor: secondary ? '#e3eff2' : colors.primary, opacity: disabled ? .5 : pressed ? .75 : 1 }]}><Text style={{ color: secondary ? colors.ink : '#fff', fontWeight: '700', fontSize: 16, textAlign: 'center' }}>{title}</Text></Pressable>;
}
export function Field({ label, ...props }: TextInputProps & { label: string }) { return <View style={{ gap: 6 }}><Text style={s.label}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor={colors.muted} style={s.input} {...props} /></View>; }
export function Loading() { return <ActivityIndicator size="large" color={colors.primary} style={{ margin: 28 }} />; }
export const s = StyleSheet.create({ page: { padding: 20, gap: 16, paddingBottom: 48 }, card: { padding: 18, borderRadius: 18, backgroundColor: '#fff', borderWidth: 1, borderColor: colors.border, gap: 12 }, title: { color: colors.ink, fontSize: 26, fontWeight: '800' }, body: { color: colors.muted, fontSize: 16, lineHeight: 24 }, label: { color: colors.ink, fontSize: 14, fontWeight: '600' }, input: { borderWidth: 1, borderColor: colors.border, borderRadius: 12, backgroundColor: '#fff', paddingHorizontal: 14, paddingVertical: 14, color: colors.ink, fontSize: 16 }, button: { minHeight: 48, padding: 14, borderRadius: 12, justifyContent: 'center' }, error: { color: colors.danger, backgroundColor: '#fff0f1', padding: 12, borderRadius: 10, fontSize: 15, lineHeight: 22 } });
