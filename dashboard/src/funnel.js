// First dates -> second-date intent (section 2.3.4).
function renderFunnel(f) {
  const el = document.getElementById("funnel");
  if (!f || !f.first_dates) { el.replaceWith(emptyNote()); return; }
  new Chart(el, {
    type: "bar",
    data: {
      labels: ["דייטים ראשונים", "דייט שני (כן)", "אולי"],
      datasets: [{
        data: [f.first_dates, f.second_dates, f.maybe],
        backgroundColor: ["#2e6fb7", "#2e9e5b", "#d9a300"],
      }],
    },
    options: { plugins: { legend: { display: false } } },
  });
}
