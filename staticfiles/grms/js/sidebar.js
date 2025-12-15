(function () {
  if (window.GRMS_SIDEBAR_LOADED) return;
  window.GRMS_SIDEBAR_LOADED = true;

  const SELECTORS = {
    sidebar: "#grms-sidebar",
    search: "#sidebar-search",
    group: ".sidebar-group",
    header: ".sg-header",
    content: ".sg-content",
    link: ".ss-link",
  };

  function markActiveLinks(nav) {
    const currentPath = window.location.pathname;
    nav.querySelectorAll(SELECTORS.link).forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;
      const linkPath = new URL(href, window.location.origin).pathname;
      if (currentPath.startsWith(linkPath)) {
        link.classList.add("active");
        const group = link.closest(SELECTORS.group);
        const subgroup = link.closest(".sidebar-subgroup");
        if (group) group.classList.add("has-active");
        if (subgroup) subgroup.classList.add("has-active");
      }
    });
  }

  function handleSearch(nav) {
    const searchInput = document.querySelector(SELECTORS.search);
    if (!searchInput) return;

    searchInput.addEventListener("input", (event) => {
      const term = event.target.value.trim().toLowerCase();
      const groups = nav.querySelectorAll(SELECTORS.group);

      groups.forEach((group) => {
        let groupHasMatch = false;
        const subgroupBlocks = group.querySelectorAll(".sidebar-subgroup");
        const directLinks = group.querySelectorAll(":scope > .sg-content > .sg-list > .ss-link");

        if (subgroupBlocks.length) {
          subgroupBlocks.forEach((sub) => {
            let subHasMatch = false;
            sub.querySelectorAll(SELECTORS.link).forEach((link) => {
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

  function collapseGroup(group) {
    if (!group) return;
    group.classList.remove("is-open");
    const header = group.querySelector(SELECTORS.header);
    const content = group.querySelector(SELECTORS.content);
    if (header) header.setAttribute("aria-expanded", "false");
    if (content) {
      content.style.maxHeight = "0px";
      content.classList.remove("is-scrollable");
      content.scrollTop = 0;
    }
  }

  function setGroupHeight(group) {
    const content = group.querySelector(SELECTORS.content);
    if (!content) return;

    content.style.maxHeight = `${content.scrollHeight}px`;
    content.classList.remove("is-scrollable");
  }

  function openGroup(group, groups) {
    if (!group) return;
    groups.forEach((item) => {
      if (item !== group) collapseGroup(item);
    });

    const header = group.querySelector(SELECTORS.header);
    group.classList.add("is-open");
    if (header) header.setAttribute("aria-expanded", "true");
    setGroupHeight(group);
  }

  function bindAccordion(nav, scrollArea) {
    const groups = Array.from(nav.querySelectorAll(SELECTORS.group));
    if (!groups.length) return;

    groups.forEach((group) => {
      const header = group.querySelector(SELECTORS.header);
      if (!header) return;
      header.addEventListener("click", () => {
        const isOpen = group.classList.contains("is-open");
        if (isOpen) {
          collapseGroup(group);
        } else {
          openGroup(group, groups);
        }
      });
    });

    const activeGroup = groups.find((group) => group.classList.contains("has-active")) || groups[0];
    openGroup(activeGroup, groups);

    const updateOpenHeight = () => {
      const open = nav.querySelector(`${SELECTORS.group}.is-open`);
      if (open) setGroupHeight(open);
    };

    if (scrollArea) {
      scrollArea.addEventListener("scroll", updateOpenHeight, { passive: true });
    }
    window.addEventListener("resize", updateOpenHeight);
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("popup")) return;
    const sidebar = document.querySelector(SELECTORS.sidebar);
    if (!sidebar) return;

    const nav = sidebar.querySelector(".sidebar-nav");
    if (!nav) return;
    const scrollArea = sidebar.querySelector(".grms-sidebar-scroll") || nav;

    markActiveLinks(nav);
    handleSearch(nav);
    bindAccordion(nav, scrollArea);
  });
})();
