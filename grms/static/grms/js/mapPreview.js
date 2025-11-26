(function (root) {
    "use strict";

    // Color palette for preview layers
    const COLORS = {
        road: { color: "#cbd5e1", weight: 4, opacity: 0.75 },
        section: { color: "#1d4ed8", weight: 5, opacity: 0.9 },
        segment: { color: "#06b6d4", weight: 6, opacity: 0.95 },
    };

    function ensureLeaflet() {
        if (!root.L) {
            throw new Error("Leaflet must be loaded before initializing the map.");
        }
    }

    function getFlattenedGeometry(geojson) {
        const geometry = geojson?.type === "Feature" ? geojson.geometry : geojson;
        if (!geometry || !geometry.type || !geometry.coordinates) {
            return [];
        }
        if (geometry.type === "LineString" && Array.isArray(geometry.coordinates)) {
            return geometry.coordinates;
        }
        if (geometry.type === "MultiLineString" && Array.isArray(geometry.coordinates)) {
            return geometry.coordinates.flat().filter(Array.isArray);
        }
        return [];
    }

    function normaliseGeometry(geojson) {
        const flattened = getFlattenedGeometry(geojson);
        if (!flattened.length) {
            return null;
        }
        return { type: "LineString", coordinates: flattened };
    }

    function isDirectFlightLine(coords, start, end) {
        if (!Array.isArray(coords) || coords.length !== 2 || !start || !end) {
            return false;
        }

        const tolerance = 1e-6;
        const matches = (point, reference) => (
            Math.abs(point[0] - reference.lng) <= tolerance && Math.abs(point[1] - reference.lat) <= tolerance
        );

        return matches(coords[0], start) && matches(coords[1], end);
    }

    function initMap(divId, mapRegion) {
        ensureLeaflet();
        const map = root.L.map(divId);
        root.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        if (mapRegion?.viewport?.northeast && mapRegion?.viewport?.southwest) {
            const { northeast, southwest } = mapRegion.viewport;
            const bounds = root.L.latLngBounds(
                [southwest.lat, southwest.lng],
                [northeast.lat, northeast.lng],
            );
            map.fitBounds(bounds, { padding: [20, 20] });
        } else if (mapRegion?.center?.lat && mapRegion?.center?.lng) {
            map.setView([mapRegion.center.lat, mapRegion.center.lng], mapRegion.center.zoom || 7);
        }
        return map;
    }

    function createOverlay(map) {
        return map ? root.L.layerGroup().addTo(map) : null;
    }

    function clearOverlay(overlay) {
        if (overlay && typeof overlay.clearLayers === "function") {
            overlay.clearLayers();
        }
    }

    function haversineDistanceMeters(start, end) {
        const toRadians = Math.PI / 180;
        const dLat = (end[1] - start[1]) * toRadians;
        const dLng = (end[0] - start[0]) * toRadians;
        const lat1 = start[1] * toRadians;
        const lat2 = end[1] * toRadians;
        const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return 6371000 * c;
    }

    function computeCumulativeDistances(coords) {
        if (!Array.isArray(coords) || coords.length === 0) {
            return [];
        }
        const cumulative = [0];
        for (let i = 1; i < coords.length; i += 1) {
            const segment = haversineDistanceMeters(coords[i - 1], coords[i]);
            cumulative.push(cumulative[i - 1] + segment);
        }
        return cumulative;
    }

    function interpolatePoint(start, end, fraction) {
        const t = Math.max(0, Math.min(1, fraction));
        return [
            start[0] + (end[0] - start[0]) * t,
            start[1] + (end[1] - start[1]) * t,
        ];
    }

    function pointAtDistance(coords, cumulative, target) {
        if (!Array.isArray(coords) || coords.length === 0) {
            return null;
        }
        const total = cumulative[cumulative.length - 1] || 0;
        if (target <= 0) {
            return coords[0];
        }
        if (target >= total) {
            return coords[coords.length - 1];
        }
        for (let i = 1; i < cumulative.length; i += 1) {
            if (cumulative[i] >= target) {
                const prev = cumulative[i - 1];
                const segmentLength = cumulative[i] - prev;
                const fraction = segmentLength === 0 ? 0 : (target - prev) / segmentLength;
                return interpolatePoint(coords[i - 1], coords[i], fraction);
            }
        }
        return coords[coords.length - 1];
    }

    function deriveTotalKilometres(totalLengthKm, coords) {
        const declared = Number(totalLengthKm);
        if (Number.isFinite(declared) && declared > 0) {
            return declared;
        }
        const cumulative = computeCumulativeDistances(coords);
        const routeLengthMeters = cumulative[cumulative.length - 1] || 0;
        return routeLengthMeters / 1000;
    }

    function sliceGeometryByChainage(geometry, totalLengthKm, startKm, endKm) {
        const coords = getFlattenedGeometry(geometry);
        if (!coords.length || coords.length < 2) {
            return [];
        }
        const cumulative = computeCumulativeDistances(coords);
        const routeLengthMeters = cumulative[cumulative.length - 1];
        if (!routeLengthMeters) {
            return [];
        }
        const effectiveLengthKm = deriveTotalKilometres(totalLengthKm, coords);
        if (!Number.isFinite(effectiveLengthKm) || effectiveLengthKm <= 0) {
            return [];
        }

        const scale = routeLengthMeters / (effectiveLengthKm * 1000);
        const safeStartKm = Number.isFinite(Number(startKm)) ? Number(startKm) : 0;
        const safeEndKm = Number.isFinite(Number(endKm)) ? Number(endKm) : effectiveLengthKm;
        const startDistance = Math.max(0, Math.min(routeLengthMeters, safeStartKm * 1000 * scale));
        const endDistance = Math.max(startDistance, Math.min(routeLengthMeters, safeEndKm * 1000 * scale));

        const sliced = [];
        const startPoint = pointAtDistance(coords, cumulative, startDistance);
        if (startPoint) {
            sliced.push(startPoint);
        }
        for (let i = 1; i < coords.length - 1; i += 1) {
            if (cumulative[i] > startDistance && cumulative[i] < endDistance) {
                sliced.push(coords[i]);
            }
        }
        const endPoint = pointAtDistance(coords, cumulative, endDistance);
        if (endPoint) {
            sliced.push(endPoint);
        }
        return sliced;
    }

    function sliceGeometryByDistanceMeters(geometry, startMeters, endMeters) {
        const coords = getFlattenedGeometry(geometry);
        if (!coords.length || coords.length < 2) {
            return [];
        }

        const cumulative = computeCumulativeDistances(coords);
        const routeLength = cumulative[cumulative.length - 1];
        if (!routeLength && routeLength !== 0) {
            return [];
        }

        const startDistance = Math.max(0, Math.min(routeLength, Number(startMeters) || 0));
        const endDistance = Math.min(
            routeLength,
            Math.max(startDistance, Number.isFinite(Number(endMeters)) ? Number(endMeters) : routeLength),
        );

        const sliced = [];
        const startPoint = pointAtDistance(coords, cumulative, startDistance);
        if (startPoint) {
            sliced.push(startPoint);
        }
        for (let i = 1; i < coords.length - 1; i += 1) {
            if (cumulative[i] > startDistance && cumulative[i] < endDistance) {
                sliced.push(coords[i]);
            }
        }
        const endPoint = pointAtDistance(coords, cumulative, endDistance);
        if (endPoint) {
            sliced.push(endPoint);
        }
        return sliced;
    }

    function drawRouteLine(mapOrLayer, geometry, style) {
        if (!mapOrLayer || !geometry) {
            return null;
        }
        return root.L.geoJSON(geometry, { style }).addTo(mapOrLayer);
    }

    function renderGeometry(mapOrLayer, geometry, style) {
        return drawRouteLine(mapOrLayer, geometry, style);
    }

    function fitMapToLayer(map, layer) {
        if (!map || !layer || !layer.getBounds) {
            return;
        }
        const bounds = layer.getBounds();
        if (bounds && bounds.isValid()) {
            map.fitBounds(bounds, { padding: [16, 16] });
        }
    }

    function renderNoGeometry(container) {
        if (!container) {
            return;
        }
        container.innerHTML = "";
        const notice = document.createElement("div");
        notice.className = "map-notice";
        notice.textContent = "No geometry available — save the record first.";
        container.appendChild(notice);
    }

    function utm37ToLatLng(easting, northing) {
        if (!root.proj4) {
            return null;
        }
        if (!Number.isFinite(easting) || !Number.isFinite(northing)) {
            return null;
        }
        const utm = "+proj=utm +zone=37 +datum=WGS84 +units=m +no_defs";
        const [lng, lat] = root.proj4(utm, "WGS84", [Number(easting), Number(northing)]);
        return { lat, lng };
    }

    function latLngFromPoint(point) {
        if (!point) {
            return null;
        }
        if (Number.isFinite(point.lat) && Number.isFinite(point.lng)) {
            return { lat: Number(point.lat), lng: Number(point.lng) };
        }
        if (Number.isFinite(point.latitude) && Number.isFinite(point.longitude)) {
            return { lat: Number(point.latitude), lng: Number(point.longitude) };
        }
        if (Number.isFinite(point.easting) && Number.isFinite(point.northing)) {
            return utm37ToLatLng(Number(point.easting), Number(point.northing));
        }
        return null;
    }

    function extractEndpoints(road) {
        if (!road) {
            return {};
        }
        const start = latLngFromPoint(road.start || road.start_point || road);
        const end = latLngFromPoint(road.end || road.end_point || road);
        return { start, end };
    }

    function ensureRoadGeometry(road) {
        return normaliseGeometry(road?.geometry);
    }

    async function loadRoad(roadId, apiBase) {
        const url = `${apiBase || "/api/roads/"}${roadId}/`;
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error("Unable to load road data.");
        }
        return response.json();
    }

    async function loadSection(sectionId, apiBase) {
        const url = `${apiBase || "/api/sections/"}${sectionId}/`;
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error("Unable to load section data.");
        }
        return response.json();
    }

    async function loadSegment(segmentId, apiBase) {
        const url = `${apiBase || "/api/segments/"}${segmentId}/`;
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error("Unable to load segment data.");
        }
        return response.json();
    }

    function createPreviewMap(container, mapRegion) {
        const map = initMap(container, mapRegion);
        const overlay = createOverlay(map);
        return { map, overlay };
    }

    function renderRoadPreview(map, overlay, road) {
        clearOverlay(overlay);
        const geometry = ensureRoadGeometry(road);
        const { start, end } = extractEndpoints(road);
        const safeGeometry = geometry;

        const markers = [];
        if (start) { markers.push(root.L.marker([start.lat, start.lng]).addTo(overlay)); }
        if (end) { markers.push(root.L.marker([end.lat, end.lng]).addTo(overlay)); }

        const roadLayer = safeGeometry ? renderGeometry(overlay, safeGeometry, COLORS.road) : null;
        fitMapToLayer(map, roadLayer || overlay);
        return { geometry: safeGeometry, roadLayer, markers };
    }

    function renderSectionPreview(map, overlay, road, section) {
        clearOverlay(overlay);

        const roadGeometry = ensureRoadGeometry(road);
        if (!roadGeometry) {
            // No parent geometry: show a simple message and exit early.
            const container = map && map.getContainer ? map.getContainer() : null;
            if (container) {
                container.innerHTML = "<p style='color:red'>Road has no saved geometry.<br>Use Route Preview → Save first.</p>";
            }
            return { roadLayer: null, sectionLayer: null, markers: [] };
        }

        // Always draw the parent road in a light style.
        const roadLayer = renderGeometry(overlay, roadGeometry, COLORS.road);

        // Use the declared road length if available, otherwise infer from geometry.
        const roadLengthKm = Number(road?.total_length_km ?? road?.length_km ?? 0) || null;

        const startKm = section?.start_chainage_km;
        const endKm = section?.end_chainage_km;

        // Slice the road geometry by chainage.
        const sectionSlice = sliceGeometryByChainage(
            roadGeometry,
            roadLengthKm,
            startKm,
            endKm,
        );

        let sectionLayer = null;
        const markers = [];

        if (sectionSlice && sectionSlice.length >= 2) {
            const sectionGeometry = {
                type: "LineString",
                coordinates: sectionSlice,
            };

            // Draw the section in a stronger color on top of the road.
            sectionLayer = renderGeometry(overlay, sectionGeometry, COLORS.section);

            // Derive markers from the sliced geometry itself (first/last vertices).
            const first = sectionSlice[0];
            const last = sectionSlice[sectionSlice.length - 1];

            if (Array.isArray(first) && first.length >= 2) {
                markers.push(
                    root.L.marker([first[1], first[0]]).addTo(overlay)
                );
            }
            if (Array.isArray(last) && last.length >= 2) {
                markers.push(
                    root.L.marker([last[1], last[0]]).addTo(overlay)
                );
            }
        }

        // Focus on the section if available; otherwise on the whole road.
        fitMapToLayer(map, sectionLayer || roadLayer);

        return { roadLayer, sectionLayer, markers };
    }

    function renderSegmentPreview(map, overlay, road, section, segment) {
        clearOverlay(overlay);

        const roadGeometry = ensureRoadGeometry(road);
        const sectionGeometry = normaliseGeometry(section?.geometry);

        if (!sectionGeometry || !section) {
            const container = map && map.getContainer ? map.getContainer() : null;
            if (container) {
                container.innerHTML = "<p style='color:red'>Section has no saved geometry.<br>Use Route Preview → Save first.</p>";
            }
            return { roadLayer: null, sectionLayer: null, segmentLayer: null };
        }

        const roadLayer = roadGeometry ? renderGeometry(overlay, roadGeometry, COLORS.road) : null;
        const sectionLayer = renderGeometry(overlay, sectionGeometry, COLORS.section);

        const sectionLengthKm = Number(section.end_chainage_km - section.start_chainage_km);

        const segmentSlice = sliceGeometryByChainage(
            sectionGeometry,
            sectionLengthKm,
            Number(segment.station_from_km),
            Number(segment.station_to_km)
        );

        const segmentGeometry = segmentSlice && segmentSlice.length
            ? {
                type: "LineString",
                coordinates: segmentSlice,
            }
            : null;

        const segmentLayer = segmentGeometry ? renderGeometry(overlay, segmentGeometry, COLORS.segment) : null;

        // Fit map to the most specific layer
        fitMapToLayer(map, segmentLayer || sectionLayer || roadLayer);

        return { roadLayer, sectionLayer, segmentLayer };
    }

    async function loadAndRenderRoad(roadId, options = {}) {
        const containerId = options.containerId || options.container;
        const target = typeof containerId === "string" ? document.getElementById(containerId) : containerId;

        let map = options.map;
        let overlay = options.overlay || options.layerGroup;

        if (!map) {
            const created = createPreviewMap(target, options.mapRegion);
            map = created.map;
            overlay = created.overlay;
        } else if (!overlay) {
            overlay = createOverlay(map);
        }

        const road = options.road || await loadRoad(roadId, options.apiBase);
        const result = renderRoadPreview(map, overlay, road);
        return { ...result, map, overlay };
    }

    async function loadAndRenderSection(sectionId, startChainage, endChainage, options = {}) {
        const containerId = options.containerId || options.container;
        const target = typeof containerId === "string" ? document.getElementById(containerId) : containerId;

        let map = options.map;
        let overlay = options.overlay || options.layerGroup;

        if (!map) {
            const created = createPreviewMap(target, options.mapRegion);
            map = created.map;
            overlay = created.overlay;
        } else if (!overlay) {
            overlay = createOverlay(map);
        }

        const road = options.road || (options.roadId ? await loadRoad(options.roadId, options.apiBase) : null);
        const section = options.section || await loadSection(sectionId, options.apiBase);
        section.start_chainage_km = startChainage ?? section.start_chainage_km;
        section.end_chainage_km = endChainage ?? section.end_chainage_km;

        const result = renderSectionPreview(map, overlay, road, section);
        return { ...result, map, overlay };
    }

    async function loadAndRenderSegment(segmentId, startChainage, endChainage, options = {}) {
        const containerId = options.containerId || options.container;
        const target = typeof containerId === "string" ? document.getElementById(containerId) : containerId;

        let map = options.map;
        let overlay = options.overlay || options.layerGroup;

        if (!map) {
            const created = createPreviewMap(target, options.mapRegion);
            map = created.map;
            overlay = created.overlay;
        } else if (!overlay) {
            overlay = createOverlay(map);
        }

        const road = options.road || (options.roadId ? await loadRoad(options.roadId, options.apiBase) : null);
        const segment = options.segment || await loadSegment(segmentId, options.apiBase);
        segment.start_chainage_km = startChainage ?? segment.start_chainage_km ?? segment.station_from_km;
        segment.end_chainage_km = endChainage ?? segment.end_chainage_km ?? segment.station_to_km;

        const result = renderSegmentPreview(map, overlay, road, options.section, segment);
        return { ...result, map, overlay };
    }

    async function previewRoad(map, road, options) {
        const target = options?.layerGroup || map;
        return renderRoadPreview(map, target, road);
    }

    async function previewRoadSection(map, road, section, options) {
        const target = options?.layerGroup || map;
        return renderSectionPreview(map, target, road, section);
    }

    async function previewRoadSegment(map, road, segment, options = {}) {
        const target = options?.layerGroup || map;
        return renderSegmentPreview(map, target, road, options.section, segment);
    }

    root.MapPreview = {
        initMap,
        createPreviewMap,
        clearOverlay,
        createOverlay,
        computeCumulativeDistances,
        sliceRouteByChainage: sliceGeometryByChainage,
        sliceRouteByDistanceMeters: sliceGeometryByDistanceMeters,
        drawRouteLine,
        renderGeometry,
        renderNoGeometry,
        loadAndRenderRoad,
        loadAndRenderSection,
        loadAndRenderSegment,
        previewRoad,
        previewRoadSection,
        previewRoadSegment,
        getFlattenedGeometry,
        utm37ToLatLng,
    };
})(window);
