(function () {
  if (window.GRMS_SIDEBAR_LOADED) return;
  window.GRMS_SIDEBAR_LOADED = true;

  function markActiveLinks() {
    const currentPath = window.location.pathname;
    document.querySelectorAll("#grms-sidebar .ss-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;
      const linkPath = new URL(href, window.location.origin).pathname;
      if (currentPath.startsWith(linkPath)) {
        link.classList.add("active");
        const group = link.closest(".sidebar-group");
        const subgroup = link.closest(".sidebar-subgroup");
        if (group) group.classList.add("has-active");
        if (subgroup) subgroup.classList.add("has-active");
      }
    });
  }

  function handleSearch() {
    const searchInput = document.getElementById("sidebar-search");
    if (!searchInput) return;

    searchInput.addEventListener("input", (event) => {
      const term = event.target.value.trim().toLowerCase();
      const groups = document.querySelectorAll("#grms-sidebar .sidebar-group");

      groups.forEach((group) => {
        let groupHasMatch = false;
        const subgroupBlocks = group.querySelectorAll(".sidebar-subgroup");
        const directLinks = group.querySelectorAll(":scope > .sg-content > .sg-list > .ss-link");

        if (subgroupBlocks.length) {
          subgroupBlocks.forEach((sub) => {
            let subHasMatch = false;
            sub.querySelectorAll(".ss-link").forEach((link) => {
              const match = !term || link.textContent.toLowerCase().includes(term);
              link.style.display = match ? "" : "none";
              if (match) subHasMatch = true;
            });

            sub.style.display = subHasMatch || !term ? "" : "none";
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
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("popup")) return;
    const sidebar = document.getElementById("grms-sidebar");
    if (!sidebar) return;

    markActiveLinks();
    handleSearch();
  });
})();
