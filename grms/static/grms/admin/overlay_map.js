(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function parseConfig() {
        var el = document.getElementById("overlay-map-config");
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            console.error("Invalid overlay map config", err);
            return null;
        }
    }

    function fetchGeoJson(url) {
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (resp) { return resp.ok ? resp.json() : null; });
    }

    function buildLayer(geojson, style, pointToLayer) {
        if (!geojson || !window.L) return null;
        return L.geoJSON(geojson, {
            style: style,
            pointToLayer: pointToLayer,
        });
    }

    function getSelectedValue(id) {
        var el = document.getElementById(id);
        return el && el.value ? el.value : null;
    }

    ready(function () {
        var config = parseConfig();
        var container = document.getElementById("overlay-map");
        if (!config || !container || !window.L) {
            return;
        }

        var map = L.map(container);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);

        var defaultCenter = window.DEFAULT_MAP_CENTER || [13.5, 39.5];
        if (Array.isArray(defaultCenter) && defaultCenter.length >= 2) {
            var lat = Number(defaultCenter[0]);
            var lng = Number(defaultCenter[1]);
            if (Number.isFinite(lat) && Number.isFinite(lng)) {
                map.setView([lat, lng], 7);
            }
        } else if (defaultCenter && typeof defaultCenter === "object"
            && Number.isFinite(defaultCenter.lat) && Number.isFinite(defaultCenter.lng)) {
            map.setView([Number(defaultCenter.lat), Number(defaultCenter.lng)], defaultCenter.zoom || 7);
        }

        var roadLayer;
        var sectionsLayer;
        var segmentsLayer;
        var structuresLayer;

        function clearLayer(layer) {
            if (layer && map.hasLayer(layer)) {
                map.removeLayer(layer);
            }
        }

        function updateMapBounds(layers) {
            var bounds = null;
            layers.forEach(function (layer) {
                if (layer && layer.getBounds) {
                    var layerBounds = layer.getBounds();
                    if (layerBounds && layerBounds.isValid()) {
                        bounds = bounds ? bounds.extend(layerBounds) : layerBounds;
                    }
                }
            });
            if (bounds && bounds.isValid()) {
                map.fitBounds(bounds, { padding: [20, 20] });
            }
        }

        function currentStyle(feature) {
            if (feature && feature.properties && feature.properties.is_current) {
                return { color: "#1f77b4", weight: 7, opacity: 1 };
            }
            return { color: "#9ca3af", weight: 4, opacity: 0.7 };
        }

        function segmentStyle(feature) {
            if (feature && feature.properties && feature.properties.is_current) {
                return { color: "#ef4444", weight: 7, opacity: 1 };
            }
            return { color: "#f97316", weight: 4, opacity: 0.8 };
        }

        function structureMarker(feature, latlng) {
            var isCurrent = feature && feature.properties && feature.properties.is_current;
            var color = isCurrent ? "#1f77b4" : "#10b981";
            return L.circleMarker(latlng, {
                radius: isCurrent ? 8 : 5,
                color: color,
                weight: isCurrent ? 3 : 2,
                fillColor: color,
                fillOpacity: 0.9,
            });
        }

        function render() {
            var roadId = getSelectedValue("id_road") || config.road_id;
            var sectionId = getSelectedValue("id_section") || config.section_id;
            if (!roadId) {
                return;
            }

            var roadUrl = new URL(config.urls.road, window.location.origin);
            roadUrl.searchParams.set("road_id", roadId);
            var sectionUrl = new URL(config.urls.sections, window.location.origin);
            sectionUrl.searchParams.set("road_id", roadId);
            sectionUrl.searchParams.set("current_id", config.current_id || "");
            var segmentUrl = new URL(config.urls.segments, window.location.origin);
            segmentUrl.searchParams.set("road_id", roadId);
            if (sectionId) {
                segmentUrl.searchParams.set("section_id", sectionId);
            }
            segmentUrl.searchParams.set("current_id", config.current_id || "");
            var structureUrl = new URL(config.urls.structures, window.location.origin);
            structureUrl.searchParams.set("road_id", roadId);
            if (sectionId) {
                structureUrl.searchParams.set("section_id", sectionId);
            }
            structureUrl.searchParams.set("current_id", config.current_id || "");

            Promise.all([
                fetchGeoJson(roadUrl.toString()),
                fetchGeoJson(sectionUrl.toString()),
                fetchGeoJson(segmentUrl.toString()),
                fetchGeoJson(structureUrl.toString()),
            ]).then(function (results) {
                var roadGeo = results[0];
                var sectionsGeo = results[1];
                var segmentsGeo = results[2];
                var structuresGeo = results[3];

                clearLayer(roadLayer);
                clearLayer(sectionsLayer);
                clearLayer(segmentsLayer);
                clearLayer(structuresLayer);

                roadLayer = buildLayer(roadGeo, { color: "#111827", weight: 5, opacity: 0.8 });
                sectionsLayer = buildLayer(sectionsGeo, currentStyle);
                segmentsLayer = buildLayer(segmentsGeo, segmentStyle);
                structuresLayer = buildLayer(structuresGeo, null, structureMarker);

                [roadLayer, sectionsLayer, segmentsLayer, structuresLayer].forEach(function (layer) {
                    if (layer) {
                        layer.addTo(map);
                    }
                });

                updateMapBounds([roadLayer, sectionsLayer, segmentsLayer, structuresLayer]);
            });
        }

        render();

        var roadSelect = document.getElementById("id_road");
        var sectionSelect = document.getElementById("id_section");
        if (roadSelect) {
            roadSelect.addEventListener("change", render);
        }
        if (sectionSelect) {
            sectionSelect.addEventListener("change", render);
        }
    });
})();
