(function () {
    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function toggleSections(category) {
        var isLine = ["Retaining Wall", "Gabion Wall"].indexOf(category) !== -1;
        var pointSections = document.querySelectorAll(".structure-point");
        var lineSections = document.querySelectorAll(".structure-line");
        var pointFields = ["station_km", "location_point", "easting", "northing"];
        var lineFields = ["start_chainage_km", "end_chainage_km", "location_line"];

        pointSections.forEach(function (section) {
            section.style.display = isLine ? "none" : "";
        });
        lineSections.forEach(function (section) {
            section.style.display = isLine ? "" : "none";
        });

        pointFields.forEach(function (name) {
            document.querySelectorAll(".form-row.field-" + name).forEach(function (row) {
                row.style.display = isLine ? "none" : "";
            });
        });
        lineFields.forEach(function (name) {
            document.querySelectorAll(".form-row.field-" + name).forEach(function (row) {
                row.style.display = isLine ? "" : "none";
            });
        });
    }

    ready(function () {
        var selector = document.getElementById("id_structure_category");
        if (!selector) return;

        toggleSections(selector.value);
        selector.addEventListener("change", function (event) {
            toggleSections(event.target.value);
        });
    });
})();
