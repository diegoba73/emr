declare module 'react-big-calendar' {
  import { ComponentType } from 'react';

  export interface CalendarProps {
  localizer: any;
  events: any[];
  startAccessor: string | ((event: any) => Date);
  endAccessor: string | ((event: any) => Date);
  style?: React.CSSProperties;
  onSelectEvent?: (event: any) => void;
  eventPropGetter?: (event: any) => any;
  view?: string;
  onView?: (view: string) => void;
  date?: Date;
  onNavigate?: (newDate: Date, view: string, action: string) => void;
  views?: string[];
  defaultView?: string;
  selectable?: boolean;
  onSelectSlot?: (slotInfo: { start: Date; end: Date; action: string }) => void;
  step?: number;
  timeslots?: number;
  messages?: {
    next?: string;
    previous?: string;
    today?: string;
    month?: string;
    week?: string;
    day?: string;
    noEventsInRange?: string;
    showMore?: (total: number) => string;
  };
  culture?: string;
  components?: any;
}

  export const Calendar: ComponentType<CalendarProps>;
  export const dateFnsLocalizer: (config: any) => any;
} 