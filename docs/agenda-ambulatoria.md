# Agenda ambulatoria de 20 minutos

## Uso

- Secretaría y administrador: menú **Horarios de atención**, seleccionan cualquiera de los médicos.
- Médico: no puede configurar horarios ni excepciones, tampoco mediante la API.
- Cada franja define día, inicio, fin y atención (consulta o estudio). Permite agregar, editar y quitar franjas. Para lunes a viernes de 09:00 a 13:00 se cargan cinco franjas.
- Consultas: consultorio opcional configurado por el secretaría/administrador. Estudios: sala obligatoria. El paciente no selecciona estos recursos.
- Paciente: **Mis turnos**, selecciona médico, consulta/estudio y fecha. El calendario muestra los horarios libres del día seleccionado y sus propias reservas. Seleccionar un horario abre una confirmación con motivo opcional.
- Los horarios libres nunca incluyen datos de otros pacientes. No hay selector de prioridad ni consultorio para el paciente.

## Reglas

- Nuevas reservas y reprogramaciones: 20 minutos. Vista día/semana: tres celdas por hora.
- Las reservas históricas no se redimensionan. Editar solamente el motivo conserva su duración.
- El paciente siempre reserva mediante `POST /api/turnos/reservar-horario/`; la identidad, estado y recurso son asignados por el servidor. El POST genérico no permite eludir la agenda.
- Un médico sin horarios publicados no ofrece reservas al paciente. Para permitir la transición desde la agenda existente, el personal conserva la carga manual si el médico nunca tiene franjas registradas; si hay franjas, se valida el día, tipo, recurso y horario configurados. Quitar todas las franjas deja nuevamente al médico sin configuración.
- Se consideran ocupación del médico y del recurso, bloqueos y ajustes por fecha existentes. Un turno cancelado libera el intervalo. No se permite reservar horas pasadas desde el portal.
- Las reservas de estudios del portal son reservas logísticas de agenda; no generan por sí mismas una orden clínica ni un informe.
- Cambiar horarios publicados no cancela ni mueve reservas existentes.
- Se bloquean las filas del médico y del recurso dentro de la transacción al reservar. Los cambios de configuración también bloquean al médico. Pruebas automatizadas locales con SQLite: no equivalen a una prueba de carga/concurrencia sobre PostgreSQL.

## Migración y despliegue

Se agrega `medicos.0007_agenda_ambulatoria_20_min`: tipo de atención, recurso y duración por defecto. No modifica fechas ni duración de turnos existentes. Requiere desplegar backend y frontend y aplicar la migración antes de usar las nuevas pantallas.

En el entorno local se verificó con `docker exec emr_backend python manage.py migrate medicos 0007_agenda_ambulatoria_20_min`; la base informó que ya estaba aplicada. Producción no fue modificada.

## Verificación

- Tests nuevos en `medicos/tests/test_agenda_reservas.py`: propiedad de agendas, roles, slots, datos privados, duración, límites de franjas, bloqueos, recursos compartidos, duplicados, reservas propias y reprogramación.
- Tests de interfaz en `ReservaTurnoPaciente.test.tsx` y regresión de `TurnoModal.test.tsx`.
- Se ajustaron las expectativas de creación/reprogramación de turnos y asignación de estudios al contrato de 20 minutos.
- Seis tests de `turnos/tests/test_estado_turnos.py` esperan 404 para laboratorio pero reciben 403. Se reprodujeron los mismos seis fallos sobre HEAD `0d111ec` en una copia aislada, sin estos cambios. Ambos códigos rechazan la acción; no se ampliaron permisos para resolver esas expectativas.
