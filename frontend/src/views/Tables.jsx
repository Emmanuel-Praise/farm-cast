import React from 'react';
import { ChannelTag, ZoneChip, hhmm } from '../components/shared.jsx';

export function ReportsView({ reports, stats }) {
  const wa = reports.filter((r) => (r.channel || 'whatsapp') !== 'sms').length;
  const sms = reports.length - wa;
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>All ground reports — today</h2>
          <div className="hint">{reports.length} received</div>
        </div>
        <div className="top-actions">
          <span className="chip ok">WhatsApp {wa}</span>
          <span className="chip neutral">SMS {sms}</span>
        </div>
      </div>
      <table>
        <thead>
          <tr><th>Time</th><th>Farmer</th><th>Zone</th><th>Channel</th><th>Report</th></tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td>{hhmm(r.received_at)}</td>
              <td>{r.farmer_name || `farmer ${r.farmer_id}`}</td>
              <td>{r.locality ? <ZoneChip name={r.locality} /> : '–'}</td>
              <td><ChannelTag channel={r.channel} /></td>
              <td>{r.reply} — {r.raw_text || ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function dayLabel(iso) {
  const d = new Date(iso);
  const now = new Date();
  const days = Math.floor((new Date(now.toDateString()) - new Date(d.toDateString())) / 86400000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days} days ago`;
}

export function BroadcastsView({ messages }) {
  const byDay = {};
  messages.forEach((m) => {
    const day = (m.sent_at || '').slice(0, 10) || 'unknown';
    (byDay[day] = byDay[day] || []).push(m);
  });
  const rows = Object.entries(byDay)
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .slice(0, 5)
    .map(([day, ms]) => {
      const ok = ms.filter((m) => ['sent', 'mocked', 'delivered'].includes(m.status)).length;
      const fail = ms.length - ok;
      const wa = ms.filter((m) => (m.channel || 'whatsapp') !== 'sms').length;
      return {
        day, ok, total: ms.length, fail, wa, sms: ms.length - wa,
        complete: fail === 0,
      };
    });

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>Broadcast run history</h2>
          <div className="hint">Daily 6:00 AM personalised messages to every farmer</div>
        </div>
        <span className="chip ok">Scheduler running</span>
      </div>
      <table>
        <thead>
          <tr><th>Date</th><th>Time</th><th>Delivered</th><th>Retry</th><th>Channel split</th><th>Status</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.day}>
              <td>{dayLabel(r.day)}</td>
              <td>06:00</td>
              <td>{r.ok} / {r.total}</td>
              <td>{r.fail}</td>
              <td>WhatsApp {r.wa}{r.sms ? ` · SMS ${r.sms}` : ''}</td>
              <td>
                {r.complete
                  ? <span className="chip ok">Complete</span>
                  : <span className="chip warn">Partial</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CallListView({ callList }) {
  return (
    <div className="card">
      <div className="card-head"><h2>Call list (failed after retry)</h2></div>
      <table>
        <thead><tr><th>Farmer</th><th>Phone</th><th>Reason</th></tr></thead>
        <tbody>
          {callList.map((c) => (
            <tr key={c.id}>
              <td>{c.name || c.farmer_id}</td><td>{c.phone || ''}</td><td>{c.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
