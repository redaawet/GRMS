(function () {
  if (window.GRMS_SIDEBAR_LOADED) return;
  window.GRMS_SIDEBAR_LOADED = true;

  const ACTIVE_GROUP_KEY = "grmsSidebarActiveGroup";
  const COLLAPSE_KEY = "grmsSidebarCollapsed";

  function setMaxHeight(content, open) {
    if (!content) return;
    content.style.maxHeight = open ? `${content.scrollHeight}px` : "0px";
  }

  function openGroup(group, saveState = true) {
    const allGroups = document.querySelectorAll("#grms-sidebar .sidebar-group");
    allGroups.forEach((other) => {
      if (other !== group) {
        other.classList.remove("open");
        setMaxHeight(other.querySelector(":scope > .sg-content"), false);
        closeAllSubgroups(other);
      }
    });

    group.classList.add("open");
    ensureDefaultSubgroup(group);
    setMaxHeight(group.querySelector(":scope > .sg-content"), true);
    if (saveState) {
      const key = group.getAttribute("data-group") || "";
      localStorage.setItem(ACTIVE_GROUP_KEY, key);
    }
  }

  function closeGroup(group) {
    group.classList.remove("open");
    setMaxHeight(group.querySelector(":scope > .sg-content"), false);
    localStorage.removeItem(ACTIVE_GROUP_KEY);
  }

  function openSubgroup(subgroup) {
    const siblings = subgroup.parentElement?.querySelectorAll(".sidebar-subgroup") || [];
    siblings.forEach((sib) => {
      if (sib !== subgroup) {
        sib.classList.remove("open");
        const list = sib.querySelector(":scope > .ss-list");
        if (list) list.style.display = "none";
      }
    });

    subgroup.classList.add("open");
    const list = subgroup.querySelector(":scope > .ss-list");
    if (list) list.style.display = "flex";
  }

  function closeAllSubgroups(group) {
    const subgroups = group.querySelectorAll(".sidebar-subgroup");
    subgroups.forEach((sub) => {
      sub.classList.remove("open");
      const list = sub.querySelector(":scope > .ss-list");
      if (list) list.style.display = "none";
    });
  }

  function ensureDefaultSubgroup(group) {
    const openSub = group.querySelector(".sidebar-subgroup.open");
    if (openSub) return;
    const first = group.querySelector(".sidebar-subgroup");
    if (first) openSubgroup(first);
  }

  function activateSingleSubgroups() {
    document.querySelectorAll("#grms-sidebar .sidebar-group").forEach((group) => {
      const subgroups = group.querySelectorAll(":scope > .sg-content > .sidebar-subgroup");
      if (subgroups.length === 1) {
        const single = subgroups[0];
        group.classList.add("single-subgroup");
        single.classList.add("no-toggle");
        openSubgroup(single);
        setMaxHeight(group.querySelector(":scope > .sg-content"), group.classList.contains("open"));
      }
    });
  }

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
        const group = link.closest(".sidebar-group");
        const subgroup = link.closest(".sidebar-subgroup");
        if (group) activeGroup = group;
        if (subgroup) activeSubgroup = subgroup;
      }
    });

    return { activeGroup, activeSubgroup };
  }

  function restoreGroupState(fallbackGroup, preferredGroup) {
    const savedKey = localStorage.getItem(ACTIVE_GROUP_KEY);
    const savedGroup = savedKey
      ? document.querySelector(`#grms-sidebar .sidebar-group[data-group="${savedKey}"]`)
      : null;

    const group = preferredGroup || savedGroup || fallbackGroup;
    if (group) {
      openGroup(group, Boolean(savedGroup));
    }
  }

  function updateHeights() {
    document.querySelectorAll("#grms-sidebar .sidebar-group.open").forEach((group) => {
      setMaxHeight(group.querySelector(":scope > .sg-content"), true);
    });
  }

  function handleGroupToggles() {
    document.querySelectorAll("#grms-sidebar .sg-header").forEach((header) => {
      header.addEventListener("click", () => {
        const group = header.closest(".sidebar-group");
        if (!group) return;
        if (group.classList.contains("open")) {
          closeGroup(group);
        } else {
          openGroup(group);
        }
      });
    });
  }

  function handleSubgroupToggles() {
    document.querySelectorAll("#grms-sidebar .ss-header").forEach((header) => {
      header.addEventListener("click", (event) => {
        event.stopPropagation();
        const subgroup = header.closest(".sidebar-subgroup");
        if (!subgroup) return;
        if (subgroup.classList.contains("no-toggle")) return;
        if (subgroup.classList.contains("open")) {
          subgroup.classList.remove("open");
          const list = subgroup.querySelector(":scope > .ss-list");
          if (list) list.style.display = "none";
        } else {
          openSubgroup(subgroup);
          const group = header.closest(".sidebar-group");
          if (group) setMaxHeight(group.querySelector(":scope > .sg-content"), true);
        }
      });
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
        const subgroups = group.querySelectorAll(".sidebar-subgroup");

        subgroups.forEach((sub) => {
          let subHasMatch = false;
          sub.querySelectorAll(".ss-link").forEach((link) => {
            const match = !term || link.textContent.toLowerCase().includes(term);
            link.style.display = match ? "" : "none";
            if (match) subHasMatch = true;
          });

          sub.style.display = subHasMatch || !term ? "" : "none";
          if (term) {
            if (subHasMatch) {
              openSubgroup(sub);
            } else {
              sub.classList.remove("open");
              const list = sub.querySelector(":scope > .ss-list");
              if (list) list.style.display = "none";
            }
          }
          if (subHasMatch) groupHasMatch = true;
        });

        group.style.display = groupHasMatch || !term ? "" : "none";
        const content = group.querySelector(":scope > .sg-content");
        if (term) {
          if (groupHasMatch) {
            openGroup(group, false);
          } else {
            closeGroup(group);
            setMaxHeight(content, false);
          }
        }
      });

      if (!term) {
        restoreGroupState(
          document.querySelector("#grms-sidebar .sidebar-group"),
          document.querySelector("#grms-sidebar .sidebar-group.open")
        );
        updateHeights();
      }
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

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("popup")) return;
    const sidebar = document.getElementById("grms-sidebar");
    if (!sidebar) return;

    const { activeGroup, activeSubgroup } = markActiveLinks();
    activateSingleSubgroups();
    if (activeGroup) {
      openGroup(activeGroup, false);
    }
    if (activeSubgroup) {
      openSubgroup(activeSubgroup);
    }

    restoreGroupState(
      document.querySelector("#grms-sidebar .sidebar-group"),
      activeGroup
    );
    updateHeights();
    handleGroupToggles();
    handleSubgroupToggles();
    handleSearch();
    handleCollapseToggle();
    window.addEventListener("resize", updateHeights);
  });
})();
