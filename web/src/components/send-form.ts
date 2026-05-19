import { api, ApiError } from '../api';
import { toast } from './toast';

const TOKEN_KEY = 'ccb_api_token';

export function sendForm(): HTMLElement {
  const root = document.createElement('section');
  root.className = 'card';
  root.innerHTML = `
    <h2 class="text-lg font-semibold mb-1">Send a test message</h2>
    <p class="text-sm text-slate-500 mb-4">
      The token is read from local storage so you never type it twice
    </p>
    <form class="form flex flex-col gap-3">
      <label class="text-sm">
        <span class="block mb-1 text-slate-700">API token</span>
        <input class="input token" name="token" type="password" placeholder="Bearer token" />
      </label>
      <label class="text-sm">
        <span class="block mb-1 text-slate-700">Message</span>
        <textarea class="input msg" name="text" rows="2"
          placeholder="A short test from the dashboard"></textarea>
      </label>
      <div class="flex justify-end">
        <button type="submit" class="btn-primary">Send notification</button>
      </div>
    </form>
  `;

  const form = root.querySelector('.form') as HTMLFormElement;
  const tokenInput = root.querySelector('.token') as HTMLInputElement;
  const msgInput = root.querySelector('.msg') as HTMLTextAreaElement;

  tokenInput.value = localStorage.getItem(TOKEN_KEY) ?? '';

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const token = tokenInput.value.trim();
    const text = msgInput.value.trim() || 'Hello from the dashboard';
    if (!token) {
      toast('Set a bearer token first', 'error');
      return;
    }
    localStorage.setItem(TOKEN_KEY, token);
    try {
      await api.notify(token, text, 'dashboard');
      toast('Notification sent', 'success');
      msgInput.value = '';
    } catch (err) {
      const msg = err instanceof ApiError ? `${err.status}: ${err.body}` : 'Network error';
      toast(msg, 'error');
    }
  });

  return root;
}
