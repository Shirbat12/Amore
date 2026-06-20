// Popup: edit settings and open dashboard / questionnaire.
const $ = (id) => document.getElementById(id);

function readSettings() {
  return {
    api: $("apiBase").value.trim() || "http://localhost:8000",
    web: $("webBase").value.trim() || "http://localhost:5500",
    user: $("userId").value.trim() || "demo_user",
  };
}

async function load() {
  const s = await chrome.storage.local.get(["apiBase", "webBase", "userId", "enabled"]);
  $("apiBase").value = s.apiBase || "http://localhost:8000";
  $("webBase").value = s.webBase || "http://localhost:5500";
  $("userId").value = s.userId || "demo_user";
  $("enabled").checked = s.enabled !== false;
}

$("save").addEventListener("click", async () => {
  const { api, web, user } = readSettings();
  await chrome.storage.local.set({
    apiBase: api,
    webBase: web,
    userId: user,
    enabled: $("enabled").checked,
  });
  $("status").textContent = "נשמר ✓";
  setTimeout(() => { $("status").textContent = ""; }, 2000);
});

function openPage(path, extraParams) {
  const { api, web, user } = readSettings();
  const q = new URLSearchParams({ api, user, ...extraParams });
  chrome.tabs.create({ url: `${web}${path}?${q.toString()}` });
}

$("dashboard").addEventListener("click", (e) => {
  e.preventDefault();
  openPage("/dashboard/index.html");
});

$("questionnaire").addEventListener("click", (e) => {
  e.preventDefault();
  // No profile tokens from the popup — user fills after a date manually.
  openPage("/questionnaire/vibe_form.html");
});

load();
