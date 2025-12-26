(function () {
  const $ = (window.django && django.jQuery) ? django.jQuery : null;
  if (!$) return;

  function patchSelect2Ajax($el, getParams) {
    const select2 = $el.data("select2");
    if (!select2 || !select2.options?.options?.ajax) return;

    const ajax = select2.options.options.ajax;
    const oldUrl = ajax.url;

    ajax.url = function (params) {
      const base = (typeof oldUrl === "function") ? oldUrl(params) : oldUrl;
      const u = new URL(base, window.location.origin);
      const extra = getParams() || {};
      Object.keys(extra).forEach((k) => {
        const v = extra[k];
        if (v) u.searchParams.set(k, v);
        else u.searchParams.delete(k);
      });
      return u.toString();
    };
  }

  function wire() {
    const roadEl = document.getElementById("id_road");
    const sectionEl = document.getElementById("id_section");
    if (!roadEl || !sectionEl) return;

    const $section = $(sectionEl);

    patchSelect2Ajax($section, () => ({ road: roadEl.value }));

    roadEl.addEventListener("change", () => {
      $section.val(null).trigger("change");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    wire();
    setTimeout(wire, 0);
    setTimeout(wire, 250);
    setTimeout(wire, 800);
  });

  document.addEventListener("formset:added", () => {
    setTimeout(wire, 0);
    setTimeout(wire, 250);
  });
})();
