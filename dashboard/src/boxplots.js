function emptyNote() {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = "עדיין אין מספיק נתונים לגרף הזה 💫";
  return p;
}

// VAS distribution per character tag, drawn as real box-and-whisker plots using
// the chartjs-chart-boxplot plugin (it registers a "boxplot" chart type with
// Chart.js). The plugin computes quartiles, median, whiskers and outliers from
// the raw VAS arrays the backend already sends ({ tag: [v1, v2, ...] }), so we
// feed those arrays straight in — no manual stats needed (section 2.3.4).
//
// If the plugin failed to load (e.g. the CDN was blocked), we fall back to a
// simple min/mean/max range so the dashboard still renders something useful.
function renderBoxplots(byTag) {
  const el = document.getElementById("boxplots");
  const tags = byTag ? Object.keys(byTag) : [];
  if (!tags.length) { el.replaceWith(emptyNote()); return; }

  if (boxplotTypeAvailable()) {
    renderRealBoxplots(el, byTag, tags);
  } else {
    renderRangeFallback(el, byTag, tags);
  }
}

// True only when the boxplot plugin has registered its chart type with Chart.js.
// Chart.registry.getController throws if the type is unknown, hence the try.
function boxplotTypeAvailable() {
  try {
    return !!Chart.registry.getController("boxplot");
  } catch (e) {
    return false;
  }
}

// Real box-and-whisker plot: pass the raw VAS arrays; the plugin does the stats.
function renderRealBoxplots(el, byTag, tags) {
  new Chart(el, {
    type: "boxplot",
    data: {
      labels: tags,
      datasets: [{
        label: "התפלגות VAS",
        data: tags.map((t) => byTag[t]),       // one array of values per tag
        backgroundColor: "rgba(193,110,127,.30)",
        borderColor: "#c16e7f",
        borderWidth: 1,
        itemRadius: 2,                          // draw each date as a small dot
        outlierBackgroundColor: "#a0506a",      // flag outlier dates in deep rose
      }],
    },
    options: {
      scales: { y: { min: 0, max: 100 } },
      plugins: { legend: { display: false } },
    },
  });
}

// Fallback (plugin unavailable): min/mean/max range with a mean marker — the
// original approximation, kept only so a CDN failure never blanks the chart.
function renderRangeFallback(el, byTag, tags) {
  const stats = tags.map((t) => {
    const v = byTag[t];
    const mean = v.reduce((a, b) => a + b, 0) / v.length;
    return { min: Math.min(...v), max: Math.max(...v), mean };
  });

  new Chart(el, {
    type: "bar",
    data: {
      labels: tags,
      datasets: [
        { label: "טווח VAS", data: stats.map((s) => [s.min, s.max]),
          backgroundColor: "rgba(193,110,127,.30)" },
        { label: "ממוצע", type: "scatter",
          data: stats.map((s, i) => ({ x: i, y: s.mean })),
          backgroundColor: "#a0506a" },
      ],
    },
    options: { scales: { y: { min: 0, max: 100 } } },
  });
}
