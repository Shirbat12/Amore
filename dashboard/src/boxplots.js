// VAS distribution per character tag. Chart.js core has no boxplot type, so we
// show min / mean / max as a floating-bar range with a mean marker (2.3.4).
function renderBoxplots(byTag) {
  const el = document.getElementById("boxplots");
  const tags = byTag ? Object.keys(byTag) : [];
  if (!tags.length) { el.replaceWith(emptyNote()); return; }

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
          backgroundColor: "rgba(46,111,183,.35)" },
        { label: "ממוצע", type: "scatter",
          data: stats.map((s, i) => ({ x: i, y: s.mean })),
          backgroundColor: "#c0392b" },
      ],
    },
    options: { scales: { y: { min: 0, max: 100 } } },
  });
}
