import { describe, expect, it } from 'vitest';

import { ServerSentEventParser } from './ServerSentEventParser';

describe('ServerSentEventParser', () => {
  it('gives a named event once its blank line arrives', () => {
    const parser = new ServerSentEventParser();

    expect(parser.push('event: sale-status\ndata: {"a":1}\n')).toEqual([]);
    expect(parser.push('\n')).toEqual([{ eventName: 'sale-status', data: '{"a":1}' }]);
  });

  it('joins a line split across chunks and handles CRLF and CR line ends', () => {
    const parser = new ServerSentEventParser();

    expect(parser.push('event: res')).toEqual([]);
    expect(parser.push('ync\r\ndata: {}\r\n\r\nevent: x\rdata:y\r\r')).toEqual([
      { eventName: 'resync', data: '{}' },
      { eventName: 'x', data: 'y' },
    ]);
  });

  it('skips heartbeat comments, unknown fields and events without data', () => {
    const parser = new ServerSentEventParser();

    expect(parser.push(': heartbeat\n\nid: 7\nretry: 100\nevent: empty\n\n')).toEqual([]);
  });

  it('joins several data lines and defaults the event name to message', () => {
    const parser = new ServerSentEventParser();

    expect(parser.push('data: first\ndata\ndata: third\n\n')).toEqual([
      { eventName: 'message', data: 'first\n\nthird' },
    ]);
  });
});
