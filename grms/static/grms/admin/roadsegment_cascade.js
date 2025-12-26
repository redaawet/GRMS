(function () {
  const $ = (window.django && django.jQuery) ? django.jQuery : null;
  if (!$) return;

  function patchSelect2Ajax(selectEl, getParams) {
    const $sel = $(selectEl);
    const select2 = $sel.data("select2");
    if (!select2 || !select2.options?.options?.ajax) return;

    const ajax = select2.options.options.ajax;
    const oldUrl = ajax.url;

    ajax.url = function (params) {
      const base = (typeof oldUrl === "function") ? oldUrl(params) : oldUrl;
      const u = new URL(base, window.location.origin);
      const extra = getParams() || {};
      for (const k in extra) {
        const v = extra[k];
        if (v) u.searchParams.set(k, v);
        else u.searchParams.delete(k);
      }
      return u.toString();
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    const roadEl = document.getElementById("id_road");
    const sectionEl = document.getElementById("id_section");
    if (!roadEl || !sectionEl) return;

    patchSelect2Ajax(sectionEl, () => ({ road: roadEl.value }));

    roadEl.addEventListener("change", () => {
      $(sectionEl).val(null).trigger("change");
    });
  });
})();
