// Probar el manejo de fechas y zona horaria
function testTimezoneHandling() {
  console.log('=== PROBANDO MANEJO DE FECHAS Y ZONA HORARIA ===');
  
  // Simular una fecha del backend (con zona horaria)
  const backendDate = '2025-08-05T14:00:00-03:00';
  console.log('Fecha del backend:', backendDate);
  
  // Función original (problemática)
  const originalFormat = (dateString) => {
    const date = new Date(dateString);
    return date.toISOString().slice(0, 16);
  };
  
  // Función nueva (corregida)
  const newFormat = (dateString) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };
  
  console.log('Formato original (problemático):', originalFormat(backendDate));
  console.log('Formato nuevo (corregido):', newFormat(backendDate));
  
  // Probar conversión de vuelta al backend
  const formDate = '2025-08-05T14:00';
  console.log('\nFecha del formulario:', formDate);
  
  const originalBackend = (dateString) => {
    const fecha = new Date(dateString);
    return fecha.toISOString();
  };
  
  const newBackend = (dateString) => {
    const fecha = new Date(dateString);
    const offset = fecha.getTimezoneOffset() * 60000;
    const localDate = new Date(fecha.getTime() - offset);
    return localDate.toISOString();
  };
  
  console.log('Conversión original al backend:', originalBackend(formDate));
  console.log('Conversión nueva al backend:', newBackend(formDate));
  
  // Mostrar información de zona horaria
  console.log('\n=== INFORMACIÓN DE ZONA HORARIA ===');
  console.log('Zona horaria del sistema:', Intl.DateTimeFormat().resolvedOptions().timeZone);
  console.log('Offset actual:', new Date().getTimezoneOffset(), 'minutos');
  console.log('Fecha actual local:', new Date().toLocaleString());
  console.log('Fecha actual UTC:', new Date().toISOString());
}

testTimezoneHandling();
