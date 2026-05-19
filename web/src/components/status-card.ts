import { api, ApiError } from '../api';

export function statusCard(): HTMLElement {
  const root = document.createElement('section');
  root.className = 'card flex items-center justify-between gap-6';
  root.innerHTML = `
    <div class="flex items-center gap-4">
      <div class="dot h-3 w-3 rounded-full bg-slate-300"></div>
      <div>
        <div class="text-sm uppercase tracking-wider text-slate-500">API status</div>
        <div class="status mt-1 text-lg font-semibold">checking…</div>
      </div>
    </div>
    <dl class="grid grid-cols-2 gap-x-8 gap-y-1 text-right text-sm text-slate-600">
      <dt>version</dt><dd class="version mono">—</dd>
      <dt>pending asks</dt><dd class="pending mono">—</dd>
    </dl>
  `;

  const dot = root.querySelector('.dot') as HTMLDivElement;
  const status = root.querySelector('.status') as HTMLDivElement;
  const version = root.querySelector('.version') as HTMLDivElement;
  const pending = root.querySelector('.pending') as HTMLDivElement;

  async function refresh(): Promise<void> {
    try {
      const h = await api.health();
      dot.className = 'dot h-3 w-3 rounded-full bg-emerald-500 shadow-glow';
      status.textContent = 'online';
      version.textContent = h.version;
      pending.textContent = String(h.pending_asks);
    } catch (e) {
      dot.className = 'dot h-3 w-3 rounded-full bg-rose-500';
      status.textContent = e instanceof ApiError ? `error ${e.status}` : 'offline';
      version.textContent = '—';
      pending.textContent = '—';
    }
  }

  refresh();
  setInterval(refresh, 5000);
  return root;
}
