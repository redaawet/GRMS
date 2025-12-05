(function () {
  const THEME_KEY = "grms-theme";
  const GROUP_KEY = "grms-sidebar-groups";

  function applyTheme(theme) {
    const root = document.documentElement;
    const normalized = theme === "dark" ? "dark" : "light";
    root.setAttribute("data-grms-theme", normalized);
  }

  function loadTheme() {
    const saved = window.localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") {
      applyTheme(saved);
    } else {
      // Default: light
      applyTheme("light");
    }
  }

  function setupThemeToggle() {
    const btn = document.getElementById("grms-theme-toggle");
    if (!btn) return;

    btn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-grms-theme") || "light";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      window.localStorage.setItem(THEME_KEY, next);
    });
  }

  function loadGroupState() {
    try {
      const raw = window.localStorage.getItem(GROUP_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function saveGroupState(state) {
    try {
      window.localStorage.setItem(GROUP_KEY, JSON.stringify(state));
    } catch (e) {
      // ignore
    }
  }

  function setupAccordions() {
    const state = loadGroupState();
    document.querySelectorAll(".grms-sidebar-group").forEach((group) => {
      const id = group.getAttribute("data-group-id") || "";
      const header = group.querySelector(".grms-group-header");
      if (!header) return;

      // Apply initial open/closed state (default: open)
      if (state[id] === false) {
        group.classList.add("is-collapsed");
      }

      header.addEventListener("click", () => {
        const collapsed = group.classList.toggle("is-collapsed");
        state[id] = !collapsed;
        saveGroupState(state);
      });
    });
  }

  function highlightActiveLink() {
    const path = window.location.pathname;
    let bestMatch = null;
    let bestLen = 0;

    document.querySelectorAll(".grms-menu-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;
      if (path === href || path.startsWith(href)) {
        if (href.length > bestLen) {
          bestLen = href.length;
          bestMatch = link;
        }
      }
    });

    if (bestMatch) {
      bestMatch.classList.add("is-active");
      const group = bestMatch.closest(".grms-sidebar-group");
      if (group) {
        group.classList.remove("is-collapsed");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadTheme();
    setupThemeToggle();
    setupAccordions();
    highlightActiveLink();
  });
})();
