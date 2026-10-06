import React from 'react';
import { ChatIcon, SmsIcon } from '../components/icons.jsx';

export const ZONE_ALTS = {
  Mezam: 'mid-altitude · capital Bamenda',
  Momo: 'western highlands',
  Bui: 'highland · Nso plateau',
  Boyo: 'highland',
  'Donga-Mantung': 'northern highlands',
  Menchum: 'lowland valleys',
  'Ngo-Ketunjia': 'lowland plain',
};

export function zoneAlt(zone, elev, n) {
  const bits = [];
  if (elev) bits.push(`${Number(elev).toLocaleString()} m`);
  if (ZONE_ALTS[zone]) bits.push(ZONE_ALTS[zone]);
  bits.push(`${n} ${n === 1 ? 'locality' : 'localities'}`);
  return bits.join(' · ');
}

export function statusFor(category) {
  switch (category) {
    case 'HEAVY_RAIN': return { kind: 'warn', label: 'Heavy rain alert' };
    case 'RAIN': return { kind: 'warn', label: 'Rain alert' };
    case 'LIGHT_RAIN': return { kind: 'ok', label: 'Normal' };
    case 'DRY_SPELL': return { kind: 'dry', label: 'Dry spell alert' };
    default: return { kind: 'neutral', label: 'Dry' };
  }
}

const AV = ['', 'b', 'a'];

export function initials(name) {
  const parts = (name || '?').trim().split(/\s+/);
  return ((parts[0] || '?')[0] + (parts[1] || '')[0]).toUpperCase();
}

export function hhmm(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso).slice(11, 16) : d.toTimeString().slice(0, 5);
}

export function ChannelTag({ channel }) {
  const sms = (channel || '').toLowerCase() === 'sms';
  return (
    <span className="ch">
      {sms ? <SmsIcon /> : <ChatIcon />} {sms ? 'SMS' : 'WhatsApp'}
    </span>
  );
}

export function ZoneChip({ name, kind = 'neutral' }) {
  return <span className={`chip ${kind}`}>{name}</span>;
}

export function FeedList({ items }) {
  if (!items.length) return <div className="hint">No reports yet today.</div>;
  return (
    <div className="feed">
      {items.map((r, i) => (
        <div className="feed-item" key={r.id}>
          <div className={`avatar ${AV[i % 3]}`}>{initials(r.farmer_name)}</div>
          <div className="feed-body">
            <div className="feed-top">
              <b>{r.farmer_name || `farmer ${r.farmer_id}`}</b>
              {r.locality ? <ZoneChip name={r.locality} /> : null}
              <span className="time">{hhmm(r.received_at)}</span>
            </div>
            <div className="feed-msg">“{r.raw_text || ''}”</div>
            <div className="feed-meta">
              <ChannelTag channel={r.channel} />
              <span>Reply: {r.reply}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
