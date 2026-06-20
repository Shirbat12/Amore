// Single source of truth for the web front-ends (dashboard + questionnaire).
(function () {
  const DEFAULT_API_BASE = "http://localhost:8000";
  const DEFAULT_USER_ID = "demo_user";
  const params = new URLSearchParams(location.search);
  window.AMORE_CONFIG = {
    apiBase: (params.get("api") || DEFAULT_API_BASE).replace(/\/$/, ""),
    userId: params.get("user") || DEFAULT_USER_ID,
  };
})();
