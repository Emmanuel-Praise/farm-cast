import React from 'react';
import { ZONES, statusFor } from '../components/shared.jsx';

function dayLabels(n) {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const out = [];
  const d = new Date();
  for (let i = 1; i <= n; i++) {
    out.push(days[(d.getDay() + i) % 7]);
  }
  return out;
}

function ZoneCard({ zone, data, farmers }) {
  const daily = (data?.forecast?.daily || []).slice(1, 6);
  const labels = dayLabels(5);
  const max = Math.max(1, ...daily);
  const barCls = data?.category === 'HEAVY_RAIN' || data?.category === 'RAIN'
    ? 'wet'
    : data?.category === 'DRY_SPELL' || data?.category === 'DRY' ? 'dry' : '';
  const st = statusFor(data?.category);
  const temp = data?.forecast?.tmax;

  return (
    <div className="zone-card">
      <div className="zh">
        <h3>{zone.name}</h3>
        <span className={`chip ${st.kind}`}>{data ? st.label : 'No data'}</span>
      </div>
      <div className="alt">{zone.alt} · {farmers} farmers</div>
      <div className="mini-stats">
        <div className="mini">
          <div className="k">48h rain</div>
          <div className="v">{data ? `${data.forecast.p48} mm` : '–'}</div>
        </div>
        <div className="mini">
          <div className="k">Temperature</div>
          <div className="v">{temp != null ? `${Math.round(temp)}°C` : '–'}</div>
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

export default function ZonesView({ zoneData, counts }) {
  return (
    <div className="zone-grid">
      {ZONES.map((z) => (
        <ZoneCard key={z.name} zone={z} data={zoneData[z.name]} farmers={counts[z.name] || 0} />
      ))}
    </div>
  );
}
