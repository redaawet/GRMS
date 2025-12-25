(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function isAutocomplete(selectEl) {
        return (
            selectEl.classList.contains("admin-autocomplete") ||
            selectEl.hasAttribute("data-ajax--url")
        );
    }

    function parseExtras(extra) {
        if (!extra) {
            return [];
        }
        return extra.split(",").map(function (entry) {
            var parts = entry.split(":");
            return { elementId: parts[0], param: parts[1] };
        });
    }

    function buildUrl(base, config, parentValue) {
        var url = new URL(base, window.location.origin);
        if (parentValue) {
            url.searchParams.set(config.param, parentValue);
        } else {
            url.searchParams.delete(config.param);
        }
        config.extras.forEach(function (extra) {
            var extraEl = document.getElementById(extra.elementId);
            if (extraEl && extraEl.value) {
                url.searchParams.set(extra.param, extraEl.value);
            } else {
                url.searchParams.delete(extra.param);
            }
        });
        return url.toString();
    }

    function clearSelect(selectEl) {
        if (window.django && window.django.jQuery) {
            window.django.jQuery(selectEl).val(null).trigger("change");
        } else {
            selectEl.value = "";
            selectEl.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function refreshChild(child, config) {
        var parent = document.getElementById(config.parentId);
        if (!parent) {
            return;
        }
        var parentValue = parent.value;
        var baseUrl = child.getAttribute("data-cascade-base-url")
            || child.getAttribute("data-ajax--url")
            || config.url;
        if (!baseUrl) {
            return;
        }
        if (!child.getAttribute("data-cascade-base-url")) {
            child.setAttribute("data-cascade-base-url", baseUrl);
        }
        child.setAttribute("data-ajax--url", buildUrl(baseUrl, config, parentValue));
        child.disabled = !parentValue;
        clearSelect(child);
    }

    function setupChild(child) {
        if (child.dataset.cascadeAutocompleteInitialized) {
            return;
        }
        if (!isAutocomplete(child)) {
            return;
        }
        var parentId = child.dataset.cascadeParent;
        var param = child.dataset.cascadeParam || "";
        if (!parentId || !param) {
            return;
        }
        var config = {
            parentId: parentId,
            param: param,
            url: child.dataset.cascadeUrl || "",
            extras: parseExtras(child.dataset.cascadeExtra),
        };
        var parent = document.getElementById(parentId);
        if (!parent) {
            return;
        }
        parent.addEventListener("change", function () {
            refreshChild(child, config);
        });
        child.dataset.cascadeAutocompleteInitialized = "true";
        refreshChild(child, config);
    }

    function initialize() {
        Array.from(document.querySelectorAll("[data-cascade-parent]")).forEach(setupChild);
    }

    ready(function () {
        initialize();
        if ("MutationObserver" in window) {
            var observer = new MutationObserver(function () {
                initialize();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    });
})();
