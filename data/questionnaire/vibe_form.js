// Vibe questionnaire — multi-step wizard (section 4.2).
// One question per screen with a progress bar, smooth step transitions, and a
// final thank-you screen. Collects sliders + tag clouds + intent + free text and
// POSTs to /feedback on submit.

const params = new URLSearchParams(location.search);
// Base URL + user come from the shared config (assets/config.js).
const API_BASE = window.AMORE_CONFIG.apiBase;
const USER_ID = window.AMORE_CONFIG.userId;
// The profile scraped at match time is passed through (questionnaire-specific)
// so the saved record links the dry features to this outcome.
const PROFILE = (params.get("profile") || "").split(",").filter(Boolean);

const TOPIC_BANK = [
  "קריירה ועבודה", "טיולים וחו\\\"ל", "משפחה וילדות", "תחביבים ופנאי",
  "פוליטיקה ואקטואליה", "שיחת חולין", "תוכניות לעתיד", "הראה התעניינות כלפיי",
];
const VIBE_BANK = [
  "מצחיק ומשעשע", "עמוק ופילוסופי", "מביך ומתוח", "ראיון עבודה",
  "קליל וזורם", "אינטלקטואלי", "ידידותי/חברי", "כבד/מעיק",
];

const SLIDERS = ["interest_flow", "attraction", "reality_match", "comfort"];
const selected = { topic: new Set(), vibe: new Set() };
let intent = null;

// ---- step engine ----------------------------------------------------------
const steps = [...document.querySelectorAll(".step")];
const progress = document.getElementById("progress");
let current = 0;

function show(index) {
  current = Math.max(0, Math.min(steps.length - 1, index));
  steps.forEach((s, i) => s.classList.toggle("is-active", i === current));
  // Fill the bar proportionally; welcome = 0%, last step = 100%.
  progress.style.width = `${Math.round((current / (steps.length - 1)) * 100)}%`;
  window.scrollTo({ top: 0 });
}

function next() { if (current < steps.length - 1) show(current + 1); }
function back() { if (current > 0) show(current - 1); }

// Wire every navigation button by its data-action.
document.querySelectorAll("[data-action]").forEach((btn) => {
  const action = btn.dataset.action;
  btn.addEventListener("click", () => {
    if (action === "start" || action === "next") next();
    else if (action === "back") back();
    else if (action === "submit") submit();
  });
});

// Enter advances to the next step — except inside the free-text box, where
// Enter should add a newline.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  if (document.activeElement && document.activeElement.tagName === "TEXTAREA") return;
  const active = steps[current];
  const primary = active.querySelector('[data-action="next"], [data-action="start"], [data-action="submit"]');
  if (primary) { e.preventDefault(); primary.click(); }
});

// ---- live slider readouts -------------------------------------------------
SLIDERS.forEach((id) => {
  const el = document.getElementById(id);
  const out = document.getElementById(`${id}_val`);
  const sync = () => { out.textContent = el.value; };
  el.addEventListener("input", sync);
  sync();
});

// ---- tag clouds (up to 3, with a live counter) ----------------------------
function buildTags(containerId, counterId, bank, bucket) {
  const root = document.getElementById(containerId);
  const counter = document.getElementById(counterId);
  const updateCounter = () => { counter.textContent = `נבחרו ${bucket.size} מתוך 3`; };
  bank.forEach((tag) => {
    const b = document.createElement("button");
    b.className = "pill";
    b.textContent = tag;
    b.addEventListener("click", () => {
      if (bucket.has(tag)) { bucket.delete(tag); b.classList.remove("on"); }
      else if (bucket.size < 3) { bucket.add(tag); b.classList.add("on"); }
      updateCounter();
    });
    root.appendChild(b);
  });
  updateCounter();
}

buildTags("topic_tags", "topic_counter", TOPIC_BANK, selected.topic);
buildTags("vibe_tags", "vibe_counter", VIBE_BANK, selected.vibe);

// ---- second-date intent (single choice, auto-advances) --------------------
document.querySelectorAll(".intent-col button").forEach((b) => {
  b.addEventListener("click", () => {
    intent = b.dataset.intent;
    document.querySelectorAll(".intent-col button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    setTimeout(next, 260); // brief beat so the selection registers visually
  });
});

function intentToBool(value) {
  if (value === "yes") return true;
  if (value === "no") return false;
  return null; // "maybe" or unanswered
}

// ---- submit ---------------------------------------------------------------
async function submit() {
  const submitBtn = document.getElementById("submit");
  const slider = (id) => Number(document.getElementById(id).value);
  const payload = {
    user_id: USER_ID,
    profile: PROFILE,
    vas_scores: {
      interest_flow: slider("interest_flow"),
      attraction: slider("attraction"),
      reality_match: slider("reality_match"),
      comfort: slider("comfort"),
    },
    topic_tags: [...selected.topic],
    vibe_tags: [...selected.vibe],
    second_date: intentToBool(intent),
    free_text: document.getElementById("free_text").value.trim(),
  };

  submitBtn.disabled = true;
  submitBtn.textContent = "שולחת…";
  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const tags = (data.extracted_tags || []).join(", ");
    document.getElementById("done_msg").innerHTML = tags
      ? `הדייט נשמר. תגיות שזיהינו: <span class="tags-found">${tags}</span>`
      : "הדייט נשמר. נדייק לך את ההמלצות.";
    next(); // move to the thank-you screen
  } catch (e) {
    submitBtn.disabled = false;
    submitBtn.textContent = "שליחה";
    alert("שגיאה בשליחה. ודאי שהשרת רץ.");
  }
}

show(0);
