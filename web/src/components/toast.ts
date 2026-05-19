let container: HTMLDivElement | null = null;

function ensureContainer(): HTMLDivElement {
  if (container) return container;
  const el = document.createElement('div');
  el.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2';
  document.body.appendChild(el);
  container = el;
  return el;
}

export function toast(message: string, kind: 'info' | 'error' | 'success' = 'info'): void {
  const c = ensureContainer();
  const el = document.createElement('div');
  const palette: Record<typeof kind, string> = {
    info: 'bg-slate-800 text-white',
    error: 'bg-rose-600 text-white',
    success: 'bg-emerald-600 text-white',
  };
  el.className = `${palette[kind]} rounded-lg px-4 py-2 text-sm shadow-glow animate-fadein`;
  el.textContent = message;
  c.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 200ms';
    setTimeout(() => el.remove(), 220);
  }, 2500);
}
