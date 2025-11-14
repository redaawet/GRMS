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

    function loadGoogleMaps(apiKey) {
        if (window.google && window.google.maps) {
            return Promise.resolve(window.google.maps);
        }
        if (!apiKey) {
            return Promise.reject(new Error("Google Maps API key is not configured."));
        }
        return new Promise(function (resolve, reject) {
            const script = document.createElement("script");
            script.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(apiKey);
            script.async = true;
            script.onerror = function () {
                reject(new Error("Unable to load Google Maps."));
            };
            script.onload = function () {
                if (window.google && window.google.maps) {
                    resolve(window.google.maps);
                } else {
                    reject(new Error("Google Maps API did not initialise."));
                }
            };
            document.head.appendChild(script);
        });
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

        function showStatus(message, level) {
            if (!statusEl) {
                return;
            }
            statusEl.textContent = message || "";
            statusEl.className = "road-map-panel__status" + (level ? " " + level : "");
        }

        function disableMapInteractions() {
            if (panel) {
                panel.classList.add("road-map-panel--disabled");
            }
            [routeButton, refreshButton].forEach(function (btn) {
                if (btn) {
                    btn.disabled = true;
                }
            });
            if (travelModeSelect) {
                travelModeSelect.disabled = true;
            }
            markerRadios.forEach(function (radio) {
                radio.disabled = true;
            });
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
            const position = { lat: lat, lng: lng };
            marker.setPosition(position);
            if (map) {
                marker.setMap(map);
            }
        }

        function syncMarkersFromInputs() {
            updateMarkerPosition(startMarker, startLat, startLng);
            updateMarkerPosition(endMarker, endLat, endLng);
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
                return Promise.reject(new Error("Save the road before using the map."));
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
            showStatus("Requesting Google Maps viewport…");
            fetchMapContext(extraParams)
                .then(function (payload) {
                    showStatus("Map context loaded.", "success");
                    if (!mapLoaded) {
                        loadGoogleMaps(config.google_maps_api_key)
                            .then(function () {
                                initialiseMap(payload);
                            })
                            .catch(function (err) {
                                showStatus(err.message, "error");
                            });
                    } else {
                        updateMapViewport(payload);
                    }
                    if (payload.start && !startLat.value) {
                        setInputsFromPoint(payload.start, "start");
                    }
                    if (payload.end && !endLat.value) {
                        setInputsFromPoint(payload.end, "end");
                    }
                    syncMarkersFromInputs();
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        function initialiseMap(payload) {
            mapLoaded = true;
            const mapNode = ensureMapContainer();
            const center = (payload.map_region && payload.map_region.center) || { lat: 13.5, lng: 39.5 };
            map = new google.maps.Map(mapNode, {
                center: center,
                zoom: 10,
                mapTypeControl: false,
            });
            startMarker = new google.maps.Marker({
                label: "A",
                draggable: false,
            });
            endMarker = new google.maps.Marker({
                label: "B",
                draggable: false,
            });
            syncMarkersFromInputs();
            updateMapViewport(payload);
            map.addListener("click", function (event) {
                const lat = event.latLng.lat();
                const lng = event.latLng.lng();
                if (activeMarker === "end") {
                    endLat.value = lat.toFixed(6);
                    endLng.value = lng.toFixed(6);
                } else {
                    startLat.value = lat.toFixed(6);
                    startLng.value = lng.toFixed(6);
                }
                syncMarkersFromInputs();
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
                const mapBounds = new google.maps.LatLngBounds(
                    new google.maps.LatLng(sw.lat, sw.lng),
                    new google.maps.LatLng(ne.lat, ne.lng)
                );
                map.fitBounds(mapBounds);
            } else if (payload.map_region && payload.map_region.center) {
                map.setCenter(payload.map_region.center);
            }
        }

        function ensureCoordinates() {
            const values = {
                start_lat: parseFloat(startLat.value),
                start_lng: parseFloat(startLng.value),
                end_lat: parseFloat(endLat.value),
                end_lng: parseFloat(endLng.value),
            };
            if (!isFinite(values.start_lat) || !isFinite(values.start_lng)) {
                throw new Error("Enter a valid start latitude and longitude.");
            }
            if (!isFinite(values.end_lat) || !isFinite(values.end_lng)) {
                throw new Error("Enter a valid end latitude and longitude.");
            }
            return values;
        }

        function previewRoute() {
            if (!config.api.route) {
                showStatus("Save the road before requesting a preview.", "error");
                return;
            }
            let coords;
            try {
                coords = ensureCoordinates();
            } catch (err) {
                showStatus(err.message, "error");
                return;
            }
            showStatus("Requesting Google Maps route…");
            fetch(config.api.route, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify({
                    start: { lat: coords.start_lat, lng: coords.start_lng },
                    end: { lat: coords.end_lat, lng: coords.end_lng },
                    travel_mode: travelModeSelect ? travelModeSelect.value : "DRIVING",
                }),
            })
                .then(function (response) {
                    if (!response.ok) {
                        return response.json().catch(function () { return {}; }).then(function (payload) {
                            throw new Error(payload.detail || "Unable to fetch Google Maps route.");
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
                    syncMarkersFromInputs();
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        [startLat, startLng, endLat, endLng].forEach(function (input) {
            input.addEventListener("change", syncMarkersFromInputs);
            input.addEventListener("input", function () {
                // Delay updates to avoid noisy marker moves during typing.
                clearTimeout(input._roadAdminTimer);
                input._roadAdminTimer = setTimeout(syncMarkersFromInputs, 400);
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
            routeButton.addEventListener("click", previewRoute);
        }

        if (!config.google_maps_api_key) {
            disableMapInteractions();
            showStatus(
                "Google Maps integration is disabled because the GOOGLE_MAPS_API_KEY environment variable is not configured.",
                "error"
            );
            return;
        }

        if (!config.road_id) {
            showStatus("Save the road record before using the map integration.", "error");
            return;
        }

        refreshMap();
    }

    document.addEventListener("DOMContentLoaded", initRoadAdmin);
})();
