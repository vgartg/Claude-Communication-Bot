import type { Health, PendingList, RouteCatalogEntry } from './types';

export class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string) {
    super(`HTTP ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

interface CallOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  token?: string;
  signal?: AbortSignal;
}

async function call<T>(path: string, opts: CallOptions = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (opts.token) headers['Authorization'] = `Bearer ${opts.token}`;

  const res = await fetch(path, {
    method: opts.method ?? 'GET',
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  const text = await res.text();
  if (!res.ok) throw new ApiError(res.status, text);
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export const api = {
  health: (signal?: AbortSignal) => call<Health>('/api/health', { signal }),
  routes: () => call<RouteCatalogEntry[]>('/api/routes'),
  pending: (signal?: AbortSignal) => call<PendingList>('/api/pending', { signal }),
  notify: (token: string, text: string, sessionId?: string) =>
    call<{ status: string }>('/api/notify', {
      method: 'POST',
      token,
      body: { text, session_id: sessionId ?? null },
    }),
};
