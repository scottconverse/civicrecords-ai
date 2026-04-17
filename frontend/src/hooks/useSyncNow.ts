import { useState, useEffect, useRef, useCallback } from "react";

interface SyncNowState {
  isSyncing: boolean;
  elapsedSeconds: number;
  error: string | null;
}

const POLL_INTERVALS = [5000, 10000, 20000, 30000]; // ms, cap at 30s
const TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

export function useSyncNow(sourceId: string, onComplete: () => void) {
  const [state, setState] = useState<SyncNowState>({
    isSyncing: false,
    elapsedSeconds: 0,
    error: null,
  });

  const triggeredAtRef = useRef<number | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const elapsedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollIndexRef = useRef(0);

  const clearTimers = useCallback(() => {
    if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current);
    if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
  }, []);

  const stopSync = useCallback(
    (errorMsg: string | null = null) => {
      clearTimers();
      setState({ isSyncing: false, elapsedSeconds: 0, error: errorMsg });
      triggeredAtRef.current = null;
      pollIndexRef.current = 0;
    },
    [clearTimers]
  );

  const pollForCompletion = useCallback(async () => {
    const triggeredAt = triggeredAtRef.current;
    if (!triggeredAt) return;

    if (Date.now() - triggeredAt > TIMEOUT_MS) {
      stopSync(null);
      onComplete();
      return;
    }

    try {
      const resp = await fetch(`/datasources/${sourceId}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      const lastSyncAt = data.last_sync_at ? new Date(data.last_sync_at).getTime() : 0;
      if (lastSyncAt > triggeredAt) {
        stopSync(null);
        onComplete();
        return;
      }
    } catch {
      // Poll errors are non-fatal — keep polling
    }

    const nextInterval = POLL_INTERVALS[Math.min(pollIndexRef.current, POLL_INTERVALS.length - 1)];
    pollIndexRef.current = Math.min(pollIndexRef.current + 1, POLL_INTERVALS.length - 1);
    pollIntervalRef.current = setTimeout(pollForCompletion, nextInterval);
  }, [sourceId, stopSync, onComplete]);

  const triggerSync = useCallback(async () => {
    if (state.isSyncing) return;

    try {
      const resp = await fetch(`/datasources/${sourceId}/ingest`, { method: "POST" });
      if (!resp.ok) throw new Error(`Trigger failed: HTTP ${resp.status}`);

      triggeredAtRef.current = Date.now();
      pollIndexRef.current = 0;
      setState({ isSyncing: true, elapsedSeconds: 0, error: null });

      elapsedIntervalRef.current = setInterval(() => {
        setState((prev) => ({
          ...prev,
          elapsedSeconds: prev.elapsedSeconds + 1,
        }));
      }, 1000);

      pollIntervalRef.current = setTimeout(pollForCompletion, POLL_INTERVALS[0]);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Sync trigger failed",
      }));
    }
  }, [sourceId, state.isSyncing, pollForCompletion]);

  useEffect(() => () => clearTimers(), [clearTimers]);

  return { ...state, triggerSync };
}
