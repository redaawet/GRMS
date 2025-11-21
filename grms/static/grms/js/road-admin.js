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

        function getRoadCoordinates() {
            const coords = {
                start: [parseFloat(startLat.value), parseFloat(startLng.value)],
                end: [parseFloat(endLat.value), parseFloat(endLng.value)],
            };
            if (!coords.start.every(Number.isFinite) || !coords.end.every(Number.isFinite)) {
                return null;
            }
            return coords;
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
            roadLine = L.polyline([coords.start, coords.end]).addTo(map);
            if (shouldFit) {
                map.fitBounds(roadLine.getBounds(), { padding: [40, 40] });
            }
            return true;
        }

        function ensureMapContainer() {
            if (panel.querySelector("#road-map")) {
                return panel.querySelector("#road-map");
            }
            panel.innerHTML = "";
            const mapNode = document.createElement("div");
            mapNode.id = "road-map";
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
                    if (payload.start && !startLat.value) {
                        setInputsFromPoint(payload.start, "start");
                    }
                    if (payload.end && !endLat.value) {
                        setInputsFromPoint(payload.end, "end");
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
            const values = {
                start_lat: parseFloat(startLat.value),
                start_lng: parseFloat(startLng.value),
                end_lat: parseFloat(endLat.value),
                end_lng: parseFloat(endLng.value),
                start_easting: parseFloat(document.getElementById("id_start_easting")?.value),
                start_northing: parseFloat(document.getElementById("id_start_northing")?.value),
                end_easting: parseFloat(document.getElementById("id_end_easting")?.value),
                end_northing: parseFloat(document.getElementById("id_end_northing")?.value),
            };

            const startHasLatLng = Number.isFinite(values.start_lat) && Number.isFinite(values.start_lng);
            const endHasLatLng = Number.isFinite(values.end_lat) && Number.isFinite(values.end_lng);
            const startHasUtm = Number.isFinite(values.start_easting) && Number.isFinite(values.start_northing);
            const endHasUtm = Number.isFinite(values.end_easting) && Number.isFinite(values.end_northing);

            if (!startHasLatLng && !startHasUtm) {
                throw new Error("Enter a valid start latitude/longitude or UTM easting/northing.");
            }
            if (!endHasLatLng && !endHasUtm) {
                throw new Error("Enter a valid end latitude/longitude or UTM easting/northing.");
            }

            return {
                start: startHasLatLng
                    ? { lat: values.start_lat, lng: values.start_lng }
                    : { easting: values.start_easting, northing: values.start_northing },
                end: endHasLatLng
                    ? { lat: values.end_lat, lng: values.end_lng }
                    : { easting: values.end_easting, northing: values.end_northing },
            };
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
                        const latLngs = payload.route.geometry.map(function (coord) {
                            return [coord[1], coord[0]];
                        });
                        const style = ROUTE_STYLES[(payload.travel_mode || travelModeSelect.value || "DRIVING").toUpperCase()] ||
                            ROUTE_STYLES.DRIVING;
                        routeLine = L.polyline(latLngs, style).addTo(map);
                        map.fitBounds(routeLine.getBounds(), { padding: [20, 20] });
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
