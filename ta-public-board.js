/**
 * Unlisted public Time Attack boards (Live Timing + Leaderboards).
 * How To Use / site nav stay unchanged. Config: data/board-config.json
 */
const CONFIG_URL = "data/board-config.json";
const CLASS_LETTERS = ["X", "R", "S2", "S1", "A", "B", "C", "D"];
const WINDOWS = [
  { value: "all", label: "Anytime" },
  { value: "today", label: "Today" },
  { value: "7d", label: "This Week" },
  { value: "30d", label: "This Month" },
  { value: "365d", label: "This Year" },
];

const page = document.body.dataset.taPage || "live";
const trackFilter = document.getElementById("track-filter");
const classFilter = document.getElementById("class-filter");
const windowFilter = document.getElementById("window-filter");
const boardBody = document.getElementById("board-body");
const resultCount = document.getElementById("result-count");
const updatedAt = document.getElementById("updated-at");
const boardError = document.getElementById("board-error");
const liveBody = document.getElementById("live-body");
const liveEmpty = document.getElementById("live-empty");
const sessionClock = document.getElementById("session-clock");

let apiBase = "https://dsr-eventlab-timing-production.up.railway.app";
let pollSeconds = 5;
let entries = [];
let tracksCatalog = [];
let sessionEndsAt = "";
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
  const names = [];
  try {
    const res = await fetch("data/tracks.json", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      names.push(...(data.tracks || []).map((t) => t.name).filter(Boolean));
    }
  } catch {
    /* ignore */
  }
  try {
    const res = await fetch("data/time-attack-codes.json", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      for (const event of data.events || []) {
        if (event.track) names.push(String(event.track));
      }
    }
  } catch {
    /* ignore — file may be unpublished locally */
  }
  tracksCatalog = uniqueSorted(names);
}

function fillWindowFilter() {
  if (!windowFilter) return;
  const previous = windowFilter.value || "all";
  windowFilter.innerHTML = WINDOWS.map(
    (w) => `<option value="${w.value}">${w.label}</option>`
  ).join("");
  windowFilter.value = WINDOWS.some((w) => w.value === previous) ? previous : "all";
}

function fillClassFilter() {
  if (!classFilter) return;
  const previous = classFilter.value || "all";
  classFilter.innerHTML =
    `<option value="all">All classes</option>` +
    CLASS_LETTERS.map((c) => `<option value="${c}">${c}</option>`).join("");
  classFilter.value = CLASS_LETTERS.includes(previous) ? previous : "all";
}

function fillTrackFilter() {
  const fromData = uniqueSorted(entries.map((e) => e.track));
  const tracks = uniqueSorted([...tracksCatalog, ...fromData]);
  const previous = trackFilter.value;
  trackFilter.innerHTML =
    `<option value="all">All tracks</option>` +
    tracks.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join("");
  if (previous && (previous === "all" || tracks.includes(previous))) {
    trackFilter.value = previous;
  } else {
    trackFilter.value = "all";
  }
}

function formatSubmitted(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return escapeHtml(iso);
  return escapeHtml(
    date.toLocaleString("en-AU", { timeZone: "Australia/Sydney" })
  );
}

function formatCountdown(endsAt) {
  if (!endsAt) return "";
  const end = new Date(endsAt);
  if (Number.isNaN(end.getTime())) return "";
  const ms = end.getTime() - Date.now();
  if (ms <= 0) return "New AEST day — refresh";
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  return `${h}h ${m}m left in today’s session (AEST)`;
}

function tickClock() {
  if (!sessionClock) return;
  sessionClock.textContent = formatCountdown(sessionEndsAt);
}

function bestPerPlayer(laps) {
  const byPlayer = new Map();
  for (const lap of laps) {
    const key = `${lap.player}\t${lap.track}`;
    if (!byPlayer.has(key)) byPlayer.set(key, []);
    byPlayer.get(key).push(lap);
  }
  const groups = [];
  for (const [key, playerLaps] of byPlayer) {
    const player = key.split("\t")[0];
    const bySpeed = [...playerLaps].sort((a, b) => a.lap_time_s - b.lap_time_s);
    const chronological = [...playerLaps].sort((a, b) =>
      String(b.submitted_at || "").localeCompare(String(a.submitted_at || ""))
    );
    groups.push({
      player,
      track: bySpeed[0].track,
      best: bySpeed[0],
      laps: chronological,
    });
  }
  groups.sort((a, b) => a.best.lap_time_s - b.best.lap_time_s);
  return groups;
}

function renderLiveBoard() {
  const groups = bestPerPlayer(entries);
  resultCount.textContent = groups.length
    ? `${groups.length} driver${groups.length === 1 ? "" : "s"} · best Clean Time Attack · today (AEST)`
    : "No Clean Time Attack times today";

  if (!groups.length) {
    boardBody.innerHTML = `<tr><td colspan="6">No one on a Time Attack event right now.</td></tr>`;
    return;
  }

  boardBody.innerHTML = groups
    .map((group, index) => {
      const open = expandedPlayers.has(`${group.player}\t${group.track}`);
      const best = group.best;
      const count = group.laps.length;
      const key = `${group.player}\t${group.track}`;
      const main = `<tr class="board-row ${open ? "is-open" : ""}" data-player="${escapeHtml(
        key
      )}" tabindex="0" role="button" aria-expanded="${open ? "true" : "false"}">
        <td>${index + 1}</td>
        <td>
          <span class="driver-name">${escapeHtml(group.player)}</span>
          <span class="lap-count muted">${count} lap${count === 1 ? "" : "s"}</span>
        </td>
        <td>${escapeHtml(group.track)}</td>
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
            <td class="muted">${formatSubmitted(lap.submitted_at)}</td>
            <td></td>
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
          <td colspan="5" class="muted">Today’s Clean laps (newest first) — tap driver again to collapse</td>
        </tr>` +
        detailRows
      );
    })
    .join("");
}

function renderLeaderboard() {
  resultCount.textContent = entries.length
    ? `${entries.length} best Clean Time Attack lap${entries.length === 1 ? "" : "s"}`
    : "No Clean Time Attack times for this filter";

  if (!entries.length) {
    boardBody.innerHTML = `<tr><td colspan="6">No times yet for this selection.</td></tr>`;
    return;
  }

  boardBody.innerHTML = entries
    .map(
      (lap, index) => `<tr>
        <td>${index + 1}</td>
        <td class="driver-name">${escapeHtml(lap.player)}</td>
        <td>${escapeHtml(lap.track)}</td>
        <td class="time">${escapeHtml(lap.lap_time)}</td>
        <td>${escapeHtml(lap.class_pi)}</td>
        <td>${escapeHtml(carDisplay(lap))}</td>
      </tr>`
    )
    .join("");
}

function renderBoard() {
  if (page === "leaderboard") renderLeaderboard();
  else renderLiveBoard();
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
    if (liveEmpty) {
      liveEmpty.hidden = false;
      liveEmpty.textContent = "No one on a Time Attack event right now.";
    }
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

function endpoint() {
  if (page === "leaderboard") return "leaderboard";
  return "board";
}

function currentWindow() {
  if (page === "leaderboard") return windowFilter?.value || "all";
  return "today";
}

async function refresh() {
  try {
    const params = new URLSearchParams();
    params.set("limit", page === "leaderboard" ? "200" : "500");
    params.set("window", currentWindow());
    params.set("mode", "time_attack");
    if (trackFilter.value && trackFilter.value !== "all") {
      params.set("track", trackFilter.value);
    }
    if (classFilter?.value && classFilter.value !== "all") {
      params.set("class", classFilter.value);
    }
    const qs = `?${params}`;
    const fetches = [fetch(`${apiBase}/v1/${endpoint()}${qs}`, { cache: "no-store" })];
    if (page === "live") {
      fetches.push(fetch(`${apiBase}/v1/live`, { cache: "no-store" }));
    }
    const [boardRes, liveRes] = await Promise.all(fetches);
    if (!boardRes.ok) throw new Error(`board HTTP ${boardRes.status}`);
    const board = await boardRes.json();
    entries = board.laps || [];
    sessionEndsAt = (board.session && board.session.ends_at) || "";
    fillTrackFilter();
    renderBoard();
    tickClock();
    updatedAt.textContent = "";
    boardError.hidden = true;

    if (liveRes && liveRes.ok) {
      const live = await liveRes.json();
      renderLive(live.racers || []);
    }
  } catch (error) {
    console.error(error);
    boardError.hidden = false;
    boardError.textContent =
      "Timing board is unreachable right now. Times will show here once the API is back.";
    resultCount.textContent = "";
  }
}

if (boardBody) {
  boardBody.addEventListener("click", (event) => {
    if (page !== "live") return;
    const row = event.target.closest("tr.board-row");
    if (!row) return;
    togglePlayer(row.dataset.player);
  });
  boardBody.addEventListener("keydown", (event) => {
    if (page !== "live") return;
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = event.target.closest("tr.board-row");
    if (!row) return;
    event.preventDefault();
    togglePlayer(row.dataset.player);
  });
}

trackFilter.addEventListener("change", () => {
  expandedPlayers.clear();
  refresh();
});
if (classFilter) {
  classFilter.addEventListener("change", () => {
    expandedPlayers.clear();
    refresh();
  });
}
if (windowFilter) {
  windowFilter.addEventListener("change", () => {
    expandedPlayers.clear();
    refresh();
  });
}

(async function init() {
  fillClassFilter();
  fillWindowFilter();
  await loadConfig();
  await loadTracks();
  fillTrackFilter();
  await refresh();
  setInterval(refresh, Math.max(3, pollSeconds) * 1000);
  if (sessionClock) setInterval(tickClock, 30000);
})();
