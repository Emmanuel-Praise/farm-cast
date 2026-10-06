import React from 'react';

export default function Topbar({ title, subtitle, onRefresh, onDryRun }) {
  return (
    <div className="topbar">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="top-actions">
        <button className="btn" onClick={onRefresh}>
          Refresh
        </button>
        <button className="btn primary" onClick={onDryRun}>
          Dry-run broadcast
        </button>
      </div>
    </div>
  );
}
