import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { getPantallaSala } from '../services/recepcionApi';
import type { PantallaLlamadoItem, PantallaMitad } from '../types/recepcion';

const emptyMitad = (): PantallaMitad => ({
  actual: null,
  llamando: [],
  otros_llamando: [],
  proximo: null,
  historial: [],
  pendientes: [],
});

function codigoDe(item: PantallaLlamadoItem | null | undefined): string {
  if (!item) return '';
  return item.codigo_llamado || (item.numero_orden_dia ? `#${item.numero_orden_dia}` : '');
}

/** Bip corto al detectar un llamado nuevo (Web Audio). */
function playBip() {
  try {
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.35, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
    window.setTimeout(() => void ctx.close(), 600);
  } catch {
    /* TV sin audio: ignorar */
  }
}

function FilaChica({
  item,
  accent,
  muted,
  badge,
}: {
  item: PantallaLlamadoItem;
  accent: string;
  muted?: boolean;
  badge?: string;
}) {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 2,
        px: 1.5,
        py: 0.85,
        borderRadius: 1.5,
        bgcolor: muted ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.06)',
        opacity: muted ? 0.75 : 1,
        border: badge ? `1px solid ${accent}66` : undefined,
      }}
    >
      {badge ? (
        <Typography
          sx={{
            fontSize: '0.7rem',
            fontWeight: 800,
            color: accent,
            textTransform: 'uppercase',
            minWidth: 64,
          }}
        >
          {badge}
        </Typography>
      ) : null}
      <Typography fontWeight={800} sx={{ minWidth: 56, fontSize: '1.05rem' }}>
        {codigoDe(item) || '—'}
      </Typography>
      <Typography fontWeight={600} sx={{ flex: 1, fontSize: '1rem' }} noWrap>
        {item.paciente_nombre_publico}
      </Typography>
      <Typography sx={{ color: accent, fontWeight: 600, fontSize: '0.95rem' }} noWrap>
        {item.destino || item.puesto_label || ''}
      </Typography>
    </Box>
  );
}

function PanelMitad({
  titulo,
  mitad,
  accent,
}: {
  titulo: string;
  mitad: PantallaMitad;
  accent: string;
}) {
  const llamando = (mitad.llamando?.length
    ? mitad.llamando
    : mitad.actual?.estado_flujo === 'LLAMADO'
      ? [mitad.actual]
      : []
  ).filter(Boolean) as PantallaLlamadoItem[];

  const llamado = llamando[0] || null;
  const otrosLlamando = llamando.slice(1);
  const proximo = mitad.proximo || null;
  const recientes = (mitad.historial || []).slice(0, 4);

  return (
    <Paper
      elevation={0}
      sx={{
        flex: 1,
        minWidth: 0,
        bgcolor: '#111827',
        borderRadius: 3,
        p: { xs: 2, md: 3 },
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid #1f2937',
        minHeight: 320,
      }}
    >
      <Typography
        variant="h5"
        sx={{ fontWeight: 800, letterSpacing: 0.5, color: accent, mb: 1.5 }}
      >
        {titulo}
      </Typography>

      {recientes.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.75, opacity: 0.55, fontWeight: 700 }}>
            Anteriores
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {recientes.map((c) => (
              <FilaChica key={`h-${c.id}`} item={c} accent={accent} muted />
            ))}
          </Box>
        </Box>
      )}

      {otrosLlamando.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.75, opacity: 0.7, fontWeight: 700 }}>
            También llamando
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {otrosLlamando.map((c) => (
              <FilaChica key={`l-${c.id}`} item={c} accent={accent} badge="Llamando" />
            ))}
          </Box>
        </Box>
      )}

      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          minHeight: 180,
          py: 1,
        }}
      >
        {llamado ? (
          <>
            <Typography
              variant="overline"
              sx={{ color: accent, fontWeight: 800, letterSpacing: 1.5, mb: 0.5 }}
            >
              Llamando
            </Typography>
            <Typography
              sx={{
                fontWeight: 900,
                fontSize: { xs: '3rem', md: '4.8rem' },
                lineHeight: 1,
                letterSpacing: 2,
                color: '#fff',
              }}
            >
              {codigoDe(llamado) || '—'}
            </Typography>
            <Typography
              sx={{
                fontWeight: 700,
                fontSize: { xs: '1.6rem', md: '2.3rem' },
                mt: 1.5,
                lineHeight: 1.15,
              }}
            >
              {llamado.paciente_nombre_publico}
            </Typography>
            <Typography
              sx={{
                mt: 2,
                fontSize: { xs: '1.25rem', md: '1.7rem' },
                color: accent,
                fontWeight: 700,
              }}
            >
              Dirigirse a {llamado.destino || llamado.puesto_label || 'recepción'}
            </Typography>
          </>
        ) : (
          <Typography sx={{ fontSize: '1.4rem', opacity: 0.55 }}>
            Sin llamados en este momento
          </Typography>
        )}
      </Box>

      {proximo && (
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          <Typography variant="subtitle2" sx={{ mb: 0.75, opacity: 0.65, fontWeight: 700 }}>
            Siguiente
          </Typography>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 2,
              px: 2,
              py: 1.25,
              borderRadius: 2,
              bgcolor: 'rgba(255,255,255,0.07)',
              border: `1px solid ${accent}55`,
            }}
          >
            <Typography fontWeight={900} sx={{ fontSize: '1.4rem', minWidth: 64 }}>
              {codigoDe(proximo) || '—'}
            </Typography>
            <Typography fontWeight={700} sx={{ flex: 1, fontSize: '1.2rem' }} noWrap>
              {proximo.paciente_nombre_publico}
            </Typography>
            <Typography sx={{ color: accent, fontWeight: 600 }} noWrap>
              {proximo.puesto_label || proximo.destino || 'en cola'}
            </Typography>
          </Box>
        </Box>
      )}
    </Paper>
  );
}

function firmaLlamados(m: PantallaMitad): string {
  const rows = m.llamando?.length ? m.llamando : m.actual ? [m.actual] : [];
  return rows
    .filter((r) => r.estado_flujo === 'LLAMADO')
    .map((r) => `${r.id}:${r.llamado_en || ''}`)
    .join('|');
}

/**
 * Pantalla pública fullscreen para TV de sala de espera.
 * Ruta: /pantalla-sala
 */
const PantallaSala: React.FC = () => {
  const [recepcion, setRecepcion] = useState<PantallaMitad>(emptyMitad);
  const [medico, setMedico] = useState<PantallaMitad>(emptyMitad);
  const firmaRef = useRef('');
  const primedRef = useRef(false);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        const data = await getPantallaSala();
        if (!active) return;
        const rec = data.mitad_recepcion || emptyMitad();
        const med = data.mitad_medico || emptyMitad();
        const firma = `${firmaLlamados(rec)}||${firmaLlamados(med)}`;
        if (primedRef.current && firma && firma !== firmaRef.current) {
          playBip();
        }
        primedRef.current = true;
        firmaRef.current = firma;
        setRecepcion(rec);
        setMedico(med);
      } catch {
        /* TV sigue mostrando último estado */
      }
    };
    void tick();
    const id = window.setInterval(tick, 4000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: '#0b1220',
        color: '#f8fafc',
        p: { xs: 1.5, md: 3 },
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}
      onClick={() => {
        /* gesto para desbloquear audio en algunos TV/navegadores */
        if (!primedRef.current) playBip();
      }}
    >
      <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: 1, opacity: 0.85 }}>
        Turnos en atención
      </Typography>

      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          gap: 2,
          alignItems: 'stretch',
        }}
      >
        <PanelMitad titulo="Recepción" mitad={recepcion} accent="#93c5fd" />
        <PanelMitad titulo="Médico" mitad={medico} accent="#86efac" />
      </Box>
    </Box>
  );
};

export default PantallaSala;
