// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock de react-big-calendar para evitar incompatibilidad ESM/CJS (dom-helpers) en Jest/jsdom.
// Las pruebas funcionales de agenda deben cubrirse en tests específicos de Turnos.
jest.mock('react-big-calendar', () => ({
  Calendar: () => null,
  dateFnsLocalizer: () => ({}),
  Views: {
    MONTH: 'month',
    WEEK: 'week',
    WORK_WEEK: 'work_week',
    DAY: 'day',
    AGENDA: 'agenda',
  },
}));
