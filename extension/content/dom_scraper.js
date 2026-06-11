// Content script: read dry profile features off the page (section 2.2, input).
//
// Goal: turn the profile currently on screen into a small list of canonical
// feature tokens like "age:27-30" or "interest:travel". Those tokens are the
// only thing the backend sees, so the scraper just has to be reliable.
//
// Dating sites are React single-page apps. Their CSS class names are scrambled
// and change often, so we NEVER rely on one class. Instead every field has a
// list of candidate selectors that are tried in order, plus a text-based
// fallback. To adapt to a site redesign you only edit the SELECTORS map below
// (and use the console helper at the bottom to find the right selectors fast).

// ---------------------------------------------------------------------------
// Per-site selector config. Keyed by hostname so more sites can be added later.
// Each field holds an ORDERED list of selectors: the first one that matches the
// visible profile wins. Put the most stable selector (a data-testid, an aria
// label, a semantic tag) first and looser class-based ones last.
// ---------------------------------------------------------------------------
const SITES = {
  "okcupid.com": {
    // The card of the profile currently being shown in the Double Take feed.
    // Scoping every query to this root avoids reading the wrong profile when
    // several cards are mounted in the DOM at once.
    root: [
      '[data-testid="doubletake-profile"]',
      '[class*="userprofile"]',
      "main",
    ],
    // Age usually appears in the profile header next to the name.
    age: [
      '[data-testid="profile-age"]',
      '[class*="age"]',
    ],
    // Interests / passions are rendered as a row of pills or tags.
    interests: [
      '[data-testid="interest"]',
      '[class*="interest"] li',
      '[class*="passions"] li',
      '[class*="tag"]',
    ],
    // Optional: city/region shown under the name.
    location: [
      '[data-testid="profile-location"]',
      '[class*="location"]',
    ],
  },
};

// Pick the config for the current host (handles www. and other subdomains).
function siteConfig() {
  const host = location.hostname.replace(/^www\./, "");
  const key = Object.keys(SITES).find((domain) => host.endsWith(domain));
  return key ? SITES[key] : null;
}

// ---------------------------------------------------------------------------
// Small DOM helpers — every one is null-safe so a missing field never throws.
// ---------------------------------------------------------------------------

// Return the first element matching any selector in the list, or null.
function firstMatch(selectors, scope = document) {
  for (const sel of selectors) {
    const el = scope.querySelector(sel);
    if (el) return el;
  }
  return null;
}

// Return all elements matching any selector in the list (deduplicated).
function allMatches(selectors, scope = document) {
  const found = new Set();
  for (const sel of selectors) {
    scope.querySelectorAll(sel).forEach((el) => found.add(el));
  }
  return [...found];
}

// Clean a raw label into a token-safe value: lowercase, trimmed, spaces -> "_".
function canonical(raw) {
  return raw.trim().toLowerCase().replace(/\s+/g, "_").replace(/[^\w:+-]/g, "");
}

// Map a numeric age to one of the four bands the pipeline expects.
function ageBand(age) {
  const n = parseInt(age, 10);
  if (Number.isNaN(n)) return null;
  if (n <= 22) return "age:18-22";
  if (n <= 26) return "age:23-26";
  if (n <= 30) return "age:27-30";
  return "age:31+";
}

// ---------------------------------------------------------------------------
// Field extractors. Each returns zero or more canonical tokens.
// ---------------------------------------------------------------------------

// Age: try the dedicated selector first; if that fails, fall back to scanning
// the card text for a standalone 2-digit number (typical "Name, 27" header).
function extractAge(cfg, root) {
  const el = firstMatch(cfg.age, root);
  if (el) {
    const band = ageBand(el.textContent);
    if (band) return [band];
  }
  const headerText = (root.textContent || "").slice(0, 200); // header is near the top
  const m = headerText.match(/\b(1[89]|[2-9]\d)\b/); // 18..99
  const band = m ? ageBand(m[1]) : null;
  return band ? [band] : [];
}

// Interests: read every pill and emit one "interest:<value>" token per item.
function extractInterests(cfg, root) {
  const tokens = [];
  for (const el of allMatches(cfg.interests, root)) {
    const value = canonical(el.textContent || "");
    if (value) tokens.push(`interest:${value}`);
  }
  return tokens;
}

// Location: a single "location:<city>" token, if present.
function extractLocation(cfg, root) {
  const el = firstMatch(cfg.location || [], root);
  const value = el ? canonical(el.textContent || "") : "";
  return value ? [`location:${value}`] : [];
}

// ---------------------------------------------------------------------------
// Public entry point used by overlay.js (same content-script world).
// ---------------------------------------------------------------------------

// Extract canonical profile tokens from the currently visible profile card.
function scrapeProfile() {
  const cfg = siteConfig();
  if (!cfg) return []; // unsupported site -> nothing to score

  const root = firstMatch(cfg.root) || document.body;
  const tokens = [
    ...extractAge(cfg, root),
    ...extractInterests(cfg, root),
    ...extractLocation(cfg, root),
  ];
  return [...new Set(tokens)]; // dedupe; order is not significant downstream
}

// Expose to overlay.js.
window.__amoreScrapeProfile = scrapeProfile;

// ---------------------------------------------------------------------------
// Console debug helper (development only).
// Open the dating site, log in, then run  __amoreDebugScrape()  in DevTools to
// see what each field resolved to. Use it to fix the SELECTORS above when the
// site changes: if a field is empty, right-click the value on the page ->
// Inspect, copy a stable attribute, and add it to the matching list.
// ---------------------------------------------------------------------------
window.__amoreDebugScrape = function () {
  const cfg = siteConfig();
  if (!cfg) {
    console.warn("[A-MORE] no config for this host:", location.hostname);
    return;
  }
  const root = firstMatch(cfg.root) || document.body;
  const report = {
    host: location.hostname,
    rootMatched: !!firstMatch(cfg.root),
    age: extractAge(cfg, root),
    interests: extractInterests(cfg, root),
    location: extractLocation(cfg, root),
    tokens: scrapeProfile(),
  };
  console.table(report.tokens.map((t) => ({ token: t })));
  console.log("[A-MORE] scrape report:", report);
  return report;
};
