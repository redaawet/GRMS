(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
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
            opt.textContent = option.label;
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

    function fetchOptions(url) {
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (resp) { return resp.ok ? resp.json() : { results: [] }; })
            .then(function (payload) { return payload.results || []; });
    }

    ready(function () {
        var roadSelect = document.getElementById("id_road");
        var sectionSelect = document.getElementById("id_section");
        var structureSelect = document.getElementById("id_structure");

        if (!roadSelect || !sectionSelect || !structureSelect) {
            return;
        }

        function refreshSections() {
            var roadId = roadSelect.value;
            if (!roadId) {
                replaceOptions(sectionSelect, [], "Select a road first");
                replaceOptions(structureSelect, [], "Select a section first");
                return;
            }
            var url = new URL("section-options/", window.location.href);
            url.searchParams.set("road_id", roadId);
            fetchOptions(url.toString()).then(function (options) {
                replaceOptions(sectionSelect, options, "Select a section");
                refreshStructures();
            });
        }

        function refreshStructures() {
            var roadId = roadSelect.value;
            var sectionId = sectionSelect.value;
            if (!roadId) {
                replaceOptions(structureSelect, [], "Select a road first");
                return;
            }
            var url = new URL("structure-options/", window.location.href);
            url.searchParams.set("road_id", roadId);
            if (sectionId) {
                url.searchParams.set("section_id", sectionId);
            }
            fetchOptions(url.toString()).then(function (options) {
                replaceOptions(structureSelect, options, "Select a structure");
            });
        }

        roadSelect.addEventListener("change", refreshSections);
        sectionSelect.addEventListener("change", refreshStructures);

        refreshSections();
    });
})();
