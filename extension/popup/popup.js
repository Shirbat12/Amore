// Popup: edit settings and link to the dashboard.
const $ = (id) => document.getElementById(id);

async function load() {
  const s = await chrome.storage.local.get(["apiBase", "userId", "enabled"]);
  $("apiBase").value = s.apiBase || "http://localhost:8000";
  $("userId").value = s.userId || "demo_user";
  $("enabled").checked = s.enabled !== false;
}

$("save").addEventListener("click", async () => {
  await chrome.storage.local.set({
    apiBase: $("apiBase").value.trim(),
    userId: $("userId").value.trim(),
    enabled: $("enabled").checked,
  });
  $("status").textContent = "Saved.";
});

$("dashboard").addEventListener("click", (e) => {
  e.preventDefault();
  const base = $("apiBase").value.trim() || "http://localhost:8000";
  const user = $("userId").value.trim() || "demo_user";
  // The static dashboard reads ?api= and ?user= query params.
  chrome.tabs.create({
    url: `http://localhost:5500/dashboard/index.html?api=${encodeURIComponent(base)}&user=${encodeURIComponent(user)}`,
  });
});

load();
