(function () {
  const ACTIVE_GROUP_KEY = "activeSidebarGroup";
  const COLLAPSE_KEY = "grmsSidebarCollapsed";

  function getGroupContent(group) {
    return (
      group.querySelector(".group-content") || group.querySelector(":scope > .submenu")
    );
  }

  function setMaxHeight(element, expanded) {
    if (!element) return;
    element.style.maxHeight = expanded ? `${element.scrollHeight}px` : "0px";
    element.style.opacity = expanded ? "1" : "0";
  }

  function closeOtherGroups(currentGroup) {
    document.querySelectorAll(".sidebar-group").forEach((group) => {
      if (group !== currentGroup) {
        const content = getGroupContent(group);
        group.classList.remove("group-open");
        setMaxHeight(content, false);
      }
    });
  }

  function openGroup(group, saveState = true) {
    const content = getGroupContent(group);
    group.classList.add("group-open");
    setMaxHeight(content, true);
    if (saveState) {
      localStorage.setItem(ACTIVE_GROUP_KEY, group.dataset.group || "");
    }
  }

  function toggleGroup(group) {
    const content = getGroupContent(group);
    const shouldOpen = !group.classList.contains("group-open");

    closeOtherGroups(group);
    if (shouldOpen) {
      openGroup(group);
    } else {
      group.classList.remove("group-open");
      setMaxHeight(content, false);
      localStorage.removeItem(ACTIVE_GROUP_KEY);
    }
  }

  function closeSiblingSubgroups(subgroup) {
    const siblings = subgroup.parentElement?.querySelectorAll(".sidebar-subgroup") || [];
    siblings.forEach((sib) => {
      if (sib !== subgroup) {
        const submenu = sib.querySelector(":scope > .submenu");
        sib.classList.remove("sub-open");
        setMaxHeight(submenu, false);
      }
    });
  }

  function openSubgroup(subgroup) {
    const submenu = subgroup.querySelector(":scope > .submenu");
    subgroup.classList.add("sub-open");
    setMaxHeight(submenu, true);
  }

  function toggleSubgroup(subgroup) {
    const submenu = subgroup.querySelector(":scope > .submenu");
    const shouldOpen = !subgroup.classList.contains("sub-open");
    closeSiblingSubgroups(subgroup);
    if (shouldOpen) {
      openSubgroup(subgroup);
    } else {
      subgroup.classList.remove("sub-open");
      setMaxHeight(submenu, false);
    }
  }

  function markActiveLinks() {
    const currentUrl = window.location.pathname;
    let activeGroup = null;
    let activeSubgroup = null;

    document.querySelectorAll("#grms-sidebar .menu-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;
      const linkPath = new URL(href, window.location.origin).pathname;
      if (currentUrl.startsWith(linkPath)) {
        link.classList.add("active-item");
        const group = link.closest(".sidebar-group");
        const subgroup = link.closest(".sidebar-subgroup");
        if (group) activeGroup = group;
        if (subgroup) activeSubgroup = subgroup;
      }
    });

    return { activeGroup, activeSubgroup };
  }

  function restoreGroupState(defaultGroup) {
    const saved = localStorage.getItem(ACTIVE_GROUP_KEY);
    const target = saved
      ? document.querySelector(`.sidebar-group[data-group="${saved}"]`)
      : null;

    const groupToOpen = target || defaultGroup;
    if (groupToOpen) {
      closeOtherGroups(groupToOpen);
      openGroup(groupToOpen, Boolean(groupToOpen));
    }
  }

  function handleSearch() {
    const searchInput = document.getElementById("sidebar-search");
    if (!searchInput) return;

    const filterMenu = (term) => {
      const needle = term.trim().toLowerCase();

      document.querySelectorAll(".sidebar-group").forEach((group) => {
        const content = getGroupContent(group);
        const subgroups = group.querySelectorAll(".sidebar-subgroup");
        let groupHasMatch = false;

        if (subgroups.length) {
          subgroups.forEach((sub) => {
            let subHasMatch = false;
            sub.querySelectorAll(".menu-link").forEach((link) => {
              const match = !needle || link.textContent.toLowerCase().includes(needle);
              link.parentElement.style.display = match ? "" : "none";
              if (match) subHasMatch = true;
            });
            sub.style.display = subHasMatch ? "" : "none";
            if (needle && subHasMatch) {
              openSubgroup(sub);
            }
            groupHasMatch = groupHasMatch || subHasMatch;
          });
        } else {
          group.querySelectorAll(".menu-link").forEach((link) => {
            const match = !needle || link.textContent.toLowerCase().includes(needle);
            link.parentElement.style.display = match ? "" : "none";
            if (match) groupHasMatch = true;
          });
        }

        if (needle) {
          if (groupHasMatch) {
            openGroup(group, false);
            setMaxHeight(content, true);
          } else {
            group.classList.remove("group-open");
            setMaxHeight(content, false);
          }
        } else if (!group.classList.contains("group-open")) {
          setMaxHeight(content, false);
        }
      });
    };

    searchInput.addEventListener("input", (event) => filterMenu(event.target.value));
  }

  function handleCollapseToggle() {
    const toggle = document.getElementById("sidebar-toggle");
    if (!toggle) return;

    const collapsed = localStorage.getItem(COLLAPSE_KEY) === "true";
    document.body.classList.toggle("sidebar-collapsed", collapsed);

    toggle.addEventListener("click", () => {
      document.body.classList.toggle("sidebar-collapsed");
      const isCollapsed = document.body.classList.contains("sidebar-collapsed");
      localStorage.setItem(COLLAPSE_KEY, String(isCollapsed));
    });
  }

  function updateOpenHeights() {
    document.querySelectorAll(".sidebar-group.group-open").forEach((group) => {
      const content = getGroupContent(group);
      setMaxHeight(content, true);
    });
    document.querySelectorAll(".sidebar-subgroup.sub-open").forEach((sub) => {
      const submenu = sub.querySelector(":scope > .submenu");
      setMaxHeight(submenu, true);
    });
  }

  function initAccordions() {
    document.querySelectorAll(".sidebar-group-header").forEach((header) => {
      header.addEventListener("click", () => {
        const group = header.closest(".sidebar-group");
        if (group) toggleGroup(group);
      });
    });

    document.querySelectorAll(".sidebar-subgroup-header").forEach((header) => {
      header.addEventListener("click", () => {
        const subgroup = header.closest(".sidebar-subgroup");
        if (subgroup) toggleSubgroup(subgroup);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const { activeGroup, activeSubgroup } = markActiveLinks();
    if (activeSubgroup) {
      openSubgroup(activeSubgroup);
    }

    restoreGroupState(activeGroup || document.querySelector(".sidebar-group"));

    initAccordions();
    handleSearch();
    handleCollapseToggle();
    updateOpenHeights();
    window.addEventListener("resize", updateOpenHeights);
  });
})();
