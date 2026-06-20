import { formatLocalDateTimeSeconds } from './formatLocalDateTime';

describe('formatLocalDateTimeSeconds', () => {
  test('serializa hora local sin Z ni toISOString', () => {
    const d = new Date(2025, 0, 2, 10, 5, 9);
    expect(formatLocalDateTimeSeconds(d)).toBe('2025-01-02T10:05:09');
  });
});
