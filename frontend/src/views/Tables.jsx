import React from 'react';
import { Chip } from '../components/Chip.jsx';

export function ReportsView({ reports }) {
  return (
    <div className="card">
      <div className="card-head"><h2>All ground reports</h2></div>
      <table>
        <thead><tr><th>ID</th><th>Farmer</th><th>Reply</th><th>Text</th><th>Date</th></tr></thead>
        <tbody>
          {(reports || []).map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td><td>{r.farmer_id}</td>
              <td><Chip kind={r.reply === 'YES' ? 'ok' : 'dry'}>{r.reply}</Chip></td>
              <td>{r.raw_text || ''}</td><td>{r.asked_for_date || ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function LocalitiesView({ localities }) {
  return (
    <div className="card">
      <div className="card-head"><h2>Localities</h2></div>
      <table>
        <thead><tr><th>Name</th><th>Division</th><th>Lat/Lon</th><th>Elev</th><th>Source</th></tr></thead>
        <tbody>
          {(localities || []).map((l) => (
            <tr key={l.id}>
              <td><b>{l.name}</b></td><td>{l.division || ''}</td>
              <td>{l.lat}, {l.lon}</td><td>{l.elevation_m || ''}m</td>
              <td>{l.source || ''}{l.verified ? ' ✓' : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BroadcastsView({ messages }) {
  return (
    <div className="card">
      <div className="card-head"><h2>Recent messages</h2></div>
      <table>
        <thead><tr><th>ID</th><th>Farmer</th><th>Kind</th><th>Status</th><th>Body</th></tr></thead>
        <tbody>
          {(messages || []).map((m) => (
            <tr key={m.id}>
              <td>{m.id}</td><td>{m.farmer_id}</td><td>{m.kind}</td>
              <td>{m.status}</td><td>{(m.text_body || '').slice(0, 120)}</td>
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
          {(callList || []).map((c) => (
            <tr key={c.id}>
              <td>{c.name || c.farmer_id}</td><td>{c.phone || ''}</td><td>{c.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
