const DATA_URL = "data/tracks.json";

const icons = {
  car: "🏎️",
  robot: "🤖",
  driver: "👤",
};

const trackList = document.getElementById("track-list");
const loadError = document.getElementById("load-error");
const toast = document.getElementById("toast");
let toastTimer;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function showToast(message) {
  toast.hidden = false;
  toast.textContent = message;
  requestAnimationFrame(() => toast.classList.add("is-visible"));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 1600);
}

async function copyCode(code) {
  try {
    await navigator.clipboard.writeText(code);
    showToast(`Copied ${code}`);
  } catch {
    const field = document.createElement("textarea");
    field.value = code;
    field.setAttribute("readonly", "");
    field.style.position = "absolute";
    field.style.left = "-9999px";
    document.body.appendChild(field);
    field.select();
    document.execCommand("copy");
    field.remove();
    showToast(`Copied ${code}`);
  }
}

function renderEvents(events = []) {
  if (!events.length) {
    return `<p class="coming-soon">Coming soon!</p>`;
  }

  const items = events
    .map(
      (event) => `
      <li>
        <button class="code-btn" type="button" data-code="${escapeHtml(event.code)}">
          <span class="laps">${escapeHtml(event.laps)} Laps</span>
          <span class="code">${escapeHtml(event.code)}</span>
          <span class="hint">tap to copy</span>
        </button>
      </li>`
    )
    .join("");

  return `<ul class="events">${items}</ul>`;
}

function renderVariant(variant) {
  const content = variant.comingSoon
    ? `<p class="coming-soon">Coming soon!</p>`
    : renderEvents(variant.events);

  return `
    <article class="variant">
      <button class="variant-toggle" type="button" aria-expanded="false">
        <span class="chevron" aria-hidden="true"></span>
        <span class="variant-icon" aria-hidden="true">${icons[variant.icon] || ""}</span>
        <span class="variant-label">${escapeHtml(variant.label)}</span>
      </button>
      <div class="variant-body">
        <div class="inner">${content}</div>
      </div>
    </article>`;
}

function renderTrack(track) {
  const variants = (track.variants || []).map(renderVariant).join("");

  return `
    <article class="track">
      <button class="track-toggle" type="button" aria-expanded="false">
        <span class="chevron" aria-hidden="true"></span>
        <span class="track-icon" aria-hidden="true">${icons.car}</span>
        <span class="track-name">${escapeHtml(track.name)}</span>
      </button>
      <div class="track-body">
        <div class="inner">${variants}</div>
      </div>
    </article>`;
}

function wireAccordions(root) {
  root.querySelectorAll(".track-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const track = button.closest(".track");
      const open = track.classList.toggle("is-open");
      button.setAttribute("aria-expanded", String(open));
    });
  });

  root.querySelectorAll(".variant-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const variant = button.closest(".variant");
      const open = variant.classList.toggle("is-open");
      button.setAttribute("aria-expanded", String(open));
    });
  });

  root.querySelectorAll(".code-btn").forEach((button) => {
    button.addEventListener("click", () => copyCode(button.dataset.code));
  });
}

function applyMeta(data) {
  if (data.title) {
    document.title = `${data.title} · ${data.instagram?.handle || "DoomSantos Racing"}`;
  }

  if (data.tagline) {
    document.getElementById("page-tagline").textContent = data.tagline;
  }

  const link = document.getElementById("instagram-link");
  if (data.instagram?.handle) {
    link.textContent = data.instagram.handle;
  }
  if (data.instagram?.url) {
    link.href = data.instagram.url;
  }
}

async function init() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    applyMeta(data);
    trackList.innerHTML = (data.tracks || []).map(renderTrack).join("");
    wireAccordions(trackList);
  } catch (error) {
    console.error(error);
    loadError.hidden = false;
  }
}

init();
