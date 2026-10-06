import React from 'react';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', title: 'System Overview' },
  { id: 'reports', label: 'Farmer Reports', title: 'Farmer Reports', badge: 'reports' },
  { id: 'zones', label: 'Localities', title: 'Localities', badge: 'localities' },
  { id: 'broadcasts', label: 'Broadcasts', title: 'Broadcast Runs' },
  { id: 'calllist', label: 'Call list', title: 'Call List', badge: 'call' },
];

export default function Sidebar({ view, onNav, counts, apiState }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo">FC</div>
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
            {n.label}
            {n.badge && counts[n.badge] != null ? <span className="badge">{counts[n.badge]}</span> : null}
          </button>
        ))}
      </nav>
      <div className="side-foot">
        <div>Next broadcast · 6:00 AM Africa/Douala</div>
        <div>{apiState}</div>
      </div>
    </aside>
  );
}
