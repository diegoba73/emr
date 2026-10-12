import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, CircularProgress, Stack, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { listSolicitudesExamen } from '../../services/limsApi';
import { listEstudiosMicrobiologia } from '../../services/limsMicroApi';
import type { EstudioMicrobiologia, SolicitudExamenLims } from '../../types/lims';
import { useData } from '../../contexts/DataContext';
import {
  canDownloadInformeClinicoPdf,
  canDownloadInformeMicroPdf,
  pathDetalleEstudioMicro,
  pathDetalleOrdenLab,
} from '../../utils/limsAccess';
import { estadoOrdenColor, labelEstadoOrdenLims } from '../../utils/limsEstadosOrden';
import {
  estadoMicroGeneralColor,
  labelEstadoMicroGeneral,
} from '../../utils/limsEstadosMicro';
import type { EstadoSolicitudLims } from '../../types/lims';
import { pacienteFichaAnalisisPath, withNavBack } from '../../utils/navBack';
import { downloadInformeLimsPdf } from '../../services/limsApi';
import { downloadInformeMicroPdf } from '../../services/limsMicroApi';
import { formatLimsPdfDownloadError } from '../../utils/limsDownload';
import toast from 'react-hot-toast';

export interface PacienteLabsAccesoPanelProps {
  pacienteId: number;
  /** Ruta de retorno al cerrar el detalle. */
  backPath: string;
  backLabel?: string;
}

/**
 * Resumen de órdenes clínicas + micro del paciente con acceso a PDF vigente y ficha 360.
 * Usado en guardia (panel + link) y reutilizable en otros contextos clínicos.
 */
const PacienteLabsAccesoPanel: React.FC<PacienteLabsAccesoPanelProps> = ({
  pacienteId,
  backPath,
  backLabel = '← Volver',
}) => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [loading, setLoading] = useState(true);
  const [labs, setLabs] = useState<SolicitudExamenLims[]>([]);
  const [micros, setMicros] = useState<EstudioMicrobiologia[]>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      listSolicitudesExamen({ paciente: pacienteId }).catch(() => []),
      listEstudiosMicrobiologia({ paciente: pacienteId }).catch(() => []),
    ])
      .then(([l, m]) => {
        if (cancelled) return;
        setLabs(l);
        setMicros(m);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pacienteId]);

  if (loading) {
    return (
      <Box display="flex" alignItems="center" gap={1} py={1}>
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Cargando análisis…
        </Typography>
      </Box>
    );
  }

  if (labs.length === 0 && micros.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Sin órdenes de laboratorio para este paciente.
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
        <Typography variant="subtitle2" fontWeight={600}>
          Análisis del paciente
        </Typography>
        <Button
          size="small"
          variant="outlined"
          onClick={() =>
            navigate(
              pacienteFichaAnalisisPath(pacienteId),
              withNavBack(backPath, backLabel)
            )
          }
        >
          Ver en Paciente 360
        </Button>
      </Box>
      {labs.slice(0, 8).map((s) => (
        <Box
          key={`lab-${s.id}`}
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 0.75,
            alignItems: 'center',
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            px: 1,
            py: 0.75,
          }}
        >
          <Chip size="small" label="Clínica" variant="outlined" />
          <Typography variant="body2" fontWeight={600}>
            {s.numero || `#${s.id}`}
          </Typography>
          <Chip
            size="small"
            label={labelEstadoOrdenLims(s.estado)}
            color={estadoOrdenColor(s.estado as EstadoSolicitudLims)}
          />
          {s.estado === 'INFORMADO_PARCIAL' && (
            <Alert severity="warning" sx={{ py: 0, px: 1, flex: '1 1 100%' }}>
              Informe parcial vigente
            </Alert>
          )}
          <Button
            size="small"
            onClick={() =>
              navigate(
                pathDetalleOrdenLab(currentUser, s.id),
                withNavBack(backPath, backLabel)
              )
            }
          >
            Abrir
          </Button>
          {canDownloadInformeClinicoPdf(currentUser, s.estado) && (
            <Button
              size="small"
              variant="outlined"
              onClick={() => {
                void downloadInformeLimsPdf(s.id).catch((err) =>
                  toast.error(formatLimsPdfDownloadError(err))
                );
              }}
            >
              {s.estado === 'INFORMADO_PARCIAL' ? 'PDF parcial' : 'PDF'}
            </Button>
          )}
        </Box>
      ))}
      {micros.slice(0, 8).map((e) => (
        <Box
          key={`micro-${e.id}`}
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 0.75,
            alignItems: 'center',
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            px: 1,
            py: 0.75,
          }}
        >
          <Chip size="small" color="success" label="Micro" variant="outlined" />
          <Typography variant="body2" fontWeight={600}>
            {e.numero || `#${e.id}`}
          </Typography>
          <Chip
            size="small"
            label={labelEstadoMicroGeneral(e.estado, {
              tieneInformePreliminar: e.tiene_informe_preliminar,
              tieneInformeFinal: e.tiene_informe_final,
            })}
            color={estadoMicroGeneralColor(e.estado, {
              tieneInformePreliminar: e.tiene_informe_preliminar,
              tieneInformeFinal: e.tiene_informe_final,
            })}
          />
          <Typography variant="caption" color="text.secondary">
            {e.tipo_cultivo_nombre || e.tipo_estudio}
          </Typography>
          {e.tiene_informe_preliminar && !e.tiene_informe_final && (
            <Alert severity="warning" sx={{ py: 0, px: 1, flex: '1 1 100%' }}>
              Informe preliminar vigente
            </Alert>
          )}
          <Button
            size="small"
            onClick={() =>
              navigate(
                pathDetalleEstudioMicro(e.id),
                withNavBack(backPath, backLabel)
              )
            }
          >
            Abrir
          </Button>
          {canDownloadInformeMicroPdf(currentUser, e.estado, {
            tieneFinalValidado: Boolean(e.tiene_informe_final) ||
              e.estado === 'VALIDADO' ||
              e.estado === 'INFORMADO',
            tienePreliminarEmitido: Boolean(e.tiene_informe_preliminar),
          }) && (
            <Button
              size="small"
              variant="outlined"
              onClick={() => {
                void downloadInformeMicroPdf(e.id).catch((err) =>
                  toast.error(formatLimsPdfDownloadError(err))
                );
              }}
            >
              {e.tiene_informe_final
                ? 'PDF'
                : e.tiene_informe_preliminar
                  ? 'PDF preliminar'
                  : 'PDF'}
            </Button>
          )}
        </Box>
      ))}
    </Stack>
  );
};

export default PacienteLabsAccesoPanel;
