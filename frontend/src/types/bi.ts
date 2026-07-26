export interface BiKpisResponse {
  desde: string;
  hasta: string;
  lims?: {
    tat_horas: { p50: number | null; p90: number | null; n: number };
    rechazo_muestras: {
      total: number;
      rechazadas: number;
      tasa: number;
      top_motivos: Array<{ motivo_rechazo: string; total: number }>;
    };
    productividad: {
      por_dia: Array<{ dia: string | null; total: number }>;
      por_usuario: Array<{ usuario: string; total: number }>;
    };
    ordenes_en_rango: number;
  };
  turnos?: {
    total_programados: number;
    cancelados: number;
    no_shows: number;
    tasa_no_show: number;
  };
  internacion?: {
    camas_por_estado: Record<string, number>;
    ocupacion_pct: number;
    internaciones_activas: number;
    error?: string;
  };
}

export interface PortalResumen {
  paciente_id: number;
  proximos_turnos: number;
  resultados_laboratorio_listos: number;
  documentos_archivos: number;
  estudios_entregados: number;
  documentos_total: number;
}
