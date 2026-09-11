const DATA_URL = "data/leaderboard.json";

const trackFilter = document.getElementById("track-filter");
const classFilter = document.getElementById("class-filter");
const integrityFilter = document.getElementById("integrity-filter");
const boardBody = document.getElementById("board-body");
const resultCount = document.getElementById("result-count");
const updatedAt = document.getElementById("updated-at");
const boardError = document.getElementById("board-error");

let entries = [];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true })
  );
}

function carDisplay(entry) {
  return entry.car || (entry.car_ordinal != null ? `Car #${entry.car_ordinal}` : "—");
}

function integrityOf(entry) {
  const raw = (entry.integrity || "").toLowerCase();
  if (raw === "rewound" || entry.suspect_rewind) return "Rewound";
  return "Clean";
}

function fillFilters() {
  const tracks = uniqueSorted(entries.map((e) => e.track));
  trackFilter.innerHTML = tracks
    .map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`)
    .join("");

  if (!tracks.length) {
    trackFilter.innerHTML = `<option value="">No tracks yet</option>`;
  }

  refreshClassFilter();
}

function refreshClassFilter() {
  const track = trackFilter.value;
  const classOptions = uniqueSorted(
    entries.filter((e) => e.track === track).map((e) => e.class_pi || `${e.class} ${e.pi}`)
  );

  const previous = classFilter.value || "all";
  classFilter.innerHTML =
    `<option value="all">All</option>` +
    classOptions
      .map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`)
      .join("");

  classFilter.value = classOptions.includes(previous) ? previous : "all";
}

function render() {
  const track = trackFilter.value;
  const classPi = classFilter.value;
  const integrity = (integrityFilter?.value || "all").toLowerCase();

  let rows = entries.filter((e) => e.track === track);
  if (classPi !== "all") {
    rows = rows.filter((e) => (e.class_pi || `${e.class} ${e.pi}`) === classPi);
  }
  if (integrity === "clean") {
    rows = rows.filter((e) => integrityOf(e) === "Clean");
  } else if (integrity === "rewound") {
    rows = rows.filter((e) => integrityOf(e) === "Rewound");
  }

  rows = [...rows].sort((a, b) => a.lap_time_s - b.lap_time_s);

  resultCount.textContent = rows.length
    ? `${rows.length} result${rows.length === 1 ? "" : "s"}`
    : "No times for this filter yet";

  if (!rows.length) {
    boardBody.innerHTML = `<tr><td colspan="6">No lap times yet for this selection.</td></tr>`;
    return;
  }

  boardBody.innerHTML = rows
    .map((entry, index) => {
      const label = entry.class_pi || `${entry.class} ${entry.pi}`;
      const integrityLabel = integrityOf(entry);
      const integrityClass = integrityLabel.toLowerCase();
      return `<tr>
        <td>${index + 1}</td>
        <td>${escapeHtml(entry.player)}</td>
        <td class="time">${escapeHtml(entry.lap_time)}</td>
        <td>${escapeHtml(label)}</td>
        <td>${escapeHtml(carDisplay(entry))}</td>
        <td><span class="integrity-pill ${integrityClass}">${escapeHtml(integrityLabel)}</span></td>
      </tr>`;
    })
    .join("");
}

async function init() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    entries = data.entries || [];
    if (data.updated_at) {
      const date = new Date(data.updated_at);
      updatedAt.textContent = Number.isNaN(date.getTime())
        ? ""
        : `Updated ${date.toLocaleString()}`;
    }
    fillFilters();
    render();
  } catch (error) {
    console.error(error);
    boardError.hidden = false;
    resultCount.textContent = "";
  }
}

trackFilter.addEventListener("change", () => {
  refreshClassFilter();
  render();
});
classFilter.addEventListener("change", render);
integrityFilter?.addEventListener("change", render);

init();
