
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 8000,
});

// Authentication helpers
const TOKEN_KEY = 'aquaguard_access_token';

export const getAuthToken = () => sessionStorage.getItem(TOKEN_KEY);

export const saveAuthToken = (token) => {
  sessionStorage.setItem(TOKEN_KEY, token);
};

export const clearAuthToken = () => {
  sessionStorage.removeItem(TOKEN_KEY);
};

// Automatically attach the logged-in user's token.
api.interceptors.request.use((config) => {
  const token = getAuthToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Authentication API
export const login = async (username, password) => {
  const response = await api.post('/auth/login', {
    username,
    password,
  });

  saveAuthToken(response.data.access_token);
  return response.data;
};

export const logout = () => {
  clearAuthToken();
};

// Existing dashboard API functions
export const getRooms = async () =>
  (await api.get('/rooms')).data;

export const getOverview = async () =>
  (await api.get('/overview')).data;

export const getDashboard = async (roomId) => {
  const params = { room_id: roomId };

  const [summary, readings, alerts, settings, seasonal, room] =
    await Promise.all([
      api.get('/summary', { params }),
      api.get('/readings', { params: { ...params, limit: 40 } }),
      api.get('/alerts', { params }),
      api.get('/settings', { params }),
      api.get('/seasonal-analysis', { params }),
      api.get(`/rooms/${encodeURIComponent(roomId)}`),
    ]);

  return {
    summary: summary.data,
    readings: readings.data,
    alerts: alerts.data,
    settings: settings.data,
    seasonal: seasonal.data,
    room: room.data,
  };
};

// Admin hostel management API
export const getAdminHostels = async () =>
  (await api.get('/admin/hostels')).data;

export const createHostel = async (hostelData) =>
  (await api.post('/admin/hostels', hostelData)).data;

export const updateHostel = async (hostelId, hostelData) =>
  (await api.patch(`/admin/hostels/${hostelId}`, hostelData)).data;

export const updateHostelUsername = async (hostelId, username) =>
  (await api.put(`/admin/hostels/${hostelId}/username`, {
    username,
  })).data;

export const resetHostelPassword = async (hostelId, newPassword) =>
  (await api.put(`/admin/hostels/${hostelId}/password`, {
    new_password: newPassword,
  })).data;

export const deleteHostel = async (hostelId) =>
  (await api.delete(`/admin/hostels/${hostelId}`)).data;

// AquaGuard physical ESP32 controls and configuration.
export const getDeviceStatus = async () =>
  (await api.get('/device/status')).data;

// Device command polling is intended for the ESP32, not the browser.
// Never expose DEVICE_API_KEY in frontend code.
export const getDeviceCommand = async () =>
  (await api.get('/device/command', {
    params: {
      device_id: 'ESP32-101',
      sensor_id: 'SENSOR-101',
    },
  })).data;

export const controlDevice = async (command) =>
  (await api.post('/device/control', { command })).data;

export const updateDeviceWaterLimit = async (water_limit_litres) =>
  (await api.put('/device/water-limit', {
    water_limit_litres,
  })).data;

export const updateDeviceContinuousFlow = async (duration_seconds) =>
  (await api.put('/device/continuous-flow', {
    duration_seconds,
  })).data;

export const updateDeviceLowFlow = async (
  threshold_lpm,
  confirmation_seconds
) =>
  (await api.put('/device/low-flow', {
    threshold_lpm,
    confirmation_seconds,
  })).data;
