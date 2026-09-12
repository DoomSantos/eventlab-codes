/**
 * Private timing lab — rolling 24h board + live presence from timing API.
 * Main rows: best Clean lap per driver. Tap a driver to expand all their 24h laps.
 * Config: data/board-config.json → { "apiBase": "http://127.0.0.1:8787" }
 */
const CONFIG_URL = "data/board-config.json";

const trackFilter = document.getElementById("track-filter");
const classFilter = document.getElementById("class-filter");
const boardBody = document.getElementById("board-body");
const resultCount = document.getElementById("result-count");
const updatedAt = document.getElementById("updated-at");
const boardError = document.getElementById("board-error");
const liveBody = document.getElementById("live-body");
const liveEmpty = document.getElementById("live-empty");

let apiBase = "http://127.0.0.1:8787";
let pollSeconds = 5;
let entries = [];
let tracksCatalog = [];
/** @type {Set<string>} */
const expandedPlayers = new Set();

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
  if (entry.car) return entry.car;
  if (entry.car_ordinal != null) return `Car #${entry.car_ordinal}`;
  return "—";
}

async function loadConfig() {
  try {
    const res = await fetch(CONFIG_URL, { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    if (data.apiBase) apiBase = String(data.apiBase).replace(/\/$/, "");
    if (data.pollSeconds) pollSeconds = Number(data.pollSeconds) || 5;
  } catch {
    /* keep defaults */
  }
}

async function loadTracks() {
  try {
    const res = await fetch("data/tracks.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    tracksCatalog = (data.tracks || []).map((t) => t.name).filter(Boolean);
  } catch {
    tracksCatalog = [];
  }
}

function fillTrackFilter() {
  const fromData = uniqueSorted(entries.map((e) => e.track));
  const tracks = uniqueSorted([...tracksCatalog, ...fromData]);
  const previous = trackFilter.value;
  trackFilter.innerHTML = tracks
    .map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`)
    .join("");
  if (!tracks.length) {
    trackFilter.innerHTML = `<option value="">No tracks</option>`;
  } else if (previous && tracks.includes(previous)) {
    trackFilter.value = previous;
  }
  refreshClassFilter();
}

function refreshClassFilter() {
  const track = trackFilter.value;
  const classOptions = uniqueSorted(
    entries.filter((e) => e.track === track).map((e) => e.class_pi)
  );
  const previous = classFilter.value || "all";
  classFilter.innerHTML =
    `<option value="all">All</option>` +
    classOptions
      .map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`)
      .join("");
  classFilter.value = classOptions.includes(previous) ? previous : "all";
}

function filteredLaps() {
  const track = trackFilter.value;
  const classPi = classFilter.value;
  let rows = entries.filter((e) => e.track === track);
  if (classPi !== "all") {
    rows = rows.filter((e) => e.class_pi === classPi);
  }
  return rows;
}

/** Best lap per player for ranking; expand list is chronological by submitted_at. */
function bestPerPlayer(laps) {
  const byPlayer = new Map();
  for (const lap of laps) {
    const key = lap.player;
    if (!byPlayer.has(key)) byPlayer.set(key, []);
    byPlayer.get(key).push(lap);
  }
  const groups = [];
  for (const [player, playerLaps] of byPlayer) {
    const bySpeed = [...playerLaps].sort((a, b) => a.lap_time_s - b.lap_time_s);
    const chronological = [...playerLaps].sort((a, b) =>
      String(b.submitted_at || "").localeCompare(String(a.submitted_at || ""))
    );
    groups.push({
      player,
      best: bySpeed[0],
      laps: chronological,
    });
  }
  groups.sort((a, b) => a.best.lap_time_s - b.best.lap_time_s);
  return groups;
}

function formatSubmitted(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return escapeHtml(iso);
  return escapeHtml(date.toLocaleString());
}

function renderBoard() {
  const laps = filteredLaps();
  const groups = bestPerPlayer(laps);

  resultCount.textContent = groups.length
    ? `${groups.length} driver${groups.length === 1 ? "" : "s"} · best Clean lap · rolling 24h`
    : "No Clean times in the last 24h for this filter";

  if (!groups.length) {
    boardBody.innerHTML = `<tr><td colspan="5">No lap times yet for this selection.</td></tr>`;
    return;
  }

  boardBody.innerHTML = groups
    .map((group, index) => {
      const open = expandedPlayers.has(group.player);
      const best = group.best;
      const count = group.laps.length;
      const newest = [...group.laps].sort((a, b) =>
        String(b.submitted_at).localeCompare(String(a.submitted_at))
      )[0];
      const main = `<tr class="board-row ${open ? "is-open" : ""}" data-player="${escapeHtml(
        group.player
      )}" tabindex="0" role="button" aria-expanded="${open ? "true" : "false"}">
        <td>${index + 1}</td>
        <td>
          <span class="driver-name">${escapeHtml(group.player)}</span>
          <span class="lap-count muted">${count} lap${count === 1 ? "" : "s"}</span>
          <div class="muted board-updated">Best ${escapeHtml(best.lap_time)} · last in ${formatSubmitted(
            newest?.submitted_at
          )}</div>
        </td>
        <td class="time">${escapeHtml(best.lap_time)}</td>
        <td>${escapeHtml(best.class_pi)}</td>
        <td>${escapeHtml(carDisplay(best))}</td>
      </tr>`;

      if (!open) return main;

      const detailRows = group.laps
        .map((lap) => {
          const isBest = lap.id === best.id;
          return `<tr class="board-detail ${isBest ? "is-best" : ""}">
            <td></td>
            <td colspan="1" class="muted">${formatSubmitted(lap.submitted_at)}</td>
            <td class="time">${escapeHtml(lap.lap_time)}${
              isBest ? ' <span class="best-tag">Best</span>' : ""
            }</td>
            <td>${escapeHtml(lap.class_pi)}</td>
            <td>${escapeHtml(carDisplay(lap))}</td>
          </tr>`;
        })
        .join("");

      return (
        main +
        `<tr class="board-detail-head">
          <td></td>
          <td colspan="4" class="muted">All Clean laps (24h, newest first) — tap driver again to collapse</td>
        </tr>` +
        detailRows
      );
    })
    .join("");
}

function togglePlayer(player) {
  if (!player) return;
  if (expandedPlayers.has(player)) expandedPlayers.delete(player);
  else expandedPlayers.add(player);
  renderBoard();
}

function renderLive(racers) {
  if (!liveBody) return;
  if (!racers.length) {
    liveBody.innerHTML = "";
    if (liveEmpty) liveEmpty.hidden = false;
    return;
  }
  if (liveEmpty) liveEmpty.hidden = true;
  liveBody.innerHTML = racers
    .map(
      (r) => `<li>
        <strong>${escapeHtml(r.player)}</strong>
        <span class="muted"> · ${escapeHtml(r.track)} · ${escapeHtml(r.class_pi)}${
          r.car ? " · " + escapeHtml(r.car) : ""
        }</span>
      </li>`
    )
    .join("");
}

async function refresh() {
  try {
    const params = new URLSearchParams();
    if (trackFilter.value) params.set("track", trackFilter.value);
    params.set("limit", "500");
    const qs = params.toString() ? `?${params}` : "";
    const [boardRes, liveRes] = await Promise.all([
      fetch(`${apiBase}/v1/board${qs}`, { cache: "no-store" }),
      fetch(`${apiBase}/v1/live`, { cache: "no-store" }),
    ]);
    if (!boardRes.ok) throw new Error(`board HTTP ${boardRes.status}`);
    const board = await boardRes.json();
    entries = board.laps || [];
    fillTrackFilter();
    renderBoard();
    updatedAt.textContent = `API ${apiBase}`;
    boardError.hidden = true;

    if (liveRes.ok) {
      const live = await liveRes.json();
      renderLive(live.racers || []);
    }
  } catch (error) {
    console.error(error);
    boardError.hidden = false;
    boardError.innerHTML = `Timing API unreachable at <code>${escapeHtml(
      apiBase
    )}</code>. Start it with <code>python -m server</code>, then refresh.`;
    resultCount.textContent = "";
  }
}

boardBody.addEventListener("click", (event) => {
  const row = event.target.closest("tr.board-row");
  if (!row) return;
  togglePlayer(row.dataset.player);
});

boardBody.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const row = event.target.closest("tr.board-row");
  if (!row) return;
  event.preventDefault();
  togglePlayer(row.dataset.player);
});

trackFilter.addEventListener("change", () => {
  expandedPlayers.clear();
  refreshClassFilter();
  renderBoard();
  refresh();
});
classFilter.addEventListener("change", () => {
  expandedPlayers.clear();
  renderBoard();
});

(async function init() {
  await loadConfig();
  await loadTracks();
  fillTrackFilter();
  await refresh();
  setInterval(refresh, Math.max(3, pollSeconds) * 1000);
})();
