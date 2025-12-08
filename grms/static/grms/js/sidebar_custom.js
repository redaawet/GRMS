// Adds collapsible behavior to the custom sidebar
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sidebar-group-title').forEach((title) => {
    title.addEventListener('click', () => {
      const group = title.parentElement;
      const list = group.querySelector('.sidebar-items');
      list.classList.toggle('open');
    });
  });
});
