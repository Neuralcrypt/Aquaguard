import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 8000,
});

export const getRooms = async () => (await api.get('/rooms')).data;
export const getOverview = async () => (await api.get('/overview')).data;
export const getDashboard = async (roomId) => {
  const params = { room_id: roomId };
  const [summary, readings, alerts, settings, seasonal, room] = await Promise.all([
    api.get('/summary', { params }),
    api.get('/readings', { params: { ...params, limit: 40 } }),
    api.get('/alerts', { params }),
    api.get('/settings', { params }),
    api.get('/seasonal-analysis', { params }),
    api.get(`/rooms/${encodeURIComponent(roomId)}`),
  ]);
  return { summary: summary.data, readings: readings.data, alerts: alerts.data, settings: settings.data, seasonal: seasonal.data, room: room.data };
};

// AquaGuard physical ESP32 controls and configuration.
export const getDeviceStatus = async () => (await api.get('/device/status')).data;
export const getDeviceCommand = async () => (await api.get('/device/command', {
  params: { device_id: 'ESP32-101', sensor_id: 'SENSOR-101' },
})).data;
export const controlDevice = async (command) => (await api.post('/device/control', { command })).data;
export const updateDeviceWaterLimit = async (water_limit_litres) =>
  (await api.put('/device/water-limit', { water_limit_litres })).data;
export const updateDeviceContinuousFlow = async (duration_seconds) =>
  (await api.put('/device/continuous-flow', { duration_seconds })).data;
export const updateDeviceLowFlow = async (threshold_lpm, confirmation_seconds) =>
  (await api.put('/device/low-flow', { threshold_lpm, confirmation_seconds })).data;
