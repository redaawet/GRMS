(function () {
  function setHeaderHeight() {
    const header = document.getElementById("header");
    if (!header) return;

    const height = header.offsetHeight || parseInt(getComputedStyle(header).height, 10) || 0;
    if (height) {
      document.documentElement.style.setProperty("--grms-header-height", `${height}px`);
    }
  }

  function markSidebarPresence() {
    const sidebar = document.getElementById("grms-sidebar");
    if (!sidebar) return;
    document.body.classList.add("grms-has-sidebar");
  }

  document.addEventListener("DOMContentLoaded", () => {
    setHeaderHeight();
    markSidebarPresence();
  });

  window.addEventListener("resize", setHeaderHeight);
})();
