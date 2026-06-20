// DISABLED — A-MORE learns only from post-date questionnaires + dry profile
// tokens (not Like/Pass swipes). This file is kept for reference; it is not
// loaded from manifest.json.
//
// Content script: log which profiles the user accepts or rejects (section 4.1,
// Decision-Alignment KPI). When the user clicks Like or Pass on the profile
// that's currently on screen, we scrape its dry tokens and send {action,
// profile} to the backend through the service worker. This signal — did the
// user follow A-MORE's score? — was not captured anywhere before.
//
// Like the scraper, button selectors differ per site and change often, so they
// live in one editable map with accessible-name fallbacks. Use the console
// helper at the bottom to confirm detection and fix selectors after a redesign.

const SELECTION_SITES = {
  "okcupid.com": {
    // Most stable signal first (test id / accessible name), looser ones last.
    like: [
      '[data-testid="like-button"]',
      '[aria-label*="like" i]',
      'button[title*="like" i]',
    ],
    pass: [
      '[data-testid="pass-button"]',
      '[aria-label*="pass" i]',
      'button[title*="pass" i]',
    ],
  },
};

// Pick the config for the current host (handles www. and other subdomains).
function selectionConfig() {
  const host = location.hostname.replace(/^www\./, "");
  const key = Object.keys(SELECTION_SITES).find((domain) => host.endsWith(domain));
  return key ? SELECTION_SITES[key] : null;
}

// Respect the same on/off switch as the overlay.
async function selectionEnabled() {
  const s = await window.__amoreStorageGet("enabled");
  return s.enabled !== false;
}

// True if the clicked node, or any ancestor, matches a selector in the list.
// Using closest() means a click on an icon inside the button still counts.
function matchesAny(target, selectors) {
  for (const sel of selectors) {
    if (target.closest(sel)) return true;
  }
  return false;
}

// A single user action can fire several DOM events; ignore repeats within a
// short window so we log each like/pass once.
let lastSent = 0;
function tooSoon() {
  const now = Date.now();
  if (now - lastSent < 800) return true;
  lastSent = now;
  return false;
}

async function onClick(e) {
  if (!window.__amoreExtensionAlive()) return;
  const cfg = selectionConfig();
  if (!cfg) return;
  if (!(await selectionEnabled())) return;
  if (typeof window.__amoreScrapeProfile !== "function") return;

  const target = e.target;
  let action = null;
  if (matchesAny(target, cfg.like)) action = "like";
  else if (matchesAny(target, cfg.pass)) action = "pass";
  if (!action || tooSoon()) return;

  const profile = window.__amoreScrapeProfile();
  if (!profile.length) return;

  window.__amoreSendMessage({ type: "LOG_SELECTION", action, profile });
  console.debug("[A-MORE] selection:", action, profile);
}

window.__amoreOnRetire(function () {
  document.removeEventListener("click", onClick, true);
});

// Capture phase so we still see the click even if the app stops propagation.
document.addEventListener("click", onClick, true);

// Console helper (development): run __amoreDebugSelection(), then click a
// Like/Pass button. Detected actions print via console.debug ("Verbose" level).
// If nothing prints, update the selectors above: Inspect the button, copy a
// stable attribute (prefer data-testid or aria-label), add it to the list.
window.__amoreDebugSelection = function () {
  console.log("[A-MORE] selection config for", location.hostname, ":", selectionConfig());
  console.log("Now click Like/Pass; matches log via console.debug (enable Verbose).");
};
