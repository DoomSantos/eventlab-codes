/**
 * Dark custom menus for native <select>s. Windows keeps the opened
 * list white unless we replace it.
 */
(function () {
  const OPEN = "is-open";
  const CSS = `
.dsr-select { position: relative; }
.dsr-select-native {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
.dsr-select-btn {
  width: 100%; padding: 0.7rem 2.4rem 0.7rem 0.8rem; border-radius: 10px;
  border: 1px solid rgba(232,226,214,0.1); background-color: #1a1814;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='none' stroke='%239a9184' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round' d='M1.6 1.8 6 6.2 10.4 1.8'/></svg>");
  background-repeat: no-repeat; background-position: right 0.85rem center;
  color: #ece7dc; font: inherit; text-align: left; cursor: pointer;
}
.dsr-select-btn:hover, .dsr-select-btn:focus-visible {
  border-color: rgba(125,255,106,0.35); outline: none;
}
.dsr-select-menu {
  display: none; position: absolute; z-index: 50; left: 0; right: 0;
  top: calc(100% + 6px); max-height: 22rem; overflow: auto; padding: 0.35rem;
  border-radius: 10px; border: 1px solid rgba(232,226,214,0.1);
  background: #1a1814; box-shadow: 0 10px 28px rgba(0,0,0,0.35);
}
.dsr-select.is-open .dsr-select-menu {
  display: flex; flex-direction: column; gap: 2px;
}
.dsr-select-option {
  display: block; width: 100%; margin: 0; text-align: left; border: 0;
  border-radius: 8px; padding: 0.55rem 0.7rem; background: transparent;
  color: #ece7dc; font: inherit; cursor: pointer;
}
.dsr-select-option:hover, .dsr-select-option:focus-visible {
  background: #221f19; color: #ece7dc; outline: none;
}
.dsr-select-option[aria-selected="true"] {
  color: #7dff6a; background: rgba(125,255,106,0.12);
}`;

  function ensureStyles() {
    if (document.getElementById("dsr-select-css")) return;
    const style = document.createElement("style");
    style.id = "dsr-select-css";
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function closeAll(except) {
    document.querySelectorAll(".dsr-select." + OPEN).forEach((wrap) => {
      if (wrap !== except) setOpen(wrap, false);
    });
  }

  function setOpen(wrap, open) {
    wrap.classList.toggle(OPEN, open);
    const btn = wrap.querySelector(".dsr-select-btn");
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      const selected = wrap.querySelector('.dsr-select-option[aria-selected="true"]');
      if (selected) selected.focus();
      else {
        const first = wrap.querySelector(".dsr-select-option");
        if (first) first.focus();
      }
    }
  }

  function selectedLabel(select) {
    const opt = select.selectedOptions && select.selectedOptions[0];
    return opt ? opt.textContent : "";
  }

  function sync(wrap) {
    const select = wrap.querySelector("select");
    const btn = wrap.querySelector(".dsr-select-btn");
    const menu = wrap.querySelector(".dsr-select-menu");
    if (!select || !btn || !menu) return;
    btn.textContent = selectedLabel(select);
    menu.replaceChildren();
    [...select.options].forEach((opt) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "dsr-select-option";
      item.setAttribute("role", "option");
      item.dataset.value = opt.value;
      item.textContent = opt.textContent;
      item.disabled = Boolean(opt.disabled);
      if (opt.selected) item.setAttribute("aria-selected", "true");
      item.addEventListener("click", () => {
        if (select.value !== opt.value) {
          select.value = opt.value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
        }
        sync(wrap);
        setOpen(wrap, false);
        btn.focus();
      });
      menu.appendChild(item);
    });
  }

  function enhance(select) {
    if (select.closest(".dsr-select")) {
      sync(select.closest(".dsr-select"));
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "dsr-select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.classList.add("dsr-select-native");
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dsr-select-btn";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    if (select.id) btn.id = `${select.id}-button`;
    const label = select.id
      ? document.querySelector(`label[for="${select.id}"]`)
      : null;
    if (label) btn.setAttribute("aria-label", label.textContent.trim());

    const menu = document.createElement("div");
    menu.className = "dsr-select-menu";
    menu.setAttribute("role", "listbox");

    wrap.appendChild(btn);
    wrap.appendChild(menu);

    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = !wrap.classList.contains(OPEN);
      closeAll(wrap);
      setOpen(wrap, open);
    });
    btn.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        closeAll(wrap);
        setOpen(wrap, true);
      }
    });
    menu.addEventListener("keydown", (event) => {
      const items = [...menu.querySelectorAll(".dsr-select-option:not(:disabled)")];
      const index = items.indexOf(document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(wrap, false);
        btn.focus();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        items[Math.min(items.length - 1, index + 1)]?.focus();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        items[Math.max(0, index - 1)]?.focus();
      } else if (event.key === "Home") {
        event.preventDefault();
        items[0]?.focus();
      } else if (event.key === "End") {
        event.preventDefault();
        items[items.length - 1]?.focus();
      }
    });

    select.addEventListener("change", () => sync(wrap));
    new MutationObserver(() => sync(wrap)).observe(select, {
      childList: true,
      subtree: true,
      attributes: true,
    });
    sync(wrap);
  }

  function boot() {
    ensureStyles();
    document.querySelectorAll("select").forEach(enhance);
    new MutationObserver(() => {
      document.querySelectorAll("select").forEach((el) => {
        if (!el.closest(".dsr-select")) enhance(el);
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
  }

  window.dsrEnhanceSelects = function (root) {
    (root || document).querySelectorAll("select").forEach(enhance);
  };

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".dsr-select")) closeAll();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAll();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
