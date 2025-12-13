(function () {
  function setOffsets() {
    const header = document.getElementById("header");
    const breadcrumbs = document.querySelector(".breadcrumbs")?.closest("nav");

    const h = header ? header.getBoundingClientRect().height : 0;
    const b = breadcrumbs ? breadcrumbs.getBoundingClientRect().height : 0;

    const top = Math.ceil(h + b);
    document.documentElement.style.setProperty("--grms-top-offset", `${top}px`);
  }

  window.addEventListener("load", setOffsets, { once: true });
  window.addEventListener("resize", setOffsets);
})();
