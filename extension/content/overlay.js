// Content script: paint the match-score overlay on the profile (section 2.3.4).
//
// Asks the background worker for a score for the scraped profile and renders a
// small badge anchored top-right: the score, the model's reasons, and two quick
// links — fill the post-date questionnaire (carrying THIS profile's tokens, so
// the feedback ties back to the profile) and open the dashboard. Respects the
// "Enabled" switch and re-scores when the visible profile changes.

const BADGE_ID = "amore-overlay-badge";
let lastProfile = []; // tokens of the profile currently shown (for the links)

function colorFor(score) {
  if (score >= 70) return "#2e9e5b";
  if (score >= 45) return "#d9a300";
  return "#c0392b";
}

async function isEnabled() {
  const { enabled } = await chrome.storage.local.get("enabled");
  return enabled !== false;
}

// Where things live. apiBase = backend; webBase = the static server that hosts
// the dashboard + questionnaire pages. Both overridable from the popup.
async function getSettings() {
  const s = await chrome.storage.local.get(["apiBase", "userId", "webBase"]);
  return {
    apiBase: s.apiBase || "http://localhost:8000",
    userId: s.userId || "demo_user",
    webBase: s.webBase || "http://localhost:5500",
  };
}

function removeBadge() {
  const badge = document.getElementById(BADGE_ID);
  if (badge) badge.remove();
}

// Questionnaire URL carrying this profile's tokens, so the feedback the user
// submits is linked to the exact profile they just saw (closes the loop).
function questionnaireUrl(s, profile) {
  const q = new URLSearchParams({ api: s.apiBase, user: s.userId, profile: profile.join(",") });
  return `${s.webBase}/questionnaire/vibe_form.html?${q.toString()}`;
}

function dashboardUrl(s) {
  const q = new URLSearchParams({ api: s.apiBase, user: s.userId });
  return `${s.webBase}/dashboard/index.html?${q.toString()}`;
}

function renderBadge(result, s, profile) {
  let badge = document.getElementById(BADGE_ID);
  if (!badge) {
    badge = document.createElement("div");
    badge.id = BADGE_ID;
    Object.assign(badge.style, {
      position: "fixed", top: "16px", right: "16px", zIndex: 999999,
      background: "#fff", borderRadius: "12px", padding: "10px 14px",
      boxShadow: "0 4px 14px rgba(0,0,0,.18)", fontFamily: "system-ui, sans-serif",
      fontSize: "13px", color: "#1f3a5f", maxWidth: "240px",
    });
    document.body.appendChild(badge);
  }
  const lowConf = result.confidence === "low";
  const reasons = (result.reasons || []).map((r) => `<li>${r.text}</li>`).join("");
  const linkStyle = "flex:1;text-align:center;text-decoration:none;font-size:12px;"
    + "padding:6px 8px;border-radius:8px;border:1px solid #e0c9cf;color:#a0506a;";
  badge.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="font-weight:700;font-size:20px;color:${colorFor(result.score)}">${result.score}</span>
      <span style="font-weight:600">A-MORE match</span>
    </div>
    ${lowConf ? '<div style="color:#888;font-size:11px;">low confidence — still learning</div>' : ""}
    ${reasons ? `<ul style="margin:6px 0 0;padding-inline-start:16px;">${reasons}</ul>` : ""}
    <div style="display:flex;gap:6px;margin-top:10px;" dir="rtl">
      <a href="${questionnaireUrl(s, profile)}" target="_blank" rel="noopener" style="${linkStyle}">📋 שאלון</a>
      <a href="${dashboardUrl(s)}" target="_blank" rel="noopener" style="${linkStyle}">📊 דאשבורד</a>
    </div>
  `;
}

async function scoreCurrentProfile() {
  if (!(await isEnabled())) { removeBadge(); return; }
  if (typeof window.__amoreScrapeProfile !== "function") return;
  const profile = window.__amoreScrapeProfile();
  if (!profile.length) return;
  lastProfile = profile;
  const s = await getSettings();
  chrome.runtime.sendMessage({ type: "SCORE_PROFILE", profile }, (result) => {
    if (result && !result.error) renderBadge(result, s, profile);
  });
}

// Initial run + react to SPA navigation / card swaps.
scoreCurrentProfile();
const observer = new MutationObserver(() => {
  clearTimeout(window.__amoreDebounce);
  window.__amoreDebounce = setTimeout(scoreCurrentProfile, 600);
});
observer.observe(document.body, { childList: true, subtree: true });

// React the moment the user flips the switch in the popup.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !("enabled" in changes)) return;
  if (changes.enabled.newValue === false) removeBadge();
  else scoreCurrentProfile();
});
