(function () {
  const $ = (window.django && django.jQuery) ? django.jQuery : null;
  if (!$ || !$.fn || !$.fn.select2) return;

  function patch($el, getExtra) {
    const s2 = $el.data("select2");
    if (!s2 || !s2.options?.options?.ajax) return;

    const ajax = s2.options.options.ajax;
    const oldData = ajax.data;

    ajax.data = function (params) {
      const base = oldData ? oldData(params) : params;
      const extra = getExtra ? (getExtra() || {}) : {};
      return Object.assign({}, base, extra);
    };
  }

  function attachDependentAutocomplete(childSelector, parentSelector, paramName) {
    const $children = $(childSelector);
    const $parent = $(parentSelector);
    if (!$children.length || !$parent.length) return;

    $children.each(function () {
      const $child = $(this);
      patch($child, () => {
        const value = $parent.val();
        return value ? { [paramName]: value } : {};
      });
    });

    $parent.on("change", () => {
      $children.val(null).trigger("change");
    });
  }

  function wire() {
    attachDependentAutocomplete("#id_section", "#id_road", "road_id");
    attachDependentAutocomplete("#id_segment", "#id_section", "section_id");
    attachDependentAutocomplete("#id_road_segment", "#id_section", "section_id");
  }

  document.addEventListener("DOMContentLoaded", () => {
    wire();
    setTimeout(wire, 0);
    setTimeout(wire, 300);
    setTimeout(wire, 900);
  });

  document.addEventListener("formset:added", () => {
    setTimeout(wire, 0);
    setTimeout(wire, 300);
  });
})();
