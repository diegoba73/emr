import React, { useCallback, useEffect, useRef } from 'react';
import { Box, Button, Fab, Tooltip } from '@mui/material';
import ReplayIcon from '@mui/icons-material/Replay';
import { driver, type Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
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
    if (hit) {
      resolve(hit);
      return;
    }
    const started = Date.now();
    const obs = new MutationObserver(() => {
      const el = document.querySelector(selector);
      if (el) {
        obs.disconnect();
        resolve(el);
      } else if (Date.now() - started > timeoutMs) {
        obs.disconnect();
        resolve(null);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => {
      obs.disconnect();
      resolve(document.querySelector(selector));
    }, timeoutMs);
  });
}

async function resolveStepRoute(step: DemoTourStep): Promise<string | null> {
  if (step.resolveRoute) {
    try {
      return await step.resolveRoute();
    } catch {
      return step.route || null;
    }
  }
  return step.route || null;
}

/** Tour guiado marketing (driver.js) + FAB reiniciar / cambiar rol. */
export const DemoTourHost: React.FC = () => {
  const { isAuthenticated } = useData();
  const navigate = useNavigate();
  const driverRef = useRef<Driver | null>(null);
  const idxRef = useRef(0);
  const stepsRef = useRef<DemoTourStep[]>([]);
  const startedOnceRef = useRef(false);

  const destroyDriver = useCallback(() => {
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
      idxRef.current = index;
      const step = steps[index];
      const route = await resolveStepRoute(step);
      if (route) {
        navigate(route);
        await new Promise((r) => setTimeout(r, 400));
      }
      const selector = typeof step.element === 'string' ? step.element : '';
      if (selector) {
        await waitForElement(selector);
      }

      destroyDriver();
      const isLast = index >= steps.length - 1;
      const d = driver({
        showProgress: true,
        progressText: `${index + 1} de ${steps.length}`,
        animate: true,
        allowClose: true,
        overlayOpacity: 0.55,
        stagePadding: 6,
        nextBtnText: isLast ? 'Listo' : 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        steps: [
          {
            element: selector || undefined,
            popover: {
              ...(step.popover || { title: 'Demo', description: '' }),
              showButtons: ['next', 'previous', 'close'],
            },
          },
        ],
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
          d.destroy();
        },
      });
      driverRef.current = d;
      d.drive(0);
    },
    [destroyDriver, navigate]
  );

  const startTour = useCallback(
    (role: DemoTourRole) => {
      activateDemoTour(role);
      stepsRef.current = getTourSteps(role);
      idxRef.current = 0;
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
    startedOnceRef.current = true;
    const t = window.setTimeout(() => startTour(role), 500);
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
