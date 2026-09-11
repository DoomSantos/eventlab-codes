const DATA_URL = "data/leaderboard.json";

const trackFilter = document.getElementById("track-filter");
const classFilter = document.getElementById("class-filter");
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

  let rows = entries.filter((e) => e.track === track);
  if (classPi !== "all") {
    rows = rows.filter((e) => (e.class_pi || `${e.class} ${e.pi}`) === classPi);
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
      const integrity = entry.integrity || (entry.suspect_rewind ? "Suspect" : "Clean");
      return `<tr>
        <td>${index + 1}</td>
        <td>${escapeHtml(entry.player)}</td>
        <td class="time">${escapeHtml(entry.lap_time)}</td>
        <td>${escapeHtml(label)}</td>
        <td>${escapeHtml(carDisplay(entry))}</td>
        <td>${escapeHtml(integrity)}</td>
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

init();
