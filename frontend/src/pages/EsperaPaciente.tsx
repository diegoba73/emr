import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import { useParams } from 'react-router-dom';
import { getEsperaPaciente, postEsperaYaVoy } from '../services/recepcionApi';
import type { EsperaPacienteEstado } from '../types/recepcion';

const VIBRA_OK = typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function';
const PATRON_VIBRAR = [400, 120, 400, 120, 400, 120, 800, 400];
const STORAGE_ALERTAS = 'synesis_espera_alertas_on';

function getAudioCtx(): AudioContext | null {
  try {
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return null;
    return new Ctx();
  } catch {
    return null;
  }
}

function tocarSirena(ctx: AudioContext | null) {
  if (!ctx) return;
  try {
    if (ctx.state === 'suspended') void ctx.resume();
    const now = ctx.currentTime;
    for (let i = 0; i < 3; i += 1) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.value = i % 2 === 0 ? 880 : 1175;
      gain.gain.setValueAtTime(0.0001, now + i * 0.35);
      gain.gain.exponentialRampToValueAtTime(0.35, now + i * 0.35 + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.35 + 0.3);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + i * 0.35);
      osc.stop(now + i * 0.35 + 0.32);
    }
  } catch {
    /* ignore */
  }
}

function vibrarFuerte(): boolean {
  try {
    if (!navigator.vibrate) return false;
    navigator.vibrate(0);
    return Boolean(navigator.vibrate(PATRON_VIBRAR));
  } catch {
    return false;
  }
}

/**
 * Pantalla pública del paciente (QR del kiosco).
 *
 * Los navegadores exigen un gesto del usuario para vibrar/sonar (política de seguridad).
 * Intentamos vibrar igual al llamar; si el SO lo bloquea, alcanza con un toque en cualquier
 * parte de la pantalla (más simple que un botón “técnico”).
 */
const EsperaPaciente: React.FC = () => {
  const { token = '' } = useParams<{ token: string }>();
  const [data, setData] = useState<EsperaPacienteEstado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [alertasOn, setAlertasOn] = useState(() => {
    try {
      return sessionStorage.getItem(STORAGE_ALERTAS) === '1';
    } catch {
      return false;
    }
  });
  const [avisando, setAvisando] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const loopRef = useRef<number | null>(null);
  const wakeLockRef = useRef<{ release: () => Promise<void> } | null>(null);
  const llamadoVistoRef = useRef(false);

  const load = useCallback(async () => {
    if (!token || token.length < 12) {
      setError('Enlace inválido.');
      setLoading(false);
      return;
    }
    try {
      const estado = await getEsperaPaciente(token);
      setData(estado);
      setError(null);
    } catch {
      setError('No encontramos esta espera. Pedí un QR nuevo en el kiosco.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 2500);
    return () => window.clearInterval(id);
  }, [load]);

  /** Solo corta sonido/vibración. No toca el estado clínico (eso es «Ya voy»). */
  const silenciarAviso = useCallback(() => {
    setAvisando(false);
    if (loopRef.current != null) {
      window.clearInterval(loopRef.current);
      loopRef.current = null;
    }
    try {
      navigator.vibrate?.(0);
    } catch {
      /* ignore */
    }
    try {
      document.title = 'Espera — SYNESIS';
    } catch {
      /* ignore */
    }
  }, []);

  /** Paciente confirma que escuchó el llamado (solo si estaba LLAMADO). */
  const confirmarYaVoy = useCallback(() => {
    silenciarAviso();
    if (token && token.length >= 12) {
      void postEsperaYaVoy(token)
        .then(() => load())
        .catch(() => undefined);
    }
  }, [token, load, silenciarAviso]);

  const iniciarAviso = useCallback(() => {
    setAvisando(true);
    try {
      document.title = '¡Te están llamando!';
    } catch {
      /* ignore */
    }
    const disparar = () => {
      vibrarFuerte();
      tocarSirena(audioCtxRef.current);
    };
    disparar();
    if (loopRef.current != null) window.clearInterval(loopRef.current);
    loopRef.current = window.setInterval(disparar, 2200);
  }, []);

  /** Al dejar de estar llamado: solo silenciar. Nunca «Ya voy» automático. */
  useEffect(() => {
    if (!data?.llamado) {
      llamadoVistoRef.current = false;
      silenciarAviso();
      return;
    }
    if (llamadoVistoRef.current) return;
    llamadoVistoRef.current = true;
    vibrarFuerte();
    if (alertasOn) iniciarAviso();
    else {
      // Sin gesto previo: al menos intentamos vibrar + flash visual
      setAvisando(true);
      vibrarFuerte();
      const id = window.setInterval(() => vibrarFuerte(), 2200);
      loopRef.current = id;
    }
  }, [data?.llamado, alertasOn, iniciarAviso, silenciarAviso]);

  useEffect(() => {
    if (data?.llamado && alertasOn) {
      iniciarAviso();
    }
  }, [alertasOn, data?.llamado, iniciarAviso]);

  useEffect(
    () => () => {
      silenciarAviso();
      void wakeLockRef.current?.release().catch(() => undefined);
    },
    [silenciarAviso]
  );

  const desbloquearAlertas = useCallback(async () => {
    if (alertasOn) return;
    const ctx = audioCtxRef.current || getAudioCtx();
    audioCtxRef.current = ctx;
    if (ctx?.state === 'suspended') {
      try {
        await ctx.resume();
      } catch {
        /* ignore */
      }
    }
    vibrarFuerte();
    tocarSirena(ctx);
    setAlertasOn(true);
    try {
      sessionStorage.setItem(STORAGE_ALERTAS, '1');
    } catch {
      /* ignore */
    }
    try {
      const nav = navigator as Navigator & {
        wakeLock?: { request: (type: 'screen') => Promise<{ release: () => Promise<void> }> };
      };
      if (nav.wakeLock?.request) {
        wakeLockRef.current = await nav.wakeLock.request('screen');
      }
    } catch {
      /* ignore */
    }
  }, [alertasOn]);

  // Cualquier toque / tecla desbloquea (más natural que un botón solo)
  useEffect(() => {
    if (alertasOn) return undefined;
    const onGesture = () => {
      void desbloquearAlertas();
    };
    window.addEventListener('pointerdown', onGesture, { once: true, passive: true });
    window.addEventListener('keydown', onGesture, { once: true });
    window.addEventListener('touchstart', onGesture, { once: true, passive: true });
    return () => {
      window.removeEventListener('pointerdown', onGesture);
      window.removeEventListener('keydown', onGesture);
      window.removeEventListener('touchstart', onGesture);
    };
  }, [alertasOn, desbloquearAlertas]);

  const bg = data?.llamado ? (avisando ? undefined : '#14532d') : '#e8eef5';
  const fg = data?.llamado ? '#ffffff' : '#0f172a';

  return (
    <Box
      onClick={() => void desbloquearAlertas()}
      sx={{
        minHeight: '100vh',
        bgcolor: bg || '#14532d',
        color: fg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
        cursor: alertasOn || data?.llamado ? 'default' : 'pointer',
        ...(avisando
          ? {
              animation: 'synesisFlash 0.85s ease-in-out infinite',
              '@keyframes synesisFlash': {
                '0%, 100%': { backgroundColor: '#14532d' },
                '50%': { backgroundColor: '#22c55e' },
              },
            }
          : { transition: 'background-color 0.3s ease' }),
      }}
    >
      <Box sx={{ width: '100%', maxWidth: 440, textAlign: 'center' }}>
        {loading && !data ? (
          <CircularProgress sx={{ color: fg }} />
        ) : error ? (
          <Alert severity="error" sx={{ textAlign: 'left' }}>
            {error}
          </Alert>
        ) : data ? (
          <>
            {data.paciente_nombre_publico && (
              <Typography sx={{ mb: 1, opacity: 0.9, fontWeight: 600, fontSize: '1.15rem' }}>
                {data.paciente_nombre_publico}
              </Typography>
            )}
            {(data.codigo_llamado || data.numero_orden_dia != null) && (
              <Typography
                sx={{
                  fontSize: '3.5rem',
                  fontWeight: 900,
                  lineHeight: 1,
                  mb: 1.5,
                  letterSpacing: 2,
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {data.codigo_llamado || `#${data.numero_orden_dia}`}
              </Typography>
            )}
            <Typography
              sx={{
                fontSize: data.llamado ? '2.4rem' : '1.75rem',
                fontWeight: 900,
                mb: 1.5,
                lineHeight: 1.15,
              }}
            >
              {data.titulo}
            </Typography>
            <Typography sx={{ fontSize: '1.25rem', fontWeight: 600, mb: 2, opacity: 0.95 }}>
              {data.detalle}
            </Typography>
            {data.destino && data.llamado && (
              <Box
                sx={{
                  bgcolor: 'rgba(255,255,255,0.2)',
                  color: '#fff',
                  borderRadius: 2,
                  p: 2,
                  mb: 2,
                }}
              >
                <Typography fontWeight={800} fontSize="1.5rem">
                  {data.destino}
                </Typography>
              </Box>
            )}

            {!data.llamado && !data.finalizado && !alertasOn && (
              <Box
                sx={{
                  mt: 2,
                  p: 3,
                  borderRadius: 3,
                  bgcolor: '#0f172a',
                  color: '#fff',
                }}
              >
                <Typography sx={{ fontSize: '1.6rem', fontWeight: 900, mb: 1 }}>
                  Tocá la pantalla
                </Typography>
                <Typography sx={{ fontSize: '1.15rem', fontWeight: 600, opacity: 0.95 }}>
                  Así el celular podrá vibrar cuando te llamen.
                </Typography>
                {!VIBRA_OK && (
                  <Typography sx={{ mt: 1.5, fontSize: '0.95rem', opacity: 0.85 }}>
                    Este teléfono puede no vibrar; igual sonará y parpadeará.
                  </Typography>
                )}
              </Box>
            )}

            {!data.llamado && !data.finalizado && alertasOn && (
              <Alert severity="success" sx={{ mt: 2, textAlign: 'left', fontWeight: 700 }}>
                Listo. Dejá la pantalla abierta: cuando te llamen vibra y avisa solo.
              </Alert>
            )}

            {data.llamado && (
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={(e) => {
                  e.stopPropagation();
                  confirmarYaVoy();
                }}
                sx={{
                  mt: 1,
                  py: 2,
                  fontSize: '1.25rem',
                  fontWeight: 800,
                  bgcolor: '#fff',
                  color: '#14532d',
                  '&:hover': { bgcolor: '#f0fdf4' },
                }}
              >
                Ya voy — silenciar
              </Button>
            )}

            {data.prioridad?.hora_turno && !data.llamado && !data.finalizado && (
              <Typography sx={{ mt: 2, fontWeight: 700, color: data.llamado ? fg : '#1e3a8a' }}>
                Turno {data.prioridad.hora_turno} · {data.prioridad.label}
              </Typography>
            )}
          </>
        ) : null}
      </Box>
    </Box>
  );
};

export default EsperaPaciente;
