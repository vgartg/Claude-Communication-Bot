import './style.css';
import { statusCard } from './components/status-card';
import { pendingList } from './components/pending-list';
import { sendForm } from './components/send-form';
import { routesCard } from './components/routes-card';

const app = document.getElementById('app');
if (!app) throw new Error('Missing #app root element');

app.innerHTML = `
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto max-w-6xl px-6 py-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="h-10 w-10 rounded-xl bg-brand-500 flex items-center justify-center text-white font-bold">
          C
        </div>
        <div>
          <div class="text-lg font-semibold">Claude Communication Bot</div>
          <div class="text-xs text-slate-500">
            Telegram bridge for coding agents — pings on stop, routes questions to your phone
          </div>
        </div>
      </div>
      <a
        href="https://github.com/v-gorbanev/Claude-Communication-Bot"
        class="text-sm text-slate-500 hover:text-brand-600"
      >
        GitHub →
      </a>
    </div>
  </header>

  <main class="mx-auto max-w-6xl px-6 py-8 flex flex-col gap-6">
    <div id="status"></div>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div id="pending"></div>
      <div id="send"></div>
    </div>
    <div id="routes"></div>
  </main>
`;

document.getElementById('status')!.appendChild(statusCard());
document.getElementById('pending')!.appendChild(pendingList());
document.getElementById('send')!.appendChild(sendForm());
document.getElementById('routes')!.appendChild(routesCard());
