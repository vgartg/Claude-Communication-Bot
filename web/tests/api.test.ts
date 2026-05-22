import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../src/api';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

function mockFetch(body: unknown, init: { status?: number; text?: string } = {}): void {
  globalThis.fetch = vi.fn(async () => {
    const status = init.status ?? 200;
    const text = init.text ?? (body == null ? '' : JSON.stringify(body));
    return new Response(text, { status });
  }) as unknown as typeof fetch;
}

describe('api client', () => {
  it('parses JSON on success', async () => {
    mockFetch({ status: 'ok', version: '0.1.0', pending_asks: 2 });
    const h = await api.health();
    expect(h.version).toBe('0.1.0');
    expect(h.pending_asks).toBe(2);
  });

  it('throws ApiError with status and body on 4xx', async () => {
    mockFetch(null, { status: 401, text: 'Missing bearer token' });
    await expect(api.notify('', 'hello')).rejects.toBeInstanceOf(ApiError);
    try {
      await api.notify('', 'hello');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(401);
      expect((e as ApiError).body).toContain('Missing bearer token');
    }
  });

  it('sends Bearer token when notifying', async () => {
    const spy = vi.fn(async () => new Response('{"status":"sent"}', { status: 202 }));
    globalThis.fetch = spy as unknown as typeof fetch;
    await api.notify('abc123', 'hi', 'sess-1');
    const call = spy.mock.calls[0] as unknown as [string, RequestInit];
    expect(call[0]).toBe('/api/notify');
    const headers = call[1].headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer abc123');
    expect(JSON.parse(String(call[1].body))).toEqual({ text: 'hi', session_id: 'sess-1' });
  });
});
