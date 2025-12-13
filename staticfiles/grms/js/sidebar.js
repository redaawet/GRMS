(function () {
  if (window.GRMS_SIDEBAR_LOADED) return;
  window.GRMS_SIDEBAR_LOADED = true;

  const COLLAPSE_KEY = "grmsSidebarCollapsed";

  function markActiveLinks() {
    const currentPath = window.location.pathname;
    let activeGroup = null;
    let activeSubgroup = null;

    document.querySelectorAll("#grms-sidebar .ss-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;
      const linkPath = new URL(href, window.location.origin).pathname;
      if (currentPath.startsWith(linkPath)) {
        link.classList.add("active");
        const group = link.closest("details.sidebar-group");
        const subgroup = link.closest("details.sidebar-subgroup");
        if (group) activeGroup = group;
        if (subgroup) activeSubgroup = subgroup;
      }
    });

    if (activeGroup) activeGroup.open = true;
    if (activeSubgroup) activeSubgroup.open = true;

    return { activeGroup, activeSubgroup };
  }

  function handleSearch() {
    const searchInput = document.getElementById("sidebar-search");
    if (!searchInput) return;

    searchInput.addEventListener("input", (event) => {
      const term = event.target.value.trim().toLowerCase();
      const groups = document.querySelectorAll("#grms-sidebar details.sidebar-group");

      groups.forEach((group) => {
        let groupHasMatch = false;
        const subgroups = group.querySelectorAll("details.sidebar-subgroup");
        const directLinks = group.querySelectorAll(":scope > .sg-content > .ss-link");

        if (subgroups.length) {
          subgroups.forEach((sub) => {
            let subHasMatch = false;
            sub.querySelectorAll(".ss-link").forEach((link) => {
              const match = !term || link.textContent.toLowerCase().includes(term);
              link.style.display = match ? "" : "none";
              if (match) subHasMatch = true;
            });

            sub.style.display = subHasMatch || !term ? "" : "none";
            if (term) sub.open = subHasMatch;
            if (subHasMatch) groupHasMatch = true;
          });
        }

        if (directLinks.length) {
          let directMatch = false;
          directLinks.forEach((link) => {
            const match = !term || link.textContent.toLowerCase().includes(term);
            link.style.display = match ? "" : "none";
            if (match) directMatch = true;
          });

          if (directMatch) groupHasMatch = true;
        }

        group.style.display = groupHasMatch || !term ? "" : "none";
        if (term) group.open = groupHasMatch;
      });
    });
  }

  function handleCollapseToggle() {
    const toggle = document.getElementById("sidebar-toggle");
    if (!toggle) return;

    const applyCollapsed = (collapsed) => {
      document.body.classList.toggle("sidebar-collapsed", collapsed);
      toggle.textContent = collapsed ? "▸" : "▾";
    };

    applyCollapsed(localStorage.getItem(COLLAPSE_KEY) === "true");

    toggle.addEventListener("click", () => {
      const collapsed = !document.body.classList.contains("sidebar-collapsed");
      applyCollapsed(collapsed);
      localStorage.setItem(COLLAPSE_KEY, String(collapsed));
    });
  }

  function enforceSingleOpenGroup() {
    const groups = Array.from(
      document.querySelectorAll("#grms-sidebar details.sidebar-group")
    );

    groups.forEach((group) => {
      group.addEventListener("toggle", () => {
        if (!group.open) return;
        groups.forEach((other) => {
          if (other !== group) {
            other.open = false;
          }
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("popup")) return;
    const sidebar = document.getElementById("grms-sidebar");
    if (!sidebar) return;

    markActiveLinks();
    handleSearch();
    handleCollapseToggle();
    enforceSingleOpenGroup();
  });
})();
