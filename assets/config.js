// Single source of truth for the web front-ends (dashboard + questionnaire) of
// where the backend lives and which user is being viewed. Defaults to the local
// dev server; either value can be overridden per-page via the URL query string
// (?api=...&user=...). Load this BEFORE any script that calls the API.
//
// Note: the Chrome extension does NOT use this file — it runs in its own context
// and keeps its own defaults in extension/background/service_worker.js (settable
// from the popup). Both default to the same URL below.
(function () {
  const DEFAULT_API_BASE = "http://localhost:8000";
  const DEFAULT_USER_ID = "demo_user";
  const params = new URLSearchParams(location.search);
  window.AMORE_CONFIG = {
    apiBase: params.get("api") || DEFAULT_API_BASE,
    userId: params.get("user") || DEFAULT_USER_ID,
  };
})();
