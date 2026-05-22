import { api } from '../api';

export function routesCard(): HTMLElement {
  const root = document.createElement('section');
  root.className = 'card';
  root.innerHTML = `
    <h2 class="text-lg font-semibold mb-4">HTTP routes</h2>
    <ul class="list flex flex-col gap-2 text-sm"></ul>
  `;
  const list = root.querySelector('.list') as HTMLUListElement;

  api
    .routes()
    .then((items) => {
      list.innerHTML = items
        .map(
          (r) => `
        <li class="flex items-baseline gap-3">
          <span class="pill bg-brand-50 text-brand-700 mono">${r.method}</span>
          <code class="mono text-slate-800">${r.path}</code>
          <span class="text-slate-500">${escapeHtml(r.description)}</span>
          ${r.auth ? '<span class="pill bg-amber-50 text-amber-700">auth</span>' : ''}
        </li>`,
        )
        .join('');
    })
    .catch(() => {
      list.innerHTML =
        '<li class="text-slate-500">Routes unavailable while the API is offline</li>';
    });

  return root;
}

function escapeHtml(s: string): string {
  return s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}
