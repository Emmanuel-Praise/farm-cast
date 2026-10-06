const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

async function handle(res, path) {
  if (!res.ok) {
    let detail = '';
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {
      detail = await res.text();
    }
    throw new Error(`${res.status} ${path}: ${detail}`.slice(0, 300));
  }
  return res.json();
}

const get = (path) => fetch(`${BASE}${path}`).then((r) => handle(r, path));

export const api = {
  stats: () => get('/admin/stats'),
  localities: () => get('/admin/localities'),
  zones: () => get('/admin/zones'),
  reports: () => get('/admin/reports'),
  messages: () => get('/admin/messages'),
  callList: () => get('/admin/call-list'),
  forecast: (place) => get(`/admin/forecast?place=${encodeURIComponent(place)}`),
  broadcastDryRun: () =>
    fetch(`${BASE}/admin/broadcast/run?dry_run=true`, { method: 'POST' }).then((r) =>
      handle(r, '/admin/broadcast/run'),
    ),
};
