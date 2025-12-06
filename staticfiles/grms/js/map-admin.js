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

    function toLatLng(point) {
        if (!point) {
            return null;
        }
        if (Array.isArray(point) && point.length >= 2) {
            const lat = Number(point[0]);
            const lng = Number(point[1]);
            return Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
        }
        if (Number.isFinite(point.lat) && Number.isFinite(point.lng)) {
            return { lat: Number(point.lat), lng: Number(point.lng) };
        }
        if (Number.isFinite(point.latitude) && Number.isFinite(point.longitude)) {
            return { lat: Number(point.latitude), lng: Number(point.longitude) };
        }
        return null;
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
        let geometryLayer;
        let mapClickBound = false;
        let activeMarker = "start";
        const editableMarkers = {};
        let lastPayload = null;
        let roadLayer;
        let sectionLayer;
        let segmentLayer;
        let lastRoadRouteKey;

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

                    if (sectionLayer && routes) {
                        routes.removeLayer(sectionLayer);
                        sectionLayer = null;
                    }

                    if (payload.route && Array.isArray(payload.route.geometry) && payload.route.geometry.length && routes) {
                        const geometry = Array.isArray(payload.route.geometry)
                            ? { type: "LineString", coordinates: payload.route.geometry }
                            : payload.route.geometry;
                        const style = ROUTE_STYLES[(travelMode || "DRIVING").toUpperCase()] || ROUTE_STYLES.DRIVING;
                        sectionLayer = L.geoJSON(geometry, { style }).addTo(routes);
                        map.fitBounds(sectionLayer.getBounds(), { padding: [24, 24] });
                    } else {
                        showStatus("No geometry available — save the record first.", "error");
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
            const rectangle = L.rectangle(bounds, { color: "#16a34a", weight: 3, dashArray: "6 4", fillOpacity: 0.08 });
            rectangle.addTo(overlay);
            return bounds;
        }

        function renderSegmentContext(roadGeometry, roadData, roadRouteKey) {
            if (!routes || !window.MapPreview) {
                return;
            }

            const coords = window.MapPreview.getFlattenedGeometry(roadGeometry);
            if (!coords.length) {
                return;
            }

            const baseRoadGeometry = { type: "LineString", coordinates: coords };

            if (roadLayer) {
                routes.removeLayer(roadLayer);
            }
            roadLayer = L.geoJSON(baseRoadGeometry, { style: { color: "#0f172a", weight: 5, opacity: 1 } }).addTo(routes);
            lastRoadRouteKey = roadRouteKey || "geometry";

            const sectionConfig = config.section || {};
            const sectionSourceGeometry = sectionConfig.geometry || baseRoadGeometry;
            const sectionCoords = window.MapPreview.getFlattenedGeometry(sectionSourceGeometry);
            const sectionLength = sectionConfig.length_km || sectionConfig.end_chainage_km || roadData.length_km;
            const sectionSlice = window.MapPreview.sliceRouteByChainage(
                sectionSourceGeometry,
                sectionLength,
                sectionConfig.start_chainage_km,
                sectionConfig.end_chainage_km,
            );

            const effectiveSectionGeometry = sectionSlice && sectionSlice.length
                ? { type: "LineString", coordinates: sectionSlice }
                : (sectionCoords.length ? { type: "LineString", coordinates: sectionCoords } : null);

            if (sectionLayer) {
                routes.removeLayer(sectionLayer);
                sectionLayer = null;
            }

            if (effectiveSectionGeometry) {
                sectionLayer = L.geoJSON(effectiveSectionGeometry, { style: { color: "#1d4ed8", weight: 6, opacity: 1 } })
                    .addTo(routes);
            }

            if (segmentLayer) {
                routes.removeLayer(segmentLayer);
                segmentLayer = null;
            }

            const segmentConfig = config.segment;
            if (segmentConfig && effectiveSectionGeometry) {
                const segmentSlice = window.MapPreview.sliceRouteByChainage(
                    effectiveSectionGeometry,
                    segmentConfig.length_km || sectionLength,
                    segmentConfig.station_from_km || segmentConfig.start_chainage_km,
                    segmentConfig.station_to_km || segmentConfig.end_chainage_km,
                );
                if (segmentSlice && segmentSlice.length) {
                    segmentLayer = L.geoJSON(
                        { type: "LineString", coordinates: segmentSlice },
                        { style: { color: "#f97316", weight: 7, opacity: 1 } },
                    ).addTo(routes);
                    map.fitBounds(segmentLayer.getBounds(), { padding: [24, 24] });
                } else if (sectionLayer) {
                    map.fitBounds(sectionLayer.getBounds(), { padding: [24, 24] });
                }
            }
        }

        function renderStoredSectionGeometry() {
            const sectionConfig = config.section || {};
            const sectionId = sectionConfig.id;
            const geometryUrl = sectionConfig.geometry_url || (sectionId
                ? `/admin/grms/roadsection/${sectionId}/get_geometry/`
                : null);

            if (!geometryLayer || !map || !sectionId || !geometryUrl) {
                return;
            }

            const startPointConfig = sectionConfig.points && sectionConfig.points.start;
            const endPointConfig = sectionConfig.points && sectionConfig.points.end;

            geometryLayer.clearLayers();

            fetch(geometryUrl)
                .then(function (response) { return response.json(); })
                .then(function (payload) {
                    const rawGeometry = payload && payload.geometry;
                    const parsedGeometry = typeof rawGeometry === "string" ? JSON.parse(rawGeometry) : rawGeometry;
                    const payloadStart = toLatLng(payload && payload.start_point);
                    const payloadEnd = toLatLng(payload && payload.end_point);
                    const startPoint = payloadStart || toLatLng(startPointConfig);
                    const endPoint = payloadEnd || toLatLng(endPointConfig);

                    if (parsedGeometry && Array.isArray(parsedGeometry.coordinates)) {
                        const coords = parsedGeometry.coordinates.map(function (coord) { return [coord[1], coord[0]]; });
                        const line = L.polyline(coords, { color: "#0050ff", weight: 6 }).addTo(geometryLayer);
                        if (startPoint) {
                            L.marker([startPoint.lat, startPoint.lng]).addTo(geometryLayer);
                        }
                        if (endPoint) {
                            L.marker([endPoint.lat, endPoint.lng]).addTo(geometryLayer);
                        }
                        map.fitBounds(line.getBounds());
                        return;
                    }

                    if (startPoint) {
                        L.marker([startPoint.lat, startPoint.lng]).addTo(geometryLayer);
                    }
                    if (endPoint) {
                        L.marker([endPoint.lat, endPoint.lng]).addTo(geometryLayer);
                    }
                })
                .catch(function (err) {
                    console.error(err);
                });
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
                geometryLayer = L.layerGroup().addTo(map);
            } else if (overlay) {
                overlay.clearLayers();
                if (markers) {
                    markers.clearLayers();
                }
                if (routes) {
                    routes.clearLayers();
                    roadLayer = null;
                    sectionLayer = null;
                    lastRoadRouteKey = null;
                }
                if (geometryLayer) {
                    geometryLayer.clearLayers();
                }
            }

            bindMapClick();

            const viewportBounds = addViewport(mapRegion);
            const roadData = Object.assign({}, config.road || {}, { start: roadStart, end: roadEnd });
            const roadRouteKey = roadData && roadData.start && roadData.end
                ? [roadData.start.lat, roadData.start.lng, roadData.end.lat, roadData.end.lng].join("|")
                : null;

            const roadGeometry = (lastPayload && lastPayload.road && lastPayload.road.geometry)
                || (roadData && roadData.geometry);
            if (roadGeometry && (config.section || config.segment)) {
                renderSegmentContext(roadGeometry, roadData || {}, roadRouteKey);
            } else if ((config.section || config.segment) && !roadGeometry) {
                showStatus("Road has no saved geometry. Use Route Preview → Save first.", "error");
            }

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

            if ((config.scope === "section" || config.scope === "segment")
                && config.section && config.section.id) {
                renderStoredSectionGeometry();
            }

            if (Array.isArray(lastPayload && lastPayload.travel_modes) && travelModeSelect) {
                setTravelModeOptions(lastPayload.travel_modes);
            }

            const noGeometryForPreview = (config.section || config.segment) && !roadGeometry;
            if (noGeometryForPreview) {
                showStatus("No geometry available — save the record first.", "error");
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
