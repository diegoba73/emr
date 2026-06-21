// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock explícito de react-big-calendar: evita fallo ESM/CJS (dom-helpers/position) en Jest/jsdom
// cuando App.test.tsx carga App → Turnos. Ver src/__mocks__/react-big-calendar.tsx.
jest.mock('react-big-calendar');
