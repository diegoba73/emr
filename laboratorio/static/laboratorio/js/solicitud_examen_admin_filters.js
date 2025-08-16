'use strict';
(function($) {
    $(document).ready(function() {
        var pacienteSelect = $('#id_paciente');
        var consultaSelect = $('#id_consulta_asociada');
        var consultaOriginalAjaxData = null; // Para guardar la función 'data' original de Django

        console.log("Solicitud Examen Admin Filters JS (v.DesdeCero) Loaded.");

        if (!pacienteSelect.length || !consultaSelect.length) {
            console.error("Error: No se encontraron los elementos #id_paciente o #id_consulta_asociada.");
            return;
        }
        console.log("Elementos Paciente y Consulta Asociada encontrados.");

        function actualizarEstadoYFiltroConsulta() {
            var pacienteId = pacienteSelect.val();

            if (!consultaSelect.data('select2')) {
                console.warn("Select2 aún no está inicializado en #id_consulta_asociada. Esperando...");
                // Si Select2 no está listo, no hacer nada más con él todavía.
                // Se intentará de nuevo cuando el intervalo lo detecte.
                if (!pacienteId) { // Si no hay paciente, al menos deshabilitar el campo HTML
                    consultaSelect.prop('disabled', true);
                }
                return;
            }

            var select2Instance = consultaSelect.data('select2');

            if (pacienteId && pacienteId !== "") {
                console.log("Paciente seleccionado. ID:", pacienteId, ". Habilitando y configurando filtro para Consulta Asociada.");
                consultaSelect.prop('disabled', false);

                if (select2Instance && select2Instance.options && select2Instance.options.options && select2Instance.options.options.ajax) {
                    var ajaxOptions = select2Instance.options.options.ajax;

                    // Capturar la función 'data' original de Django solo una vez
                    if (consultaOriginalAjaxData === null) {
                        if (typeof ajaxOptions.data === 'function') {
                            consultaOriginalAjaxData = ajaxOptions.data;
                            console.log("Función 'data' AJAX original de Django para consulta_asociada CAPTURADA.");
                        } else {
                            console.error("¡ERROR CRÍTICO! No se pudo capturar la función 'data' original de Django. El filtrado no funcionará. ajaxOptions.data es:", ajaxOptions.data);
                            return; // No continuar si no podemos obtener la función original
                        }
                    }

                    // Sobrescribir la función 'data' para añadir paciente_id
                    ajaxOptions.data = function(params) {
                        var data = {};
                        if (typeof consultaOriginalAjaxData === 'function') {
                            data = consultaOriginalAjaxData(params); // Llamar a la original
                        } else {
                            // Fallback si la original no se pudo capturar (no debería pasar si se llegó aquí)
                            console.warn("Usando fallback para parámetros AJAX, la función original no fue capturada.");
                            data = { term: params.term, page: params.page || 1 };
                            data.app_label = consultaSelect.data('app-label') || 'historias_clinicas';
                            data.model_name = consultaSelect.data('model-name') || 'consulta';
                            data.field_name = consultaSelect.data('field-name') || 'consulta_asociada';
                        }

                        data.paciente_id = pacienteId; // Añadir siempre el pacienteId actual
                        console.log("[DEBUG JS] Datos para petición AJAX de consulta_asociada:", data);
                        return data;
                    };
                    console.log("Filtro para consulta_asociada configurado con paciente_id:", pacienteId);
                } else {
                    console.error("No se pudieron acceder a las opciones AJAX de Select2 para #id_consulta_asociada.");
                }
                // Limpiar la selección actual de consulta para forzar una nueva búsqueda con el filtro
                consultaSelect.val(null).trigger('change');

            } else {
                console.log("Ningún paciente seleccionado. Deshabilitando Consulta Asociada.");
                consultaSelect.prop('disabled', true);
                if (consultaSelect.data('select2')) { // Solo si Select2 está inicializado
                    consultaSelect.val(null).trigger('change'); // Limpiar valor
                }
                // Opcional: Restaurar la función 'data' original si queremos que muestre todas las consultas
                if (consultaOriginalAjaxData && select2Instance && select2Instance.options && select2Instance.options.options && select2Instance.options.options.ajax) {
                    select2Instance.options.options.ajax.data = consultaOriginalAjaxData;
                    console.log("Función 'data' AJAX de consulta_asociada restaurada a la original.");
                }
            }
        }

        // Listener para cambios en la selección del paciente
        pacienteSelect.on('change', function() {
            actualizarEstadoYFiltroConsulta();
        });

        // Verificar periódicamente si Select2 se ha inicializado en consultaSelect
        var checkSelect2ReadyInterval = setInterval(function() {
            if (consultaSelect.data('select2')) {
                clearInterval(checkSelect2ReadyInterval);
                console.log("Select2 detectado como inicializado en #id_consulta_asociada por Django.");
                // Aplicar estado inicial y filtro basado en el valor actual del paciente (si lo hay)
                actualizarEstadoYFiltroConsulta();
            }
        }, 200); // Verificar cada 200ms

    });
})(django.jQuery);
