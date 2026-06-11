// Content script: paint the match-score overlay on the profile (section 2.3.4).
//
// Asks the background worker for a score for the scraped profile and renders a
// small badge anchored top-right. Re-runs when the visible profile changes.

const BADGE_ID = "amore-overlay-badge";

function colorFor(score) {
  if (score >= 70) return "#2e9e5b";
  if (score >= 45) return "#d9a300";
  return "#c0392b";
}

function renderBadge(result) {
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
  const reasons = (result.reasons || [])
    .map((r) => `<li>${r.text}</li>`)
    .join("");
  badge.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="font-weight:700;font-size:20px;color:${colorFor(result.score)}">
        ${result.score}
      </span>
      <span style="font-weight:600">A-MORE match</span>
    </div>
    ${lowConf ? '<div style="color:#888;font-size:11px;">low confidence — still learning</div>' : ""}
    ${reasons ? `<ul style="margin:6px 0 0;padding-inline-start:16px;">${reasons}</ul>` : ""}
  `;
}

async function scoreCurrentProfile() {
  if (typeof window.__amoreScrapeProfile !== "function") return;
  const profile = window.__amoreScrapeProfile();
  if (!profile.length) return;
  chrome.runtime.sendMessage({ type: "SCORE_PROFILE", profile }, (result) => {
    if (result && !result.error) renderBadge(result);
  });
}

// Initial run + react to SPA navigation / card swaps.
scoreCurrentProfile();
const observer = new MutationObserver(() => {
  clearTimeout(window.__amoreDebounce);
  window.__amoreDebounce = setTimeout(scoreCurrentProfile, 600);
});
observer.observe(document.body, { childList: true, subtree: true });
