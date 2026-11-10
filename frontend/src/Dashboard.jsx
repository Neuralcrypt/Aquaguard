import { useCallback, useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, getDashboard, getOverview, getRooms } from './services/api';
import StatCard from './components/StatCard';
import DevicePanel from './components/DevicePanel';
import './App.css';

const fmt = (n) => Number(n ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
const currentSeason = () => { const m = new Date().getMonth() + 1; return [3, 4, 5, 6].includes(m) ? 'Summer' : [7, 8, 9, 10].includes(m) ? 'Monsoon' : 'Winter'; };

function StatusBadge({ status }) {
  const cls = status === 'Active' ? 'status-active' : status === 'Issue' ? 'status-issue' : 'status-inactive';
  return <span className={`status-badge ${cls}`}><span className="status-dot" />{status}</span>;
}

export default function App() {
  const [rooms, setRooms] = useState([]);
  const [overview, setOverview] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState('ROOM-101');
  const [search, setSearch] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [roomSettingsDirty, setRoomSettingsDirty] = useState(false);
  const [notice, setNotice] = useState('');
  const [season, setSeason] = useState(currentSeason());
  const [limit, setLimit] = useState('350');
  const [duration, setDuration] = useState('15');
  const [roomIdInput, setRoomIdInput] = useState('');
  const [roomNameInput, setRoomNameInput] = useState('');
  const [newLimit, setNewLimit] = useState('350');
  const [newDuration, setNewDuration] = useState('15');
  const [roomSaving, setRoomSaving] = useState(false);
  const [showRoomForm, setShowRoomForm] = useState(false);
  const [alertFilter, setAlertFilter] = useState('All');

  const refresh = useCallback(async (roomId = selectedRoom) => {
    try {
      const [roomList, overviewData] = await Promise.all([getRooms(), getOverview()]);
      setRooms(roomList); setOverview(overviewData);
      const exists = roomList.some(r => r.id === roomId);
      if (!exists && roomList.length) {
        roomId = roomList[0].id;
        setSelectedRoom(roomId);
      }
      if (exists || roomList.length) {
        const result = await getDashboard(roomId);
        setData(result); setError('');
      } else { setData(null); setError('No rooms are registered yet. Add a room to begin.'); }
    } catch (e) {
      setError(e.response?.data?.detail || 'Cannot reach the API. Check that the backend and database are running.');
    } finally { setLoading(false); }
  }, [selectedRoom]);

  useEffect(() => { refresh(selectedRoom); const timer = setInterval(() => refresh(selectedRoom), 3000); return () => clearInterval(timer); }, [refresh, selectedRoom]);
  useEffect(() => {
    const selected = data?.settings?.find(s => s.season === season);
    if (selected && !roomSettingsDirty) { setLimit(String(selected.daily_limit_litres)); setDuration(String(selected.continuous_flow_minutes)); }
  }, [data, season, roomSettingsDirty]);

  const selectedRoomInfo = rooms.find(r => r.id === selectedRoom);
  const filteredRooms = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rooms.filter(r => !q || r.id.toLowerCase().includes(q) || r.name.toLowerCase().includes(q));
  }, [rooms, search]);
  const chartData = [...(data?.readings || [])].reverse().map(r => ({ time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), litres: r.interval_volume_litres }));
  const seasonalData = data?.seasonal?.seasons || [];
  const filteredAlerts = (data?.alerts || []).filter(alert =>
    alertFilter === 'All' || alert.status === alertFilter
  );

  const saveSettings = async (event) => {
    event.preventDefault(); setSaving(true); setNotice('');
    try {
      await api.put(`/settings/${season}`, { daily_limit_litres: Number(limit), continuous_flow_minutes: Number(duration) }, { params: { room_id: selectedRoom } });
      setRoomSettingsDirty(false);
      setNotice(`${season} settings saved for ${selectedRoomInfo?.name || selectedRoom}.`);
      await refresh(selectedRoom);
    } catch (e) { setNotice(e.response?.data?.detail || 'Could not save settings.'); }
    finally { setSaving(false); }
  };

  const createRoom = async (event) => {
    event.preventDefault(); setRoomSaving(true); setNotice('');
    const id = roomIdInput.trim().toUpperCase();
    try {
      const response = await api.post('/rooms', { id, name: roomNameInput.trim() || `Room ${id.replace(/^ROOM-/, '')}`, daily_limit_litres: Number(newLimit), continuous_flow_minutes: Number(newDuration) });
      setNotice(`Room ${response.data.name} was saved. No sensor has been assigned yet.`);
      setRoomIdInput(''); setRoomNameInput(''); setShowRoomForm(false); setSelectedRoom(response.data.id);
      await refresh(response.data.id);
    } catch (e) { setNotice(e.response?.data?.detail || 'Could not create room. Check the ID and limit.'); }
    finally { setRoomSaving(false); }
  };

  const renameRoom = async (room) => {
    const name = window.prompt('Enter the display name for this room:', room.name);
    if (name === null || !name.trim() || name.trim() === room.name) return;
    try { await api.patch(`/rooms/${encodeURIComponent(room.id)}`, { name: name.trim() }); setNotice('Room name updated.'); await refresh(selectedRoom); }
    catch (e) { setNotice(e.response?.data?.detail || 'Could not update room name.'); }
  };

  const removeRoom = async (room) => {
    if (room.id === 'ROOM-101') {
      setNotice('The default room ROOM-101 is protected and cannot be removed.');
      return;
    }
    if (!window.confirm(`Remove ${room.name} (${room.id})? Rooms with historical readings or alerts cannot be deleted.`)) return;
    setNotice('');
    try {
      await api.delete(`/rooms/${encodeURIComponent(room.id)}`);
      const remaining = rooms.filter(r => r.id !== room.id);
      const nextRoomId = selectedRoom === room.id ? (remaining[0]?.id || '') : selectedRoom;
      setSelectedRoom(nextRoomId);
      setRooms(remaining);
      setNotice(`Room ${room.id} was removed.`);
      await refresh(nextRoomId);
    } catch (e) {
      setNotice(e.response?.data?.detail || 'Could not remove room.');
    }
  };

  const updateAlert = async (id, status) => { try { await api.patch(`/alerts/${id}`, { status }); await refresh(selectedRoom); } catch { setNotice('Could not update alert status.'); } };
  const deleteAlert = async (alert) => {
    if (!window.confirm(`Permanently delete this ${alert.alert_type.replaceAll('_', ' ')} alert? This cannot be undone.`)) return;
    try {
      await api.delete(`/alerts/${alert.id}`);
      setNotice(`Alert #${alert.id} deleted.`);
      await refresh(selectedRoom);
    } catch (e) {
      setNotice(e.response?.data?.detail || 'Could not delete alert.');
    }
  };
  const runAnalysis = async () => { try { const r = await api.post('/anomaly-analysis', null, { params: { room_id: selectedRoom } }); setNotice(r.data.status === 'insufficient_data' ? `Analysis needs ${r.data.minimum_readings} readings; currently ${r.data.available_readings}.` : `Analysis completed using ${r.data.method}.`); } catch (e) { setNotice(e.response?.data?.detail || 'Anomaly analysis failed.'); } };

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand-lockup"><div className="brand-mark"><span>A</span></div><div className="brand"><strong>AquaGuard</strong><span>HOSTEL WATER INTELLIGENCE</span></div></div>
      <div className="topbar-right"><span className="topbar-label">CENTRAL MONITORING</span><span className="topbar-separator"/><span className="live-dot"/><span>Prototype</span></div>
    </header>
    <main className="main-content">
      <section className="hero"><div><p className="eyebrow">HOSTEL WATER / CENTRAL OVERVIEW</p><h1>Hostel Water Management</h1><p className="hero-sub">Monitor room-wise consumption, water limits, and sensor health from one dashboard.</p></div><button className="button button-light" onClick={() => refresh(selectedRoom)}>↻ Refresh data</button></section>
      {error && <div className="banner banner-error">{error}</div>}
      {notice && <div className="banner">{notice}<button className="dismiss" onClick={() => setNotice('')}>×</button></div>}
      {loading && !overview ? <div className="loading">Loading hostel data…</div> : <>
        <section className="overview-grid">
          <StatCard label="Registered rooms" value={fmt(overview?.room_count)} unit="rooms" note="Rooms configured in the database" />
          <StatCard label="Active sensors" value={fmt(overview?.active_sensors)} unit="active" note="Devices currently monitoring" />
          <StatCard label="Sensor issues" value={fmt(overview?.sensor_issues)} unit="issues" note="Devices disconnected or not reporting" />
          <StatCard label="Today's measured usage" value={fmt(overview?.today_litres)} unit="L" note="Actual water measured by sensors today" />
        </section>

        <section className="panel directory-panel">
          <div className="panel-heading directory-heading"><div><p className="eyebrow">ROOM DIRECTORY</p><h2>Rooms & device status</h2><p className="panel-subtitle">Select a room to view its allowance, usage, and alerts.</p></div><button className="button button-primary" onClick={() => setShowRoomForm(v => !v)}>{showRoomForm ? 'Cancel' : '+ Add room'}</button></div>
          {showRoomForm && <form className="room-create-form" onSubmit={createRoom}>
            <div className="form-title"><strong>Register a room</strong><span>No physical sensor is required at this stage.</span></div>
            <label>Room ID<input value={roomIdInput} onChange={e => setRoomIdInput(e.target.value)} placeholder="e.g. ROOM-102 or 102" pattern="[A-Za-z0-9_-]+" required maxLength={50}/></label>
            <label>Display name<input value={roomNameInput} onChange={e => setRoomNameInput(e.target.value)} placeholder="e.g. Boys Hostel · Room 102" maxLength={100}/></label>
            <label>Default daily allowance (L)<input type="number" min="1" max="100000" value={newLimit} onChange={e => setNewLimit(e.target.value)} required/></label>
            <label>Continuous-flow alert (min)<input type="number" min="1" max="1440" value={newDuration} onChange={e => setNewDuration(e.target.value)} required/></label>
            <button className="button button-primary" disabled={roomSaving}>{roomSaving ? 'Saving…' : 'Save room'}</button>
          </form>}
          <div className="table-toolbar"><label className="search-box"><span>⌕</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search room number or name…"/></label><span className="table-count">{filteredRooms.length} rooms</span></div>
          <div className="table-scroll"><table className="data-table"><thead><tr><th>ROOM</th><th>SENSOR</th><th>STATUS</th><th>TODAY'S USAGE</th><th>DAILY LIMIT</th><th>OPEN ALERTS</th><th>ACTION</th></tr></thead><tbody>
            {filteredRooms.map(room => <tr key={room.id} className={selectedRoom === room.id ? 'selected-row' : ''}>
              <td><button className="room-link" onClick={() => setSelectedRoom(room.id)}>{room.name}</button><span className="cell-secondary">{room.id}</span></td>
              <td>{room.sensor_id || 'Not assigned'}<span className="cell-secondary">{room.last_seen_at ? `Last seen ${new Date(room.last_seen_at).toLocaleString()}` : 'No sensor telemetry'}</span></td>
              <td><StatusBadge status={room.sensor_status}/>{room.sensor_issue && <span className="issue-reason">{room.sensor_issue}</span>}</td>
              <td>{fmt(room.today_litres)} L</td><td>{fmt(room.daily_limit_litres)} L</td><td><span className={room.pending_alerts ? 'alert-number' : 'quiet-number'}>{room.pending_alerts}</span></td>
              <td><div className="room-actions"><button type="button" className="table-action" onClick={() => setSelectedRoom(room.id)}>View</button><button type="button" className="table-action muted-action" onClick={() => renameRoom(room)}>Rename</button><button type="button" className="table-action delete-action" disabled={room.id === 'ROOM-101'} title={room.id === 'ROOM-101' ? 'The default room is protected' : 'Remove room'} onClick={() => removeRoom(room)}>Remove</button></div></td>
            </tr>)}
            {!filteredRooms.length && <tr><td colSpan="7" className="table-empty">No matching rooms. Add a room to register its water allowance.</td></tr>}
          </tbody></table></div>
          <p className="table-footnote">A room without a sensor can still have a saved water allowance. Usage is measured only after sensor readings arrive.</p>
        </section>

        {data && <>
          <section className="section-title"><div><p className="eyebrow">SELECTED ROOM</p><h2>{data.room.name}</h2><p>{data.room.id} · room-level water monitoring</p></div><StatusBadge status={data.room.sensor_status}/></section>
          {data.room.sensor_status === 'Issue' && data.room.sensor_issue && (
            <div className="sensor-message sensor-message-issue">
              <strong>Device issue:</strong> {data.room.sensor_issue}. Check ESP32 power and Wi-Fi connectivity.
            </div>
          )}
          {data.room.sensor_status === 'Inactive' && data.room.sensor_id && (
            <div className="sensor-message sensor-message-inactive">
              <strong>Monitoring stopped:</strong> The device is connected, but water monitoring is not running.
            </div>
          )}
          <section className="panel room-settings-compact">
            <details>
              <summary>
                <span><strong>Room settings</strong><small>Manage seasonal daily allowance and room-level continuous-flow policy</small></span>
                <span className="room-settings-current">{season} · {fmt(data.summary.daily_limit_litres)} L/day</span>
              </summary>
              <form onSubmit={saveSettings} className="room-settings-form">
                <label>Season
                  <select value={season} onChange={e => { setRoomSettingsDirty(false); setSeason(e.target.value); }}>
                    <option>Summer</option><option>Monsoon</option><option>Winter</option>
                  </select>
                </label>
                <label>Daily allowance (litres)
                  <input type="number" min="1" max="100000" step="1" value={limit} onChange={e => { setLimit(e.target.value); setRoomSettingsDirty(true); }} required />
                </label>
                <label>Continuous-flow alert (minutes)
                  <input type="number" min="1" max="1440" step="1" value={duration} onChange={e => { setDuration(e.target.value); setRoomSettingsDirty(true); }} required />
                </label>
                <button className="button button-primary" disabled={saving}>{saving ? 'Saving…' : 'Save room settings'}</button>
              </form>
            </details>
          </section>
          {data.room.id === 'ROOM-101' && (
            <DevicePanel onNotice={setNotice} />
          )}
          <section className="stats-grid room-stats"><StatCard label="Today's consumption" value={fmt(data.summary.today_litres)} unit="L" note={`Current season: ${data.summary.season}`}/><StatCard label="Daily allowance" value={fmt(data.summary.daily_limit_litres)} unit="L" note="Configured for this room and season"/><StatCard label="Remaining allowance" value={fmt(data.summary.remaining_litres)} unit="L" note="Allowance minus measured usage"/><StatCard label="Live flow rate" value={data.summary.device_online ? fmt(data.summary.latest_flow_rate_lpm) : '—'} unit={data.summary.device_online ? 'L/min' : ''} note={data.summary.device_online ? (data.summary.last_reading_at ? `Device heartbeat ${new Date(data.summary.last_reading_at).toLocaleTimeString()}` : 'Device connected') : 'Device telemetry unavailable'}/></section>
          <section className="content-grid"><article className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">CONSUMPTION HISTORY</p><h2>Interval water usage</h2></div><span className="unit-pill">Litres / reading</span></div>{chartData.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><defs><linearGradient id="usageFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#168a82" stopOpacity={0.25}/><stop offset="100%" stopColor="#168a82" stopOpacity={0.02}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6eaf0"/><XAxis dataKey="time" tick={{fontSize:11}} axisLine={false} tickLine={false}/><YAxis tick={{fontSize:11}} axisLine={false} tickLine={false}/><Tooltip/><Area type="monotone" dataKey="litres" stroke="#168a82" fill="url(#usageFill)" strokeWidth={2}/></AreaChart></ResponsiveContainer></div> : <div className="empty-state"><span>〰</span><strong>No consumption readings</strong><p>This room's water allowance is saved. Connect a sensor later or submit clearly labelled test readings during development.</p></div>}</article>
          <article className="panel seasonal-panel"><div className="panel-heading"><div><p className="eyebrow">SEASONAL BREAKDOWN</p><h2>Usage by season</h2></div></div><div className="chart-wrap small-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={seasonalData}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6eaf0"/><XAxis dataKey="season" tick={{fontSize:11}} axisLine={false} tickLine={false}/><YAxis tick={{fontSize:11}} axisLine={false} tickLine={false}/><Tooltip/><Bar dataKey="total_litres" fill="#3f8e89" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div><p className="muted small-note">Historical readings only. Empty seasons are not evidence of zero real-world consumption.</p></article></section>
          <section className="panel alerts-panel alerts-panel-full">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">ATTENTION REQUIRED</p>
                <h2>Room alerts</h2>
                <p className="panel-subtitle">Review, resolve or permanently remove alerts for this room.</p>
              </div>
              <div className="alerts-toolbar">
                <span className="count-pill">{(data.alerts || []).filter(alert => alert.status !== 'Resolved').length} open</span>
                <select aria-label="Filter room alerts" value={alertFilter} onChange={e => setAlertFilter(e.target.value)}>
                  <option>All</option><option>Pending</option><option>Investigating</option><option>Resolved</option>
                </select>
              </div>
            </div>
            {filteredAlerts.length ? (
              <div className="alert-list">
                {filteredAlerts.map(alert => (
                  <div className="alert-row" key={alert.id}>
                    <div className={`alert-icon ${alert.severity === 'high' ? 'high' : ''}`}>!</div>
                    <div className="alert-body">
                      <strong>{alert.alert_type.replaceAll('_', ' ')}</strong>
                      <p>{alert.message}</p>
                      <span>{new Date(alert.created_at).toLocaleString()}</span>
                    </div>
                    <div className="alert-actions">
                      <select aria-label={`Status for alert ${alert.id}`} value={alert.status} onChange={e => updateAlert(alert.id, e.target.value)}>
                        <option>Pending</option><option>Investigating</option><option>Resolved</option>
                      </select>
                      <button type="button" className="table-action delete-action" onClick={() => deleteAlert(alert)} aria-label={`Delete alert ${alert.id}`} title="Permanently delete alert">Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-alerts"><span>✓</span><strong>No alerts in this filter</strong><p>New alerts will appear here when a monitoring rule is triggered.</p></div>
            )}
          </section>
          <section className="bottom-actions"><div><strong>Analysis tools</strong><p>Available for saved readings; no sensor hardware is required to configure rooms.</p></div><button className="button button-light" onClick={runAnalysis}>Run anomaly analysis</button></section>
        </>}
      </>}
      <footer><span>AquaGuard · B.Tech major project prototype</span><span>Sensor issues require human investigation · No automatic valve control</span></footer>
    </main>
  </div>;
}
