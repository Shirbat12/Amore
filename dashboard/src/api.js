// Tiny fetch helper.
// Frontend routes:
//   /dashboard/                  -> all questionnaire responses / demo user
//   /dashboard/Yael.c40@gmail.com -> specific user

const _params = new URLSearchParams(window.location.search);

const API_BASE = (_params.get("api") || "http://127.0.0.1:8000").replace(/\/$/, "");

function getUserIdFromPath() {
  const pathParts = window.location.pathname.split("/").filter(Boolean);

  // Expected:
  // /dashboard
  // /dashboard/Yael.c40@gmail.com
  const dashboardIndex = pathParts.indexOf("dashboard");

  if (dashboardIndex !== -1 && pathParts[dashboardIndex + 1]) {
    return decodeURIComponent(pathParts[dashboardIndex + 1]).trim();
  }

  return null;
}

const USER_ID =
  (_params.get("user") || getUserIdFromPath() || "demo_user").trim();

async function fetchInsights() {
  const encodedUserId = encodeURIComponent(USER_ID);
  const url = `${API_BASE}/insights/${encodedUserId}`;

  console.log("Fetching insights from:", url);

  const res = await fetch(url);

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`insights failed: ${res.status} ${errorText}`);
  }

  const data = await res.json();

  console.log("Insights data:", data);

  return data;
}