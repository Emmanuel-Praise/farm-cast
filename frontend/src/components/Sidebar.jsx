import React from 'react';
import { SproutIcon, GridIcon, ChatIcon, PinIcon, MegaIcon } from './icons.jsx';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', title: 'System Overview', Icon: GridIcon },
  { id: 'reports', label: 'Farmer Reports', title: 'Farmer Reports', Icon: ChatIcon, badge: 'reports' },
  { id: 'zones', label: 'Zones', title: 'Zones & Micro-climates', Icon: PinIcon },
  { id: 'broadcasts', label: 'Broadcasts', title: 'Broadcast Runs', Icon: MegaIcon },
  { id: 'calllist', label: 'Call list', title: 'Call List', Icon: ChatIcon, badge: 'call' },
];

export default function Sidebar({ view, onNav, counts }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo"><SproutIcon /></div>
        <div>
          <strong>FarmCast</strong>
          <small>NW Cameroon Agent</small>
        </div>
      </div>
      <div className="side-label">Console</div>
      <nav>
        {NAV.map((n) => (
          <button
            key={n.id}
            className={'nav-item' + (view === n.id ? ' active' : '')}
            onClick={() => onNav(n)}
          >
            <span className="ico"><n.Icon /></span>
            {n.label}
            {n.badge && counts[n.badge] != null ? <span className="badge">{counts[n.badge]}</span> : null}
          </button>
        ))}
      </nav>
      <div className="side-foot">
        <div className="row"><span className="dot"></span> Agent online</div>
        <div style={{ marginTop: 8 }}>Next broadcast · 6:00 AM</div>
      </div>
    </aside>
  );
}
