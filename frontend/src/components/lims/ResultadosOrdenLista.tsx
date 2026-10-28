import React, { useMemo, useState } from 'react';
import {
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import type { ResultadoExamenLims, SolicitudExamenLims } from '../../types/lims';
import { groupResultadosPorPanel } from '../../utils/limsResultadosPanel';
import { PANEL_HEMOGRAMA } from '../../utils/limsOrdenInforme';
import {
  calcAbsolutoFormula,
  formatValorFormulaLeucoConAbsoluto,
  FORMULA_LEUCO_CODIGOS,
  esResultadoNoCalculable,
} from '../../utils/calculosDerivados';
import ResultadoEstadoBadge from './ResultadoEstadoBadge';
import ResultadoRangoInfo from './ResultadoRangoInfo';
import TendenciaAnalitoDialog from './TendenciaAnalitoDialog';

export interface ResultadosOrdenListaProps {
  resultados: ResultadoExamenLims[];
  /** Si se pasa, agrupa filas por panel / perfil inferido. */
  orden?: Pick<SolicitudExamenLims, 'paneles_resumen' | 'tipos_examen' | 'orden_grupos_informe'>;
  /** Conclusión/observaciones: bajo hemograma si hay PAN_HEMO; si no, al final. */
  observaciones?: string | null;
  /**
   * `laboratorio`: columnas operativas (unidad aparte, rango detallado).
   * `clinico`: compacto para ficha médica (valor+unidad juntos).
   */
  modo?: 'laboratorio' | 'clinico';
  /** Estado de la orden; en modo clínico define si vacío/no-calculable = «En proceso». */
  estadoOrden?: string | null;
}

function valorConAbsolutoFormula(
  r: ResultadoExamenLims,
  resultados: ResultadoExamenLims[]
): { texto: string; pctIncluidoEnValor: boolean } {
  const base = (r.valor_obtenido ?? '').trim();
  if (!base) return { texto: '', pctIncluidoEnValor: false };
  const codigo = (r.tipo_examen_codigo || '').toUpperCase();
  if (!FORMULA_LEUCO_CODIGOS.has(codigo)) return { texto: base, pctIncluidoEnValor: false };
  const leuco = resultados.find((x) => (x.tipo_examen_codigo || '').toUpperCase() === 'LEUCO');
  if (!leuco) return { texto: base, pctIncluidoEnValor: false };
  const pct = Number(r.valor_numerico ?? base);
  const leu = Number(leuco.valor_numerico ?? leuco.valor_obtenido);
  if (!Number.isFinite(pct) || !Number.isFinite(leu)) return { texto: base, pctIncluidoEnValor: false };
  const abs = calcAbsolutoFormula(pct, leu);
  if (abs == null) return { texto: base, pctIncluidoEnValor: false };
  return {
    texto: formatValorFormulaLeucoConAbsoluto(base, abs),
    pctIncluidoEnValor: true,
  };
}

function ResultadoRow({
  r,
  modo,
  resultados,
  ordenFinalizada,
  onVerTendencia,
}: {
  r: ResultadoExamenLims;
  modo: 'laboratorio' | 'clinico';
  resultados: ResultadoExamenLims[];
  ordenFinalizada: boolean;
  onVerTendencia: (r: ResultadoExamenLims, valorDisplay: string) => void;
}) {
  const { texto: valorRaw, pctIncluidoEnValor } = valorConAbsolutoFormula(r, resultados);
  const clinico = modo === 'clinico';
  const ocultarValorClinico =
    clinico && !ordenFinalizada && (!valorRaw || esResultadoNoCalculable(valorRaw));
  const valor = ocultarValorClinico ? '' : valorRaw;
  const unidadRaw = !valor || esResultadoNoCalculable(valor) ? '' : (r.unidad ?? '').trim();
  // El % ya va pegado al número cargado («45% · abs.…»); no repetirlo al final.
  const unidad =
    pctIncluidoEnValor && (unidadRaw === '%' || unidadRaw.toLowerCase() === 'porcentaje')
      ? ''
      : unidadRaw;
  const puedeVerTendencia = Boolean(r.solicitud && r.tipo_examen);
  const nombreAnalito = String(r.tipo_examen_nombre || r.tipo_examen || 'Analito');

  return (
    <TableRow
      sx={
        !ocultarValorClinico && r.es_critico
          ? { bgcolor: 'error.light', '& .MuiTableCell-root': { color: 'error.contrastText' } }
          : !ocultarValorClinico && r.es_patologico
            ? { bgcolor: 'warning.light' }
            : undefined
      }
    >
      <TableCell sx={{ py: clinico ? 0.75 : undefined }}>
        <Typography variant="body2" fontWeight={600} component="span">
          {r.tipo_examen_nombre || r.tipo_examen}
        </Typography>
        {r.tipo_examen_codigo ? (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            {r.tipo_examen_codigo}
          </Typography>
        ) : null}
      </TableCell>
      <TableCell sx={{ py: clinico ? 0.75 : undefined, whiteSpace: 'nowrap' }}>
        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25 }}>
          <Typography
            variant="body2"
            fontWeight={valor ? 700 : 400}
            component="span"
            sx={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {valor || '—'}
          </Typography>
          {valor && unidad ? (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 0.75 }}>
              {unidad}
            </Typography>
          ) : null}
          {puedeVerTendencia && (
            <Tooltip title="Ver tendencia histórica">
              <Button
                size="small"
                variant="outlined"
                color="primary"
                disableRipple
                startIcon={<ShowChartIcon fontSize="small" />}
                aria-label={`Ver tendencia de ${nombreAnalito}`}
                onClick={() => onVerTendencia(r, valor)}
                sx={{ ml: 0.75, minWidth: 0, px: 1, py: 0.15, textTransform: 'none' }}
              >
                Gráfico
              </Button>
            </Tooltip>
          )}
        </Box>
      </TableCell>
      {!clinico && <TableCell>{unidad || '—'}</TableCell>}
      <TableCell sx={{ py: clinico ? 0.75 : undefined }}>
        {clinico ? (
          <Typography variant="caption" color="text.secondary">
            {ocultarValorClinico
              ? '—'
              : r.rango_referencia_snapshot || r.tipo_examen_rango_referencia || '—'}
          </Typography>
        ) : (
          <ResultadoRangoInfo resultado={r} />
        )}
      </TableCell>
      <TableCell sx={{ py: clinico ? 0.75 : undefined }}>
        <ResultadoEstadoBadge
          resultado={r}
          modo={modo}
          ordenFinalizada={ordenFinalizada}
        />
      </TableCell>
    </TableRow>
  );
}

const ResultadosOrdenLista: React.FC<ResultadosOrdenListaProps> = ({
  resultados,
  orden,
  observaciones,
  modo = 'laboratorio',
  estadoOrden = null,
}) => {
  const [tendencia, setTendencia] = useState<{
    r: ResultadoExamenLims;
    valorDisplay: string;
  } | null>(null);

  const grupos = useMemo(
    () => (orden ? groupResultadosPorPanel(orden, resultados) : [{ key: 'all', titulo: '', resultados }]),
    [orden, resultados]
  );
  const obs = (observaciones || '').trim();
  const tieneHemograma = grupos.some((g) => g.codigo === PANEL_HEMOGRAMA);
  const clinico = modo === 'clinico';
  const ordenFinalizada = (estadoOrden || '').toUpperCase() === 'FINALIZADO';

  if (resultados.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 1 }}>
        Sin resultados en esta orden.
      </Typography>
    );
  }

  const rTend = tendencia?.r;
  const valorTend = tendencia?.valorDisplay ?? '';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: clinico ? 1.5 : 2 }}>
      {grupos.map((grupo) => {
        const esPerfil = Boolean(grupo.codigo) || grupo.resultados.length > 1;
        return (
          <Box key={grupo.key}>
            {grupo.titulo && (
              <Box
                sx={{
                  mb: 0.75,
                  px: esPerfil ? 1.25 : 0,
                  py: esPerfil ? 0.75 : 0,
                  borderRadius: 1,
                  bgcolor: esPerfil ? 'action.hover' : 'transparent',
                  borderLeft: esPerfil ? 3 : 0,
                  borderColor: 'primary.main',
                }}
              >
                <Typography variant="subtitle2" fontWeight={700}>
                  {grupo.titulo}
                  {grupo.codigo ? (
                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                      {grupo.codigo}
                    </Typography>
                  ) : null}
                  {esPerfil && (
                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                      · {grupo.resultados.length} analitos
                    </Typography>
                  )}
                </Typography>
              </Box>
            )}
            <TableContainer component={Paper} variant="outlined">
              <Table
                size="small"
                sx={{
                  '& .MuiTableCell-root': {
                    textAlign: 'left',
                    verticalAlign: 'middle',
                  },
                }}
              >
                <TableHead>
                  <TableRow>
                    <TableCell>Examen</TableCell>
                    <TableCell>{clinico ? 'Resultado' : 'Valor'}</TableCell>
                    {!clinico && <TableCell>Unidad</TableCell>}
                    <TableCell>Referencia</TableCell>
                    <TableCell>Estado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.resultados.map((r) => (
                    <ResultadoRow
                      key={r.id}
                      r={r}
                      modo={modo}
                      resultados={resultados}
                      ordenFinalizada={ordenFinalizada}
                      onVerTendencia={(res, valorDisplay) => setTendencia({ r: res, valorDisplay })}
                    />
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            {obs && grupo.codigo === PANEL_HEMOGRAMA && (
              <Box sx={{ mt: 1.5 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Conclusión / observaciones del hemograma
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                  {obs}
                </Typography>
              </Box>
            )}
          </Box>
        );
      })}
      {obs && !tieneHemograma && (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Observaciones
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
            {obs}
          </Typography>
        </Box>
      )}
      {rTend && rTend.solicitud && rTend.tipo_examen ? (
        <TendenciaAnalitoDialog
          open
          onClose={() => setTendencia(null)}
          solicitudId={rTend.solicitud}
          tipoExamenId={rTend.tipo_examen}
          tipoExamenNombre={String(rTend.tipo_examen_nombre || rTend.tipo_examen || 'Analito')}
          tipoExamenCodigo={rTend.tipo_examen_codigo}
          actual={
            valorTend
              ? {
                  valor: valorTend,
                  valor_numerico: rTend.valor_numerico,
                  unidad: rTend.unidad ?? null,
                  fecha: rTend.fecha_validacion || rTend.muestra_fecha_toma || null,
                  rango_min: rTend.rango_min_snapshot,
                  rango_max: rTend.rango_max_snapshot,
                }
              : null
          }
        />
      ) : null}
    </Box>
  );
};

export default ResultadosOrdenLista;
