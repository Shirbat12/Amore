// Popup: user identity + quick links. API/web URLs are built-in defaults.
const $ = (id) => document.getElementById(id);

async function load() {
  const s = await chrome.storage.local.get(["userId", "enabled"]);
  $("userId").value = s.userId || AMORE_DEFAULTS.USER_ID;
  $("enabled").checked = s.enabled !== false;
}

$("save").addEventListener("click", async () => {
  await chrome.storage.local.set({
    userId: $("userId").value.trim() || AMORE_DEFAULTS.USER_ID,
    enabled: $("enabled").checked,
  });
  $("status").textContent = "נשמר ✓";
  setTimeout(() => { $("status").textContent = ""; }, 2000);
});

$("dashboard").addEventListener("click", (e) => {
  e.preventDefault();
  const user = $("userId").value.trim() || AMORE_DEFAULTS.USER_ID;
  const q = new URLSearchParams({ user });
  chrome.tabs.create({
    url: `${AMORE_DEFAULTS.WEB_BASE}/dashboard/index.html?${q.toString()}`,
  });
});

load();
