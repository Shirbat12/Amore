// Correlation "heatmap" rendered as a diverging horizontal bar chart:
// rho drives the bar length/color, q-value drives opacity (section 2.3.4).
function renderHeatmap(rows) {
  const el = document.getElementById("heatmap");
  if (!rows || !rows.length) { el.replaceWith(emptyNote()); return; }
  const labels = rows.map((r) => r.feature.replace(/^profile:|^trait:/, ""));
  const data = rows.map((r) => r.rho);
  const colors = rows.map((r) => {
    const alpha = Math.max(0.2, 1 - r.q);            // significant -> opaque
    return r.rho >= 0
      ? `rgba(46,158,91,${alpha})`
      : `rgba(192,57,43,${alpha})`;
  });
  new Chart(el, {
    type: "bar",
    data: { labels, datasets: [{ label: "Spearman ρ", data, backgroundColor: colors }] },
    options: { indexAxis: "y", scales: { x: { min: -1, max: 1 } },
               plugins: { legend: { display: false } } },
  });
}

function emptyNote() {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = "אין עדיין מספיק נתונים.";
  return p;
}
