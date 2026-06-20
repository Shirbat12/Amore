// Content script: paint the match-score overlay on the profile (section 2.3.4).
//
// Asks the background worker for a score for the scraped profile and renders a
// small badge anchored top-right: the score, the model's reasons, and two quick
// links — fill the post-date questionnaire (carrying THIS profile's tokens, so
// the feedback ties back to the profile) and open the dashboard. Respects the
// "Enabled" switch and re-scores when the visible profile changes.

const BADGE_ID = "amore-overlay-badge";
let lastProfile = []; // tokens of the profile currently shown (for the links)
let lastScoreResult = null;

// Brand palette (matches assets/theme.css — content scripts can't import it).
const BRAND = {
  surface: "#fffbf8",
  border: "rgba(194,161,90,.34)",
  ink: "#4a2e3a",
  roseDeep: "#a0506a",
  mauve: "#9a7c86",
  gold: "#c2a15a",
  good: "#2e9e5b",
};

function colorFor(score) {
  if (score >= 70) return BRAND.good;
  if (score >= 45) return BRAND.gold;
  return BRAND.roseDeep;
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

function linkStyle() {
  return "flex:1;text-align:center;text-decoration:none;font-size:12px;font-weight:600;"
    + "padding:6px 10px;border-radius:999px;border:1px solid " + BRAND.border + ";"
    + "color:" + BRAND.roseDeep + ";background:" + BRAND.surface + ";";
}

function insightFromReasons(result) {
  const reasons = (result && result.reasons) || [];
  const texts = [];
  for (let i = 0; i < reasons.length && texts.length < 2; i++) {
    if (reasons[i].text) texts.push(reasons[i].text);
  }
  if (!texts.length) return "עדיין אין מספיק היסטוריה — נלמד מהבחירות והשאלונים שלך.";
  return texts.join(" · ");
}

// TODO(backend, Liel): POST /profile_insight
// req:  { user_id, profile: ["age:27-30", "interest:travel"] }
// resp: { insight: "<one or two Hebrew sentences>" }
async function fetchProfileInsight(s, profile, result) {
  try {
    const res = await fetch(`${s.apiBase}/profile_insight`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: s.userId, profile }),
    });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    if (data.insight) return data.insight;
    throw new Error("empty insight");
  } catch (e) {
    return insightFromReasons(result);
  }
}

function renderBadge(result, s, profile) {
  lastScoreResult = result;
  let badge = document.getElementById(BADGE_ID);
  if (!badge) {
    badge = document.createElement("div");
    badge.id = BADGE_ID;
    Object.assign(badge.style, {
      position: "fixed", top: "16px", right: "16px", zIndex: 999999,
      background: BRAND.surface, border: "1px solid " + BRAND.border,
      borderRadius: "12px", padding: "10px 14px",
      boxShadow: "0 4px 14px rgba(74,46,58,.12)",
      fontFamily: "'Rubik', system-ui, sans-serif",
      fontSize: "13px", color: BRAND.ink, maxWidth: "260px",
    });
    document.body.appendChild(badge);
  }
  const lowConf = result.confidence === "low";
  const reasons = (result.reasons || []).map((r) => `<li>${r.text}</li>`).join("");
  const ls = linkStyle();
  badge.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="font-weight:700;font-size:20px;color:${colorFor(result.score)}">${result.score}</span>
      <span style="font-weight:600;color:${BRAND.roseDeep}">A-MORE match</span>
    </div>
    ${lowConf ? '<div style="color:' + BRAND.mauve + ';font-size:11px;">ביטחון נמוך — עדיין לומדים</div>' : ""}
    ${reasons ? `<ul style="margin:6px 0 0;padding-inline-start:16px;color:${BRAND.ink};">${reasons}</ul>` : ""}
    <div id="amore-insight-box" hidden style="margin-top:8px;padding:8px 10px;border-radius:8px;background:rgba(246,227,220,.55);color:${BRAND.ink};font-size:12px;line-height:1.5;"></div>
    <div style="display:flex;gap:6px;margin-top:10px;" dir="rtl">
      <button type="button" id="amore-ai-btn" aria-label="תובנת AI על הפרופיל" style="${ls}cursor:pointer;">💬 תובנת AI</button>
    </div>
    <div style="display:flex;gap:6px;margin-top:6px;" dir="rtl">
      <a href="${questionnaireUrl(s, profile)}" target="_blank" rel="noopener" aria-label="פתיחת שאלון דייט" style="${ls}">📋 שאלון</a>
      <a href="${dashboardUrl(s)}" target="_blank" rel="noopener" aria-label="פתיחת דאשבורד" style="${ls}">📊 דאשבורד</a>
    </div>
  `;

  const aiBtn = badge.querySelector("#amore-ai-btn");
  const insightBox = badge.querySelector("#amore-insight-box");
  aiBtn.addEventListener("click", async () => {
    aiBtn.disabled = true;
    aiBtn.textContent = "טוען…";
    insightBox.hidden = false;
    insightBox.textContent = "מכינה תובנה…";
    const text = await fetchProfileInsight(s, profile, lastScoreResult);
    insightBox.textContent = text;
    aiBtn.disabled = false;
    aiBtn.textContent = "💬 תובנת AI";
  });
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
