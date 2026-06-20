function emptyNote() {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = "עדיין אין מספיק נתונים לגרף הזה 💫";
  return p;
}

// First dates -> second-date intent (section 2.3.4), in the brand palette.
function renderFunnel(f) {
  const el = document.getElementById("funnel");
  if (!f || !f.first_dates) { el.replaceWith(emptyNote()); return; }
  new Chart(el, {
    type: "bar",
    data: {
      labels: ["דייטים ראשונים", "דייט שני (כן)", "אולי"],
      datasets: [{
        data: [f.first_dates, f.second_dates, f.maybe],
        backgroundColor: ["#c16e7f", "#c2a15a", "#d9b8c0"],
      }],
    },
    options: { plugins: { legend: { display: false } } },
  });
}
