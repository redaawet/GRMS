(function () {
  const storageKey = "grmsSidebarState";

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

  function toggleItems(items, expanded, state, key) {
    if (!items) return;

    if (expanded) {
      items.classList.add("active");
      state[key] = "expanded";
    } else {
      items.classList.remove("active");
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
      toggleItems(items, initialExpanded, state, key);

      header.addEventListener("click", () => {
        const isExpanded = items.classList.toggle("active");
        state[key] = isExpanded ? "expanded" : "collapsed";
        saveState(state);
      });
    });

    saveState(state);
  }

  document.addEventListener("DOMContentLoaded", initSidebar);
})();
