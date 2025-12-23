(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function buildOption(option, currentValue, currentLabel) {
        var opt = document.createElement("option");
        opt.value = option.id;
        opt.textContent = option.label;
        if (String(option.id) === String(currentValue)) {
            opt.selected = true;
        }
        return opt;
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
            selectEl.appendChild(buildOption(option, current.value, current.label));
        });
        if (current.value && !selectEl.value && current.label) {
            var fallback = document.createElement("option");
            fallback.value = current.value;
            fallback.textContent = current.label + " (current)";
            fallback.selected = true;
            selectEl.appendChild(fallback);
        }
    }

    function fetchOptions(url) {
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (resp) { return resp.ok ? resp.json() : { results: [] }; })
            .then(function (payload) { return payload.results || []; });
    }

    ready(function () {
        var roadSelect = document.getElementById("id_road");
        var sectionSelect = document.getElementById("id_section");
        var segmentSelect = document.getElementById("id_road_segment") || document.getElementById("id_segment");

        if (!roadSelect || !sectionSelect) {
            return;
        }

        function refreshSections() {
            var roadId = roadSelect.value;
            if (!roadId) {
                replaceOptions(sectionSelect, [], "Select a road first");
                if (segmentSelect) {
                    replaceOptions(segmentSelect, [], "Select a section first");
                }
                return;
            }
            var url = new URL("section-options/", window.location.href);
            url.searchParams.set("road_id", roadId);
            fetchOptions(url.toString()).then(function (options) {
                replaceOptions(sectionSelect, options, "Select a section");
                if (segmentSelect) {
                    refreshSegments();
                }
            });
        }

        function refreshSegments() {
            if (!segmentSelect) {
                return;
            }
            var sectionId = sectionSelect.value;
            if (!sectionId) {
                replaceOptions(segmentSelect, [], "Select a section first");
                return;
            }
            var url = new URL("segment-options/", window.location.href);
            url.searchParams.set("section_id", sectionId);
            fetchOptions(url.toString()).then(function (options) {
                replaceOptions(segmentSelect, options, "Select a segment");
            });
        }

        roadSelect.addEventListener("change", refreshSections);
        sectionSelect.addEventListener("change", refreshSegments);

        refreshSections();
    });
})();
