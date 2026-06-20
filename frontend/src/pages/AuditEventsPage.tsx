import React, { useMemo, useState } from 'react';
import {
  Box,
  Button,
  Drawer,
  TextField,
  Typography,
  Stack,
  CircularProgress,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { AuditEvent, getAuditEvent, getAuditEvents } from '../services/auditoria';

const PAGE_SIZE = 50;

const formatDateTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

const EventDetailDrawer: React.FC<{ id: number | null; onClose: () => void }> = ({ id, onClose }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit-event', id],
    queryFn: () => getAuditEvent(id as number),
    enabled: typeof id === 'number',
  });

  return (
    <Drawer anchor="right" open={typeof id === 'number'} onClose={onClose}>
      <Box sx={{ width: 520, p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          AuditEvent #{id}
        </Typography>
        {isLoading && (
          <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        )}
        {error && (
          <Typography color="error">Error cargando evento</Typography>
        )}
        {data && (
          <Box sx={{ display: 'grid', gap: 1 }}>
            <Typography variant="body2"><b>timestamp</b>: {formatDateTime(data.timestamp)}</Typography>
            <Typography variant="body2"><b>actor</b>: {data.actor_username || data.actor || '—'}</Typography>
            <Typography variant="body2"><b>action</b>: {data.action}</Typography>
            <Typography variant="body2"><b>entity</b>: {data.entity_type}:{data.entity_id || '—'}</Typography>
            <Typography variant="body2"><b>repr</b>: {data.entity_repr}</Typography>
            <Typography variant="body2"><b>module</b>: {data.module || '—'}</Typography>
            <Typography variant="body2"><b>request_id</b>: {data.request_id}</Typography>
            <Typography variant="body2"><b>ip</b>: {data.ip_address || '—'}</Typography>
            <Typography variant="body2"><b>success</b>: {String(data.success)}</Typography>
            {data.error_message && (
              <Typography variant="body2" color="error"><b>error</b>: {data.error_message}</Typography>
            )}
            <Typography variant="subtitle2" sx={{ mt: 2 }}>before_state</Typography>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(data.before_state, null, 2)}</pre>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>after_state</Typography>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(data.after_state, null, 2)}</pre>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>metadata</Typography>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(data.metadata, null, 2)}</pre>
          </Box>
        )}
      </Box>
    </Drawer>
  );
};

const AuditEventsPage: React.FC = () => {
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filters, setFilters] = useState({
    entity_type: '',
    entity_id: '',
    actor: '',
    action: '',
    fecha_desde: '',
    fecha_hasta: '',
  });

  const params = useMemo(() => {
    const p: Record<string, string | number> = {
      page: page + 1,
      page_size: PAGE_SIZE,
    };
    if (filters.entity_type.trim()) p.entity_type = filters.entity_type.trim();
    if (filters.entity_id.trim()) p.entity_id = filters.entity_id.trim();
    if (filters.actor.trim()) p.actor = Number(filters.actor.trim());
    if (filters.action.trim()) p.action = filters.action.trim();
    if (filters.fecha_desde.trim()) p.fecha_desde = filters.fecha_desde.trim();
    if (filters.fecha_hasta.trim()) p.fecha_hasta = filters.fecha_hasta.trim();
    return p;
  }, [filters, page]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['audit-events', params],
    queryFn: () => getAuditEvents(params),
  });

  const rows: AuditEvent[] = data?.results || [];
  const total = data?.count ?? 0;

  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>Auditoría</Typography>
        <Button variant="outlined" onClick={() => refetch()}>Refrescar</Button>
      </Stack>

      <Box sx={{ mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
          <TextField
            label="entity_type"
            value={filters.entity_type}
            onChange={(e) => setFilters((f) => ({ ...f, entity_type: e.target.value }))}
            size="small"
            fullWidth
          />
          <TextField
            label="entity_id"
            value={filters.entity_id}
            onChange={(e) => setFilters((f) => ({ ...f, entity_id: e.target.value }))}
            size="small"
            fullWidth
          />
          <TextField
            label="actor"
            value={filters.actor}
            onChange={(e) => setFilters((f) => ({ ...f, actor: e.target.value }))}
            size="small"
            fullWidth
          />
          <TextField
            label="action"
            value={filters.action}
            onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}
            size="small"
            fullWidth
          />
        </Stack>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mt: 1 }}>
          <TextField
            label="fecha_desde (ISO)"
            value={filters.fecha_desde}
            onChange={(e) => setFilters((f) => ({ ...f, fecha_desde: e.target.value }))}
            size="small"
            fullWidth
            placeholder="2026-01-01T00:00:00Z"
          />
          <TextField
            label="fecha_hasta (ISO)"
            value={filters.fecha_hasta}
            onChange={(e) => setFilters((f) => ({ ...f, fecha_hasta: e.target.value }))}
            size="small"
            fullWidth
            placeholder="2026-12-31T23:59:59Z"
          />
          <Button
            variant="contained"
            onClick={() => {
              setPage(0);
              refetch();
            }}
          >
            Aplicar
          </Button>
        </Stack>
      </Box>

      {error && <Typography color="error">Error cargando auditoría</Typography>}

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 640 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Timestamp</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Action</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Entity</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Entity ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Actor</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Request ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>OK</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 6 }}>
                    <CircularProgress size={28} />
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    Sin registros
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row) => (
                  <TableRow
                    key={row.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onDoubleClick={() => setSelectedId(row.id)}
                  >
                    <TableCell>{row.id}</TableCell>
                    <TableCell>{formatDateTime(row.timestamp)}</TableCell>
                    <TableCell>
                      <Chip size="small" label={row.action} />
                    </TableCell>
                    <TableCell>{row.entity_type}</TableCell>
                    <TableCell>{row.entity_id ?? '—'}</TableCell>
                    <TableCell>{row.actor_username ?? '—'}</TableCell>
                    <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {row.request_id}
                    </TableCell>
                    <TableCell>{row.success ? 'yes' : 'no'}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={PAGE_SIZE}
          rowsPerPageOptions={[PAGE_SIZE]}
          onRowsPerPageChange={() => {}}
        />
      </Paper>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        Doble clic en una fila para ver detalle.
      </Typography>

      <EventDetailDrawer id={selectedId} onClose={() => setSelectedId(null)} />
    </Box>
  );
};

export default AuditEventsPage;
