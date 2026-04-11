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

// ─── Shipments (role-filtered when authenticated) ─────────────────────────────

export const fetchShipments = (f = {}) =>
  apiFetch(`/shipments/${buildQuery(f)}`, {}, true);

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

export async function uploadFile(files, refresh = false) {
  const formData = new FormData();
  if (Array.isArray(files)) {
    files.forEach(f => formData.append('file', f));
  } else {
    formData.append('file', files);
  }
  const query = refresh ? '?refresh=true' : '';
  return apiFetch(`/upload/${query}`, { method: 'POST', body: formData }, true);
}

/**
 * Upload file with real-time progress tracking
 */
export function uploadFileWithProgress(files, refresh = false, onProgress = () => {}) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    if (Array.isArray(files)) {
      files.forEach(f => formData.append('file', f));
    } else {
      formData.append('file', files);
    }
    
    const query = refresh ? '?refresh=true' : '';
    const xhr = new XMLHttpRequest();
    const token = localStorage.getItem('access_token');
    
    xhr.open('POST', `${API_BASE}/upload/${query}`);
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch (e) {
          resolve(xhr.responseText);
        }
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new Error(body.error || body.detail || 'Upload failed'));
        } catch (e) {
          reject(new Error(`HTTP ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error('Network error during upload'));
    xhr.send(formData);
  });
}

export const clearAllData = () => apiFetch('/clear-data/', { method: 'DELETE' }, true);

export const reprocessUpload = (id) => apiFetch(`/uploads/${id}/reprocess/`, { method: 'POST' }, true);

// ─── KPIs ─────────────────────────────────────────────────────────────────────

export const fetchSummary        = (f = {}) => apiFetch(`/kpis/summary/${buildQuery(f)}`, {}, true);
export const fetchRevenueTrends  = (f = {}) => apiFetch(`/kpis/revenue-trends/${buildQuery(f)}`, {}, true);
export const fetchTopRoutes      = (f = {}) => apiFetch(`/kpis/top-routes/${buildQuery(f)}`, {}, true);
export const fetchDelayedShipments = (f = {}) => apiFetch(`/kpis/delayed-shipments/${buildQuery(f)}`, {}, true);
export const fetchDrilldown      = (f = {}) => apiFetch(`/kpis/drilldown/${buildQuery(f)}`, {}, true);
export const fetchComparison     = (f = {}) => apiFetch(`/kpis/comparison/${buildQuery(f)}`, {}, true);
export const fetchTransporterPerformance = (f = {}) => apiFetch(`/kpis/transporter-performance/${buildQuery(f)}`, {}, true);

// ─── Analytics ───────────────────────────────────────────────────────────────

export const fetchOperationalIntelligence = (f = {}) => apiFetch(`/analysis/operational-intelligence/${buildQuery(f)}`, {}, true);
export const fetchRootCause  = (f = {}) => apiFetch(`/analysis/root-cause/${buildQuery(f)}`, {}, true);
export const fetchRisk       = (f = {}) => apiFetch(`/analysis/risk/${buildQuery(f)}`, {}, true);
export const fetchShortage   = (f = {}) => apiFetch(`/analysis/shortage/${buildQuery(f)}`, {}, true);

// ─── Quality & Insights ───────────────────────────────────────────────────────

export const fetchQuality       = () => apiFetch('/quality/', {}, true);
export const fetchInsights      = (f = {}) => apiFetch(`/insights/${buildQuery(f)}`, {}, true);
export const fetchSmartInsights = (f = {}) => apiFetch(`/insights/smart/${buildQuery(f)}`, {}, true);

// ─── History ─────────────────────────────────────────────────────────────────

export const fetchUploadHistory = () => apiFetch('/uploads/', {}, true);
export const deleteUpload       = (id) => apiFetch(`/uploads/${id}/`, { method: 'DELETE' }, true);
export const bulkDeleteUploads  = (ids) => apiFetch('/uploads/bulk-delete/', { method: 'POST', body: JSON.stringify({ ids }) }, true);


/** Get invoice URL for viewing in new tab */
export const getInvoiceUrl = (shipmentId) =>
  `${API_BASE}/shipments/${shipmentId}/invoice/`;


// ─── Profit Analysis ─────────────────────────────────────────────────────────

export function uploadProfitFile(files, refresh = false, onProgress = () => {}) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    if (Array.isArray(files)) {
      files.forEach(f => formData.append('file', f));
    } else {
      formData.append('file', files);
    }
    
    const query = refresh ? '?refresh=true' : '';
    const xhr = new XMLHttpRequest();
    const token = localStorage.getItem('access_token');
    
    xhr.open('POST', `${API_BASE}/profit/upload/${query}`);
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)); } catch { resolve(xhr.responseText); }
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new Error(body.error || body.detail || 'Upload failed'));
        } catch { reject(new Error(`HTTP ${xhr.status}`)); }
      }
    };

    xhr.onerror = () => reject(new Error('Network error during upload'));
    xhr.send(formData);
  });
}

export const fetchProfitSummary   = (f = {}) => apiFetch(`/profit/summary/${buildQuery(f)}`, {}, true);
export const fetchProfitLanes     = (f = {}) => apiFetch(`/profit/lanes/${buildQuery(f)}`, {}, true);
export const fetchProfitTrends    = (f = {}) => apiFetch(`/profit/trends/${buildQuery(f)}`, {}, true);
export const fetchProfitAlerts    = (f = {}) => apiFetch(`/profit/alerts/${buildQuery(f)}`, {}, true);
export const fetchProfitDrilldown = (lc, dc, f = {}) => {
  const q = buildQuery({ ...f, loading_city: lc, delivery_city: dc });
  return apiFetch(`/profit/drilldown/${q}`, {}, true);
};
export const fetchProfitLaneShipments = (lc, dc, f = {}) => {
  const q = buildQuery({ ...f, loading_city: lc, delivery_city: dc });
  return apiFetch(`/profit/shipments/${q}`, {}, true);
};
export const fetchProfitInsights = (f = {}) => apiFetch(`/profit/insights/${buildQuery(f)}`, {}, true);
