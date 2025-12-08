(function () {
  function updateHeaderOffset() {
    const header = document.getElementById('header');
    if (!header) return;

    const measuredHeight = Math.ceil(header.getBoundingClientRect().height);
    if (!measuredHeight) return;

    document.documentElement.style.setProperty('--grms-header-offset', `${measuredHeight}px`);
  }

  document.addEventListener('DOMContentLoaded', () => {
    updateHeaderOffset();
    window.addEventListener('resize', updateHeaderOffset, { passive: true });
  });

  window.addEventListener('load', updateHeaderOffset);
})();
