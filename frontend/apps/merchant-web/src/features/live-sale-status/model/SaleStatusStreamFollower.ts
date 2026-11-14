import { openSaleStatusStream, type SaleStatusStreamConnection } from '../api/openSaleStatusStream';
import { isExpectedStreamFailure } from './isExpectedStreamFailure';
import { LiveStatusReconnectPolicy } from './LiveStatusReconnectPolicy';
import { readServerSentEvents } from './readServerSentEvents';
import type { ServerSentEvent } from './ServerSentEventParser';

/** What the follower tells the screen about: events, recoveries, polling, a lost token and bugs. */
export interface SaleStatusStreamListener {
  onEvent: (event: ServerSentEvent) => void;
  onRecovered: () => void;
  onPollingChange: (isPolling: boolean) => void;
  onSignedOut: () => void;
  /** An error that is not an expected stream failure; must not throw. The feed still reconnects. */
  onUnexpectedError: (error: unknown) => void;
}

// Follows the live sale-status stream until stopped: reads it, reconnects after any failure with
// growing waits, asks for polling after three failures in a row and stops for good on 401.
// Unexpected errors (bugs, not network trouble) are also reported through the listener.
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

  // Follows the stream once and plans the next try. Any failure counts as a failed connection, so
  // the feed backs off and polls rather than stopping; only unexpected ones are also reported.
  private async connect(): Promise<void> {
    const { signal } = this.abortController;
    try {
      const isSignedOut = await this.followStreamUntilItEnds(signal);
      if (isSignedOut) return;
    } catch (error) {
      // The reconnection is planned before reporting, so reporting can never stop the feed.
      if (!signal.aborted) this.scheduleReconnect();
      if (!isExpectedStreamFailure(error, signal)) this.listener.onUnexpectedError(error);
      return;
    }
    if (!signal.aborted) this.scheduleReconnect();
  }

  // Opens the stream and reads it until it ends; true when the token was refused (401) instead.
  private async followStreamUntilItEnds(signal: AbortSignal): Promise<boolean> {
    const body = await openSaleStatusStream(this.connection, signal);
    if (body === undefined) {
      this.listener.onSignedOut();
      return true;
    }
    if (this.reconnectPolicy.recordConnected()) this.listener.onRecovered();
    this.listener.onPollingChange(false);
    await readServerSentEvents(body, signal, this.listener.onEvent);
    return false;
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
