import type { NavigateFunction } from 'react-router-dom';
import type { PacienteTimelineEvent } from '../../types';
import type { TimelineItem, TimelineItemType } from '../../components/patient360/Timeline';

export function mapTimelineEvent(
  ev: PacienteTimelineEvent,
  navigate: NavigateFunction,
): TimelineItem | null {
  const date = ev.date ? new Date(ev.date) : new Date(0);
  if (Number.isNaN(date.getTime())) return null;
  const type = (ev.type || 'otro') as TimelineItemType;
  return {
    id: ev.id,
    type,
    title: ev.title,
    subtitle: ev.subtitle || undefined,
    date,
    critical: Boolean(ev.critical),
    nested: Boolean(ev.nested),
    episodeGroupId: ev.episode_group_id || undefined,
    episodeGroupTitle: ev.episode_group_title || undefined,
    onClick: ev.navigate_to
      ? () => {
          const path = ev.navigate_to || '/portal/historia';
          const openId = ev.atencion_id || (ev.meta?.openAtencionId as number | undefined);
          if (openId) {
            navigate(path, { state: { openAtencionId: openId } });
          } else {
            navigate(path);
          }
        }
      : undefined,
  };
}
