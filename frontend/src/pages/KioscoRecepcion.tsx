import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { kioscoCheckin } from '../services/recepcionApi';
import type { KioscoCheckinResult } from '../types/recepcion';
import { getSafeClinicalActionMessage } from '../utils/apiError';

type Step = 'tipo' | 'datos' | 'resultado';

/** QR papel: solo recepción (puesto 1) o sala de extracción. Turno → app «Estoy en sala». */
const TIPOS_VISITA: { codigo: string; label: string; hint: string }[] = [
  {
    codigo: 'SIN_TURNO',
    label: 'Recepción / secretaría (puesto 1)',
    hint: 'Atención administrativa o sin turno',
  },
  {
    codigo: 'EXTRACCION',
    label: 'Sala de extracción / laboratorio',
    hint: 'Toma de muestra / sangre',
  },
];

/** Fondos claros + texto oscuro: legible en tablet / sala brillante. */
const prioridadStyle = (codigo?: string) => {
  switch (codigo) {
    case 'EN_HORARIO':
      return { bgcolor: '#dcfce7', color: '#14532d', border: '3px solid #16a34a' };
    case 'ANTICIPADO':
      return { bgcolor: '#dbeafe', color: '#1e3a8a', border: '3px solid #2563eb' };
    case 'TARDE':
      return { bgcolor: '#ffedd5', color: '#9a3412', border: '3px solid #ea580c' };
    default:
      return { bgcolor: '#e2e8f0', color: '#0f172a', border: '3px solid #64748b' };
  }
};

/**
 * Anuncio por QR impreso (celular): recepción puesto 1 o lab → DNI/apellido → código.
 * Consulta/estudio con turno: solo desde la app («Estoy en sala»).
 * Ruta: /kiosco-recepcion
 */
const KioscoRecepcion: React.FC = () => {
  const [step, setStep] = useState<Step>('tipo');
  const [tipo, setTipo] = useState<string | null>(null);
  const [dni, setDni] = useState('');
  const [apellido, setApellido] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KioscoCheckinResult | null>(null);

  const reset = () => {
    setResult(null);
    setError(null);
    setTipo(null);
    setDni('');
    setApellido('');
    setStep('tipo');
  };

  useEffect(() => {
    if (step !== 'resultado') return undefined;
    const t = window.setTimeout(() => {
      reset();
    }, 45000);
    return () => window.clearTimeout(t);
  }, [step, result?.llegada_id]);

  const elegirTipo = (codigo: string) => {
    setTipo(codigo);
    setError(null);
    setStep('datos');
  };

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!tipo) return;
    setError(null);
    setLoading(true);
    try {
      const data = await kioscoCheckin(dni.trim(), apellido.trim(), tipo);
      setResult(data);
      setStep('resultado');
      setDni('');
      setApellido('');
    } catch (err) {
      setError(getSafeClinicalActionMessage(err, 'No se pudo registrar la llegada.'));
    } finally {
      setLoading(false);
    }
  };

  const tipoLabel = TIPOS_VISITA.find((t) => t.codigo === tipo)?.label;
  const esLab = result?.tipo_actividad === 'EXTRACCION' || tipo === 'EXTRACCION';

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: '#e8eef5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: { xs: 1.5, md: 2 },
      }}
    >
      <Paper
        elevation={2}
        sx={{
          width: '100%',
          maxWidth: step === 'tipo' ? 720 : 560,
          p: { xs: 2.5, md: 4 },
          borderRadius: 3,
          bgcolor: '#ffffff',
          color: '#0f172a',
          border: '1px solid #cbd5e1',
        }}
      >
        <Typography
          variant="h4"
          fontWeight={800}
          gutterBottom
          sx={{ letterSpacing: -0.5, color: '#0f172a' }}
        >
          Bienvenido
        </Typography>

        {step === 'tipo' && (
          <>
            <Typography sx={{ mb: 2.5, fontSize: '1.2rem', color: '#334155', fontWeight: 500 }}>
              ¿Para qué venís hoy?
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
                gap: 1.5,
              }}
            >
              {TIPOS_VISITA.map((t) => (
                <Button
                  key={t.codigo}
                  variant="outlined"
                  onClick={() => elegirTipo(t.codigo)}
                  sx={{
                    py: 2.25,
                    px: 2,
                    textAlign: 'left',
                    justifyContent: 'flex-start',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    bgcolor: '#ffffff',
                    color: '#0f172a',
                    borderColor: '#94a3b8',
                    borderWidth: 2,
                    '&:hover': {
                      bgcolor: '#f1f5f9',
                      borderColor: '#0f172a',
                      borderWidth: 2,
                    },
                    borderRadius: 2,
                    textTransform: 'none',
                    minHeight: 96,
                    boxShadow: 'none',
                  }}
                >
                  <Typography
                    component="span"
                    fontWeight={800}
                    fontSize="1.3rem"
                    lineHeight={1.2}
                    sx={{ color: '#0f172a' }}
                  >
                    {t.label}
                  </Typography>
                  <Typography
                    component="span"
                    fontSize="0.95rem"
                    sx={{ color: '#475569', mt: 0.75, fontWeight: 500 }}
                  >
                    {t.hint}
                  </Typography>
                </Button>
              ))}
            </Box>
          </>
        )}

        {step === 'datos' && (
          <Box component="form" onSubmit={submit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography sx={{ mb: 0.5, fontSize: '1.15rem', color: '#334155' }}>
              Motivo:{' '}
              <Box component="strong" sx={{ color: '#0f172a' }}>
                {tipoLabel}
              </Box>
            </Typography>
            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
            <TextField
              label="DNI"
              value={dni}
              onChange={(e) => setDni(e.target.value.replace(/\D/g, ''))}
              inputProps={{ inputMode: 'numeric', style: { fontSize: '1.5rem', color: '#0f172a' } }}
              InputLabelProps={{ sx: { color: '#475569', fontWeight: 600 } }}
              required
              fullWidth
              autoFocus
            />
            <TextField
              label="Apellido"
              value={apellido}
              onChange={(e) => setApellido(e.target.value)}
              inputProps={{ style: { fontSize: '1.5rem', color: '#0f172a' } }}
              InputLabelProps={{ sx: { color: '#475569', fontWeight: 600 } }}
              required
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={loading || dni.length < 6 || apellido.trim().length < 2}
              sx={{
                py: 1.85,
                fontSize: '1.25rem',
                fontWeight: 700,
                bgcolor: '#0f172a',
                color: '#ffffff',
                '&:hover': { bgcolor: '#1e293b' },
                '&.Mui-disabled': { bgcolor: '#94a3b8', color: '#ffffff' },
              }}
            >
              {loading ? <CircularProgress size={28} sx={{ color: '#fff' }} /> : 'Anunciarme'}
            </Button>
            <Button
              size="large"
              onClick={() => setStep('tipo')}
              disabled={loading}
              sx={{ py: 1.25, color: '#0f172a', fontWeight: 600, fontSize: '1.05rem' }}
            >
              Volver
            </Button>
          </Box>
        )}

        {step === 'resultado' && result && (
          <Box sx={{ textAlign: 'center' }}>
            <Typography sx={{ mb: 1, color: '#475569', fontWeight: 600 }}>
              Tu número
            </Typography>
            <Typography
              sx={{
                fontSize: { xs: '3.5rem', md: '4.5rem' },
                fontWeight: 900,
                letterSpacing: 3,
                lineHeight: 1,
                mb: 2,
                color: '#0f172a',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {result.codigo_llamado ||
                (result.numero_orden_dia != null ? `#${result.numero_orden_dia}` : '—')}
            </Typography>

            {result.prioridad && result.prioridad.codigo !== 'SIN_TURNO' && (
              <Box
                sx={{
                  ...prioridadStyle(result.prioridad.codigo),
                  borderRadius: 2,
                  p: 2,
                  mb: 2,
                  textAlign: 'center',
                }}
              >
                {result.prioridad.hora_turno && (
                  <Typography
                    sx={{
                      fontSize: '2rem',
                      fontWeight: 900,
                      lineHeight: 1,
                      mb: 0.5,
                      fontVariantNumeric: 'tabular-nums',
                      color: 'inherit',
                    }}
                  >
                    {result.prioridad.hora_turno}
                  </Typography>
                )}
                <Typography fontWeight={800} fontSize="1.1rem" sx={{ color: 'inherit' }}>
                  {result.prioridad.label}
                </Typography>
                <Typography fontSize="0.95rem" sx={{ color: 'inherit', fontWeight: 500, mt: 0.5 }}>
                  {result.prioridad.detalle}
                </Typography>
              </Box>
            )}

            <Alert severity="success" sx={{ mb: 2, textAlign: 'left', fontWeight: 600 }}>
              {result.mensaje ||
                (esLab
                  ? 'Quedaste en cola de laboratorio. Mirá la TV de recepción.'
                  : 'Quedaste en cola de recepción. Mirá la TV.')}
            </Alert>

            <Typography sx={{ mb: 2, color: '#334155', fontSize: '1.1rem', fontWeight: 500 }}>
              {esLab
                ? 'Laboratorio te va a llamar por la TV. Opcional: dejá abierta la pantalla de avisos.'
                : 'Quedaste en cola. Cuando recepción te llame, avisa la TV'
                + (result.espera_path || result.token_espera
                  ? ' y esta pantalla si la dejás abierta.'
                  : '.')}
            </Typography>

            {(result.espera_path || result.token_espera) && (
              <Button
                fullWidth
                variant="outlined"
                size="large"
                href={result.espera_path || `/espera/${result.token_espera}`}
                sx={{
                  mb: 1.5,
                  py: 1.5,
                  fontSize: '1.05rem',
                  fontWeight: 700,
                  borderWidth: 2,
                  borderColor: '#0f172a',
                  color: '#0f172a',
                }}
              >
                Dejar pantalla abierta (avisos en el celular)
              </Button>
            )}

            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={reset}
              sx={{
                py: 1.75,
                fontSize: '1.15rem',
                fontWeight: 700,
                bgcolor: '#0f172a',
                color: '#ffffff',
                '&:hover': { bgcolor: '#1e293b' },
              }}
            >
              Listo
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default KioscoRecepcion;
