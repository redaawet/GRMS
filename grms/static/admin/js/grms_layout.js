(function () {
  function syncHeaderHeight() {
    const header = document.getElementById("header");
    if (!header) return;
    document.documentElement.style.setProperty("--grms-header-height", `${header.offsetHeight}px`);
  }

  window.addEventListener("load", syncHeaderHeight);
  window.addEventListener("resize", syncHeaderHeight);
})();
