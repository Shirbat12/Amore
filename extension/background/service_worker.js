// Background service worker: the extension's hub (section 2.1).
// Mediates between content scripts and the backend API, and caches recent scores.

const DEFAULTS = { apiBase: "http://localhost:8000", userId: "demo_user" };
const cache = new Map(); // profile-key -> { result, ts }
const TTL_MS = 60_000;

async function settings() {
  const stored = await chrome.storage.local.get(["apiBase", "userId"]);
  return { ...DEFAULTS, ...stored };
}

async function fetchScore(profile) {
  const key = profile.slice().sort().join("|");
  const hit = cache.get(key);
  if (hit && Date.now() - hit.ts < TTL_MS) return hit.result;

  const { apiBase, userId } = await settings();
  const res = await fetch(`${apiBase}/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, profile }),
  });
  if (!res.ok) throw new Error(`score failed: ${res.status}`);
  const result = await res.json();
  cache.set(key, { result, ts: Date.now() });
  return result;
}

// Forward a like/pass selection to the backend (Decision-Alignment KPI).
// Fire-and-forget: failures are logged, never surfaced to the user.
async function logSelection({ action, profile }) {
  const { apiBase, userId } = await settings();
  const res = await fetch(`${apiBase}/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, action, profile }),
  });
  if (!res.ok) throw new Error(`selection failed: ${res.status}`);
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "SCORE_PROFILE") {
    fetchScore(msg.profile)
      .then(sendResponse)
      .catch((e) => sendResponse({ error: String(e) }));
    return true; // keep the message channel open for the async reply
  }
  if (msg.type === "LOG_SELECTION") {
    logSelection(msg).catch((e) => console.debug("[A-MORE] selection log failed:", e));
    return false; // no response expected
  }
  return false;
});
