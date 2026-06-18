// Tiny fetch helper. Base URL + user come from the shared config
// (assets/config.js), which reads ?api= and ?user= with localhost defaults.
const API_BASE = window.AMORE_CONFIG.apiBase;
const USER_ID = window.AMORE_CONFIG.userId;

async function fetchInsights() {
  const res = await fetch(`${API_BASE}/insights/${encodeURIComponent(USER_ID)}`);
  if (!res.ok) throw new Error(`insights failed: ${res.status}`);
  return res.json();
}
