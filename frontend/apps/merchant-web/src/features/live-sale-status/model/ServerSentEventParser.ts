/** One dispatched event of a text/event-stream: its name and its (joined) data lines. */
export interface ServerSentEvent {
  eventName: string;
  data: string;
}

const DEFAULT_EVENT_NAME = 'message';

// Reads text/event-stream chunks as they arrive and gives each complete event (WHATWG rules:
// lines end in LF, CRLF or CR; a blank line ends an event; ":" lines are comments, such as the
// heartbeat). Chunks may split a line or an event anywhere.
export class ServerSentEventParser {
  private unfinishedText = '';
  private eventName = DEFAULT_EVENT_NAME;
  private dataLines: string[] = [];

  // Adds the next chunk of text and gives the events it completed, in order.
  push(chunk: string): ServerSentEvent[] {
    const completedEvents: ServerSentEvent[] = [];
    const lines = (this.unfinishedText + chunk).split(/\r\n|\r|\n/);
    this.unfinishedText = lines.pop() ?? '';
    for (const line of lines) {
      const completedEvent = this.readLine(line);
      if (completedEvent !== undefined) completedEvents.push(completedEvent);
    }
    return completedEvents;
  }

  // Applies one whole line; gives an event when the line is the blank line that ends one.
  private readLine(line: string): ServerSentEvent | undefined {
    if (line === '') return this.dispatchEvent();
    if (line.startsWith(':')) return undefined;
    const colonIndex = line.indexOf(':');
    const fieldName = colonIndex === -1 ? line : line.slice(0, colonIndex);
    const rawValue = colonIndex === -1 ? '' : line.slice(colonIndex + 1);
    const value = rawValue.startsWith(' ') ? rawValue.slice(1) : rawValue;
    if (fieldName === 'event') this.eventName = value;
    if (fieldName === 'data') this.dataLines.push(value);
    return undefined;
  }

  // Ends the current event; an event without data lines is dropped, as browsers do.
  private dispatchEvent(): ServerSentEvent | undefined {
    const event =
      this.dataLines.length === 0
        ? undefined
        : { eventName: this.eventName, data: this.dataLines.join('\n') };
    this.eventName = DEFAULT_EVENT_NAME;
    this.dataLines = [];
    return event;
  }
}
