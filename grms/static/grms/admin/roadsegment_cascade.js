(function () {
  const $ = (window.django && django.jQuery) ? django.jQuery : null;
  if (!$.fn || !$.fn.select2) return;

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

  function wire() {
    const roadEl = document.getElementById("id_road");
    const sectionEl = document.getElementById("id_section");
    if (!roadEl || !sectionEl) return;

    const $section = $(sectionEl);

    patch($section, () => {
      const v = roadEl.value;
      return { road: v, road_id: v, "road__id__exact": v };
    });

    roadEl.addEventListener("change", () => {
      $section.val(null).trigger("change");
    });
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
