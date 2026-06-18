// Content script: read dry profile features off the page (section 2.2, input).
//
// Turns the profile currently on screen into canonical feature tokens like
// "age:27-30" or "interest:travel". Those tokens are the only thing the backend
// sees, and the rest of the system (model, insights, KPI) speaks English
// "category:value" tokens — so this scraper also TRANSLATES OkCupid's Hebrew,
// pipe-separated profile text into that vocabulary via small mapping tables.
//
// OkCupid is a React single-page app with scrambled class names, but its
// profile-detail rows carry stable, semantic class names
// (.matchprofile-details-text, .card-content-header__location, etc.) which we
// anchor on. To adapt after a redesign, update SELECTORS below and the mapping
// tables; use __amoreDebugScrape() in the console to check the result.

// ---------------------------------------------------------------------------
// Per-site selectors. First match wins; keep the most stable selector first.
// ---------------------------------------------------------------------------
const SITES = {
  "okcupid.com": {
    // The profile card currently shown in the Double Take feed.
    root: [".quickmatch-profiledetails", ".profile-content", "main"],
    // "31 • Afridar" lives here — age is the leading number.
    ageLine: [".card-content-header__location"],
    // The four basics rows: gender/orientation, height/body, background, wiw.
    detailRows: [".matchprofile-details-text"],
    // Free-text self-summary essays.
    essays: [".profile-essay-contents"],
  },
};

// ---------------------------------------------------------------------------
// Hebrew -> canonical token mapping. Substring match (case/space insensitive on
// the Hebrew side). Extend freely — this is the front-end twin of closed_tags.
// ---------------------------------------------------------------------------
const VALUE_MAP = [
  // gender
  ["גבר", "gender:male"], ["אישה", "gender:female"],
  // orientation
  ["סטרייט", "orientation:straight"], ["הומו", "orientation:gay"],
  ["ביסקסואל", "orientation:bisexual"], ["לסבית", "orientation:lesbian"],
  // relationship style / status
  ["מונוגמי", "relationship:monogamous"], ["פוליאמורי", "relationship:nonmonogamous"],
  ["רווק", "status:single"], ["גרוש", "status:divorced"],
  // body
  ["בכושר", "body:fit"], ["רזה", "body:slim"], ["ממוצע", "body:average"],
  ["שרירי", "body:athletic"], ["מלא", "body:curvy"],
  // language
  ["אנגלית", "language:english"], ["עברית", "language:hebrew"],
  ["צרפתית", "language:french"], ["רוסית", "language:russian"], ["ערבית", "language:arabic"],
  // what they're looking for
  ["דייטינג לטווח ארוך", "wants:longterm"], ["קשר רציני", "wants:longterm"],
  ["חברים", "wants:friends"], ["משהו קליל", "wants:casual"],
];

// Essay keyword -> interest token. Scanned over the free-text summary.
const INTEREST_MAP = [
  ["גלישה", "interest:surfing"], ["גלים", "interest:surfing"], ["חוף", "interest:beach"],
  ["טיול", "interest:travel"], ["לטייל", "interest:travel"], ["עולם", "interest:travel"],
  ["כלב", "interest:dogs"], ["חתול", "interest:cats"], ["בעלי חיים", "interest:animals"],
  ["ספורט", "interest:sports"], ["כושר", "interest:fitness"], ["ריצה", "interest:running"],
  ["מוזיקה", "interest:music"], ["בישול", "interest:cooking"], ["אוכל", "interest:food"],
  ["קולנוע", "interest:movies"], ["סרטים", "interest:movies"], ["ספרים", "interest:reading"],
  ["אמנות", "interest:art"], ["צילום", "interest:photography"], ["טבע", "interest:nature"],
  ["יוגה", "interest:yoga"], ["מדיטציה", "interest:meditation"], ["משפחה", "interest:family"],
];

// ---------------------------------------------------------------------------
// DOM helpers — all null-safe so a missing field never throws.
// ---------------------------------------------------------------------------
function siteConfig() {
  const host = location.hostname.replace(/^www\./, "");
  const key = Object.keys(SITES).find((d) => host.endsWith(d));
  return key ? SITES[key] : null;
}

function firstMatch(selectors, scope = document) {
  for (const sel of selectors) {
    const el = scope.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function allMatches(selectors, scope = document) {
  const found = new Set();
  for (const sel of selectors) scope.querySelectorAll(sel).forEach((el) => found.add(el));
  return [...found];
}

// Map an age number to one of the four bands the pipeline expects.
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

// Age: the leading number of the "31 • Afridar" header line.
function extractAge(cfg, root) {
  const el = firstMatch(cfg.ageLine, root);
  if (!el) return [];
  const m = (el.textContent || "").match(/\d{2}/); // first 2-digit number
  const band = m ? ageBand(m[0]) : null;
  return band ? [band] : [];
}

// Basics rows: split each "A | B | C" line on the pipe and map every piece.
function extractDetails(cfg, root) {
  const tokens = [];
  for (const el of allMatches(cfg.detailRows, root)) {
    const parts = (el.textContent || "").split("|");
    for (const part of parts) {
      // a single part may hold several values, e.g. "מונוגמי.ת (רווק.ה)"
      for (const [needle, token] of VALUE_MAP) {
        if (part.includes(needle)) tokens.push(token);
      }
    }
  }
  return tokens;
}

// Essay: scan the free-text summary for interest keywords.
function extractInterests(cfg, root) {
  const tokens = [];
  for (const el of allMatches(cfg.essays, root)) {
    const text = el.textContent || "";
    for (const [needle, token] of INTEREST_MAP) {
      if (text.includes(needle)) tokens.push(token);
    }
  }
  return tokens;
}

// ---------------------------------------------------------------------------
// Public entry point used by overlay.js (same content-script world).
// ---------------------------------------------------------------------------
function scrapeProfile() {
  const cfg = siteConfig();
  if (!cfg) return [];
  const root = firstMatch(cfg.root) || document.body;
  const tokens = [
    ...extractAge(cfg, root),
    ...extractDetails(cfg, root),
    ...extractInterests(cfg, root),
  ];
  return [...new Set(tokens)]; // dedupe; order is not significant downstream
}

window.__amoreScrapeProfile = scrapeProfile;

// ---------------------------------------------------------------------------
// Console debug helper (development only).
// Run __amoreDebugScrape() in the page console (make sure the context dropdown
// is set to "top", not an iframe). If a field is empty, Inspect it on the page,
// copy a stable class/attribute, and add it to SELECTORS — or add a missing
// Hebrew phrase to VALUE_MAP / INTEREST_MAP.
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
    details: extractDetails(cfg, root),
    interests: extractInterests(cfg, root),
    tokens: scrapeProfile(),
  };
  console.table(report.tokens.map((t) => ({ token: t })));
  console.log("[A-MORE] scrape report:", report);
  return report;
};