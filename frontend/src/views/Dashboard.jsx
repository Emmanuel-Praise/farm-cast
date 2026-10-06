import React from 'react';
import { Chip, initials } from '../components/Chip.jsx';

export default function DashboardView({ stats }) {
  if (!stats) return <div className="card"><div className="hint">Enter ADMIN_TOKEN and press Refresh.</div></div>;
  return (
    <>
      <div className="kpis">
        <div className="kpi">
          <div className="lbl">Total farmers</div>
          <div className="val">{stats.farmers}</div>
          <div className="sub">{stats.localities} localities</div>
        </div>
        <div className="kpi">
          <div className="lbl">Ground reports today</div>
          <div className="val">{stats.reports_today}</div>
          <div className="sub">farmer YES/NO replies</div>
        </div>
        <div className="kpi">
          <div className="lbl">Alerts delivered</div>
          <div className="val">{stats.sent_today}</div>
          <div className="sub">{stats.failed_today} failed</div>
        </div>
      </div>
      <div className="cols">
        <div className="col">
          <div className="card">
            <div className="card-head">
              <div>
                <h2>Locality monitor</h2>
                <div className="hint">Dynamic — every village, not 3 fixed zones</div>
              </div>
              <Chip>Live</Chip>
            </div>
            <table>
              <thead><tr><th>Locality</th><th>Farmers</th><th>Division</th></tr></thead>
              <tbody>
                {stats.per_locality.map((l) => (
                  <tr key={l.name}><td><b>{l.name}</b></td><td>{l.n}</td><td>{l.division || ''}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card">
            <div className="card-head">
              <div><h2>Incoming ground reports</h2></div>
              <Chip kind="ok">{stats.reports_today} today</Chip>
            </div>
            {stats.recent_reports.map((r) => (
              <div className="feed-item" key={r.id}>
                <div className="avatar">{initials(r.farmer_name)}</div>
                <div className="feed-body">
                  <b>{r.farmer_name || `farmer ${r.farmer_id}`}</b>{' '}
                  <Chip kind={r.reply === 'YES' ? 'ok' : 'dry'}>{r.reply}</Chip>
                  <div className="feed-msg">{r.raw_text || ''}</div>
                  <div className="feed-meta">{r.received_at || ''}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="col">
          <div className="card">
            <div className="card-head"><h2>Today&apos;s 6 AM broadcast</h2><Chip kind="ok">WhatsApp text-only</Chip></div>
            <div className="stat-row"><span>Sent/delivered today</span><b>{stats.sent_today}</b></div>
            <div className="stat-row"><span>Failed</span><b>{stats.failed_today}</b></div>
            <div className="stat-row"><span>Open call list</span><b>{stats.call_list_open}</b></div>
          </div>
          <div className="card">
            <div className="card-head"><h2>Farmers per locality</h2></div>
            {stats.per_locality.slice(0, 10).map((l) => (
              <div className="stat-row" key={l.name}><span>{l.name}</span><b>{l.n}</b></div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
