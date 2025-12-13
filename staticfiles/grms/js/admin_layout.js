(function () {
  function setHeaderHeight() {
    const header = document.getElementById("header");
    if (!header) return;
    const height = Math.ceil(header.getBoundingClientRect().height);

    if (!height || Number.isNaN(height)) {
      document.documentElement.style.removeProperty("--grms-header-height");
      return;
    }

    document.documentElement.style.setProperty("--grms-header-height", `${height}px`);
  }

  function tagBodyForSidebar() {
    const sidebar = document.getElementById("grms-sidebar");
    if (sidebar && !document.body.classList.contains("grms-has-sidebar")) {
      document.body.classList.add("grms-has-sidebar");
    }
  }

  function init() {
    tagBodyForSidebar();
    setHeaderHeight();

    window.addEventListener("resize", setHeaderHeight);

    const header = document.getElementById("header");
    if (header && "ResizeObserver" in window) {
      const observer = new ResizeObserver(setHeaderHeight);
      observer.observe(header);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
  window.addEventListener("load", setHeaderHeight, { once: true });
})();
