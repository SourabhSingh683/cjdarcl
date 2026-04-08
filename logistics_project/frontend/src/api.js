/**
 * api.js  —  CJ Darcl Logistics Intelligence Platform
 * =====================================================
 * Centralised API client. Automatically injects JWT Bearer token
 * from localStorage into authenticated requests.
 */

const API_BASE = 'http://127.0.0.1:8000/api';

// ─── Core fetch wrapper ───────────────────────────────────────────────────────
async function apiFetch(path, options = {}, authenticated = false) {
  const url = `${API_BASE}${path}`;
  const headers = { ...(options.headers || {}) };

  if (authenticated) {
    const token = localStorage.getItem('access_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData — browser sets it with boundary
  if (!(options.body instanceof FormData)) {
    if (!headers['Content-Type'] && options.body) {
      headers['Content-Type'] = 'application/json';
    }
  }

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || body.detail || body.details || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null;
    return await res.json();
  } catch (err) {
    if (err.message === 'Failed to fetch') {
      throw new Error('Cannot connect to backend. Is it running on port 8000?');
    }
    throw err;
  }
}

function buildQuery(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') qs.append(key, val);
  });
  const str = qs.toString();
  return str ? `?${str}` : '';
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function authLogin(username, password) {
  return apiFetch('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function authVehicleLogin(vehicleNo) {
  return apiFetch('/auth/vehicle-login/', {
    method: 'POST',
    body: JSON.stringify({ vehicle_no: vehicleNo }),
  });
}

export async function authCnnoLogin(cnno) {
  return apiFetch('/auth/cnno-login/', {
    method: 'POST',
    body: JSON.stringify({ cnno }),
  });
}

export async function authOTPRequest(phone) {
  return apiFetch('/auth/otp/request/', {
    method: 'POST',
    body: JSON.stringify({ phone }),
  });
}

export async function authOTPVerify(phone, otp, extras = {}) {
  return apiFetch('/auth/otp/verify/', {
    method: 'POST',
    body: JSON.stringify({ phone, otp, ...extras }),
  });
}

export async function authMe() {
  return apiFetch('/auth/me/', {}, true);
}

export function authLogout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

export async function authRegister(payload) {
  return apiFetch('/auth/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ─── Notifications ────────────────────────────────────────────────────────────

export const fetchNotifications = (p = {}) =>
  apiFetch(`/notifications/${buildQuery(p)}`, {}, true);

export const markNotificationRead = (id) =>
  apiFetch(`/notifications/${id}/read/`, { method: 'PATCH' }, true);

export const markAllNotificationsRead = () =>
  apiFetch('/notifications/mark-all-read/', { method: 'POST' }, true);

// ─── Shipments (role-filtered when authenticated) ─────────────────────────────

export const fetchShipments = (f = {}) =>
  apiFetch(`/shipments/${buildQuery(f)}`, {}, true);

export async function uploadPOD(shipmentId, file) {
  const formData = new FormData();
  formData.append('pod_file', file);
  return apiFetch(`/shipments/${shipmentId}/pod/`, { method: 'POST', body: formData }, true);
}

export async function downloadInvoiceAction(shipmentId) {
  const token = localStorage.getItem('access_token');
  const url = `${API_BASE}/shipments/${shipmentId}/invoice/`;
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Download failed: HTTP ${res.status}`);
  
  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') || '';
  const match = cd.match(/filename="?(.+?)"?$/);
  const filename = match ? match[1] : `invoice_${shipmentId}.pdf`;

  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

// ─── Upload ───────────────────────────────────────────────────────────────────

export async function uploadFile(files) {
  const formData = new FormData();
  if (Array.isArray(files)) {
    files.forEach(f => formData.append('file', f));
  } else {
    formData.append('file', files);
  }
  return apiFetch('/upload/', { method: 'POST', body: formData });
}

export const clearAllData = () => apiFetch('/clear-data/', { method: 'DELETE' });

export const reprocessUpload = (id) => apiFetch(`/uploads/${id}/reprocess/`, { method: 'POST' });

// ─── KPIs ─────────────────────────────────────────────────────────────────────

export const fetchSummary        = (f = {}) => apiFetch(`/kpis/summary/${buildQuery(f)}`);
export const fetchRevenueTrends  = (f = {}) => apiFetch(`/kpis/revenue-trends/${buildQuery(f)}`);
export const fetchTopRoutes      = (f = {}) => apiFetch(`/kpis/top-routes/${buildQuery(f)}`);
export const fetchDelayedShipments = (f = {}) => apiFetch(`/kpis/delayed-shipments/${buildQuery(f)}`);
export const fetchDrilldown      = (f = {}) => apiFetch(`/kpis/drilldown/${buildQuery(f)}`);
export const fetchComparison     = (f = {}) => apiFetch(`/kpis/comparison/${buildQuery(f)}`);
export const fetchTransporterPerformance = (f = {}) => apiFetch(`/kpis/transporter-performance/${buildQuery(f)}`);

// ─── Analytics ───────────────────────────────────────────────────────────────

export const fetchOperationalIntelligence = (f = {}) => apiFetch(`/analysis/operational-intelligence/${buildQuery(f)}`);
export const fetchRootCause  = (f = {}) => apiFetch(`/analysis/root-cause/${buildQuery(f)}`);
export const fetchRisk       = (f = {}) => apiFetch(`/analysis/risk/${buildQuery(f)}`);
export const fetchShortage   = (f = {}) => apiFetch(`/analysis/shortage/${buildQuery(f)}`);

// ─── Quality & Insights ───────────────────────────────────────────────────────

export const fetchQuality       = () => apiFetch('/quality/');
export const fetchInsights      = (f = {}) => apiFetch(`/insights/${buildQuery(f)}`);
export const fetchSmartInsights = (f = {}) => apiFetch(`/insights/smart/${buildQuery(f)}`);

// ─── History ─────────────────────────────────────────────────────────────────

export const fetchUploadHistory = () => apiFetch('/uploads/');
export const deleteUpload       = (id) => apiFetch(`/uploads/${id}/`, { method: 'DELETE' }, true);

// ─── AI Analysis (Gemini) ────────────────────────────────────────────────────

export async function fetchAIAnalysis(question = '') {
  return apiFetch('/ai/analyze/', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

// ─── Driver Panel ─────────────────────────────────────────────────────────────

export const fetchDriverShipments = () =>
  apiFetch('/driver/shipments/', {}, true);

export async function uploadPodImages(shipmentId, photos) {
  const formData = new FormData();
  if (photos[0]) formData.append('pod_image_1', photos[0]);
  if (photos[1]) formData.append('pod_image_2', photos[1]);
  if (photos[2]) formData.append('pod_image_3', photos[2]);
  return apiFetch(`/driver/upload-pod/${shipmentId}/`, {
    method: 'POST',
    body: formData,
  }, true);
}

/** Download POD images (single image or ZIP) */
export function downloadPodUrl(shipmentId) {
  return `${API_BASE}/download-pod/${shipmentId}/`;
}

export async function downloadPod(shipmentId) {
  const token = localStorage.getItem('access_token');
  const url = `${API_BASE}/download-pod/${shipmentId}/`;
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Download failed: HTTP ${res.status}`);
  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') || '';
  const match = cd.match(/filename="?(.+?)"?$/);
  const filename = match ? match[1] : `POD_${shipmentId}`;
  // Trigger browser download
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

/** Get POD image URLs for in-app preview */
export const viewPod = (shipmentId) =>
  apiFetch(`/view-pod/${shipmentId}/`, {}, true);

/** Get invoice URL for viewing in new tab */
export const getInvoiceUrl = (shipmentId) =>
  `${API_BASE}/shipments/${shipmentId}/invoice/`;

export const deletePod = (shipmentId) =>
  apiFetch(`/driver/delete-pod/${shipmentId}/`, { method: 'POST' }, true);


