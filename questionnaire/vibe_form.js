// Vibe questionnaire client logic (section 4.2).
// Collects sliders + tag clouds + intent + free text and POSTs to /feedback.

const params = new URLSearchParams(location.search);
const API_BASE = params.get("api") || "http://localhost:8000";
const USER_ID = params.get("user") || "demo_user";
// The profile that was scraped at match time is passed through so the record
// links the dry features to this outcome.
const PROFILE = (params.get("profile") || "").split(",").filter(Boolean);

const TOPIC_BANK = [
  "קריירה ועבודה", "טיולים וחו\"ל", "משפחה וילדות", "תחביבים ופנאי",
  "פוליטיקה ואקטואליה", "שיחת חולין", "תוכניות לעתיד", "הראה התעניינות כלפיי",
];
const VIBE_BANK = [
  "מצחיק ומשעשע", "עמוק ופילוסופי", "מביך ומתוח", "ראיון עבודה",
  "קליל וזורם", "אינטלקטואלי", "ידידותי/חברי", "כבד/מעיק",
];

const selected = { topic: new Set(), vibe: new Set() };
let intent = null;

function buildTags(containerId, bank, bucket) {
  const root = document.getElementById(containerId);
  bank.forEach((tag) => {
    const b = document.createElement("button");
    b.textContent = tag;
    b.addEventListener("click", () => {
      if (bucket.has(tag)) {
        bucket.delete(tag);
        b.classList.remove("on");
      } else if (bucket.size < 3) {
        bucket.add(tag);
        b.classList.add("on");
      }
    });
    root.appendChild(b);
  });
}

buildTags("topic_tags", TOPIC_BANK, selected.topic);
buildTags("vibe_tags", VIBE_BANK, selected.vibe);

document.querySelectorAll(".intent button").forEach((b) => {
  b.addEventListener("click", () => {
    intent = b.dataset.intent;
    document.querySelectorAll(".intent button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
  });
});

function intentToBool(value) {
  if (value === "yes") return true;
  if (value === "no") return false;
  return null; // "maybe" or unanswered
}

document.getElementById("submit").addEventListener("click", async () => {
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

  const status = document.getElementById("status");
  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    status.style.color = "#2e9e5b";
    status.textContent = `תודה! נשמר. תגיות שזוהו: ${data.extracted_tags.join(", ") || "—"}`;
  } catch (e) {
    status.style.color = "#c0392b";
    status.textContent = "שגיאה בשליחה. ודא שהשרת רץ.";
  }
});
