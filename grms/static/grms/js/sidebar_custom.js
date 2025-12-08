// Adds collapsible behavior to the custom sidebar
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sidebar-group-title').forEach((title) => {
    title.addEventListener('click', () => {
      const list = title.parentElement?.querySelector('.sidebar-items');
      if (!list) return;

      const isOpen = list.classList.toggle('open');
      title.setAttribute('aria-expanded', isOpen ? 'true' : 'false');

      const icon = title.querySelector('.toggle-icon');
      if (icon) {
        icon.textContent = isOpen ? '▾' : '▸';
      }
    });
  });
});
