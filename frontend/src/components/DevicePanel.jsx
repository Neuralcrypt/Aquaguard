import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';

const explainError = (error) =>
  error.response?.data?.detail ||
  error.message ||
  'Request failed. Check the backend connection.';

export default function DevicePanel({ onNotice }) {
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState({
    water_limit_litres: '1',
    continuous_flow_seconds: '20',
    low_flow_threshold_lpm: '8.5',
    low_flow_confirmation_seconds: '5',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [commandBusy, setCommandBusy] = useState('');
  const [panelError, setPanelError] = useState('');
  const [configDirty, setConfigDirty] = useState(false);

  const loadDevice = useCallback(async (forceConfig = false) => {
    try {
      const [statusResponse, commandResponse] = await Promise.all([
        api.get('/device/status'),
        api.get('/device/command', {
          params: { device_id: 'ESP32-101', sensor_id: 'SENSOR-101' },
        }),
      ]);

      setStatus(statusResponse.data);
      const c = commandResponse.data;

      if (forceConfig || !configDirty) {
        setConfig({
          water_limit_litres: String(c.water_limit_litres ?? 1),
          continuous_flow_seconds: String(c.continuous_flow_seconds ?? 20),
          low_flow_threshold_lpm: String(c.low_flow_threshold_lpm ?? 8.5),
          low_flow_confirmation_seconds: String(c.low_flow_confirmation_seconds ?? 5),
        });
        setConfigDirty(false);
      }
      setPanelError('');
    } catch (error) {
      setPanelError(explainError(error));
    } finally {
      setLoading(false);
    }
  }, [configDirty]);

  useEffect(() => {
    loadDevice();
    const timer = window.setInterval(() => loadDevice(), 2500);
    return () => window.clearInterval(timer);
  }, [loadDevice]);

  const running = Boolean(status?.is_running);
  const online = Boolean(status?.online);
  const sessionLitres = Number(status?.session_total_litres ?? 0);
  const sessionLimit = Number(status?.water_limit_litres ?? config.water_limit_litres ?? 0);
  const sessionProgress = sessionLimit > 0
    ? Math.min(100, Math.max(0, (sessionLitres / sessionLimit) * 100))
    : 0;

  const updateConfig = (key, value) => {
    setConfig((current) => ({ ...current, [key]: value }));
    setConfigDirty(true);
  };

  const saveConfig = async (event) => {
    event.preventDefault();
    if (running) return;

    const waterLimit = Number(config.water_limit_litres);
    const continuousSeconds = Number(config.continuous_flow_seconds);
    const lowThreshold = Number(config.low_flow_threshold_lpm);
    const lowSeconds = Number(config.low_flow_confirmation_seconds);

    if (!Number.isFinite(waterLimit) || waterLimit < 1 || waterLimit > 1000) {
      setPanelError('Water limit must be between 1 and 1000 litres.');
      return;
    }
    if (!Number.isInteger(continuousSeconds) || continuousSeconds < 10 || continuousSeconds > 1800) {
      setPanelError('Continuous-flow duration must be 10–1800 seconds.');
      return;
    }
    if (!Number.isFinite(lowThreshold) || lowThreshold < 0 || lowThreshold > 200) {
      setPanelError('Low-flow threshold must be between 0 and 200 L/min.');
      return;
    }
    if (!Number.isInteger(lowSeconds) || lowSeconds < 1 || lowSeconds > 300) {
      setPanelError('Low-flow confirmation must be 1–300 seconds.');
      return;
    }

    setSaving(true);
    setPanelError('');
    try {
      await api.put('/device/water-limit', { water_limit_litres: waterLimit });
      await api.put('/device/continuous-flow', { duration_seconds: continuousSeconds });
      await api.put('/device/low-flow', {
        threshold_lpm: lowThreshold,
        confirmation_seconds: lowSeconds,
      });
      await loadDevice(true);
      onNotice?.('ESP32 configuration saved. Settings will be used by the next monitoring session.');
    } catch (error) {
      setPanelError(explainError(error));
    } finally {
      setSaving(false);
    }
  };

  const sendCommand = async (command) => {
    setCommandBusy(command);
    setPanelError('');
    try {
      const response = await api.post('/device/control', { command });
      onNotice?.(`${command} command queued (ID ${response.data.command_id}). Waiting for ESP32 acknowledgement.`);
      await loadDevice();
    } catch (error) {
      setPanelError(explainError(error));
    } finally {
      setCommandBusy('');
    }
  };

  return (
    <section className="panel device-panel water-panel">
      <div className="panel-heading device-panel-heading">
        <div>
          <p className="eyebrow">PHYSICAL DEVICE · ROOM-101</p>
          <h2>ESP32 device control</h2>
          <p className="panel-subtitle">Live hardware status, monitoring controls and session detection settings.</p>
        </div>
        <div className={`device-connection ${online ? 'is-online' : 'is-offline'}`}>
          <span className="status-dot" />
          {loading ? 'Checking…' : online ? 'Device online' : 'Device offline'}
        </div>
      </div>

      {panelError && <div className="device-error" role="alert">{panelError}</div>}

      <div className="device-status-grid">
        <div className="device-metric">
          <span>Monitoring</span>
          <strong>{running ? 'Running' : 'Standby'}</strong>
        </div>
        <div className="device-metric">
          <span>Live flow rate</span>
          <strong>{Number(status?.flow_rate_lpm ?? 0).toFixed(2)} <small>L/min</small></strong>
        </div>
        <div className="device-metric device-water-metric">
          <span>Current session water</span>
          <strong>{Number(status?.session_total_litres ?? 0).toFixed(3)} <small>L</small></strong>
        </div>
        <div className="device-metric">
          <span>Low-flow warning</span>
          <strong className={status?.low_flow_detected ? 'device-warning-text' : ''}>
            {status?.low_flow_detected ? 'Detected' : 'Clear'}
          </strong>
        </div>
      </div>

      <div className="live-water-meter">
        <div className="live-water-meter-heading">
          <span>Session water consumption</span>
          <strong>{sessionLitres.toFixed(3)} L <small>{sessionLimit > 0 ? `/ ${sessionLimit} L limit` : ''}</small></strong>
        </div>
        <div className="live-water-track" role="progressbar" aria-label="Session water consumption" aria-valuemin="0" aria-valuemax={sessionLimit || 100} aria-valuenow={sessionLitres}>
          <div className="live-water-fill" style={{ width: `${sessionProgress}%` }} />
        </div>
      </div>

      <div className="device-control-row">
        <div>
          <strong>Monitoring controls</strong>
          <p>START begins a session; RESET preserves the previous session and starts a new one.</p>
        </div>
        <div className="device-buttons">
          <button type="button" className="button button-primary" disabled={!online || running || !!commandBusy} onClick={() => sendCommand('START')}>
            {commandBusy === 'START' ? 'Sending…' : 'Start'}
          </button>
          <button type="button" className="button button-light" disabled={!online || !running || !!commandBusy} onClick={() => sendCommand('STOP')}>
            {commandBusy === 'STOP' ? 'Sending…' : 'Stop'}
          </button>
          <button type="button" className="button button-light" disabled={!online || !running || !!commandBusy} onClick={() => sendCommand('RESET')}>
            {commandBusy === 'RESET' ? 'Sending…' : 'Reset session'}
          </button>
        </div>
      </div>

      <form className="device-config-form" onSubmit={saveConfig}>
        <div className="device-config-title">
          <div>
            <strong>Device detection settings</strong>
            <p>Settings are locked while monitoring is running.</p>
          </div>
          <span className="unit-pill">ESP32-101</span>
        </div>
        <div className="device-config-grid">
          <label>Water limit (litres)
            <input type="number" min="1" max="1000" step="0.1" value={config.water_limit_litres} disabled={running || saving} onChange={(e) => updateConfig('water_limit_litres', e.target.value)} required />
          </label>
          <label>Continuous-flow duration (seconds)
            <input type="number" min="10" max="1800" step="1" value={config.continuous_flow_seconds} disabled={running || saving} onChange={(e) => updateConfig('continuous_flow_seconds', e.target.value)} required />
          </label>
          <label>Low-flow threshold (L/min)
            <input type="number" min="0" max="200" step="0.1" value={config.low_flow_threshold_lpm} disabled={running || saving} onChange={(e) => updateConfig('low_flow_threshold_lpm', e.target.value)} required />
            <small>Set to 0 to disable low-flow detection.</small>
          </label>
          <label>Low-flow confirmation (seconds)
            <input type="number" min="1" max="300" step="1" value={config.low_flow_confirmation_seconds} disabled={running || saving} onChange={(e) => updateConfig('low_flow_confirmation_seconds', e.target.value)} required />
          </label>
        </div>
        <div className="device-config-actions">
          <button type="button" className="button button-light" disabled={running || saving} onClick={() => updateConfig('water_limit_litres', '1')}>Set 1 L demo limit</button>
          <button type="submit" className="button button-primary" disabled={running || saving}>{saving ? 'Saving…' : 'Save device settings'}</button>
        </div>
        {running && <p className="device-lock-note">Stop monitoring before changing device settings. New settings apply to the next session.</p>}
      </form>
    </section>
  );
}
