import { ServerSentEventParser, type ServerSentEvent } from './ServerSentEventParser';

// Reads an event-stream body to its end, handing each event over as it completes; aborting the
// signal cancels the read so the connection closes.
export async function readServerSentEvents(
  body: ReadableStream<Uint8Array>,
  signal: AbortSignal,
  onEvent: (event: ServerSentEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const cancelRead = () => {
    void reader.cancel();
  };
  signal.addEventListener('abort', cancelRead);
  const decoder = new TextDecoder();
  const parser = new ServerSentEventParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done || signal.aborted) return;
      parser.push(decoder.decode(value, { stream: true })).forEach(onEvent);
    }
  } finally {
    signal.removeEventListener('abort', cancelRead);
  }
}
