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

    function clampFraction(value) {
        if (!Number.isFinite(value)) {
            return null;
        }
        return Math.max(0, Math.min(1, value));
    }

    function interpolatePoint(start, end, fraction) {
        const clamped = clampFraction(fraction);
        if (!start || !end || clamped === null) {
            return null;
        }
        return [
            start.lat + (end.lat - start.lat) * clamped,
            start.lng + (end.lng - start.lng) * clamped,
        ];
    }

    function formatBounds(bounds) {
        if (!bounds) {
            return null;
        }
        if (bounds.northeast && bounds.southwest) {
            return [
                [bounds.southwest.lat, bounds.southwest.lng],
                [bounds.northeast.lat, bounds.northeast.lng],
            ];
        }
        if (typeof bounds.south === "number" && typeof bounds.west === "number"
            && typeof bounds.north === "number" && typeof bounds.east === "number") {
            return [
                [bounds.south, bounds.west],
                [bounds.north, bounds.east],
            ];
        }
        return null;
    }

    function readPointFromInputs(latInput, lngInput) {
        if (!latInput || !lngInput) {
            return null;
        }
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return null;
        }
        return { lat: lat, lng: lng };
    }

    const DEFAULT_MAP_REGION = {
        formatted_address: "UTM Zone 37N (Ethiopia)",
        center: { lat: 9.0, lng: 39.0 },
        viewport: {
            northeast: { lat: 15.0, lng: 42.0 },
            southwest: { lat: 3.0, lng: 36.0 },
        },
    };

    const ROUTE_STYLES = {
        DRIVING: { color: "#2563eb", weight: 5, opacity: 0.85 },
        WALKING: { color: "#16a34a", weight: 5, opacity: 0.9 },
        BICYCLING: { color: "#f97316", weight: 5, opacity: 0.9 },
    };

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

    function initMapAdmin() {
        const config = parseJSONScript("map-admin-config");
        const hasParentGeometry = Boolean(config && config.section && config.section.has_parent_geometry);
        const panel = document.getElementById("map-panel");
        const refreshButton = document.getElementById("map-panel-refresh");
        const statusEl = document.getElementById("map-panel-status");
        const viewport = document.getElementById("map-panel-viewport");
        const travelModeSelect = document.getElementById("map-travel-mode");
        const routeButton = document.getElementById("map-route-preview");
        const startLatInput = document.getElementById("id_start_lat");
        const startLngInput = document.getElementById("id_start_lng");
        const endLatInput = document.getElementById("id_end_lat");
        const endLngInput = document.getElementById("id_end_lng");
        const startEastingInput = document.getElementById("id_start_easting");
        const startNorthingInput = document.getElementById("id_start_northing");
        const endEastingInput = document.getElementById("id_end_easting");
        const endNorthingInput = document.getElementById("id_end_northing");
        const markerRadios = document.querySelectorAll('input[name="section-marker"]');
        const allowEditing = Boolean(startLatInput && startLngInput && endLatInput && endLngInput);

        if (!config || !panel || !viewport) {
            return;
        }

        if (!window.L) {
            if (statusEl) {
                statusEl.textContent = "Leaflet failed to load.";
                statusEl.className = "road-map-panel__status error";
            }
            return;
        }

        let map;
        let overlay;
        let markers;
        let routes;
        let mapClickBound = false;
        let activeMarker = "start";
        const editableMarkers = {};
        let lastPayload = null;
        let routeLine;

        function showStatus(message, level) {
            if (!statusEl) {
                return;
            }
            statusEl.textContent = message || "";
            statusEl.className = "road-map-panel__status" + (level ? " " + level : "");
        }

        function setInputsFromLatLng(prefix, lat, lng) {
            if (!allowEditing) {
                return;
            }
            const latInput = prefix === "end" ? endLatInput : startLatInput;
            const lngInput = prefix === "end" ? endLngInput : startLngInput;
            if (!latInput || !lngInput) {
                return;
            }
            latInput.value = lat.toFixed(6);
            lngInput.value = lng.toFixed(6);
        }

        function ensureCoordinates() {
            if (hasParentGeometry) {
                return null;
            }
            const values = {
                start_lat: parseFloat(startLatInput?.value),
                start_lng: parseFloat(startLngInput?.value),
                end_lat: parseFloat(endLatInput?.value),
                end_lng: parseFloat(endLngInput?.value),
                start_easting: parseFloat(startEastingInput?.value),
                start_northing: parseFloat(startNorthingInput?.value),
                end_easting: parseFloat(endEastingInput?.value),
                end_northing: parseFloat(endNorthingInput?.value),
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

        if (hasParentGeometry) {
            [
                "id_start_lat",
                "id_start_lng",
                "id_end_lat",
                "id_end_lng",
                "id_start_easting",
                "id_start_northing",
                "id_end_easting",
                "id_end_northing",
            ].forEach(function (id) {
                const input = document.getElementById(id);
                const row = input && input.closest(".form-row");
                if (row) {
                    row.style.display = "none";
                }
            });
        }

        function setActiveMarker(value) {
            activeMarker = value === "end" ? "end" : "start";
        }

        markerRadios.forEach(function (radio) {
            radio.addEventListener("change", function (event) {
                if (event.target.checked) {
                    setActiveMarker(event.target.value);
                }
            });
        });

        function updateEditableMarker(prefix, point) {
            if (!allowEditing || !markers || !point || !window.L) {
                return;
            }
            let marker = editableMarkers[prefix];
            if (!marker) {
                marker = L.marker([point.lat, point.lng], { draggable: true, title: prefix === "end" ? "Section end" : "Section start" });
                marker.on("dragend", function (event) {
                    const pos = event.target.getLatLng();
                    setInputsFromLatLng(prefix, pos.lat, pos.lng);
                    refreshFromInputs();
                });
                editableMarkers[prefix] = marker;
            } else {
                marker.setLatLng([point.lat, point.lng]);
            }
            if (!markers.hasLayer(marker)) {
                marker.addTo(markers);
            }
        }

        function syncEditableMarkers(startPoint, endPoint) {
            if (!allowEditing || !markers) {
                return;
            }
            if (startPoint) {
                updateEditableMarker("start", startPoint);
            }
            if (endPoint) {
                updateEditableMarker("end", endPoint);
            }
        }

        function refreshFromInputs() {
            if (!lastPayload) {
                return;
            }
            renderMap(lastPayload);
        }

        function bindMapClick() {
            if (!allowEditing || !map || mapClickBound) {
                return;
            }
            map.on("click", function (event) {
                setInputsFromLatLng(activeMarker, event.latlng.lat, event.latlng.lng);
                refreshFromInputs();
            });
            mapClickBound = true;
        }

        function ensureMapContainer() {
            const existing = viewport.querySelector("#map-view");
            if (existing) {
                return existing;
            }
            viewport.innerHTML = "";
            const mapNode = document.createElement("div");
            mapNode.id = "map-view";
            mapNode.className = "road-map";
            mapNode.style.minHeight = "360px";
            viewport.appendChild(mapNode);
            return mapNode;
        }

        function setTravelModeOptions(modes) {
            if (!travelModeSelect || !Array.isArray(modes) || !modes.length) {
                return;
            }
            travelModeSelect.innerHTML = "";
            modes.forEach(function (mode) {
                const option = document.createElement("option");
                option.value = mode;
                option.textContent = mode.charAt(0) + mode.slice(1).toLowerCase();
                travelModeSelect.appendChild(option);
            });
            setDefaultTravelMode();
        }

        function setDefaultTravelMode() {
            if (!travelModeSelect) {
                return;
            }
            const desired = (config.default_travel_mode || "DRIVING").toUpperCase();
            if (travelModeSelect.querySelector(`option[value="${desired}"]`)) {
                travelModeSelect.value = desired;
            }
        }

        function previewRoute() {
            if (!routeButton || !allowEditing || !config.api || !config.api.route) {
                return;
            }
            let coords;
            try {
                coords = ensureCoordinates();
            } catch (err) {
                showStatus(err.message, "error");
                return;
            }

            if (!coords) {
                showStatus("Parent geometry is already available for preview.", "success");
                refreshFromInputs();
                return;
            }

            const travelMode = travelModeSelect ? travelModeSelect.value : (config.default_travel_mode || "DRIVING");
            showStatus("Requesting route preview…");

            fetch(config.api.route, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "",
                },
                body: JSON.stringify({
                    start: coords.start,
                    end: coords.end,
                    travel_mode: travelMode,
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
                        setInputsFromLatLng("start", payload.start.lat, payload.start.lng);
                        setInputsFromLatLng("end", payload.end.lat, payload.end.lng);
                    }

                    if (routes) {
                        routes.clearLayers();
                    }

                    if (payload.route && Array.isArray(payload.route.geometry) && payload.route.geometry.length && routes) {
                        const latLngs = payload.route.geometry.map(function (coord) {
                            return [coord[1], coord[0]];
                        });
                        const style = ROUTE_STYLES[(travelMode || "DRIVING").toUpperCase()] || ROUTE_STYLES.DRIVING;
                        const line = L.polyline(latLngs, style).addTo(routes);
                        map.fitBounds(line.getBounds(), { padding: [24, 24] });
                    }

                    syncEditableMarkers(readPointFromInputs(startLatInput, startLngInput), readPointFromInputs(endLatInput, endLngInput));
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        function addViewport(region) {
            if (!region || !overlay) {
                return null;
            }
            const bounds = formatBounds(region.viewport || region.bounds);
            if (!bounds) {
                return null;
            }
            const rectangle = L.rectangle(bounds, { color: "#22c55e", weight: 2, dashArray: "6 4", fillOpacity: 0.05 });
            rectangle.addTo(overlay);
            return bounds;
        }

        function renderMap(payload) {
            lastPayload = payload || lastPayload || {};
            const mapNode = ensureMapContainer();
            const mapRegion = (lastPayload && lastPayload.map_region) || DEFAULT_MAP_REGION;
            const center = (mapRegion && mapRegion.center) || DEFAULT_MAP_REGION.center;

            const roadStart = (lastPayload && lastPayload.road && lastPayload.road.start) || (config.road && config.road.start);
            const roadEnd = (lastPayload && lastPayload.road && lastPayload.road.end) || (config.road && config.road.end);
            if (!map) {
                map = L.map(mapNode).setView([center.lat, center.lng], mapRegion.zoom || 7);
                L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    maxZoom: 18,
                    attribution: "© OpenStreetMap contributors",
                }).addTo(map);
                overlay = L.layerGroup().addTo(map);
                markers = L.layerGroup().addTo(map);
                routes = L.layerGroup().addTo(map);
            } else if (overlay) {
                overlay.clearLayers();
                if (markers) {
                    markers.clearLayers();
                }
                if (routes) {
                    routes.clearLayers();
                }
            }

            bindMapClick();

            const viewportBounds = addViewport(mapRegion);
            const roadData = Object.assign({}, config.road || {}, { start: roadStart, end: roadEnd });

            if (viewportBounds) {
                map.fitBounds(viewportBounds, { padding: [24, 24] });
            } else if (roadStart && roadEnd) {
                const roadBounds = L.latLngBounds(
                    [roadStart.lat, roadStart.lng],
                    [roadEnd.lat, roadEnd.lng]
                );
                map.fitBounds(roadBounds, { padding: [30, 30] });
            }

            const configPoints = (config.section && config.section.points) || {};
            const startPoint = readPointFromInputs(startLatInput, startLngInput) || configPoints.start;
            const endPoint = readPointFromInputs(endLatInput, endLngInput) || configPoints.end;

            if (startPoint && markers) {
                if (allowEditing) {
                    syncEditableMarkers(startPoint, null);
                } else {
                    L.circleMarker([startPoint.lat, startPoint.lng], {
                        radius: 7,
                        color: "#0ea5e9",
                        weight: 3,
                        fillColor: "#38bdf8",
                        fillOpacity: 0.8,
                    })
                        .bindTooltip("Section start", { permanent: false })
                        .addTo(markers);
                }
            }

            if (endPoint && markers) {
                if (allowEditing) {
                    syncEditableMarkers(null, endPoint);
                } else {
                    L.circleMarker([endPoint.lat, endPoint.lng], {
                        radius: 7,
                        color: "#0ea5e9",
                        weight: 3,
                        fillColor: "#0ea5e9",
                        fillOpacity: 0.85,
                    })
                        .bindTooltip("Section end", { permanent: false })
                        .addTo(markers);
                }
            }

            if (Array.isArray(lastPayload && lastPayload.travel_modes) && travelModeSelect) {
                setTravelModeOptions(lastPayload.travel_modes);
            }
        }

        function buildQueryString() {
            const params = new URLSearchParams();
            const adminFields = config.admin_fields || {};
            const defaults = config.default_admin_selection || {};

            if (adminFields.zone_override) {
                const zone = document.getElementById(adminFields.zone_override);
                if (zone && zone.value) {
                    params.append("zone_id", zone.value);
                }
            } else if (defaults.zone_id) {
                params.append("zone_id", defaults.zone_id);
            }

            if (adminFields.woreda_override) {
                const woreda = document.getElementById(adminFields.woreda_override);
                if (woreda && woreda.value) {
                    params.append("woreda_id", woreda.value);
                }
            } else if (defaults.woreda_id) {
                params.append("woreda_id", defaults.woreda_id);
            }

            const query = params.toString();
            if (!query) {
                return "";
            }
            const base = panel.dataset.mapContextUrl || "";
            return (base.indexOf("?") === -1 ? "?" : "&") + query;
        }

        function fetchMapContext() {
            const baseUrl = panel.dataset.mapContextUrl;
            if (!baseUrl) {
                showStatus("Map context is not available.", "error");
                return;
            }
            const query = buildQueryString();
            showStatus("Loading map context…");
            fetch(baseUrl + query, { credentials: "same-origin" })
                .then(function (response) {
                    if (!response.ok) {
                        return response.json().catch(function () { return {}; }).then(function (payload) {
                            const detail = payload.detail || "Unable to load map context.";
                            throw new Error(detail);
                        });
                    }
                    return response.json();
                })
                .then(function (payload) {
                    showStatus("Map context loaded.", "success");
                    renderMap(payload);
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        if (allowEditing) {
            [startLatInput, startLngInput, endLatInput, endLngInput].forEach(function (input) {
                if (!input) {
                    return;
                }
                input.addEventListener("change", refreshFromInputs);
                input.addEventListener("input", function () {
                    clearTimeout(input._mapAdminTimer);
                    input._mapAdminTimer = setTimeout(refreshFromInputs, 350);
                });
            });
        }

        if (refreshButton) {
            refreshButton.addEventListener("click", function () {
                fetchMapContext();
            });
        }

        if (routeButton && allowEditing && config.api && config.api.route) {
            routeButton.addEventListener("click", previewRoute);
        }

        setDefaultTravelMode();

        fetchMapContext();
    }

    document.addEventListener("DOMContentLoaded", initMapAdmin);
})();
