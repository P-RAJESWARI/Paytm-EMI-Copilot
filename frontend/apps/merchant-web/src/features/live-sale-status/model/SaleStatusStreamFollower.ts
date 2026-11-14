import { openSaleStatusStream, type SaleStatusStreamConnection } from '../api/openSaleStatusStream';
import { LiveStatusReconnectPolicy } from './LiveStatusReconnectPolicy';
import { readServerSentEvents } from './readServerSentEvents';
import type { ServerSentEvent } from './ServerSentEventParser';

/** What the follower tells the screen about: events, recoveries, polling and a lost token. */
export interface SaleStatusStreamListener {
  onEvent: (event: ServerSentEvent) => void;
  onRecovered: () => void;
  onPollingChange: (isPolling: boolean) => void;
  onSignedOut: () => void;
}

// Follows the live sale-status stream until stopped: reads it, reconnects after any failure with
// growing waits, asks for polling after three failures in a row and stops for good on 401.
export class SaleStatusStreamFollower {
  private readonly abortController = new AbortController();
  private readonly reconnectPolicy = new LiveStatusReconnectPolicy();
  private reconnectTimer: ReturnType<typeof setTimeout> | undefined;

  constructor(
    private readonly connection: SaleStatusStreamConnection,
    private readonly listener: SaleStatusStreamListener,
  ) {}

  // Opens the first connection.
  start(): void {
    void this.connect();
  }

  // Closes the stream and cancels any planned reconnection.
  stop(): void {
    this.abortController.abort();
    clearTimeout(this.reconnectTimer);
  }

  // Opens the stream once and reads it until it ends or fails, then plans the next try.
  private async connect(): Promise<void> {
    const { signal } = this.abortController;
    try {
      const body = await openSaleStatusStream(this.connection, signal);
      if (body === undefined) {
        this.listener.onSignedOut();
        return;
      }
      if (this.reconnectPolicy.recordConnected()) this.listener.onRecovered();
      this.listener.onPollingChange(false);
      await readServerSentEvents(body, signal, this.listener.onEvent);
    } catch {
      // Any failure, a dropped stream or an unexpected error, counts as a failed connection, so
      // the feed backs off and falls back to polling instead of stopping with nothing caught.
    }
    if (!signal.aborted) this.scheduleReconnect();
  }

  // Counts the failure, asks for polling when due, and tries again after the backoff.
  private scheduleReconnect(): void {
    const decision = this.reconnectPolicy.recordFailure();
    if (decision.shouldPoll) this.listener.onPollingChange(true);
    this.reconnectTimer = setTimeout(() => {
      void this.connect();
    }, decision.reconnectDelayInMilliseconds);
  }
}
