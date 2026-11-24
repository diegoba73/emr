import ClinicIdentity from './ClinicIdentity';
import React, { PropsWithChildren } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, TextInput, TextInputProps } from 'react-native';
export const colors = { bg: '#f1f6f8', ink: '#17364a', primary: '#087e8b', muted: '#547180', border: '#d2e2e8', danger: '#a12736' };
export function Page({ children, showClinic = true }: PropsWithChildren<{ showClinic?: boolean }>) {
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bg }}
      contentContainerStyle={s.page}
      keyboardShouldPersistTaps="handled"
    >
      {showClinic ? <ClinicIdentity /> : null}
      {children}
    </ScrollView>
  );
}
export function Card({
  children,
  tone = 'default',
}: PropsWithChildren<{ tone?: 'default' | 'alive' | 'past' }>) {
  return (
    <View
      style={[
        s.card,
        tone === 'alive' && s.cardAlive,
        tone === 'past' && s.cardPast,
      ]}
    >
      {children}
    </View>
  );
}
export function Title({ children }: PropsWithChildren) { return <Text accessibilityRole="header" style={s.title}>{children}</Text>; }
export function Body({ children }: PropsWithChildren) { return <Text style={s.body}>{children}</Text>; }
export function ErrorText({ text }: { text: string }) { return text ? <Text accessibilityRole="alert" style={s.error}>{text}</Text> : null; }
export function Action({
  title,
  onPress,
  disabled = false,
  secondary = false,
  badge,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
  /** Numerito tipo notificación (arriba a la derecha). 0/undefined = oculto. */
  badge?: number;
}) {
  const showBadge = typeof badge === 'number' && badge > 0;
  const badgeLabel = showBadge ? (badge > 99 ? '99+' : String(badge)) : '';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      accessibilityLabel={showBadge ? `${title}, ${badgeLabel}` : title}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        s.button,
        {
          backgroundColor: secondary ? '#e3eff2' : colors.primary,
          opacity: disabled ? 0.5 : pressed ? 0.75 : 1,
          overflow: 'visible',
        },
      ]}
    >
      <Text
        style={{
          color: secondary ? colors.ink : '#fff',
          fontWeight: '700',
          fontSize: 16,
          textAlign: 'center',
        }}
      >
        {title}
      </Text>
      {showBadge ? (
        <View
          pointerEvents="none"
          style={s.badge}
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
        >
          <Text style={s.badgeText}>{badgeLabel}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}
export function Field({ label, ...props }: TextInputProps & { label: string }) { return <View style={{ gap: 6 }}><Text style={s.label}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor={colors.muted} style={s.input} {...props} /></View>; }
export function Loading() { return <ActivityIndicator size="large" color={colors.primary} style={{ margin: 28 }} />; }
export const s = StyleSheet.create({
  page: { padding: 20, gap: 16, paddingBottom: 48 },
  card: {
    padding: 18,
    borderRadius: 18,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: colors.border,
    gap: 12,
  },
  /** Turno pendiente / por atender: más presente. */
  cardAlive: {
    borderColor: colors.primary,
    borderWidth: 2,
    backgroundColor: '#f3fbfc',
    shadowColor: colors.primary,
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  /** Turno ya pasado / atendido: más apagado. */
  cardPast: {
    backgroundColor: '#e8eef1',
    borderColor: '#c5d4db',
    opacity: 0.78,
  },
  title: { color: colors.ink, fontSize: 26, fontWeight: '800' },
  body: { color: colors.muted, fontSize: 16, lineHeight: 24 },
  label: { color: colors.ink, fontSize: 14, fontWeight: '600' },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    backgroundColor: '#fff',
    paddingHorizontal: 14,
    paddingVertical: 14,
    color: colors.ink,
    fontSize: 16,
  },
  button: {
    minHeight: 48,
    padding: 14,
    borderRadius: 12,
    justifyContent: 'center',
    position: 'relative',
  },
  badge: {
    position: 'absolute',
    top: -6,
    right: -6,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 5,
    borderRadius: 10,
    backgroundColor: colors.danger,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#fff',
  },
  badgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '800',
    lineHeight: 13,
  },
  error: {
    color: colors.danger,
    backgroundColor: '#fff0f1',
    padding: 12,
    borderRadius: 10,
    fontSize: 15,
    lineHeight: 22,
  },
});
