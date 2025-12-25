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

    function fetchOptions(url) {
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (resp) { return resp.ok ? resp.json() : []; })
            .then(function (payload) {
                if (Array.isArray(payload)) {
                    return payload;
                }
                return payload.results || [];
            });
    }

    function preserveCurrent(selectEl) {
        var currentValue = selectEl.value;
        var currentLabel = "";
        if (currentValue) {
            var selected = selectEl.options[selectEl.selectedIndex];
            currentLabel = selected ? selected.textContent : "";
        }
        return { value: currentValue, label: currentLabel };
    }

    function replaceOptions(selectEl, options, placeholder) {
        var current = preserveCurrent(selectEl);
        selectEl.innerHTML = "";
        if (placeholder) {
            var empty = document.createElement("option");
            empty.value = "";
            empty.textContent = placeholder;
            selectEl.appendChild(empty);
        }
        options.forEach(function (option) {
            var opt = document.createElement("option");
            opt.value = option.id;
            opt.textContent = option.text || option.label || "";
            if (String(option.id) === String(current.value)) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        });
        if (current.value && !selectEl.value && current.label) {
            var fallback = document.createElement("option");
            fallback.value = current.value;
            fallback.textContent = current.label + " (current)";
            fallback.selected = true;
            selectEl.appendChild(fallback);
        }
    }

    function triggerChange(selectEl) {
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function refreshChild(child, config) {
        var parent = document.getElementById(config.parentId);
        if (!parent) {
            return;
        }
        var parentValue = parent.value;
        if (!parentValue) {
            replaceOptions(child, [], config.placeholder || "Select an option");
            child.disabled = true;
            triggerChange(child);
            return;
        }
        child.disabled = false;
        var url = config.url.startsWith("/")
            ? new URL(config.url, window.location.origin)
            : new URL(config.url, window.location.href);
        url.searchParams.set(config.param, parentValue);
        config.extras.forEach(function (extra) {
            var extraEl = document.getElementById(extra.elementId);
            if (extraEl && extraEl.value) {
                url.searchParams.set(extra.param, extraEl.value);
            }
        });
        fetchOptions(url.toString()).then(function (options) {
            replaceOptions(child, options, config.placeholder || "Select an option");
            triggerChange(child);
        });
    }

    function setupChild(child) {
        if (child.dataset.cascadeInitialized) {
            return;
        }
        if (isAutocomplete(child)) {
            return;
        }
        var parentId = child.dataset.cascadeParent;
        var url = child.dataset.cascadeUrl || "";
        var param = child.dataset.cascadeParam || "";
        if (!parentId || !url || !param) {
            return;
        }
        var config = {
            parentId: parentId,
            url: url,
            param: param,
            placeholder: child.dataset.cascadePlaceholder,
            extras: parseExtras(child.dataset.cascadeExtra),
        };
        var parent = document.getElementById(parentId);
        if (!parent) {
            return;
        }
        parent.addEventListener("change", function () {
            refreshChild(child, config);
        });
        child.dataset.cascadeInitialized = "true";
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
