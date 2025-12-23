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

    function parseConfig() {
        var el = document.getElementById("structure-map-config");
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            console.error("Invalid structure map config", err);
            return null;
        }
    }

    function findExistingLeafletMap() {
        if (!window.L || !L.Map) return null;

        var values = [];
        try {
            values = Object.values(window);
        } catch (err) {
            values = [];
        }

        for (var i = 0; i < values.length; i++) {
            var candidate = values[i];
            if (candidate && candidate instanceof L.Map) {
                return candidate;
            }
        }

        var containers = document.querySelectorAll(".leaflet-container");
        for (var j = 0; j < containers.length; j++) {
            var container = containers[j];
            if (container._leaflet_map_instance && container._leaflet_map_instance instanceof L.Map) {
                return container._leaflet_map_instance;
            }
        }
        return null;
    }

    function ensureMap(config) {
        if (!window.L) return null;

        var existing = findExistingLeafletMap();
        if (existing) {
            return { map: existing, origin: "existing" };
        }

        var fallbackContainer = document.getElementById("structure-overlay-map");
        if (!fallbackContainer) return null;

        var center = (config && config.center) ? [config.center.lat, config.center.lng] : [9, 39];
        var zoom = (config && config.defaultZoom) || 8;

        var fallbackMap = L.map(fallbackContainer).setView(center, zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors",
        }).addTo(fallbackMap);
        fallbackContainer._leaflet_map_instance = fallbackMap;
        return { map: fallbackMap, origin: "fallback" };
    }

    function buildPopup(properties) {
        if (!properties) return "";
        var parts = [];
        if (properties.category) parts.push(properties.category);
        if (properties.station_km !== null && properties.station_km !== undefined) {
            var km = properties.station_km;
            if (typeof km === "number" && isFinite(km)) {
                parts.push(km.toFixed(3) + " km");
            } else {
                parts.push(km + " km");
            }
        }
        if (properties.name) parts.push(properties.name);
        var label = parts.filter(Boolean).join(" · ");
        return label || properties.label || "Structure";
    }

    ready(function () {
        var selector = document.getElementById("id_structure_category");
        if (selector) {
            toggleSections(selector.value);
            selector.addEventListener("change", function (event) {
                toggleSections(event.target.value);
            });
        }

        var config = parseConfig();
        var overlayUrl = config && config.overlayUrl;
        var mapInfo = ensureMap(config);
        var map = mapInfo && mapInfo.map;
        var overlayGroup = map && window.L ? L.layerGroup().addTo(map) : null;
        var statusEl = document.getElementById("structure-overlay-status");

        function setStatus(message, level) {
            if (!statusEl) return;
            statusEl.textContent = message || "";
            statusEl.className = "help" + (level ? " " + level : "");
        }

        function currentRoadId() {
            var roadSelect = document.getElementById("id_road");
            if (roadSelect && roadSelect.value) {
                return roadSelect.value;
            }
            if (config && config.roadId) {
                return String(config.roadId);
            }
            return "";
        }

        if (!overlayUrl || !map) {
            setStatus("Map overlay unavailable. Select a road to enable the preview.");
            return;
        }

        function renderFeatures(features) {
            if (!overlayGroup) return;
            overlayGroup.clearLayers();
            if (!features || !features.length) {
                setStatus("No other structures found for this road yet.");
                return;
            }

            var bounds = [];
            features.forEach(function (feature) {
                if (!feature || !feature.geometry || !feature.geometry.coordinates) {
                    return;
                }
                var coords = feature.geometry.coordinates;
                if (!Array.isArray(coords) || coords.length < 2) {
                    return;
                }
                var latlng = [coords[1], coords[0]];
                var marker = L.marker(latlng, { title: feature.properties && feature.properties.label });
                var popup = buildPopup(feature.properties);
                marker.bindPopup(popup);
                overlayGroup.addLayer(marker);
                bounds.push(latlng);
            });

            if (bounds.length) {
                map.fitBounds(bounds, { padding: [24, 24] });
                setStatus("Showing " + bounds.length + " other structures for this road.", "success");
            } else {
                setStatus("No other structures found for this road yet.");
            }
        }

        function fetchFeatures(roadId) {
            if (!roadId) {
                setStatus("Select a road to load nearby structures.");
                if (overlayGroup) {
                    overlayGroup.clearLayers();
                }
                return;
            }
            try {
                var url = new URL(overlayUrl, window.location.origin);
                url.searchParams.set("road_id", roadId);
                if (config && config.instanceId) {
                    url.searchParams.set("exclude_id", config.instanceId);
                }
                setStatus("Loading structures…");
                fetch(url.toString(), { headers: { Accept: "application/json" } })
                    .then(function (response) {
                        if (!response.ok) {
                            throw new Error("Failed to load structures");
                        }
                        return response.json();
                    })
                    .then(function (payload) {
                        renderFeatures(payload.features || []);
                    })
                    .catch(function () {
                        setStatus("Unable to load structures for this road.", "error");
                    });
            } catch (err) {
                setStatus("Unable to build the structures overlay.", "error");
            }
        }

        var roadSelect = document.getElementById("id_road");
        if (roadSelect) {
            roadSelect.addEventListener("change", function () {
                fetchFeatures(roadSelect.value);
            });
        }

        fetchFeatures(currentRoadId());
    });
})();
