import React, { useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { LimsTipoMuestra, MuestraTransaccional, ResultadoExamenLims, SolicitudExamenLims } from '../../types/lims';
import { groupResultadosPorPanel } from '../../utils/limsResultadosPanel';
import { PANEL_HEMOGRAMA } from '../../utils/limsOrdenInforme';
import ResultadoEstadoBadge from './ResultadoEstadoBadge';
import ResultadoRangoInfo from './ResultadoRangoInfo';

export interface ResultadosOrdenListaProps {
  resultados: ResultadoExamenLims[];
  muestras?: MuestraTransaccional[];
  tiposMuestraMap?: Map<number, LimsTipoMuestra>;
  /** Si se pasa, agrupa filas por panel / perfil inferido. */
  orden?: Pick<SolicitudExamenLims, 'paneles_resumen' | 'tipos_examen' | 'orden_grupos_informe'>;
  /** Conclusión/observaciones: bajo hemograma si hay PAN_HEMO; si no, al final. */
  observaciones?: string | null;
  /**
   * `laboratorio`: muestra + columnas operativas.
   * `clinico`: compacto para ficha médica (valor+unidad juntos, sin muestra).
   */
  modo?: 'laboratorio' | 'clinico';
}

function muestraLabel(
  r: ResultadoExamenLims,
  muestras: MuestraTransaccional[],
  tiposMuestraMap: Map<number, LimsTipoMuestra>
): string {
  if (r.muestra_id == null) return '—';
  if (r.tipo_muestra_nombre) {
    return `#${r.muestra_id} · ${r.tipo_muestra_nombre}${r.muestra_estado ? ` (${r.muestra_estado})` : ''}`;
  }
  const m = muestras.find((x) => x.id === r.muestra_id);
  const tipoNom = m ? tiposMuestraMap.get(m.tipo_muestra)?.nombre : undefined;
  if (m) {
    return `#${m.id} · ${tipoNom || `tipo #${m.tipo_muestra}`} · ${m.estado}`;
  }
  return `#${r.muestra_id}`;
}

function ResultadoRow({
  r,
  muestras,
  tiposMuestraMap,
  modo,
}: {
  r: ResultadoExamenLims;
  muestras: MuestraTransaccional[];
  tiposMuestraMap: Map<number, LimsTipoMuestra>;
  modo: 'laboratorio' | 'clinico';
}) {
  const valor = (r.valor_obtenido ?? '').trim();
  const unidad = (r.unidad ?? '').trim();
  const clinico = modo === 'clinico';

  return (
    <TableRow
      key={r.id}
      sx={
        r.es_critico
          ? { bgcolor: 'error.light', '& .MuiTableCell-root': { color: 'error.contrastText' } }
          : r.es_patologico
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
      </TableCell>
      {!clinico && <TableCell>{unidad || '—'}</TableCell>}
      <TableCell sx={{ py: clinico ? 0.75 : undefined }}>
        {clinico ? (
          <Typography variant="caption" color="text.secondary">
            {r.rango_referencia_snapshot || r.tipo_examen_rango_referencia || '—'}
          </Typography>
        ) : (
          <ResultadoRangoInfo resultado={r} />
        )}
      </TableCell>
      {!clinico && (
        <TableCell>{muestraLabel(r, muestras, tiposMuestraMap)}</TableCell>
      )}
      <TableCell sx={{ py: clinico ? 0.75 : undefined }}>
        <ResultadoEstadoBadge resultado={r} />
      </TableCell>
    </TableRow>
  );
}

const ResultadosOrdenLista: React.FC<ResultadosOrdenListaProps> = ({
  resultados,
  muestras = [],
  tiposMuestraMap = new Map(),
  orden,
  observaciones,
  modo = 'laboratorio',
}) => {
  const grupos = useMemo(
    () => (orden ? groupResultadosPorPanel(orden, resultados) : [{ key: 'all', titulo: '', resultados }]),
    [orden, resultados]
  );
  const obs = (observaciones || '').trim();
  const tieneHemograma = grupos.some((g) => g.codigo === PANEL_HEMOGRAMA);
  const clinico = modo === 'clinico';

  if (resultados.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 1 }}>
        Sin resultados en esta orden.
      </Typography>
    );
  }

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
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Examen</TableCell>
                    <TableCell>{clinico ? 'Resultado' : 'Valor'}</TableCell>
                    {!clinico && <TableCell>Unidad</TableCell>}
                    <TableCell>Referencia</TableCell>
                    {!clinico && <TableCell>Muestra</TableCell>}
                    <TableCell>Estado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.resultados.map((r) => (
                    <ResultadoRow
                      key={r.id}
                      r={r}
                      muestras={muestras}
                      tiposMuestraMap={tiposMuestraMap}
                      modo={modo}
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
    </Box>
  );
};

export default ResultadosOrdenLista;
