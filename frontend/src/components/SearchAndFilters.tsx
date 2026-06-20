import React from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Typography,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Search,
  Refresh,
  Add,
  FilterList,
  Clear,
} from '@mui/icons-material';

export interface FilterOption {
  value: string;
  label: string;
}

export interface SearchAndFiltersProps {
  // Búsqueda
  searchTerm: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  
  // Filtros
  filters?: {
    [key: string]: {
      value: string;
      options: FilterOption[];
      label: string;
      onChange: (value: string) => void;
    };
  };
  
  // Acciones
  onRefresh?: () => void;
  onAdd?: () => void;
  addButtonText?: string;
  
  // Información de resultados
  totalItems?: number;
  filteredItems?: number;
  
  // Personalización
  showResultsInfo?: boolean;
  showFilters?: boolean;
  compact?: boolean;
}

const SearchAndFilters: React.FC<SearchAndFiltersProps> = ({
  searchTerm,
  onSearchChange,
  searchPlaceholder = "Buscar...",
  filters = {},
  onRefresh,
  onAdd,
  addButtonText = "Nuevo",
  totalItems,
  filteredItems,
  showResultsInfo = true,
  showFilters = true,
  compact = false,
}) => {
  const hasActiveFilters = Object.values(filters).some(filter => filter.value !== '');
  const hasSearch = searchTerm.trim() !== '';

  const handleClearAll = () => {
    onSearchChange('');
    Object.values(filters).forEach(filter => {
      filter.onChange('');
    });
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent sx={{ p: compact ? 2 : 3 }}>
        {/* Búsqueda, Filtros y Acciones en una sola línea */}
        <Box sx={{ 
          display: 'flex', 
          gap: 2, 
          alignItems: 'center', 
          flexWrap: 'nowrap',
          overflow: 'auto',
          pb: 1
        }}>
          {/* Búsqueda */}
          <TextField
            size="small"
            label="Buscar"
            placeholder={searchPlaceholder}
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
            sx={{ minWidth: 200, flexShrink: 0 }}
          />
          
          {/* Filtros */}
          {showFilters && Object.keys(filters).length > 0 && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                <FilterList sx={{ color: 'text.secondary', fontSize: 18 }} />
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  Filtros:
                </Typography>
              </Box>
              
              {Object.entries(filters).map(([key, filter]) => (
                <FormControl key={key} size="small" sx={{ minWidth: 140, flexShrink: 0 }}>
                  <InputLabel sx={{ fontSize: '0.75rem' }}>{filter.label}</InputLabel>
                  <Select
                    value={filter.value}
                    label={filter.label}
                    onChange={(e) => filter.onChange(e.target.value)}
                    sx={{ fontSize: '0.75rem' }}
                  >
                    <MenuItem value="" sx={{ fontSize: '0.75rem' }}>Todos</MenuItem>
                    {filter.options.map((option) => (
                      <MenuItem key={option.value} value={option.value} sx={{ fontSize: '0.75rem' }}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ))}
            </>
          )}
          
          {/* Espaciador */}
          <Box sx={{ flexGrow: 1 }} />
          
          {/* Botones de Acción */}
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            {(hasActiveFilters || hasSearch) && (
              <Tooltip title="Limpiar todos los filtros">
                <IconButton
                  size="small"
                  onClick={handleClearAll}
                  color="error"
                  sx={{ width: 32, height: 32 }}
                >
                  <Clear sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            )}
            
            {onRefresh && (
              <Tooltip title="Actualizar">
                <IconButton
                  size="small"
                  onClick={onRefresh}
                  color="primary"
                  sx={{ width: 32, height: 32 }}
                >
                  <Refresh sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            )}
            
            {onAdd && (
              <Button
                variant="contained"
                color="primary"
                startIcon={<Add sx={{ fontSize: 16 }} />}
                onClick={onAdd}
                size="small"
                sx={{ fontSize: '0.75rem', px: 2, py: 0.5 }}
              >
                {addButtonText}
              </Button>
            )}
          </Box>
        </Box>

        {/* Información de Resultados */}
        {showResultsInfo && (totalItems !== undefined || filteredItems !== undefined) && (
          <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Mostrando {filteredItems || 0} de {totalItems || 0} elementos
            </Typography>
            
            {(hasSearch || hasActiveFilters) && (
              <Chip
                label="Filtros activos"
                size="small"
                color="primary"
                variant="outlined"
                sx={{ height: 20, fontSize: '0.625rem' }}
              />
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default SearchAndFilters;
