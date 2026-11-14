import {
  POLLING_FALLBACK_FAILURE_COUNT,
  getReconnectDelayInMilliseconds,
} from './liveStatusTiming';

/** What to do after a failed connection: when to try again and whether to poll meanwhile. */
export interface ReconnectDecision {
  reconnectDelayInMilliseconds: number;
  shouldPoll: boolean;
}

// Counts failed connections in a row: the growing wait before the next try, polling after three
// failures, and whether a new connection is a recovery that must catch up on lost events.
export class LiveStatusReconnectPolicy {
  private consecutiveFailureCount = 0;
  private hasConnectedBefore = false;

  // Records a failed or ended connection and decides the wait and whether to poll.
  recordFailure(): ReconnectDecision {
    this.consecutiveFailureCount += 1;
    return {
      reconnectDelayInMilliseconds: getReconnectDelayInMilliseconds(this.consecutiveFailureCount),
      shouldPoll: this.consecutiveFailureCount >= POLLING_FALLBACK_FAILURE_COUNT,
    };
  }

  // Records an open stream; true when events may have been missed since the last one.
  recordConnected(): boolean {
    const mustCatchUp = this.hasConnectedBefore || this.consecutiveFailureCount > 0;
    this.consecutiveFailureCount = 0;
    this.hasConnectedBefore = true;
    return mustCatchUp;
  }
}
