const API_BASE = 'http://localhost:8000/api';

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchAnalytics(endpoint) {
  try {
    return await apiFetch(`/analytics/${endpoint}`);
  } catch {
    return [];
  }
}
