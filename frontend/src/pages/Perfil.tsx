import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  GridLegacy as Grid,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import { apiService } from '../services/api';
import type { UpdateCurrentUserPayload, UserProfileData } from '../types';

const GENERO_OPTIONS = [
  { value: '', label: 'Sin especificar' },
  { value: 'M', label: 'Masculino' },
  { value: 'F', label: 'Femenino' },
  { value: 'O', label: 'Otro' },
];

const GRUPO_SANGUINEO_OPTIONS = ['', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

function formatDrfError(err: unknown): string {
  const e = err as { response?: { data?: unknown; status?: number }; message?: string };
  const data = e.response?.data;
  if (data && typeof data === 'object') {
    const o = data as Record<string, unknown>;
    if (typeof o.error === 'string') return o.error;
    if (typeof o.detail === 'string') return o.detail;
  }
  if (e.response?.status === 401) return 'Sesión expirada. Inicie sesión nuevamente.';
  return e.message || 'No se pudo guardar el perfil.';
}

const Perfil: React.FC = () => {
  const { currentUser, setCurrentUser, loadCurrentUser } = useData();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [telefono, setTelefono] = useState('');
  const [profile, setProfile] = useState<UserProfileData>({});
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const user = await apiService.getCurrentUser();
        if (cancelled) return;
        setFirstName(user.first_name || '');
        setLastName(user.last_name || '');
        setEmail(user.email || '');
        setTelefono(user.telefono || '');
        setProfile(user.profile || {});
        setCurrentUser({
          ...user,
          rol: (user.rol || '').toUpperCase() as typeof user.rol,
        });
      } catch (err) {
        if (!cancelled) setError(formatDrfError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setCurrentUser]);

  const updateProfileField = <K extends keyof UserProfileData>(key: K, value: UserProfileData[K]) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword || newPasswordConfirm || oldPassword) {
      if (!oldPassword || !newPassword) {
        setError('Para cambiar la contraseña complete la actual y la nueva.');
        return;
      }
      if (newPassword !== newPasswordConfirm) {
        setError('La confirmación de contraseña no coincide.');
        return;
      }
      if (newPassword.length < 8) {
        setError('La nueva contraseña debe tener al menos 8 caracteres.');
        return;
      }
    }

    const payload: UpdateCurrentUserPayload = {
      first_name: firstName,
      last_name: lastName,
      email,
      telefono,
      profile: {
        fecha_nacimiento: profile.fecha_nacimiento || null,
        genero: profile.genero || null,
        direccion: profile.direccion || null,
        ciudad: profile.ciudad || null,
        codigo_postal: profile.codigo_postal || null,
        grupo_sanguineo: profile.grupo_sanguineo || null,
        alergias: profile.alergias || null,
        medicamentos_actuales: profile.medicamentos_actuales || null,
        contacto_emergencia_nombre: profile.contacto_emergencia_nombre || null,
        contacto_emergencia_telefono: profile.contacto_emergencia_telefono || null,
        contacto_emergencia_relacion: profile.contacto_emergencia_relacion || null,
      },
    };

    if (newPassword) {
      payload.old_password = oldPassword;
      payload.new_password = newPassword;
      payload.new_password_confirm = newPasswordConfirm;
    }

    setSaving(true);
    try {
      const updated = await apiService.updateCurrentUser(payload);
      setCurrentUser({
        ...updated,
        rol: (updated.rol || '').toUpperCase() as typeof updated.rol,
      });
      setProfile(updated.profile || {});
      setOldPassword('');
      setNewPassword('');
      setNewPasswordConfirm('');
      setSuccess('Perfil actualizado correctamente.');
      loadCurrentUser();
    } catch (err) {
      setError(formatDrfError(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSave} sx={{ maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h5" fontWeight={600} gutterBottom>
        Mi perfil
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Consulte y edite sus datos personales. El usuario y el rol no se pueden modificar desde aquí.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Datos de cuenta
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Usuario"
              value={currentUser?.username || ''}
              fullWidth
              disabled
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Rol"
              value={currentUser?.rol || ''}
              fullWidth
              disabled
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Nombre"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Apellido"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Teléfono"
              value={telefono}
              onChange={(e) => setTelefono(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Datos personales
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Fecha de nacimiento"
              type="date"
              value={profile.fecha_nacimiento || ''}
              onChange={(e) => updateProfileField('fecha_nacimiento', e.target.value || null)}
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              select
              label="Género"
              value={profile.genero || ''}
              onChange={(e) =>
                updateProfileField('genero', (e.target.value || null) as UserProfileData['genero'])
              }
              fullWidth
              size="small"
            >
              {GENERO_OPTIONS.map((opt) => (
                <MenuItem key={opt.value || 'empty'} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Dirección"
              value={profile.direccion || ''}
              onChange={(e) => updateProfileField('direccion', e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={8}>
            <TextField
              label="Ciudad"
              value={profile.ciudad || ''}
              onChange={(e) => updateProfileField('ciudad', e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Código postal"
              value={profile.codigo_postal || ''}
              onChange={(e) => updateProfileField('codigo_postal', e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              select
              label="Grupo sanguíneo"
              value={profile.grupo_sanguineo || ''}
              onChange={(e) => updateProfileField('grupo_sanguineo', e.target.value || null)}
              fullWidth
              size="small"
            >
              {GRUPO_SANGUINEO_OPTIONS.map((opt) => (
                <MenuItem key={opt || 'empty'} value={opt}>
                  {opt || 'Sin especificar'}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Alergias"
              value={profile.alergias || ''}
              onChange={(e) => updateProfileField('alergias', e.target.value)}
              fullWidth
              size="small"
              multiline
              minRows={2}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Medicamentos actuales"
              value={profile.medicamentos_actuales || ''}
              onChange={(e) => updateProfileField('medicamentos_actuales', e.target.value)}
              fullWidth
              size="small"
              multiline
              minRows={2}
            />
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Contacto de emergencia
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Nombre"
              value={profile.contacto_emergencia_nombre || ''}
              onChange={(e) => updateProfileField('contacto_emergencia_nombre', e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Teléfono"
              value={profile.contacto_emergencia_telefono || ''}
              onChange={(e) => updateProfileField('contacto_emergencia_telefono', e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Relación"
              value={profile.contacto_emergencia_relacion || ''}
              onChange={(e) => updateProfileField('contacto_emergencia_relacion', e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Cambiar contraseña
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Opcional. Deje vacío si no desea cambiarla.
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Contraseña actual"
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              fullWidth
              size="small"
              autoComplete="current-password"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Nueva contraseña"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              fullWidth
              size="small"
              autoComplete="new-password"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Confirmar nueva"
              type="password"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              fullWidth
              size="small"
              autoComplete="new-password"
            />
          </Grid>
        </Grid>
      </Paper>

      <Divider sx={{ mb: 2 }} />

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="submit"
          variant="contained"
          startIcon={saving ? <CircularProgress size={16} color="inherit" /> : <Save />}
          disabled={saving}
        >
          Guardar cambios
        </Button>
      </Box>
    </Box>
  );
};

export default Perfil;
