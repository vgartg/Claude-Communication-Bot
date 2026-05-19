import { api } from '../api';
import type { PendingItem } from '../types';

function renderItem(item: PendingItem): HTMLLIElement {
  const li = document.createElement('li');
  li.className = 'rounded-xl border border-slate-200 bg-slate-50 p-4';
  const optionsHtml =
    item.options.length > 0
      ? `<div class="mt-2 flex flex-wrap gap-2">${item.options
          .map((o) => `<span class="pill bg-brand-50 text-brand-700">${escapeHtml(o)}</span>`)
          .join('')}</div>`
      : '';
  const session = item.session_id
    ? `<span class="pill bg-slate-200 text-slate-700 mono">${escapeHtml(item.session_id)}</span>`
    : '';
  li.innerHTML = `
    <div class="flex items-start justify-between gap-3">
      <div class="font-medium text-slate-900">${escapeHtml(item.question)}</div>
      <span class="pill mono">${escapeHtml(item.ask_id)}</span>
    </div>
    ${optionsHtml}
    <div class="mt-2 text-xs text-slate-500 flex items-center gap-2">${session}</div>
  `;
  return li;
}

function escapeHtml(s: string): string {
  return s
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

export function pendingList(): HTMLElement {
  const root = document.createElement('section');
  root.className = 'card';
  root.innerHTML = `
    <header class="flex items-baseline justify-between mb-4">
      <h2 class="text-lg font-semibold">Pending questions</h2>
      <span class="count text-sm text-slate-500">0</span>
    </header>
    <ul class="list flex flex-col gap-3"></ul>
    <p class="empty text-sm text-slate-500">No questions are waiting right now</p>
  `;

  const list = root.querySelector('.list') as HTMLUListElement;
  const count = root.querySelector('.count') as HTMLSpanElement;
  const empty = root.querySelector('.empty') as HTMLParagraphElement;

  async function refresh(): Promise<void> {
    try {
      const data = await api.pending();
      list.innerHTML = '';
      data.items.forEach((it) => list.appendChild(renderItem(it)));
      count.textContent = String(data.items.length);
      empty.hidden = data.items.length > 0;
      list.hidden = data.items.length === 0;
    } catch {
      // status card already surfaces the offline state
    }
  }

  refresh();
  setInterval(refresh, 3000);
  return root;
}
