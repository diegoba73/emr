const axios = require('axios');

// Simular exactamente el formato de fecha que usa el frontend
async function testFrontendFormat() {
  try {
    // Simular el formData del frontend
    const formData = {
      paciente: '2',
      medico: '1', 
      especialidad: '1',
      fecha_hora: '2025-08-07T17:00',  // Formato del input datetime-local
      motivo_consulta: 'Pecho - Test frontend format',
      estado: 'CONFIRMADO'
    };
    
    console.log('Form Data del frontend:', formData);
    
    // Simular el procesamiento del frontend
    let fechaHoraInicio = formData.fecha_hora;
    
    if (formData.fecha_hora) {
      try {
        const fecha = new Date(formData.fecha_hora);
        fechaHoraInicio = fecha.toISOString();
        console.log('Fecha procesada por frontend:', fechaHoraInicio);
      } catch (error) {
        console.error('Error formateando fecha:', error);
      }
    }
    
    const turnoData = {
      fecha_hora_inicio: fechaHoraInicio,
      motivo_consulta: formData.motivo_consulta || '',
      estado: formData.estado
    };
    
    // Solo agregar campos si tienen valores válidos (como hace el frontend)
    if (formData.paciente) {
      turnoData.paciente = parseInt(formData.paciente);
    }
    if (formData.medico) {
      turnoData.medico = parseInt(formData.medico);
    }
    if (formData.especialidad) {
      turnoData.especialidad = parseInt(formData.especialidad);
    }
    
    console.log('Turno Data final:', turnoData);
    console.log('JSON a enviar:', JSON.stringify(turnoData, null, 2));
    
    // Intentar actualizar
    const updateResponse = await axios.put('http://localhost:8001/api/turnos/2/', turnoData, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Respuesta exitosa:', updateResponse.data);
    
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    console.error('Status:', error.response?.status);
  }
}

testFrontendFormat();
