(function () {
    "use strict";

    function parseConfig() {
        const el = document.getElementById("station-map-config");
        if (!el) {
            return null;
        }
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            console.error("Invalid station map config", err);
            return null;
        }
    }

    function formatBounds(region) {
        const viewport = region?.viewport || region?.bounds;
        if (!viewport || !viewport.northeast || !viewport.southwest) {
            return null;
        }
        return [
            [viewport.southwest.lat, viewport.southwest.lng],
            [viewport.northeast.lat, viewport.northeast.lng],
        ];
    }

    function ensureProjections() {
        if (!window.proj4) {
            throw new Error("Projection library failed to load.");
        }
        if (!proj4.defs["EPSG:32637"]) {
            proj4.defs("EPSG:32637", "+proj=utm +zone=37 +datum=WGS84 +units=m +no_defs");
        }
    }

    function utmToLatLng(easting, northing) {
        ensureProjections();
        const [lng, lat] = proj4("EPSG:32637", "EPSG:4326", [easting, northing]);
        return { lat, lng };
    }

    function latLngToUtm(lat, lng) {
        ensureProjections();
        const [easting, northing] = proj4("EPSG:4326", "EPSG:32637", [lng, lat]);
        return { easting, northing };
    }

    function readEastingNorthing(eastingInput, northingInput) {
        if (!eastingInput || !northingInput) {
            return null;
        }
        const easting = parseFloat(eastingInput.value);
        const northing = parseFloat(northingInput.value);
        if (!Number.isFinite(easting) || !Number.isFinite(northing)) {
            return null;
        }
        return { easting, northing };
    }

    function formatRoadLayer(payload) {
        if (!payload || !payload.geometry) {
            return null;
        }
        try {
            return L.geoJSON(payload.geometry, { style: { color: "#0f172a", weight: 5, opacity: 0.85 } });
        } catch (err) {
            console.warn("Unable to render road geometry", err);
            return null;
        }
    }

    function initMap() {
        const mapContainer = document.getElementById("traffic-station-map");
        const statusEl = document.getElementById("traffic-station-status");
        const config = parseConfig();
        if (!mapContainer || !config) {
            return;
        }

        if (!window.L) {
            if (statusEl) {
                statusEl.textContent = "Map preview unavailable because Leaflet failed to load.";
                statusEl.className = "traffic-station-panel__status error";
            }
            return;
        }

        const eastingInput = document.getElementById("id_station_easting");
        const northingInput = document.getElementById("id_station_northing");

        const bounds = formatBounds(config.map_region || {});
        const map = L.map(mapContainer);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        if (bounds) {
            map.fitBounds(bounds, { padding: [20, 20] });
        } else if (config.map_region?.center) {
            map.setView([config.map_region.center.lat, config.map_region.center.lng], config.map_region.center.zoom || 10);
        }

        const overlay = L.layerGroup().addTo(map);
        let marker = null;

        function setStatus(message, level) {
            if (!statusEl) {
                return;
            }
            statusEl.textContent = message || "";
            statusEl.className = "traffic-station-panel__status" + (level ? " " + level : "");
        }

        function placeMarker(lat, lng, focus) {
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
                return;
            }
            if (!marker) {
                marker = L.circleMarker([lat, lng], {
                    radius: 12,
                    color: "#dc2626",
                    fillColor: "#f87171",
                    fillOpacity: 0.85,
                    weight: 4,
                }).addTo(map);
            } else {
                marker.setLatLng([lat, lng]);
            }
            if (focus) {
                map.setView([lat, lng], Math.max(map.getZoom(), 14));
            }
        }

        function updateFromInputs(focus) {
            const utm = readEastingNorthing(eastingInput, northingInput);
            if (!utm) {
                return;
            }
            try {
                const { lat, lng } = utmToLatLng(utm.easting, utm.northing);
                placeMarker(lat, lng, focus);
                setStatus("Station preview updated from easting/northing.");
            } catch (err) {
                console.error(err);
                setStatus("Unable to convert easting/northing to a map location.", "error");
            }
        }

        function handleMapClick(event) {
            const { lat, lng } = event.latlng || {};
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
                return;
            }
            try {
                const utm = latLngToUtm(lat, lng);
                if (eastingInput && northingInput) {
                    eastingInput.value = utm.easting.toFixed(2);
                    northingInput.value = utm.northing.toFixed(2);
                }
                placeMarker(lat, lng, true);
                setStatus("Map click captured: easting and northing updated from the selected point.");
            } catch (err) {
                console.error(err);
                setStatus("Unable to convert the selected point into UTM coordinates.", "error");
            }
        }

        map.on("click", handleMapClick);
        eastingInput?.addEventListener("change", () => updateFromInputs(false));
        northingInput?.addEventListener("change", () => updateFromInputs(false));

        if (config.station && Number.isFinite(config.station.lat) && Number.isFinite(config.station.lng)) {
            placeMarker(config.station.lat, config.station.lng, true);
            if (eastingInput && northingInput) {
                const utm = latLngToUtm(config.station.lat, config.station.lng);
                eastingInput.value = eastingInput.value || utm.easting.toFixed(2);
                northingInput.value = northingInput.value || utm.northing.toFixed(2);
            }
            setStatus("Loaded existing station location.");
        } else {
            updateFromInputs(true);
        }

        if (config.api?.map_context) {
            fetch(config.api.map_context)
                .then((response) => response.ok ? response.json() : Promise.reject(response.statusText))
                .then((payload) => {
                    const roadLayer = formatRoadLayer(payload.road);
                    if (roadLayer) {
                        overlay.addLayer(roadLayer);
                        if (!marker && roadLayer.getBounds && roadLayer.getBounds().isValid()) {
                            map.fitBounds(roadLayer.getBounds(), { padding: [16, 16] });
                        }
                    }
                })
                .catch((err) => console.warn("Unable to load road context", err));
        }

        const placeholder = mapContainer.querySelector(".traffic-station-panel__placeholder");
        if (placeholder) {
            placeholder.remove();
        }
    }

    document.addEventListener("DOMContentLoaded", initMap);
})();
