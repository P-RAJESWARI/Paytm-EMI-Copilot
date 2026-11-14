/** A text/event-stream body a test writes to, chunk by chunk. */
export interface ControllableEventStream {
  /** Answers a request with this stream as the body. */
  createResponse: () => Response;
  /** Sends raw event-stream text, for example 'event: resync\ndata: {}\n\n'. */
  send: (text: string) => void;
  /** Ends the stream as the server would. */
  close: () => void;
  /** Breaks the stream mid-read with the given error. */
  fail: (error: Error) => void;
}

// Builds an event stream whose chunks the test decides, to drive the live status hook.
export function createControllableEventStream(): ControllableEventStream {
  const encoder = new TextEncoder();
  let streamController: ReadableStreamDefaultController<Uint8Array> | undefined;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      streamController = controller;
    },
  });
  return {
    createResponse: () => new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }),
    send: (text) => {
      streamController?.enqueue(encoder.encode(text));
    },
    close: () => {
      streamController?.close();
    },
    fail: (error) => {
      streamController?.error(error);
    },
  };
}
