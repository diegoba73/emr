import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import BarcodeScanInput from './BarcodeScanInput';

describe('BarcodeScanInput', () => {
  it('emite onScan al presionar Enter con código trimmeado', () => {
    const onScan = jest.fn();
    render(<BarcodeScanInput onScan={onScan} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '  MUE-2026-000001  ' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onScan).toHaveBeenCalledWith('MUE-2026-000001');
  });

  it('no emite onScan si el campo está vacío', () => {
    const onScan = jest.fn();
    render(<BarcodeScanInput onScan={onScan} />);
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onScan).not.toHaveBeenCalled();
  });
});
