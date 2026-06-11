// Tiny fetch helper. API base + user come from query params (?api=&user=).
const _params = new URLSearchParams(location.search);
const API_BASE = _params.get("api") || "http://localhost:8000";
const USER_ID = _params.get("user") || "demo_user";

async function fetchInsights() {
  const res = await fetch(`${API_BASE}/insights/${encodeURIComponent(USER_ID)}`);
  if (!res.ok) throw new Error(`insights failed: ${res.status}`);
  return res.json();
}
