/**
 * Normaliza códigos leídos por pistolas HID (keyboard wedge).
 *
 * Con teclado Windows en español, muchos lectores envían scan codes US:
 * el guion "-" llega como apóstrofo "'" (p.ej. LAB'2026'00018'01).
 * Los códigos LIMS del EMR usan "-" y no apóstrofos.
 */
export function normalizeBarcodeScan(raw: string): string {
  return (raw || '')
    .trim()
    .replace(/['´`]/g, '-');
}
