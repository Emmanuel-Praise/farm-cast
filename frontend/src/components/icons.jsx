import React from 'react';

const P = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

export const SproutIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <path d="M7 20h10" />
    <path d="M12 20V9" />
    <path d="M12 9c-1.5-3-5-3.5-7.5-2.5C4 9 5.5 12.5 9 13c1.5.2 3-.5 3-4z" />
    <path d="M12 9c1.5-3 5-3.5 7.5-2.5C20 9 18.5 12.5 15 13c-1.5.2-3-.5-3-4z" />
  </svg>
);

export const GridIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <rect x="3" y="3" width="7" height="9" rx="1" />
    <rect x="14" y="3" width="7" height="5" rx="1" />
    <rect x="14" y="12" width="7" height="9" rx="1" />
    <rect x="3" y="16" width="7" height="5" rx="1" />
  </svg>
);

export const ChatIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
  </svg>
);

export const SmsIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

export const PinIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

export const MegaIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <path d="M3 11l18-5v12L3 14v-3z" />
    <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
  </svg>
);

export const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" {...P}>
    <polyline points="23 4 23 10 17 10" />
    <polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10" />
    <path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14" />
  </svg>
);
