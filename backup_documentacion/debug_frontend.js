const axios = require('axios');

// Simular exactamente lo que hace el frontend
async function debugFrontend() {
  try {
    // Simular el formData del frontend
    const formData = {
      paciente: '2',
      medico: '1', 
      especialidad: '1',
      fecha_hora: '2025-08-07T18:00',  // Formato del input datetime-local
      motivo_consulta: 'Pecho - Debug frontend',
      estado: 'CONFIRMADO'
    };
    
    console.log('=== SIMULANDO FRONTEND ===');
    console.log('Form Data:', formData);
    
    // Simular el procesamiento del frontend
    let fechaHoraInicio = formData.fecha_hora || null;
    
    if (formData.fecha_hora) {
      try {
        const fecha = new Date(formData.fecha_hora);
        fechaHoraInicio = fecha.toISOString();
        console.log('Fecha procesada:', fechaHoraInicio);
      } catch (error) {
        console.error('Error formateando fecha:', error);
        fechaHoraInicio = null;
      }
    }
    
    // Validar que tengamos una fecha válida
    if (!fechaHoraInicio) {
      console.error('La fecha y hora de inicio es requerida');
      return;
    }
    
    const turnoData = {
      fecha_hora_inicio: fechaHoraInicio,
      motivo_consulta: formData.motivo_consulta || '',
      estado: formData.estado
    };
    
    // Solo agregar campos si tienen valores válidos
    if (formData.paciente) {
      turnoData.paciente = parseInt(formData.paciente);
    }
    if (formData.medico) {
      turnoData.medico = parseInt(formData.medico);
    }
    if (formData.especialidad) {
      turnoData.especialidad = parseInt(formData.especialidad);
    }
    
    console.log('Turno Data a enviar:', turnoData);
    console.log('JSON a enviar:', JSON.stringify(turnoData, null, 2));
    
    // Simular la llamada a la API
    const response = await axios.put('http://localhost:8001/api/turnos/2/', turnoData, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Respuesta exitosa:', response.data);
    
  } catch (error) {
    console.error('=== ERROR EN FRONTEND ===');
    console.error('Error:', error.message);
    console.error('Response data:', error.response?.data);
    console.error('Response status:', error.response?.status);
    console.error('Response headers:', error.response?.headers);
  }
}

debugFrontend();
