// Content script: read dry profile features off the page (section 2.2, input).
//
// Selectors differ per dating app and change often, so they live in one map you
// can adjust without touching the logic. Each entry returns an array of
// canonical feature tokens like "age:27-30" or "interest:travel".

const SELECTORS = {
  // TODO: tune these selectors for the live site DOM.
  age: '[data-testid="profile-age"], .profile-age',
  interests: '[data-testid="interest"], .interest-pill',
};

function ageBand(age) {
  const n = parseInt(age, 10);
  if (Number.isNaN(n)) return null;
  if (n <= 22) return "age:18-22";
  if (n <= 26) return "age:23-26";
  if (n <= 30) return "age:27-30";
  return "age:31+";
}

// Extract canonical profile tokens from the currently visible profile card.
function scrapeProfile() {
  const tokens = [];

  const ageEl = document.querySelector(SELECTORS.age);
  if (ageEl) {
    const band = ageBand(ageEl.textContent.trim());
    if (band) tokens.push(band);
  }

  document.querySelectorAll(SELECTORS.interests).forEach((el) => {
    const raw = el.textContent.trim().toLowerCase();
    if (raw) tokens.push(`interest:${raw}`);
  });

  return [...new Set(tokens)];
}

// Expose to overlay.js (same content-script world).
window.__amoreScrapeProfile = scrapeProfile;
