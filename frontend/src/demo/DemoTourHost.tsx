import React, { useCallback, useEffect, useRef } from 'react';
import { Box, Button, Fab, Tooltip } from '@mui/material';
import ReplayIcon from '@mui/icons-material/Replay';
import { driver, type Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import './demoTour.css';
import { useNavigate } from 'react-router-dom';
import {
  DEMO_TOUR_ACTIVE_KEY,
  activateDemoTour,
  clearDemoTour,
  isDemoTourActive,
  readDemoTourRole,
  type DemoTourRole,
} from './demoStorage';
import { getTourSteps, type DemoTourStep } from './tourSteps';
import { useData } from '../contexts/DataContext';

function waitForElement(selector: string, timeoutMs = 7000): Promise<Element | null> {
  return new Promise((resolve) => {
    const hit = document.querySelector(selector);
    if (hit) { resolve(hit); return; }
    const finish = (element: Element | null) => {
      obs.disconnect();
      window.clearTimeout(timer);
      resolve(element);
    };
    const obs = new MutationObserver(() => {
      const element = document.querySelector(selector);
      if (element) finish(element);
    });
    const timer = window.setTimeout(() => finish(document.querySelector(selector)), timeoutMs);
    obs.observe(document.body, { childList: true, subtree: true, attributes: true });
  });
}

async function resolveStepRoute(step: DemoTourStep): Promise<string | null> {
  if (step.resolveRoute) {
    try { return await step.resolveRoute(); } catch { return null; }
  }
  return step.route || null;
}

/** Tour guiado marketing (driver.js) + FAB reiniciar / cambiar rol. */
export const DemoTourHost: React.FC = () => {
  const { isAuthenticated } = useData();
  const navigate = useNavigate();
  const driverRef = useRef<Driver | null>(null);
  const requestRef = useRef(0);
  const stepsRef = useRef<DemoTourStep[]>([]);
  const startedOnceRef = useRef(false);

  const destroyDriver = useCallback(() => {
    requestRef.current += 1;
    try {
      driverRef.current?.destroy();
    } catch {
      /* ignore */
    }
    driverRef.current = null;
  }, []);

  const showStep = useCallback(
    async (index: number) => {
      const steps = stepsRef.current;
      if (index < 0 || index >= steps.length) {
        sessionStorage.setItem(DEMO_TOUR_ACTIVE_KEY, '0');
        destroyDriver();
        return;
      }
      destroyDriver();
      const request = requestRef.current;
      const step = steps[index];
      const route = await resolveStepRoute(step);
      if (request !== requestRef.current) return;
      const missingRecord = Boolean(step.resolveRoute && !route);
      if (route || step.route) {
        navigate(route || step.route!);
        await new Promise((r) => setTimeout(r, 400));
      }
      if (request !== requestRef.current) return;
      const selector = typeof step.element === 'string' ? step.element : '';
      const target = !missingRecord && selector ? await waitForElement(selector) : null;
      if (request !== requestRef.current) return;
      if (target && step.prepare) {
        step.prepare();
        await new Promise((r) => setTimeout(r, 50));
      }
      if (request !== requestRef.current) return;
      const unavailable = missingRecord || (Boolean(selector) && !target);
      const isLast = index >= steps.length - 1;
      const d = driver({
        showProgress: true,
        progressText: `${index + 1} de ${steps.length}`,
        animate: false,
        popoverClass: 'demo-tour-popover',
        disableActiveInteraction: true,
        allowClose: true,
        overlayOpacity: 0.55,
        stagePadding: 6,
        nextBtnText: isLast ? 'Listo' : 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        // Preserve the real index so Driver enables Previous and keyboard navigation.
        steps: steps.map((_, i) => i === index ? {
          element: unavailable ? undefined : selector || undefined,
          popover: {
            ...(step.popover || { title: 'Demo', description: '' }),
            ...(unavailable ? { description: missingRecord
              ? '<p>No encontramos el registro demo necesario para este paso. Revisá que los ejemplos estén cargados en este entorno.</p><p>Podés continuar con <b>Siguiente</b> o volver con <b>Anterior</b>.</p>'
              : '<p>Esta sección no está disponible o no terminó de cargar. Podés continuar con <b>Siguiente</b> y volver a intentarlo después.</p>',
            } : {}),
            showButtons: ['next', 'previous', 'close'],
          },
        } : {}),
        onNextClick: () => {
          if (isLast) {
            sessionStorage.setItem(DEMO_TOUR_ACTIVE_KEY, '0');
            destroyDriver();
            return;
          }
          void showStep(index + 1);
        },
        onPrevClick: () => {
          if (index <= 0) return;
          void showStep(index - 1);
        },
        onCloseClick: () => {
          sessionStorage.setItem(DEMO_TOUR_ACTIVE_KEY, '0');
          destroyDriver();
        },
        onDestroyStarted: () => {
          sessionStorage.setItem(DEMO_TOUR_ACTIVE_KEY, '0');
          d.destroy();
        },
      });
      driverRef.current = d;
      d.drive(index);
    },
    [destroyDriver, navigate]
  );

  const startTour = useCallback(
    (role: DemoTourRole) => {
      activateDemoTour(role);
      stepsRef.current = getTourSteps(role);
      void showStep(0);
    },
    [showStep]
  );

  useEffect(() => {
    if (!isAuthenticated) {
      destroyDriver();
      startedOnceRef.current = false;
      return;
    }
    if (!isDemoTourActive() || startedOnceRef.current) return;
    const role = readDemoTourRole();
    if (!role) return;
    const t = window.setTimeout(() => {
      startedOnceRef.current = true;
      startTour(role);
    }, 500);
    return () => window.clearTimeout(t);
  }, [isAuthenticated, destroyDriver, startTour]);

  useEffect(() => () => destroyDriver(), [destroyDriver]);

  const role = readDemoTourRole();
  if (!isAuthenticated || !role) return null;

  return (
    <Box sx={{ position: 'fixed', right: 20, bottom: 24, zIndex: 1400, textAlign: 'center' }}>
      <Tooltip title="Reiniciar tour demo">
        <Fab
          color="primary"
          size="medium"
          data-demo="restart-tour"
          onClick={() => startTour(role)}
          aria-label="Reiniciar tour demo"
        >
          <ReplayIcon />
        </Fab>
      </Tooltip>
      <Button
        size="small"
        variant="outlined"
        sx={{ display: 'block', mt: 1, bgcolor: 'background.paper' }}
        onClick={() => {
          clearDemoTour();
          destroyDriver();
          startedOnceRef.current = false;
          navigate('/demo');
        }}
      >
        Cambiar rol
      </Button>
    </Box>
  );
};

export default DemoTourHost;
