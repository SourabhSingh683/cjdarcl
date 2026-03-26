/**
 * API client for the Logistics Intelligence Dashboard v3.
 */

const API_BASE = 'http://127.0.0.1:8000/api';

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || body.details || `HTTP ${res.status}`);
    }
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

// Upload
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch('/upload/', { method: 'POST', body: formData });
}

// KPIs
export const fetchSummary = (f = {}) => apiFetch(`/kpis/summary/${buildQuery(f)}`);
export const fetchRevenueTrends = (f = {}) => apiFetch(`/kpis/revenue-trends/${buildQuery(f)}`);
export const fetchTopRoutes = (f = {}) => apiFetch(`/kpis/top-routes/${buildQuery(f)}`);
export const fetchDelayedShipments = (f = {}) => apiFetch(`/kpis/delayed-shipments/${buildQuery(f)}`);
export const fetchDrilldown = (f = {}) => apiFetch(`/kpis/drilldown/${buildQuery(f)}`);
export const fetchComparison = (f = {}) => apiFetch(`/kpis/comparison/${buildQuery(f)}`);

// Analytics
export const fetchRootCause = (f = {}) => apiFetch(`/analysis/root-cause/${buildQuery(f)}`);
export const fetchRisk = (f = {}) => apiFetch(`/analysis/risk/${buildQuery(f)}`);
export const fetchShortage = (f = {}) => apiFetch(`/analysis/shortage/${buildQuery(f)}`);

// Quality & Insights
export const fetchQuality = () => apiFetch('/quality/');
export const fetchInsights = (f = {}) => apiFetch(`/insights/${buildQuery(f)}`);
export const fetchSmartInsights = (f = {}) => apiFetch(`/insights/smart/${buildQuery(f)}`);

// History & Shipments
export const fetchUploadHistory = () => apiFetch('/uploads/');
export const fetchShipments = (f = {}) => apiFetch(`/shipments/${buildQuery(f)}`);

// AI Analysis (Gemini)
export async function fetchAIAnalysis(question = '') {
  return apiFetch('/ai/analyze/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
}
