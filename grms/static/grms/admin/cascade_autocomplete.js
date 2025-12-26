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
      Object.keys(extra).forEach((key) => {
        const value = extra[key];
        if (value) {
          u.searchParams.set(key, value);
        } else {
          u.searchParams.delete(key);
        }
      });
      return u.toString();
    };
  }

  function wireCascade() {
    const roadEl = document.getElementById("id_road");
    const sectionEl = document.getElementById("id_section");
    const segmentEl = document.getElementById("id_road_segment");

    const structureEl = document.getElementById("id_structure");
    const structureTypeEl = document.getElementById("id_structure_category")
      || document.getElementById("id_structure_type");

    if (roadEl && sectionEl) {
      patchSelect2Ajax(sectionEl, () => ({ road: roadEl.value }));
      roadEl.addEventListener("change", () => {
        $(sectionEl).val(null).trigger("change");
        if (segmentEl) $(segmentEl).val(null).trigger("change");
        if (structureEl) $(structureEl).val(null).trigger("change");
      });
    }

    if (sectionEl && segmentEl) {
      patchSelect2Ajax(segmentEl, () => ({ section: sectionEl.value }));
      sectionEl.addEventListener("change", () => {
        $(segmentEl).val(null).trigger("change");
      });
    }

    if (structureEl) {
      patchSelect2Ajax(structureEl, () => ({
        road: roadEl ? roadEl.value : "",
        section: sectionEl ? sectionEl.value : "",
        structure_type: structureTypeEl ? structureTypeEl.value : "",
      }));

      if (roadEl) roadEl.addEventListener("change", () => $(structureEl).val(null).trigger("change"));
      if (sectionEl) sectionEl.addEventListener("change", () => $(structureEl).val(null).trigger("change"));
      if (structureTypeEl) {
        structureTypeEl.addEventListener("change", () => $(structureEl).val(null).trigger("change"));
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => setTimeout(wireCascade, 0));
})();
