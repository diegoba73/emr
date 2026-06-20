import React from 'react';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { LimsTipoMuestra, MuestraTransaccional, ResultadoExamenLims } from '../../types/lims';
import ResultadoEstadoBadge from './ResultadoEstadoBadge';
import ResultadoRangoInfo from './ResultadoRangoInfo';

export interface ResultadosOrdenListaProps {
  resultados: ResultadoExamenLims[];
  muestras?: MuestraTransaccional[];
  tiposMuestraMap?: Map<number, LimsTipoMuestra>;
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

const ResultadosOrdenLista: React.FC<ResultadosOrdenListaProps> = ({
  resultados,
  muestras = [],
  tiposMuestraMap = new Map(),
}) => {
  if (resultados.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 1 }}>
        Sin resultados en esta orden.
      </Typography>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Examen</TableCell>
            <TableCell>Valor</TableCell>
            <TableCell>Numérico</TableCell>
            <TableCell>Unidad</TableCell>
            <TableCell>Referencia</TableCell>
            <TableCell>Muestra</TableCell>
            <TableCell>Estado</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {resultados.map((r) => {
            const valor = (r.valor_obtenido ?? '').trim();
            const num = r.valor_numerico;
            const numStr =
              num !== null && num !== undefined && num !== '' ? String(num) : '—';
            const unidad = (r.unidad ?? '').trim() || '—';
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
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {r.tipo_examen_nombre || r.tipo_examen}
                  </Typography>
                  <Typography variant="caption" display="block">
                    {r.tipo_examen_codigo}
                  </Typography>
                </TableCell>
                <TableCell>{valor || '—'}</TableCell>
                <TableCell>{numStr}</TableCell>
                <TableCell>{unidad}</TableCell>
                <TableCell>
                  <ResultadoRangoInfo resultado={r} />
                </TableCell>
                <TableCell>{muestraLabel(r, muestras, tiposMuestraMap)}</TableCell>
                <TableCell>
                  <ResultadoEstadoBadge resultado={r} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ResultadosOrdenLista;
