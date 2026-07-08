import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Chip,
  CircularProgress,
  Switch,
  FormControlLabel,
  MenuItem,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
} from '@mui/icons-material';

interface CatalogoItem {
  id: number;
  nombre?: string;
  descripcion?: string;
  activo?: boolean;
  [key: string]: any;
}

interface CatalogoBaseProps<T extends CatalogoItem> {
  title: string;
  items: T[];
  loading: boolean;
  onLoad: () => Promise<void>;
  onCreate: (data: Partial<T>) => Promise<T>;
  onUpdate: (id: number, data: Partial<T>) => Promise<T>;
  onDelete: (id: number) => Promise<void>;
  searchFields?: string[];
  fields?: Array<{
    key: string;
    label: string;
    type?: 'text' | 'textarea' | 'number' | 'select';
    options?: Array<{ value: string | number; label: string }>;
    required?: boolean;
  }>;
  getDisplayValue?: (item: T) => string;
  /** Solo lectura (p. ej. secretaría). */
  readOnly?: boolean;
}

function CatalogoBase<T extends CatalogoItem>({
  title,
  items,
  loading,
  onLoad,
  onCreate,
  onUpdate,
  onDelete,
  searchFields = ['nombre', 'descripcion'],
  fields = [
    { key: 'nombre', label: 'Nombre', type: 'text', required: true },
    { key: 'descripcion', label: 'Descripción', type: 'textarea' },
  ],
  getDisplayValue,
  readOnly = false,
}: CatalogoBaseProps<T>) {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingItem, setEditingItem] = useState<T | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    onLoad();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Solo ejecutar una vez al montar el componente

  const filteredItems = useMemo(() => {
    if (!searchTerm.trim()) return items;
    const search = searchTerm.toLowerCase();
    return items.filter((item) =>
      searchFields.some((field) => {
        const value = item[field];
        return value && String(value).toLowerCase().includes(search);
      })
    );
  }, [items, searchTerm, searchFields]);

  const paginatedItems = filteredItems.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleOpenDialog = (item?: T) => {
    if (item) {
      setEditingItem(item);
      const initialData: Record<string, any> = {};
      fields.forEach((field) => {
        initialData[field.key] = item[field.key] ?? '';
      });
      setFormData(initialData);
    } else {
      setEditingItem(null);
      const initialData: Record<string, any> = {};
      fields.forEach((field) => {
        initialData[field.key] = field.key === 'activo' ? true : '';
      });
      setFormData(initialData);
    }
    setError('');
    setShowDialog(true);
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setEditingItem(null);
    setError('');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');

      if (editingItem) {
        await onUpdate(editingItem.id, formData as Partial<T>);
      } else {
        await onCreate(formData as Partial<T>);
      }

      await onLoad();
      handleCloseDialog();
    } catch (error: any) {
      console.error(`Error saving ${title}:`, error);
      setError(error.response?.data?.error || error.message || `Error al guardar ${title}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(`¿Está seguro de que desea eliminar este ${title.toLowerCase()}?`)) {
      return;
    }

    try {
      await onDelete(id);
      await onLoad();
    } catch (error: any) {
      console.error(`Error deleting ${title}:`, error);
      alert(error.response?.data?.error || error.message || `Error al eliminar ${title}`);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>
          {title}
        </Typography>
        {!readOnly && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Nuevo
          </Button>
        )}
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2, display: 'flex', gap: 2 }}>
          <TextField
            size="small"
            placeholder={`Buscar ${title.toLowerCase()}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
            sx={{ flex: 1 }}
          />
        </Box>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>{fields.find(f => f.key === 'nombre') ? 'Nombre' : fields.find(f => f.key === 'codigo') ? 'Código' : 'ID'}</strong></TableCell>
              {fields.filter(f => f.key !== 'nombre' && f.key !== 'activo' && f.key !== 'codigo').map((field) => (
                <TableCell key={field.key}><strong>{field.label}</strong></TableCell>
              ))}
              <TableCell><strong>Estado</strong></TableCell>
              {!readOnly && <TableCell><strong>Acciones</strong></TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedItems.length === 0 ? (
              <TableRow>
                <TableCell colSpan={fields.filter(f => f.key !== 'activo').length + 2} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchTerm ? `No se encontraron ${title.toLowerCase()}` : `No hay ${title.toLowerCase()} registrados`}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedItems.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{(item.nombre || (item as any).codigo || '-')}</TableCell>
                  {fields.filter(f => f.key !== 'nombre' && f.key !== 'activo').map((field) => (
                    <TableCell key={field.key}>
                      {typeof item[field.key] === 'string' && item[field.key].length > 50
                        ? `${item[field.key].substring(0, 50)}...`
                        : (item[field.key] || '-')}
                    </TableCell>
                  ))}
                  <TableCell>
                    <Chip
                      label={item.activo !== false ? 'Activo' : 'Inactivo'}
                      color={item.activo !== false ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  {!readOnly && (
                  <TableCell>
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => handleOpenDialog(item)}
                    >
                      <Edit />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(item.id)}
                    >
                      <Delete />
                    </IconButton>
                  </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={filteredItems.length}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </TableContainer>

      <Dialog open={showDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingItem ? `Editar ${title}` : `Nuevo ${title}`}
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            {fields.map((field) => {
              if (field.type === 'textarea') {
                return (
                  <TextField
                    key={field.key}
                    label={field.label}
                    value={formData[field.key] || ''}
                    onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                    fullWidth
                    multiline
                    rows={3}
                    required={field.required}
                  />
                );
              } else if (field.type === 'select' && field.options) {
                return (
                  <TextField
                    key={field.key}
                    select
                    label={field.label}
                    value={formData[field.key] || ''}
                    onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                    fullWidth
                    required={field.required}
                  >
                    {field.options.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </TextField>
                );
              } else if (field.key === 'activo') {
                return (
                  <FormControlLabel
                    key={field.key}
                    control={
                      <Switch
                        checked={formData[field.key] !== false}
                        onChange={(e) => setFormData({ ...formData, [field.key]: e.target.checked })}
                      />
                    }
                    label="Activo"
                  />
                );
              } else {
                return (
                  <TextField
                    key={field.key}
                    label={field.label}
                    value={formData[field.key] || ''}
                    onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                    fullWidth
                    type={field.type || 'text'}
                    required={field.required}
                  />
                );
              }
            })}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={saving}>
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={saving || fields.some(f => f.required && !formData[f.key])}
          >
            {saving ? <CircularProgress size={20} /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default CatalogoBase;

