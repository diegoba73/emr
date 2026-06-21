import React from 'react';

type CalendarProps = React.HTMLAttributes<HTMLDivElement> & {
  children?: React.ReactNode;
};

/** Stub mínimo de Calendar para Jest; no afecta runtime de producción. */
export function Calendar({ children, ...rest }: CalendarProps) {
  return (
    <div
      data-testid="mock-react-big-calendar"
      role="region"
      aria-label="Calendario"
      {...rest}
    >
      {children}
    </div>
  );
}

/** Stub de dateFnsLocalizer usado por calendarLocalizer.ts. */
export function dateFnsLocalizer<T extends Record<string, unknown>>(config: T): T {
  return config;
}

export const Views = {
  MONTH: 'month',
  WEEK: 'week',
  WORK_WEEK: 'work_week',
  DAY: 'day',
  AGENDA: 'agenda',
} as const;
