(function () {
  const storageKey = "grmsSidebarState";
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  function loadState() {
    try {
      return JSON.parse(localStorage.getItem(storageKey)) || {};
    } catch (err) {
      return {};
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch (err) {
      // ignore persistence errors
    }
  }

  function setCollapsed(items, animate) {
    if (!items) return;

    const startHeight = items.scrollHeight;

    if (prefersReducedMotion || !animate) {
      items.style.maxHeight = "0px";
      items.style.display = "none";
      return;
    }

    items.style.maxHeight = `${startHeight}px`;
    requestAnimationFrame(() => {
      items.style.maxHeight = "0px";
    });

    items.addEventListener(
      "transitionend",
      () => {
        items.style.display = "none";
      },
      { once: true }
    );
  }

  function setExpanded(items, animate) {
    if (!items) return;

    items.style.display = "block";
    const targetHeight = items.scrollHeight;

    if (prefersReducedMotion || !animate) {
      items.style.maxHeight = `${targetHeight}px`;
      return;
    }

    items.style.maxHeight = "0px";
    requestAnimationFrame(() => {
      items.style.maxHeight = `${targetHeight}px`;
    });
  }

  function applyState(items, expanded, state, key, animate) {
    if (!items) return;

    items.style.overflow = "hidden";
    items.style.transition = "max-height 220ms ease";

    if (expanded) {
      items.classList.add("active");
      setExpanded(items, animate);
      state[key] = "expanded";
    } else {
      items.classList.remove("active");
      setCollapsed(items, animate);
      state[key] = "collapsed";
    }
  }

  function markActiveLinks() {
    const currentPath = window.location.pathname;
    const links = document.querySelectorAll(".sidebar-item");

    links.forEach((link) => {
      const href = link.getAttribute("href");

      if (!href) return;

      const linkPath = new URL(href, window.location.origin).pathname;

      if (currentPath.startsWith(linkPath)) {
        link.classList.add("active");
        const parent = link.closest(".sidebar-items");

        if (parent) {
          parent.classList.add("active");
        }
      }
    });
  }

  function initSidebar() {
    const state = loadState();

    markActiveLinks();

    const groups = document.querySelectorAll(".sidebar-group");

    groups.forEach((group, index) => {
      const header = group.querySelector(".sidebar-group-header");
      const items = group.querySelector(".sidebar-items");
      const key = group.dataset.group || header?.dataset.group || String(index);

      if (!header || !items) {
        return;
      }

      const hasActiveItem = items.querySelector(".sidebar-item.active") !== null;
      const initialExpanded = state[key] === "expanded" || hasActiveItem;
      applyState(items, initialExpanded, state, key, false);

      header.addEventListener("click", () => {
        const isExpanded = items.classList.contains("active");
        applyState(items, !isExpanded, state, key, true);
        saveState(state);
      });
    });

    saveState(state);
  }

  document.addEventListener("DOMContentLoaded", initSidebar);
})();
