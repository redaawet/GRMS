// Universal sidebar collapse for Django Admin
// Works with both the default table-based nav sidebar and any
// custom list-based menus. It attaches click handlers to group headers
// (captions in tables or titles in custom lists) and toggles the
// visibility of their associated rows or lists.

document.addEventListener('DOMContentLoaded', function () {
  const nav = document.getElementById('nav-sidebar');
  if (!nav) return;

  // Collapse logic for default admin (table-based modules)
  const modules = nav.querySelectorAll('.module');
  modules.forEach((module) => {
    const caption = module.querySelector('caption');
    if (caption) {
      const rows = module.querySelectorAll('tbody tr');
      if (rows.length === 0) return;
      caption.style.cursor = 'pointer';
      caption.addEventListener('click', function (event) {
        event.preventDefault();
        rows.forEach((row) => {
          row.classList.toggle('nav-collapsed');
        });
      });
    }
  });

  // Collapse logic for custom list-based sidebar (li.model-group)
  const customGroups = nav.querySelectorAll('li.model-group');
  customGroups.forEach((group) => {
    const header = group.querySelector('.group-header');
    const list = group.querySelector('.group-items');
    if (header && list && header.dataset.accordionBound !== 'true') {
      header.style.cursor = 'pointer';
      header.addEventListener('click', function (event) {
        event.preventDefault();
        list.classList.toggle('nav-collapsed');
      });
    }
  });
});
