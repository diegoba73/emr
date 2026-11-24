/**
 * Noticias / avisos en la pantalla de inicio (post-login).
 * Mantener alineado con frontend/src/data/announcements.ts.
 */

export type AnnouncementAudience = 'staff' | 'paciente' | 'all';

export interface Announcement {
  id: string;
  title: string;
  body: string;
  /** ISO date (AAAA-MM-DD), solo informativa en UI. */
  date?: string;
  active: boolean;
  audiences?: AnnouncementAudience[];
}

/** Fuente editable de anuncios del home. */
export const ANNOUNCEMENTS: Announcement[] = [
  {
    id: 'welcome-portal',
    title: 'Novedades del sistema',
    body: 'Desde aquí verás avisos institucionales y cambios operativos. Secretaría puede pedir actualizar este listado cuando haya comunicaciones nuevas.',
    date: '2026-11-22',
    active: true,
    audiences: ['all'],
  },
];

export function getActiveAnnouncements(
  audience: AnnouncementAudience = 'all',
): Announcement[] {
  return ANNOUNCEMENTS.filter((item) => {
    if (!item.active) return false;
    const targets = item.audiences?.length ? item.audiences : (['all'] as AnnouncementAudience[]);
    if (targets.includes('all')) return true;
    if (audience === 'all') return true;
    return targets.includes(audience);
  });
}
