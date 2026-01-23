(function () {
  if (!window.django || !django.jQuery) {
    return;
  }

  django.jQuery(function ($) {
    const $road = $("#id_road");
    const $section = $("#id_section");
    if (!$road.length || !$section.length) {
      return;
    }

    function getRoadId() {
      const value = $road.val();
      return value ? String(value) : "";
    }

    function patchAjaxData() {
      const s2 = $section.data("select2");
      if (!s2 || !s2.options || !s2.options.options || !s2.options.options.ajax) {
        return;
      }

      const existing = s2.options.options.ajax.data;
      s2.options.options.ajax.data = function (params) {
        const data = existing ? existing(params) : params;
        data["forward[road]"] = getRoadId();
        return data;
      };
    }

    patchAjaxData();

    $road.on("change", function () {
      $section.val(null).trigger("change");
    });
  });
})();
