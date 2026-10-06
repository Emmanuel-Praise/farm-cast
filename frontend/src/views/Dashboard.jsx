import React from 'react';
import { statusFor, FeedList } from '../components/shared.jsx';

export default function DashboardView({ stats, zoneRows, feed }) {
  const names = zoneRows.map((z) => z.name);
  const farmers = stats?.farmers ?? '–';
  const sent = stats?.sent_today ?? 0;
  const failed = stats?.failed_today ?? 0;
  const callOpen = stats?.call_list_open ?? 0;
  const total = sent + failed;
  const pct = total ? Math.round((sent / total) * 1000) / 10 : 0;
  const retrying = failed + callOpen;
  const counts = {};
  (stats?.per_locality || []).forEach((l) => { counts[l.name] = l.n; });
  const byDiv = {};
  zoneRows.forEach((z) => {
    const d = z.division || 'Unverified';
    byDiv[d] = (byDiv[d] || 0) + (counts[z.name] || z.farmers || 0);
  });
  const divNames = Object.keys(byDiv).sort((a, b) => byDiv[b] - byDiv[a]);
  const lead = divNames[0];

  return (
    <>
      <div className="kpis">
        <div className="kpi">
          <div className="lbl">Total farmers</div>
          <div className="val">{farmers}</div>
          <div className="sub">across {names.length} areas · whole Northwest</div>
        </div>
        <div className="kpi">
          <div className="lbl">Ground reports today</div>
          <div className="val">{stats?.reports_today ?? '–'}</div>
          <div className="sub">farmer replies in</div>
        </div>
        <div className="kpi">
          <div className="lbl">Alerts delivered 6 AM</div>
          <div className="val">{sent}<small> / {farmers}</small></div>
          <div className="sub">
            <span className="down">{retrying}</span> retrying · {failed} failed
          </div>
        </div>
      </div>

      <div className="cols">
        <div className="col">
          <div className="card">
            <div className="card-head">
              <div>
                <h2>Zone monitor — 48h outlook</h2>
                <div className="hint">Same day, every Northwest zone · live forecast</div>
              </div>
              <span className="chip neutral">Live</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Zone</th><th>Today</th><th>48h rain</th><th>Rain chance</th>
                  <th>Farmers</th><th>Last report</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {zoneRows.map((z) => {
                  const st = statusFor(z.category);
                  return (
                    <tr key={z.name}>
                      <td className="zone-name">{z.name} <small>{z.alt}</small></td>
                      <td>{z.today || '–'}</td>
                      <td><b>{z.p48 != null ? `${z.p48} mm` : '–'}</b></td>
                      <td>{z.prob != null ? `${Math.round(z.prob)}%` : '–'}</td>
                      <td>{z.farmers}</td>
                      <td>{z.last || '–'}</td>
                      <td><span className={`chip ${st.kind}`}>{st.label}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="card-head">
              <div>
                <h2>Incoming ground reports</h2>
                <div className="hint">Farmers replying to yesterday&apos;s rain check</div>
              </div>
              <span className="chip ok">{stats?.reports_today ?? 0} today</span>
            </div>
            <FeedList items={feed} />
          </div>
        </div>

        <div className="col">
          <div className="card">
            <div className="card-head">
              <h2>Today&apos;s 6 AM broadcast</h2>
              <span className="chip ok">Complete</span>
            </div>
            <div className="stat-row"><span>Messages sent</span><b>{sent} / {farmers}</b></div>
            <div className="prog"><i style={{ width: `${pct}%` }}></i></div>
            <div className="stat-row" style={{ marginTop: 12 }}><span>WhatsApp</span><b>{sent}</b></div>
            <div className="stat-row"><span>Pending retry</span><b style={{ color: 'var(--amber)' }}>{retrying}</b></div>
          </div>

          <div className="card">
            <div className="card-head">
              <h2>Farmers per zone</h2>
              <span className="chip neutral">{farmers} total</span>
            </div>
            <div className="zone-dist">
              {divNames.map((d, i) => {
                const n = byDiv[d];
                const share = farmers ? Math.round((n / farmers) * 100) : 0;
                const bar = ['amber', 'blue', ''][i % 3] || '';
                return (
                  <div className="zd-row" key={d}>
                    <div className="zd-top"><b>{d}</b><span>{n} · {share}%</span></div>
                    <div className={`zd-bar ${bar}`}><i style={{ width: `${share}%` }}></i></div>
                  </div>
                );
              })}
            </div>
            <div style={{ marginTop: 16, fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.6 }}>
              {lead && byDiv[lead] > 0
                ? `${lead} has the largest farmer base (${byDiv[lead]} farmers).`
                : 'Register farmers to see the per-zone breakdown.'}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
