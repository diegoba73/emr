import { administracionUrl } from './administracionUrl';

it('abre la consola en el backend local, incluyendo el puerto', () => {
  expect(administracionUrl('', 'http://localhost:8000/api'))
    .toBe('http://localhost:8000/api/administracion/');
});

it('mantiene el origen de la página cuando la API es relativa', () => {
  expect(administracionUrl('internacion/cama/', '/api'))
    .toBe(`${window.location.origin}/api/administracion/internacion/cama/`);
});

it('mantiene HTTPS al usar un backend explícito', () => {
  expect(administracionUrl('', 'https://emr.example/api/'))
    .toBe('https://emr.example/api/administracion/');
});
