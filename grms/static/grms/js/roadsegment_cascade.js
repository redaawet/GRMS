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

    const maxAttempts = 10;

    function getRoadId() {
      const value = $road.val();
      return value ? String(value) : "";
    }

    function clearSection() {
      $section.val(null).trigger("change");
    }

    function wireSelect2(attempt = 0) {
      const s2 = $section.data("select2");
      if (!s2 || !s2.options || !s2.options.options || !s2.options.options.ajax) {
        if (attempt < maxAttempts) {
          setTimeout(() => wireSelect2(attempt + 1), 100);
        }
        return;
      }

      const ajax = s2.options.options.ajax;
      const existing = ajax.data;
      if (existing && existing._roadsegmentWrapped) {
        return;
      }

      const wrapped = function (params) {
        const base = existing ? existing(params) : params;
        const roadId = getRoadId();
        if (!roadId) {
          return base;
        }
        return Object.assign({}, base, { road: roadId });
      };
      wrapped._roadsegmentWrapped = true;

      ajax.data = wrapped;
    }

    wireSelect2();

    $road.on("change", function () {
      clearSection();
      wireSelect2();
    });
  });
})();
