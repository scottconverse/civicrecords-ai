import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SourceCard, type DataSource } from "./SourceCard";

const mockSource: DataSource = {
  id: "test-source-id",
  name: "Test REST Source",
  source_type: "rest_api",
  is_active: true,
  health_status: "healthy",
  last_sync_at: null,
  next_sync_at: null,
  sync_schedule: "0 2 * * *",
  schedule_enabled: true,
  sync_paused: false,
  last_sync_status: null,
  active_failure_count: 0,
  consecutive_failure_count: 0,
  created_by: "00000000-0000-0000-0000-000000000000",
  created_at: "2024-01-01T00:00:00Z",
  last_ingestion_at: null,
};

describe("SourceCard — Sync Now button", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("test_sync_now_button_stays_disabled_until_completion", async () => {
    let fetchCallCount = 0;
    const triggeredAt = Date.now();

    vi.stubGlobal("fetch", vi.fn().mockImplementation((_url: string, opts?: RequestInit) => {
      fetchCallCount++;

      // POST /ingest — trigger
      if (opts?.method === "POST") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }

      // GET /datasources/test-source-id — poll; complete after 3 polls
      const lastSyncAt = fetchCallCount > 3
        ? new Date(triggeredAt + 10000).toISOString()
        : null;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockSource, last_sync_at: lastSyncAt }),
      });
    }));

    const onRefresh = vi.fn();
    render(<SourceCard source={mockSource} onRefresh={onRefresh} token="test-token" />);

    const syncBtn = screen.getByRole("button", { name: /sync now/i });
    expect(syncBtn).not.toBeDisabled();

    // Click sync and flush async state update
    await act(async () => {
      fireEvent.click(syncBtn);
    });

    // Button should now be disabled (isSyncing=true)
    expect(screen.getByRole("button", { name: /syncing/i })).toBeDisabled();

    // First poll after 5s
    await act(async () => { vi.advanceTimersByTime(5000); });
    await act(async () => {});  // flush promises

    // Second poll after 10s more
    await act(async () => { vi.advanceTimersByTime(10000); });
    await act(async () => {});

    // Third poll after 20s more — fetchCallCount will be 4, returns lastSyncAt
    await act(async () => { vi.advanceTimersByTime(20000); });
    await act(async () => {});  // flush stopSync state update

    // After completion, button should reset and onRefresh called
    expect(screen.getByRole("button", { name: /sync now/i })).not.toBeDisabled();
    expect(onRefresh).toHaveBeenCalled();
  }, 30000);

  it("test_sync_now_shows_elapsed_time_during_sync", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation((_url: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }
      // Never complete — keep syncing indefinitely
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockSource, last_sync_at: null }),
      });
    }));

    render(<SourceCard source={mockSource} onRefresh={vi.fn()} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /sync now/i }));
    });

    // Advance 7 minutes and 23 seconds (443,000 ms)
    await act(async () => { vi.advanceTimersByTime(7 * 60 * 1000 + 23 * 1000); });
    await act(async () => {});  // flush setInterval-triggered state updates

    // Button should show elapsed time — the interval fires each 1000ms → 443 ticks
    expect(screen.getByText(/7m/)).toBeInTheDocument();
  }, 30000);
});
