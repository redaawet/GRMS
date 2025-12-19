(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function buildOption(option) {
        var el = document.createElement("button");
        el.type = "button";
        el.className = "road-quick-filter__option";
        el.textContent = option.label;
        el.dataset.value = option.id;
        return el;
    }

    function attachAutocomplete(inputEl, valueEl, resultsEl, fetcher) {
        var activeRequest = null;

        function clearResults() {
            resultsEl.innerHTML = "";
            resultsEl.style.display = "none";
        }

        function renderResults(options) {
            resultsEl.innerHTML = "";
            if (!options.length) {
                clearResults();
                return;
            }
            options.forEach(function (option) {
                var el = buildOption(option);
                el.addEventListener("click", function () {
                    valueEl.value = option.id;
                    inputEl.value = option.label;
                    clearResults();
                });
                resultsEl.appendChild(el);
            });
            resultsEl.style.display = "block";
        }

        function onInput() {
            var term = inputEl.value.trim();
            if (!term) {
                valueEl.value = "";
                clearResults();
                return;
            }
            if (activeRequest) {
                activeRequest.abort();
            }
            activeRequest = new AbortController();
            fetcher(term, activeRequest.signal)
                .then(renderResults)
                .catch(function () {
                    clearResults();
                });
        }

        inputEl.addEventListener("input", onInput);
        document.addEventListener("click", function (event) {
            if (!resultsEl.contains(event.target) && event.target !== inputEl) {
                clearResults();
            }
        });

        return {
            clear: clearResults,
            render: renderResults,
        };
    }

    ready(function () {
        var roadInput = document.getElementById("road-quick-filter-input");
        var roadValue = document.getElementById("road-quick-filter-value");
        var roadResults = document.getElementById("road-quick-filter-results");
        var sectionInput = document.getElementById("section-quick-filter-input");
        var sectionValue = document.getElementById("section-quick-filter-value");
        var sectionResults = document.getElementById("section-quick-filter-results");

        if (!roadInput || !roadValue || !roadResults) {
            return;
        }

        function fetchRoads(term, signal) {
            var url = new URL("/admin/grms/road-autocomplete/", window.location.origin);
            url.searchParams.set("q", term);
            return fetch(url.toString(), { signal: signal })
                .then(function (resp) { return resp.ok ? resp.json() : { results: [] }; })
                .then(function (payload) { return payload.results || []; });
        }

        function fetchSections(term, signal) {
            var roadId = roadValue.value;
            if (!roadId) {
                return Promise.resolve([]);
            }
            var url = new URL("/admin/grms/section-autocomplete/", window.location.origin);
            url.searchParams.set("q", term);
            url.searchParams.set("road_id", roadId);
            return fetch(url.toString(), { signal: signal })
                .then(function (resp) { return resp.ok ? resp.json() : { results: [] }; })
                .then(function (payload) { return payload.results || []; });
        }

        attachAutocomplete(roadInput, roadValue, roadResults, fetchRoads);
        if (sectionInput && sectionValue && sectionResults) {
            attachAutocomplete(sectionInput, sectionValue, sectionResults, fetchSections);

            roadInput.addEventListener("change", function () {
                sectionValue.value = "";
                sectionInput.value = "";
                sectionResults.innerHTML = "";
            });
        }
    });
})();
