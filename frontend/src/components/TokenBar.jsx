import React from 'react';

export default function TokenBar({ token, setToken, place, setPlace, onForecast }) {
  return (
    <div className="tokenbar">
      <input
        type="password"
        placeholder="ADMIN_TOKEN (from .env)"
        value={token}
        onChange={(e) => setToken(e.target.value)}
      />
      <input placeholder="Test place e.g. Kumbo" value={place} onChange={(e) => setPlace(e.target.value)} />
      <button className="btn" onClick={onForecast}>
        Check forecast
      </button>
    </div>
  );
}
