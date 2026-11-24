import React from 'react';
import { act, render, waitFor } from '@testing-library/react';
import {
  notifyTurnosChanged,
  TURNOS_LIVE_CHANNEL,
  TURNOS_LIVE_EVENT,
  TURNOS_REVISION_INTERVAL_MS,
  useLiveRefresh,
} from './useLiveRefresh';

describe('notifyTurnosChanged', () => {
  it('dispara evento local en window', () => {
    const spy = jest.fn();
    window.addEventListener(TURNOS_LIVE_EVENT, spy);
    notifyTurnosChanged();
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener(TURNOS_LIVE_EVENT, spy);
  });

  it('publica en BroadcastChannel cuando está disponible', () => {
    const posts: unknown[] = [];
    class FakeChannel {
      name: string;
      onmessage: ((ev: MessageEvent) => void) | null = null;
      constructor(name: string) {
        this.name = name;
      }
      postMessage(data: unknown) {
        posts.push(data);
      }
      close() {}
    }
    const Original = (globalThis as { BroadcastChannel?: typeof BroadcastChannel }).BroadcastChannel;
    (globalThis as { BroadcastChannel: typeof BroadcastChannel }).BroadcastChannel =
      FakeChannel as unknown as typeof BroadcastChannel;
    try {
      notifyTurnosChanged();
    } finally {
      if (Original) {
        (globalThis as { BroadcastChannel: typeof BroadcastChannel }).BroadcastChannel = Original;
      } else {
        delete (globalThis as { BroadcastChannel?: typeof BroadcastChannel }).BroadcastChannel;
      }
    }
    expect(posts.length).toBeGreaterThanOrEqual(1);
    expect((posts[0] as { type: string }).type).toBe('invalidate');
    expect(TURNOS_LIVE_CHANNEL).toBe('synesis-turnos');
  });
});

function Probe(props: {
  refresh: () => void | Promise<void>;
  getRevision?: () => Promise<string | null | undefined>;
  enabled?: boolean;
}) {
  useLiveRefresh(props.refresh, {
    enabled: props.enabled !== false,
    getRevision: props.getRevision,
    listenTurnosEvents: true,
  });
  return null;
}

describe('useLiveRefresh con getRevision', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('no refresca en el primer stamp; refresca cuando el stamp cambia', async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    let stamp = 'a|1';
    const getRevision = jest.fn(async () => stamp);

    render(React.createElement(Probe, { refresh, getRevision }));

    await act(async () => {
      jest.advanceTimersByTime(TURNOS_REVISION_INTERVAL_MS);
    });
    await waitFor(() => expect(getRevision).toHaveBeenCalled());
    expect(refresh).not.toHaveBeenCalled();

    stamp = 'b|2';
    await act(async () => {
      jest.advanceTimersByTime(TURNOS_REVISION_INTERVAL_MS);
    });
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  });

  it('refresca de inmediato ante notifyTurnosChanged local', async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    const getRevision = jest.fn(async () => 'x|1');

    render(React.createElement(Probe, { refresh, getRevision }));

    await act(async () => {
      notifyTurnosChanged();
    });
    await waitFor(() => expect(refresh).toHaveBeenCalled());
  });
});
