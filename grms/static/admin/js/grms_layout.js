(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const header = document.querySelector("#header");
    if (!header) return;

    document.documentElement.style.setProperty(
      "--grms-header-height",
      `${header.offsetHeight}px`
    );
  });
})();
