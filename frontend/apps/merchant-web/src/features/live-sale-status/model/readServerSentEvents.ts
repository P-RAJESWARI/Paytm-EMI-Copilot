import { ServerSentEventParser, type ServerSentEvent } from './ServerSentEventParser';

/** Reading the event-stream body failed, for example because the connection dropped mid-stream. */
export class LiveStatusStreamReadError extends Error {}

// Reads the next chunk, turning a failed read (the body stream broke) into LiveStatusStreamReadError
// so it is told apart from an error thrown while handling an event.
async function readNextChunk(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): Promise<ReadableStreamReadResult<Uint8Array>> {
  try {
    return await reader.read();
  } catch (error) {
    throw new LiveStatusStreamReadError('The live status stream broke while reading.', {
      cause: error,
    });
  }
}

// Reads an event-stream body to its end, handing each event over as it completes; aborting the
// signal cancels the read so the connection closes. Errors from onEvent pass through unchanged.
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
      const { done, value } = await readNextChunk(reader);
      if (done || signal.aborted) return;
      parser.push(decoder.decode(value, { stream: true })).forEach(onEvent);
    }
  } finally {
    signal.removeEventListener('abort', cancelRead);
  }
}
