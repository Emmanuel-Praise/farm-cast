import React from 'react';
import { RefreshIcon, MegaIcon } from './icons.jsx';

export default function Topbar({ title, subtitle, onRefresh, onDryRun }) {
  return (
    <div className="topbar">
      <div>
        <h1>{title}</h1>
        <p dangerouslySetInnerHTML={{ __html: subtitle }} />
      </div>
      <div className="top-actions">
        <button className="btn" onClick={onRefresh}>
          <RefreshIcon /> Refresh
        </button>
        <button className="btn primary" onClick={onDryRun}>
          <MegaIcon /> Send test broadcast
        </button>
      </div>
    </div>
  );
}
