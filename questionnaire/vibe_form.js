// Vibe questionnaire client logic (section 4.2).
// Collects sliders + tag clouds + intent + free text and POSTs to /feedback.

const params = new URLSearchParams(location.search);
const API_BASE = params.get("api") || "http://localhost:8000";
const USER_ID = params.get("user") || "demo_user";
// The profile scraped at match time is passed through so the saved record links
// the dry features to this outcome.
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

// Live numeric readout: show each slider's current value and keep it in sync.
SLIDERS.forEach((id) => {
  const el = document.getElementById(id);
  const out = document.getElementById(`${id}_val`);
  const sync = () => { out.textContent = el.value; };
  el.addEventListener("input", sync);
  sync();
});

// Build a tag cloud where up to 3 pills can be selected, with a live counter.
function buildTags(containerId, counterId, bank, bucket) {
  const root = document.getElementById(containerId);
  const counter = document.getElementById(counterId);
  const updateCounter = () => { counter.textContent = `נבחרו ${bucket.size} מתוך 3`; };
  bank.forEach((tag) => {
    const b = document.createElement("button");
    b.className = "pill";
    b.textContent = tag;
    b.addEventListener("click", () => {
      if (bucket.has(tag)) {
        bucket.delete(tag);
        b.classList.remove("on");
      } else if (bucket.size < 3) {
        bucket.add(tag);
        b.classList.add("on");
      }
      updateCounter();
    });
    root.appendChild(b);
  });
  updateCounter();
}

buildTags("topic_tags", "topic_counter", TOPIC_BANK, selected.topic);
buildTags("vibe_tags", "vibe_counter", VIBE_BANK, selected.vibe);

// Second-date intent: one choice highlighted at a time.
document.querySelectorAll(".intent-row button").forEach((b) => {
  b.addEventListener("click", () => {
    intent = b.dataset.intent;
    document.querySelectorAll(".intent-row button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
  });
});

function intentToBool(value) {
  if (value === "yes") return true;
  if (value === "no") return false;
  return null; // "maybe" or unanswered
}

const status = document.getElementById("status");
const submitBtn = document.getElementById("submit");

submitBtn.addEventListener("click", async () => {
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
  status.className = "";
  status.textContent = "שולחת…";
  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    status.className = "ok";
    status.textContent = `תודה! נשמר. תגיות שזוהו: ${data.extracted_tags.join(", ") || "—"}`;
  } catch (e) {
    status.className = "err";
    status.textContent = "שגיאה בשליחה. ודאי שהשרת רץ.";
    submitBtn.disabled = false;
  }
});
