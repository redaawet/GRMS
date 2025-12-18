(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function getRoadId() {
        var el = document.getElementById("id_road");
        return el && el.value ? el.value : null;
    }

    function getCurrentObjectId() {
        var match = window.location.pathname.match(/\/(\d+)\/change\/$/);
        return match ? parseInt(match[1], 10) : null;
    }

    // Ensure maps created before DOM ready are captured.
    patchLeafletMapFactory();

    function patchLeafletMapFactory() {
        if (!window.L || L._grmsPatched) {
            return;
        }
        var originalMap = L.map;
        L.map = function () {
            var mapInstance = originalMap.apply(this, arguments);
            try {
                window.GRMS_MAPS = window.GRMS_MAPS || {};
                var containerId = mapInstance && mapInstance._container && mapInstance._container.id;
                if (containerId) {
                    window.GRMS_MAPS[containerId] = mapInstance;
                    if (containerId.endsWith("_map")) {
                        var inputId = containerId.replace(/_map$/, "");
                        window.GRMS_MAPS[inputId] = mapInstance;
                    }
                }
                if (mapInstance && mapInstance._container) {
                    mapInstance._container._grmsLeafletMap = mapInstance;
                }
            } catch (err) {
                // ignore
            }
            return mapInstance;
        };
        L._grmsPatched = true;
    }

    function findLeafletMap() {
        if (!window.L) return null;
        var maps = window.GRMS_MAPS || {};
        if (maps["id_location_point"]) {
            return maps["id_location_point"];
        }
        var keys = Object.keys(maps);
        if (keys.length) {
            return maps[keys[0]];
        }

        var containers = document.querySelectorAll(".leaflet-container");
        for (var i = 0; i < containers.length; i++) {
            var c = containers[i];
            if (c._grmsLeafletMap) {
                return c._grmsLeafletMap;
            }
        }
        return null;
    }

    function toLatLng(geometry) {
        if (!geometry || !geometry.coordinates || geometry.coordinates.length < 2) {
            return null;
        }
        return L.latLng(geometry.coordinates[1], geometry.coordinates[0]);
    }

    function markerStyle(feature, isCurrent) {
        var color = isCurrent ? "#1f77b4" : "#ff7f0e";
        return {
            radius: isCurrent ? 9 : 6,
            color: isCurrent ? "#0b3d91" : "#a35400",
            weight: isCurrent ? 3 : 2,
            fillColor: color,
            fillOpacity: 0.9,
        };
    }

    async function loadGeoJson(roadId, currentId) {
        var url = new URL("structures_geojson/", window.location.href);
        url.searchParams.set("road_id", roadId);
        if (currentId) {
            url.searchParams.set("current_id", currentId);
        }
        var resp = await fetch(url.toString(), {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!resp.ok) {
            throw new Error("Failed to load structures GeoJSON");
        }
        return await resp.json();
    }

    async function renderOverlay(map, overlayGroup, currentGroup) {
        var roadId = getRoadId();
        if (!roadId) {
            overlayGroup.clearLayers();
            currentGroup.clearLayers();
            return;
        }

        var currentId = getCurrentObjectId();
        var geojson = await loadGeoJson(roadId, currentId);

        overlayGroup.clearLayers();
        currentGroup.clearLayers();

        var bounds = L.latLngBounds([]);
        (geojson.features || []).forEach(function (feature) {
            if (!feature || feature.geometry?.type !== "Point") {
                return;
            }
            var latlng = toLatLng(feature.geometry);
            if (!latlng) return;

            var id = feature.properties && feature.properties.id ? parseInt(feature.properties.id, 10) : null;
            var isCurrent = Boolean(feature.properties && feature.properties.is_current);
            if (!isCurrent && currentId && id === currentId) {
                isCurrent = true;
            }

            var layer = L.circleMarker(latlng, markerStyle(feature, isCurrent));
            var label = (feature.properties && feature.properties.label) || "Structure";
            layer.bindPopup(label);

            if (isCurrent) {
                layer.addTo(currentGroup);
            } else {
                layer.addTo(overlayGroup);
            }

            bounds.extend(latlng);
        });

        var currentLayers = currentGroup.getLayers();
        if (currentLayers.length) {
            var ll = currentLayers[0].getLatLng();
            map.setView(ll, Math.max(map.getZoom(), 15));
        } else if (bounds.isValid()) {
            map.fitBounds(bounds.pad(0.2));
        }
    }

    function init() {
        if (!window.L) return;
        patchLeafletMapFactory();

        var attempts = 0;
        function attachWhenReady() {
            var map = findLeafletMap();
            if (!map && attempts < 10) {
                attempts += 1;
                setTimeout(attachWhenReady, 300);
                return;
            }
            if (!map) {
                return;
            }
            var overlayGroup = L.layerGroup().addTo(map);
            var currentGroup = L.layerGroup().addTo(map);

            renderOverlay(map, overlayGroup, currentGroup).catch(function (err) {
                console.error(err);
            });

            var roadEl = document.getElementById("id_road");
            if (roadEl) {
                roadEl.addEventListener("change", function () {
                    renderOverlay(map, overlayGroup, currentGroup).catch(function (err) {
                        console.error(err);
                    });
                });
            }
        }

        attachWhenReady();
    }

    ready(init);
})();
