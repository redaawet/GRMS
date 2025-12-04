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
      // ignore
    }
  }

  function initGroups() {
    const state = loadState();
    document.querySelectorAll(".grms-sidebar-group").forEach((group) => {
      const key = group.dataset.group;
      if (state[key] === "collapsed") {
        group.classList.add("is-collapsed");
      }

      const header = group.querySelector(".grms-sidebar-group-header");
      if (!header) {
        return;
      }

      header.addEventListener("click", () => {
        group.classList.toggle("is-collapsed");
        const updated = group.classList.contains("is-collapsed")
          ? "collapsed"
          : "expanded";
        state[key] = updated;
        saveState(state);
      });
    });
  }

  function initMobileToggle() {
    const toggle = document.getElementById("grms-sidebar-toggle");
    const sidebar = document.getElementById("grms-sidebar");
    if (!toggle || !sidebar) {
      return;
    }

    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("is-open");
    });

    sidebar.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 992px)").matches) {
          sidebar.classList.remove("is-open");
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initGroups();
    initMobileToggle();
  });
})();
