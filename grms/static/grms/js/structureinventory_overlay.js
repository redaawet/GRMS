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

    function patchLeafletMapFactory() {
        if (!window.L || L._grmsPatched) {
            return;
        }
        var originalMap = L.map;
        L.map = function () {
            var mapInstance = originalMap.apply(this, arguments);
            try {
                window._grmsLeafletMap = mapInstance;
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
        if (window._grmsLeafletMap) return window._grmsLeafletMap;

        var container =
            document.querySelector(".leaflet-container") ||
            document.querySelector("[id$='_map']") ||
            document.querySelector("#id_location_point");

        if (container && container._grmsLeafletMap) {
            return container._grmsLeafletMap;
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

    function waitForMap(attempts, delay, callback) {
        var tryCount = 0;
        function attempt() {
            var map = findLeafletMap();
            if (map) {
                callback(map);
                return;
            }
            tryCount += 1;
            if (tryCount < attempts) {
                setTimeout(attempt, delay);
            }
        }
        attempt();
    }

    function init() {
        if (!window.L) return;
        patchLeafletMapFactory();

        waitForMap(10, 300, function (map) {
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
        });
    }

    ready(init);
})();
