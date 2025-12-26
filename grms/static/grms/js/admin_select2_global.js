(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function shouldSkip(selectEl) {
        return (
            selectEl.classList.contains("admin-autocomplete") ||
            selectEl.hasAttribute("data-ajax--url") ||
            selectEl.classList.contains("selectfilter") ||
            selectEl.classList.contains("selectfilterstacked") ||
            selectEl.hasAttribute("data-no-select2")
        );
    }

    function initSelect2(context) {
        if (!window.django || !window.django.jQuery) {
            return;
        }
        var $ = window.django.jQuery;
        if (!$.fn.select2) {
            return;
        }
        $(context)
            .find("select")
            .each(function () {
                var selectEl = this;
                if (shouldSkip(selectEl)) {
                    return;
                }
                if (selectEl.classList.contains("select2-hidden-accessible")) {
                    return;
                }
                $(selectEl).select2({
                    width: "style",
                    dropdownAutoWidth: true,
                });
            });
    }

    ready(function () {
        initSelect2(document);
        if (window.django && window.django.jQuery) {
            window.django.jQuery(document).on("formset:added", function (_event, row) {
                initSelect2(row[0] || row);
            });
        }
        if ("MutationObserver" in window) {
            var observer = new MutationObserver(function () {
                initSelect2(document);
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    });
})();
