import React, { useCallback, useEffect, useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Topbar from './components/Topbar.jsx';
import TokenBar from './components/TokenBar.jsx';
import DashboardView from './views/Dashboard.jsx';
import ZonesView from './views/Zones.jsx';
import { ReportsView, BroadcastsView, CallListView } from './views/Tables.jsx';
import { zoneAlt, hhmm } from './components/shared.jsx';
import { api } from './api/client.js';

const TITLES = {
  dashboard: 'System Overview',
  reports: 'Farmer Reports',
  zones: 'Zones & Micro-climates',
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
  const [zoneData, setZoneData] = useState({});
  const [zones, setZones] = useState([]);
  const [forecastOut, setForecastOut] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const s = await api.stats(token);
      setStats(s);
      const [locs, reps, msgs, call, zs] = await Promise.all([
        api.localities(token),
        api.reports(token),
        api.messages(token),
        api.callList(token),
        api.zones(token),
      ]);
      setLocalities(locs);
      setReports(reps);
      setMessages(msgs);
      setCallList(call);
      setZones(zs);
      const zd = {};
      zs.forEach((z) => { zd[z.zone] = z; });
      setZoneData(zd);
    } catch (e) {
      setError(`${e.message} — set ADMIN_TOKEN and press Refresh`);
    }
  }, [token]);

  useEffect(() => {
    localStorage.setItem('fc_admin_token', token);
  }, [token]);

  useEffect(() => {
    if (localStorage.getItem('fc_admin_token')) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const locName = {};
  localities.forEach((l) => { locName[l.id] = l.name; });
  const chanByFarmer = {};
  messages.forEach((m) => { if (!(m.farmer_id in chanByFarmer)) chanByFarmer[m.farmer_id] = m.channel || 'whatsapp'; });

  const enriched = reports.map((r) => ({
    ...r,
    locality: locName[r.locality_id] || '',
    channel: chanByFarmer[r.farmer_id] || 'whatsapp',
  }));

  const counts = {};
  (stats?.per_locality || []).forEach((l) => { counts[l.name] = l.n; });

  const locDiv = {};
  localities.forEach((l) => { locDiv[l.id] = l.division || ''; });

  const zoneRows = zones.map((z) => {
    const last = enriched.find((r) => locDiv[r.locality_id] === z.zone);
    let ago = '';
    if (last?.received_at) {
      const mins = Math.max(0, Math.round((Date.now() - new Date(last.received_at).getTime()) / 60000));
      ago = mins < 60 ? `${mins} min ago` : `${Math.round(mins / 60)} hr ago`;
    }
    return {
      name: z.zone,
      alt: zoneAlt(z.zone, z.elev_m, z.localities),
      p48: z.p48, prob: z.prob_max, category: z.category,
      farmers: z.farmers, last: ago,
    };
  });

  const feed = enriched.slice(0, 8);
  const subtitle = stats
    ? `Collecting ground truth from <b>${stats.farmers} farmers</b> across ${zones.length} zones · Updated ${new Date().toTimeString().slice(0, 5)}`
    : 'Connect API token to load live data.';

  const onDryRun = async () => {
    try {
      setForecastOut(await api.broadcastDryRun(token));
    } catch (e) {
      setError(e.message);
    }
  };

  const onForecast = async () => {
    if (!place.trim()) return;
    try {
      setForecastOut(await api.forecast(token, place.trim()));
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
          call: stats?.call_list_open,
        }}
      />
      <main>
        <Topbar title={TITLES[view]} subtitle={subtitle} onRefresh={load} onDryRun={onDryRun} />
        <TokenBar token={token} setToken={setToken} place={place} setPlace={setPlace} onForecast={onForecast} />
        {error ? <div className="error">{error}</div> : null}
        {forecastOut ? (
          <div className="card" style={{ marginBottom: 16 }}>
            <pre>{JSON.stringify(forecastOut, null, 2).slice(0, 2000)}</pre>
          </div>
        ) : null}
        <div className={'view' + (view === 'dashboard' ? ' active' : '')}>
          {view === 'dashboard' ? <DashboardView stats={stats} zoneRows={zoneRows} feed={feed} /> : null}
        </div>
        <div className={'view' + (view === 'reports' ? ' active' : '')}>
          {view === 'reports' ? <ReportsView reports={enriched.slice(0, 100)} stats={stats} /> : null}
        </div>
        <div className={'view' + (view === 'zones' ? ' active' : '')}>
          {view === 'zones' ? <ZonesView zones={zones} /> : null}
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
