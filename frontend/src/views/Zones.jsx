import React from 'react';
import { statusFor, zoneAlt } from '../components/shared.jsx';

function dayLabels(n) {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const out = [];
  const d = new Date();
  for (let i = 1; i <= n; i++) {
    out.push(days[(d.getDay() + i) % 7]);
  }
  return out;
}

function ZoneCard({ zone }) {
  const daily = (zone.daily || []).slice(1, 6);
  const labels = dayLabels(5);
  const max = Math.max(1, ...daily);
  const barCls = zone.category === 'HEAVY_RAIN' || zone.category === 'RAIN'
    ? 'wet'
    : zone.category === 'DRY_SPELL' || zone.category === 'DRY' ? 'dry' : '';
  const st = statusFor(zone.category);

  return (
    <div className="zone-card">
      <div className="zh">
        <h3>{zone.zone}</h3>
        <span className={`chip ${st.kind}`}>{st.label}</span>
      </div>
      <div className="alt">{zoneAlt(zone.zone, zone.elev_m, zone.localities)} · {zone.farmers} farmers</div>
      <div className="mini-stats">
        <div className="mini">
          <div className="k">48h rain</div>
          <div className="v">{zone.p48} mm</div>
        </div>
        <div className="mini">
          <div className="k">Temperature</div>
          <div className="v">{Math.round(zone.tmax)}°C</div>
        </div>
      </div>
      <div className="hint" style={{ marginBottom: 4 }}>Next 5 days (mm)</div>
      <div className="bars">
        {labels.map((d, i) => {
          const v = daily[i] ?? 0;
          return (
            <div className="bar-col" key={d + i}>
              <span className="bv">{v}</span>
              <div className="bar-track">
                <div className={`bar ${barCls}`} style={{ height: `${Math.max(3, Math.round((v / max) * 100))}%` }}></div>
              </div>
              <small>{d}</small>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ZonesView({ zones }) {
  if (!zones.length) {
    return (
      <div className="card">
        <div className="hint">No zone data loaded yet — enter your ADMIN_TOKEN above and press Refresh.</div>
      </div>
    );
  }
  return (
    <div className="zone-grid">
      {zones.map((z) => (
        <ZoneCard key={z.zone} zone={z} />
      ))}
    </div>
  );
}
