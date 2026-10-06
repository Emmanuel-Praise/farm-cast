const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

export function headers(token) {
  return { 'X-Admin-Token': token || '' };
}

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

export const api = {
  stats: (t) => fetch(`${BASE}/admin/stats`, { headers: headers(t) }).then((r) => handle(r, '/admin/stats')),
  localities: (t) => fetch(`${BASE}/admin/localities`, { headers: headers(t) }).then((r) => handle(r, '/admin/localities')),
  zones: (t) => fetch(`${BASE}/admin/zones`, { headers: headers(t) }).then((r) => handle(r, '/admin/zones')),
  reports: (t) => fetch(`${BASE}/admin/reports`, { headers: headers(t) }).then((r) => handle(r, '/admin/reports')),
  messages: (t) => fetch(`${BASE}/admin/messages`, { headers: headers(t) }).then((r) => handle(r, '/admin/messages')),
  callList: (t) => fetch(`${BASE}/admin/call-list`, { headers: headers(t) }).then((r) => handle(r, '/admin/call-list')),
  forecast: (t, place) =>
    fetch(`${BASE}/admin/forecast?place=${encodeURIComponent(place)}`, { headers: headers(t) }).then((r) =>
      handle(r, '/admin/forecast'),
    ),
  broadcastDryRun: (t) =>
    fetch(`${BASE}/admin/broadcast/run?dry_run=true`, { method: 'POST', headers: headers(t) }).then((r) =>
      handle(r, '/admin/broadcast/run'),
    ),
};
