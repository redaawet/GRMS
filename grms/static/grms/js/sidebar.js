(function () {
  if (window.GRMS_SIDEBAR_LOADED) return;
  window.GRMS_SIDEBAR_LOADED = true;

  function setExpanded(group, expanded) {
    group.classList.toggle("is-collapsed", !expanded);
    const header = group.querySelector(".sg-header");
    const content = group.querySelector(".sg-content");
    if (header) header.setAttribute("aria-expanded", expanded ? "true" : "false");
    if (content) content.hidden = !expanded;
  }

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

  function enforceSingleOpen(groups) {
    const activeGroup = groups.find((group) => group.classList.contains("has-active"));
    const target = activeGroup || groups[0];
    groups.forEach((group) => setExpanded(group, group === target));
  }

  function handleSearch(groups) {
    const searchInput = document.getElementById("sidebar-search");
    if (!searchInput) return;

    searchInput.addEventListener("input", (event) => {
      const term = event.target.value.trim().toLowerCase();
      const hasTerm = term.length > 0;
      let firstMatch = null;

      groups.forEach((group) => {
        const subgroupBlocks = group.querySelectorAll(".sidebar-subgroup");
        const directLinks = group.querySelectorAll(":scope > .sg-content > .sg-list > .ss-link");
        let groupHasMatch = false;

        const evaluateLink = (link) => {
          const match = !hasTerm || link.textContent.toLowerCase().includes(term);
          link.style.display = match ? "" : "none";
          if (match) groupHasMatch = true;
        };

        subgroupBlocks.forEach((sub) => {
          let subHasMatch = false;
          sub.querySelectorAll(".ss-link").forEach((link) => {
            const match = !hasTerm || link.textContent.toLowerCase().includes(term);
            link.style.display = match ? "" : "none";
            if (match) subHasMatch = true;
          });
          sub.style.display = subHasMatch || !hasTerm ? "" : "none";
          if (subHasMatch) groupHasMatch = true;
        });

        directLinks.forEach(evaluateLink);

        group.style.display = !hasTerm || groupHasMatch ? "" : "none";

        if (hasTerm) {
          setExpanded(group, groupHasMatch);
          if (!firstMatch && groupHasMatch) firstMatch = group;
        }
      });

      if (!hasTerm) {
        groups.forEach((group) => {
          group.querySelectorAll(".ss-link").forEach((link) => (link.style.display = ""));
          group.querySelectorAll(".sidebar-subgroup").forEach((sub) => (sub.style.display = ""));
          group.style.display = "";
        });
        enforceSingleOpen(groups);
      } else if (!firstMatch) {
        groups.forEach((group) => setExpanded(group, false));
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("popup")) return;
    const sidebar = document.getElementById("grms-sidebar");
    if (!sidebar) return;

    markActiveLinks();

    const groups = Array.from(sidebar.querySelectorAll(".sidebar-group"));
    if (!groups.length) return;

    groups.forEach((group, index) => {
      const header = group.querySelector(".sg-header");
      if (!header) return;
      header.addEventListener("click", () => {
        const isOpen = !group.classList.contains("is-collapsed");
        groups.forEach((other) => setExpanded(other, other === group ? !isOpen : false));
      });
    });

    enforceSingleOpen(groups);
    handleSearch(groups);
  });
})();
