import { isSelectableSlotAction } from './calendarSlotSelection';

describe('calendarSlotSelection', () => {
  test('isSelectableSlotAction reconoce acciones válidas', () => {
    expect(isSelectableSlotAction('click')).toBe(true);
    expect(isSelectableSlotAction('doubleClick')).toBe(true);
    expect(isSelectableSlotAction('select')).toBe(true);
    expect(isSelectableSlotAction('drag')).toBe(false);
  });
});
