import React from 'react';

export function Chip({ kind = 'neutral', children }) {
  return <span className={`chip ${kind}`}>{children}</span>;
}

export function initials(name) {
  return (name || '?').slice(0, 2).toUpperCase();
}
