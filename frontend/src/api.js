import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 minutes - AI analysis can take time
});

// ---------------------------------------------------------------------------
// Request interceptor — attach Bearer token
// ---------------------------------------------------------------------------
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — auto-refresh on 401
// ---------------------------------------------------------------------------
let isRefreshing = false;
let failedQueue = [];

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Don't retry auth endpoints or already-retried requests
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes('/auth/')
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) throw new Error('No refresh token');

      const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
        refresh_token: refreshToken,
      });

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      processQueue(null, data.access_token);

      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function googleLogin(idToken) {
  const response = await api.post('/auth/google', { token: idToken });
  return response.data;
}

export async function signup(email, name, password) {
  const response = await api.post('/auth/signup', { email, name, password });
  return response.data;
}

export async function emailLogin(email, password) {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
}

export async function refreshTokens(refreshToken) {
  const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
  return response.data;
}

export async function getCurrentUser() {
  const response = await api.get('/auth/me');
  return response.data;
}

export async function changePassword(currentPassword, newPassword) {
  const response = await api.put('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
}

// ---------------------------------------------------------------------------
// History API
// ---------------------------------------------------------------------------

export async function getHistory() {
  const response = await api.get('/history');
  return response.data;
}

export async function getHistoryItem(id) {
  const response = await api.get(`/history/${id}`);
  return response.data;
}

export async function deleteHistoryItem(id) {
  const response = await api.delete(`/history/${id}`);
  return response.data;
}

// ---------------------------------------------------------------------------
// Existing analysis API
// ---------------------------------------------------------------------------

export async function analyzeProject(url, description = '') {
  const response = await api.post('/analyze', { url, design_description: description });
  return response.data;
}

export async function checkWiring(diagramJson) {
  const response = await api.post('/check-wiring', { diagram_json: diagramJson });
  return response.data;
}

export async function checkCode(sketchCode, diagramJson = '') {
  const response = await api.post('/check-code', {
    sketch_code: sketchCode,
    diagram_json: diagramJson,
  });
  return response.data;
}

export async function suggestFix(faultReport, diagramJson = '', sketchCode = '') {
  const response = await api.post('/suggest-fix', {
    fault_report: faultReport,
    diagram_json: diagramJson,
    sketch_code: sketchCode,
  });
  return response.data;
}

export async function healthCheck() {
  const response = await api.get('/health');
  return response.data;
}

// ---------------------------------------------------------------------------
// KiCad analysis API
// ---------------------------------------------------------------------------

export async function uploadKiCadFiles(files, description = '') {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  if (description) {
    formData.append('design_description', description);
  }
  const response = await api.post('/kicad/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function suggestKiCadFix(faultReport, schematicContent = '', pcbContent = '') {
  const response = await api.post('/kicad/suggest-fix', {
    fault_report: faultReport,
    schematic_content: schematicContent,
    pcb_content: pcbContent,
  });
  return response.data;
}
