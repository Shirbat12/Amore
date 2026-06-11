// Predicted vs actual VAS — the visual form of prediction accuracy (2.3.4).
function renderScatter(points) {
  const el = document.getElementById("scatter");
  if (!points || !points.length) { el.replaceWith(emptyNote()); return; }
  new Chart(el, {
    type: "scatter",
    data: {
      datasets: [{
        label: "תחזית מול בפועל",
        data: points.map((p) => ({ x: p.predicted, y: p.actual })),
        backgroundColor: "#2e6fb7",
      }],
    },
    options: {
      scales: {
        x: { min: 0, max: 100, title: { display: true, text: "חזוי" } },
        y: { min: 0, max: 100, title: { display: true, text: "בפועל" } },
      },
    },
  });
}
