(function () {
    "use strict";

    function parseJSONScript(id) {
        const el = document.getElementById(id);
        if (!el) {
            return null;
        }
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            console.error("Invalid configuration", err);
            return null;
        }
    }

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    function formatRouteSummary(summary) {
        if (!summary) {
            return "";
        }
        const parts = [];
        if (summary.distance_text) {
            parts.push("Distance: " + summary.distance_text);
        }
        if (summary.duration_text) {
            parts.push("Duration: " + summary.duration_text);
        }
        if (summary.start_address) {
            parts.push("From: " + summary.start_address);
        }
        if (summary.end_address) {
            parts.push("To: " + summary.end_address);
        }
        return parts.join(" · ");
    }

    const DEFAULT_MAP_REGION = {
        formatted_address: "UTM Zone 37N (Ethiopia)",
        center: { lat: 9.0, lng: 39.0 },
        bounds: {
            northeast: { lat: 15.0, lng: 42.0 },
            southwest: { lat: 3.0, lng: 36.0 },
        },
        viewport: {
            northeast: { lat: 15.0, lng: 42.0 },
            southwest: { lat: 3.0, lng: 36.0 },
        },
    };

    const defaultMapPayload = { map_region: DEFAULT_MAP_REGION };

    const ROUTE_STYLES = {
        DRIVING: { color: "#2563eb", weight: 4, opacity: 0.85 },
        WALKING: { color: "#16a34a", weight: 4, opacity: 0.9 },
        BICYCLING: { color: "#f97316", weight: 4, opacity: 0.9 },
    };

    function initRoadAdmin() {
        const config = parseJSONScript("road-admin-config");
        const panel = document.getElementById("road-map-panel");
        if (!config || !panel) {
            return;
        }

        const routeButton = document.getElementById("road-route-preview");
        const refreshButton = document.getElementById("road-map-refresh");
        const statusEl = document.getElementById("road-map-status");
        const travelModeSelect = document.getElementById("road-travel-mode");
        const zoneSelect = document.getElementById("id_admin_zone");
        const woredaSelect = document.getElementById("id_admin_woreda");
        const markerRadios = document.querySelectorAll('input[name="road-marker"]');
        const startLat = document.getElementById("id_start_lat");
        const startLng = document.getElementById("id_start_lng");
        const endLat = document.getElementById("id_end_lat");
        const endLng = document.getElementById("id_end_lng");
        const startEasting = document.getElementById("id_start_easting");
        const startNorthing = document.getElementById("id_start_northing");
        const endEasting = document.getElementById("id_end_easting");
        const endNorthing = document.getElementById("id_end_northing");

        if (!startLat || !startLng || !endLat || !endLng) {
            return;
        }

        let activeMarker = "start";
        let map;
        let startMarker;
        let endMarker;
        let mapLoaded = false;
        let routeLine;
        let roadLine;

        function showStatus(message, level) {
            if (!statusEl) {
                return;
            }
            statusEl.textContent = message || "";
            statusEl.className = "road-map-panel__status" + (level ? " " + level : "");
        }

        function setActiveMarker(value) {
            activeMarker = value;
        }

        markerRadios.forEach(function (radio) {
            radio.addEventListener("change", function (event) {
                if (event.target.checked) {
                    setActiveMarker(event.target.value);
                }
            });
        });

        function updateMarkerPosition(marker, latInput, lngInput) {
            const lat = parseFloat(latInput.value);
            const lng = parseFloat(lngInput.value);
            if (!isFinite(lat) || !isFinite(lng) || !marker) {
                return;
            }
            const position = [lat, lng];
            marker.setLatLng(position);
            if (map && !map.hasLayer(marker)) {
                marker.addTo(map);
            }
        }

        function syncMarkersFromInputs() {
            updateMarkerPosition(startMarker, startLat, startLng);
            updateMarkerPosition(endMarker, endLat, endLng);
        }

        function readPoint(prefix) {
            const latInput = prefix === "start" ? startLat : endLat;
            const lngInput = prefix === "start" ? startLng : endLng;
            const eastingInput = prefix === "start" ? startEasting : endEasting;
            const northingInput = prefix === "start" ? startNorthing : endNorthing;

            const lat = parseFloat(latInput?.value);
            const lng = parseFloat(lngInput?.value);
            if (Number.isFinite(lat) && Number.isFinite(lng)) {
                return { lat: lat, lng: lng };
            }

            const easting = parseFloat(eastingInput?.value);
            const northing = parseFloat(northingInput?.value);
            if (Number.isFinite(easting) && Number.isFinite(northing) && window.MapPreview && window.MapPreview.utm37ToLatLng) {
                const converted = window.MapPreview.utm37ToLatLng(easting, northing);
                if (converted) {
                    if (!Number.isFinite(lat) && latInput) {
                        latInput.value = converted.lat.toFixed(6);
                    }
                    if (!Number.isFinite(lng) && lngInput) {
                        lngInput.value = converted.lng.toFixed(6);
                    }
                    return converted;
                }
            }
            return null;
        }

        function getRoadCoordinates() {
            const startPoint = readPoint("start");
            const endPoint = readPoint("end");
            if (!startPoint || !endPoint) {
                return null;
            }
            return { start: startPoint, end: endPoint };
        }

        function drawRoadLine(shouldFit) {
            if (!map || !window.L) {
                return false;
            }
            const coords = getRoadCoordinates();
            if (!coords) {
                if (roadLine && map.hasLayer(roadLine)) {
                    map.removeLayer(roadLine);
                }
                roadLine = null;
                return false;
            }
            if (roadLine && map.hasLayer(roadLine)) {
                map.removeLayer(roadLine);
            }
            if (window.RoadPreview && window.RoadPreview.loadRoadLine) {
                roadLine = window.RoadPreview.loadRoadLine(map, coords.start, coords.end, { fit: shouldFit });
            }
            if (!roadLine) {
                showStatus("No geometry available — save the record first.", "error");
                return false;
            }
            if (shouldFit) {
                map.fitBounds(roadLine.getBounds(), { padding: [40, 40] });
            }
            return Boolean(roadLine);
        }

        function ensureMapContainer() {
            if (panel.querySelector("#road-map")) {
                return panel.querySelector("#road-map");
            }
            panel.innerHTML = "";
            const mapNode = document.createElement("div");
            mapNode.id = "road-map";
            mapNode.className = "road-map";
            mapNode.style.minHeight = "360px";
            panel.appendChild(mapNode);
            return mapNode;
        }

        function setInputsFromPoint(point, prefix) {
            if (!point) {
                return;
            }
            const latInput = prefix === "start" ? startLat : endLat;
            const lngInput = prefix === "start" ? startLng : endLng;
            latInput.value = point.lat;
            lngInput.value = point.lng;
        }

        function buildQueryString(params) {
            const searchParams = new URLSearchParams();
            Object.keys(params).forEach(function (key) {
                if (params[key]) {
                    searchParams.append(key, params[key]);
                }
            });
            const query = searchParams.toString();
            if (!query) {
                return "";
            }
            return (config.api.map_context.indexOf("?") === -1 ? "?" : "&") + query;
        }

        function fetchMapContext(extraParams) {
            if (!config.api.map_context) {
                return Promise.resolve(defaultMapPayload);
            }
            const query = extraParams ? buildQueryString(extraParams) : "";
            return fetch(config.api.map_context + query, { credentials: "same-origin" }).then(function (response) {
                if (!response.ok) {
                    return response.json().catch(function () { return {}; }).then(function (payload) {
                        const detail = payload.detail || "Unable to fetch map context.";
                        throw new Error(detail);
                    });
                }
                return response.json();
            });
        }

        function refreshMap(extraParams) {
            showStatus("Requesting map viewport…");
            fetchMapContext(extraParams)
                .then(function (payload) {
                    showStatus("Map context loaded.", "success");
                    if (!mapLoaded) {
                        initialiseMap(payload);
                    }
                    if (payload.road && payload.road.start && !startLat.value) {
                        setInputsFromPoint(payload.road.start, "start");
                    }
                    if (payload.road && payload.road.end && !endLat.value) {
                        setInputsFromPoint(payload.road.end, "end");
                    }
                    syncMarkersFromInputs();
                    const hasRoadLine = drawRoadLine(true);
                    if (!hasRoadLine && mapLoaded) {
                        updateMapViewport(payload);
                    }
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        function initialiseMap(payload) {
            const mapNode = ensureMapContainer();
            const center = (payload.map_region && payload.map_region.center) || DEFAULT_MAP_CENTER;
            if (!window.L) {
                showStatus("Leaflet failed to load.", "error");
                return;
            }
            mapLoaded = true;
            map = L.map(mapNode).setView([center.lat, center.lng], 8);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: "© OpenStreetMap contributors",
                maxZoom: 19,
            }).addTo(map);
            startMarker = L.marker([center.lat, center.lng], { title: "Start" }).addTo(map);
            endMarker = L.marker([center.lat, center.lng], { title: "End" }).addTo(map);
            syncMarkersFromInputs();
            updateMapViewport(payload);
            map.on("click", function (event) {
                const lat = event.latlng.lat;
                const lng = event.latlng.lng;
                if (activeMarker === "end") {
                    endLat.value = lat.toFixed(6);
                    endLng.value = lng.toFixed(6);
                } else {
                    startLat.value = lat.toFixed(6);
                    startLng.value = lng.toFixed(6);
                }
                syncMarkersFromInputs();
                drawRoadLine(true);
            });
        }

        function updateMapViewport(payload) {
            if (!map) {
                return;
            }
            const bounds = payload.map_region && (payload.map_region.bounds || payload.map_region.viewport);
            if (bounds && bounds.northeast && bounds.southwest) {
                const sw = bounds.southwest;
                const ne = bounds.northeast;
                const mapBounds = L.latLngBounds(
                    [sw.lat, sw.lng],
                    [ne.lat, ne.lng]
                );
                map.fitBounds(mapBounds);
            } else if (payload.map_region && payload.map_region.center) {
                map.setView([payload.map_region.center.lat, payload.map_region.center.lng]);
            }
        }

        function ensureCoordinates() {
            const startPoint = readPoint("start");
            const endPoint = readPoint("end");

            if (!startPoint) {
                throw new Error("Enter a valid start latitude/longitude or UTM easting/northing.");
            }
            if (!endPoint) {
                throw new Error("Enter a valid end latitude/longitude or UTM easting/northing.");
            }

            return { start: startPoint, end: endPoint };
        }

        function previewRoute() {
            let coords;
            try {
                coords = ensureCoordinates();
            } catch (err) {
                showStatus(err.message, "error");
                return;
            }
            showStatus("Requesting route preview…");
            fetch(config.api.route, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify({
                    start: coords.start,
                    end: coords.end,
                    travel_mode: travelModeSelect ? travelModeSelect.value : "DRIVING",
                }),
            })
                .then(function (response) {
                    if (!response.ok) {
                        return response.json().catch(function () { return {}; }).then(function (payload) {
                            throw new Error(payload.detail || "Unable to fetch a route preview.");
                        });
                    }
                    return response.json();
                })
                .then(function (payload) {
                    const summary = formatRouteSummary(payload.route);
                    if (summary) {
                        showStatus(summary, "success");
                    } else {
                        showStatus("Route retrieved successfully.", "success");
                    }
                    if (payload.start && payload.end) {
                        startLat.value = payload.start.lat;
                        startLng.value = payload.start.lng;
                        endLat.value = payload.end.lat;
                        endLng.value = payload.end.lng;
                    }
                    if (payload.route && payload.route.geometry && payload.route.geometry.length && map) {
                        if (routeLine) {
                            map.removeLayer(routeLine);
                        }
                        const geometry = Array.isArray(payload.route.geometry)
                            ? { type: "LineString", coordinates: payload.route.geometry }
                            : payload.route.geometry;
                        const style = ROUTE_STYLES[(payload.travel_mode || travelModeSelect.value || "DRIVING").toUpperCase()] ||
                            ROUTE_STYLES.DRIVING;
                        routeLine = L.geoJSON(geometry, { style }).addTo(map);
                        map.fitBounds(routeLine.getBounds(), { padding: [20, 20] });
                    } else {
                        showStatus("No geometry available — save the record first.", "error");
                    }
                    syncMarkersFromInputs();
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        function setDefaultTravelMode() {
            if (!travelModeSelect) {
                return;
            }
            const desired = "DRIVING";
            if (travelModeSelect.querySelector(`option[value="${desired}"]`)) {
                travelModeSelect.value = desired;
            }
        }

        [startLat, startLng, endLat, endLng].forEach(function (input) {
            input.addEventListener("change", function () {
                syncMarkersFromInputs();
                drawRoadLine(true);
            });
            input.addEventListener("input", function () {
                // Delay updates to avoid noisy marker moves during typing.
                clearTimeout(input._roadAdminTimer);
                input._roadAdminTimer = setTimeout(function () {
                    syncMarkersFromInputs();
                    drawRoadLine(true);
                }, 400);
            });
        });

        [startEasting, startNorthing, endEasting, endNorthing].forEach(function (input) {
            if (!input) {
                return;
            }
            input.addEventListener("change", function () {
                syncMarkersFromInputs();
                drawRoadLine(true);
            });
        });

        if (zoneSelect) {
            zoneSelect.addEventListener("change", function () {
                const params = {
                    zone_id: zoneSelect.value || "",
                    woreda_id: woredaSelect ? woredaSelect.value : "",
                };
                refreshMap(params);
            });
        }

        if (woredaSelect) {
            woredaSelect.addEventListener("change", function () {
                const params = {
                    zone_id: zoneSelect ? zoneSelect.value : "",
                    woreda_id: woredaSelect.value || "",
                };
                refreshMap(params);
            });
        }

        if (refreshButton) {
            refreshButton.addEventListener("click", function () {
                const params = {
                    zone_id: zoneSelect ? zoneSelect.value : "",
                    woreda_id: woredaSelect ? woredaSelect.value : "",
                };
                refreshMap(params);
            });
        }

        if (routeButton) {
            if (!config.api.route) {
                routeButton.disabled = true;
                routeButton.title = "Save the road to enable server-powered route previews.";
            } else {
                routeButton.addEventListener("click", previewRoute);
            }
        }

        setDefaultTravelMode();

        if (!config.road_id) {
            showStatus(
                "Displaying default map view (Zone 37N). Set start/end coordinates now; saving will keep them and enable routing.",
            );
        }

        refreshMap();
    }

    document.addEventListener("DOMContentLoaded", initRoadAdmin);
})();
