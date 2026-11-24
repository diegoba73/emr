import { ANNOUNCEMENTS, getActiveAnnouncements } from './announcements';

describe('getActiveAnnouncements', () => {
  it('incluye ítems activos all para staff y paciente', () => {
    const staff = getActiveAnnouncements('staff');
    const paciente = getActiveAnnouncements('paciente');
    const activeAll = ANNOUNCEMENTS.filter(
      (a) => a.active && (!a.audiences?.length || a.audiences.includes('all')),
    );
    expect(staff.length).toBeGreaterThanOrEqual(activeAll.length);
    expect(paciente.length).toBeGreaterThanOrEqual(activeAll.length);
  });

  it('no devuelve ítems inactivos', () => {
    expect(getActiveAnnouncements('all').every((a) => a.active)).toBe(true);
  });
});
