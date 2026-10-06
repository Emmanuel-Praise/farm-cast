import React, { useCallback, useEffect, useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Topbar from './components/Topbar.jsx';
import TokenBar from './components/TokenBar.jsx';
import DashboardView from './views/Dashboard.jsx';
import { ReportsView, LocalitiesView, BroadcastsView, CallListView } from './views/Tables.jsx';
import { api } from './api/client.js';

const TITLES = {
  dashboard: 'System Overview',
  reports: 'Farmer Reports',
  zones: 'Localities',
  broadcasts: 'Broadcast Runs',
  calllist: 'Call List',
};

export default function App() {
  const [view, setView] = useState('dashboard');
  const [token, setToken] = useState(() => localStorage.getItem('fc_admin_token') || '');
  const [place, setPlace] = useState('');
  const [stats, setStats] = useState(null);
  const [localities, setLocalities] = useState([]);
  const [reports, setReports] = useState([]);
  const [messages, setMessages] = useState([]);
  const [callList, setCallList] = useState([]);
  const [forecastOut, setForecastOut] = useState(null);
  const [error, setError] = useState('');
  const [apiState, setApiState] = useState('API: not connected');

  const load = useCallback(async () => {
    setError('');
    try {
      const s = await api.stats(token);
      setStats(s);
      setApiState(`API: connected · ${s.date}`);
      const [locs, reps, msgs, call] = await Promise.all([
        api.localities(token),
        api.reports(token),
        api.messages(token),
        api.callList(token),
      ]);
      setLocalities(locs);
      setReports(reps);
      setMessages(msgs);
      setCallList(call);
    } catch (e) {
      setApiState('API: not connected');
      setError(`${e.message} — set ADMIN_TOKEN and run uvicorn farmcast.web.app:app`);
    }
  }, [token]);

  useEffect(() => {
    localStorage.setItem('fc_admin_token', token);
  }, [token]);

  const onDryRun = async () => {
    try {
      const j = await api.broadcastDryRun(token);
      setForecastOut(j);
    } catch (e) {
      setError(e.message);
    }
  };

  const onForecast = async () => {
    if (!place.trim()) return;
    try {
      const j = await api.forecast(token, place.trim());
      setForecastOut(j);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="layout">
      <Sidebar
        view={view}
        onNav={(n) => setView(n.id)}
        counts={{
          reports: stats?.reports_today,
          localities: localities.length || undefined,
          call: stats?.call_list_open,
        }}
        apiState={apiState}
      />
      <main>
        <Topbar
          title={TITLES[view]}
          subtitle={
            stats
              ? `${stats.farmers} farmers across ${stats.localities} localities · ${stats.date}`
              : 'Connect API token to load live data.'
          }
          onRefresh={load}
          onDryRun={onDryRun}
        />
        <TokenBar token={token} setToken={setToken} place={place} setPlace={setPlace} onForecast={onForecast} />
        {error ? <div className="error">{error}</div> : null}
        {forecastOut ? (
          <div className="card" style={{ marginBottom: 16 }}>
            <pre>{JSON.stringify(forecastOut, null, 2).slice(0, 2000)}</pre>
          </div>
        ) : null}
        <div className={'view' + (view === 'dashboard' ? ' active' : '')}>
          {view === 'dashboard' ? <DashboardView stats={stats} /> : null}
        </div>
        <div className={'view' + (view === 'reports' ? ' active' : '')}>
          {view === 'reports' ? <ReportsView reports={reports} /> : null}
        </div>
        <div className={'view' + (view === 'zones' ? ' active' : '')}>
          {view === 'zones' ? <LocalitiesView localities={localities} /> : null}
        </div>
        <div className={'view' + (view === 'broadcasts' ? ' active' : '')}>
          {view === 'broadcasts' ? <BroadcastsView messages={messages} /> : null}
        </div>
        <div className={'view' + (view === 'calllist' ? ' active' : '')}>
          {view === 'calllist' ? <CallListView callList={callList} /> : null}
        </div>
      </main>
    </div>
  );
}
