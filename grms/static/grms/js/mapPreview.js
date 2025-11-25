(function (root) {
    "use strict";

    const COLORS = {
        road: { color: "#cbd5e1", weight: 4, opacity: 0.75 },
        section: { color: "#1d4ed8", weight: 5, opacity: 0.85 },
        segment: { color: "#06b6d4", weight: 7, opacity: 0.95 },
    };

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

    function initMap(divId) {
        if (!root.L) {
            throw new Error("Leaflet must be loaded before initializing the map.");
        }
        const map = root.L.map(divId);
        root.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        return map;
    }

    function utm37ToLatLng(easting, northing) {
        if (!root.proj4) {
            throw new Error("proj4 is required for UTM to WGS84 conversion.");
        }
        if (!Number.isFinite(easting) || !Number.isFinite(northing)) {
            return null;
        }
        const utm = "+proj=utm +zone=37 +datum=WGS84 +units=m +no_defs";
        const [lng, lat] = root.proj4(utm, "WGS84", [Number(easting), Number(northing)]);
        return { lat, lng };
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

    function sliceRouteByChainage(coords, roadTotalKm, startKm, endKm) {
        if (!Array.isArray(coords) || coords.length < 2) {
            return [];
        }
        const cumulative = computeCumulativeDistances(coords);
        const routeLength = cumulative[cumulative.length - 1];
        if (!routeLength) {
            return [];
        }
        const totalKm = Number(roadTotalKm);
        const effectiveKm = Number.isFinite(totalKm) && totalKm > 0 ? totalKm : routeLength / 1000;
        const scale = routeLength / (effectiveKm * 1000);

        const startDistance = Math.max(0, Math.min(routeLength, (Number(startKm) || 0) * 1000 * scale));
        const endKmValue = Number.isFinite(Number(endKm)) ? Number(endKm) : effectiveKm;
        const rawEndDistance = Math.max(startDistance, endKmValue * 1000 * scale);
        const endDistance = Math.min(routeLength, rawEndDistance);

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

    function sliceRouteByDistanceMeters(coords, startMeters, endMeters) {
        if (!Array.isArray(coords) || coords.length < 2) {
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

    async function fetchOSRMRoute(lat1, lng1, lat2, lng2) {
        const url = "https://router.project-osrm.org/route/v1/driving/"
            + encodeURIComponent(lng1) + "," + encodeURIComponent(lat1) + ";"
            + encodeURIComponent(lng2) + "," + encodeURIComponent(lat2)
            + "?overview=full&geometries=geojson";

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error("OSRM request failed with status " + response.status);
        }
        const payload = await response.json();
        const geometry = payload?.routes?.[0]?.geometry;
        if (!geometry || geometry.type !== "LineString" || !Array.isArray(geometry.coordinates)) {
            throw new Error(payload?.message || "OSRM returned an invalid route.");
        }
        return { type: "LineString", coordinates: geometry.coordinates };
    }

    function drawRouteLine(mapOrLayer, geometry, style) {
        if (!mapOrLayer || !root.L || !geometry) {
            return null;
        }
        return root.L.geoJSON(geometry, { style }).addTo(mapOrLayer);
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

    function latLngFromRoadFields(road, prefix) {
        if (!road) { return null; }
        const latField = Number(road[`${prefix}_latitude`] ?? road[`${prefix}_lat`]);
        const lngField = Number(road[`${prefix}_longitude`] ?? road[`${prefix}_lng`]);
        if (Number.isFinite(latField) && Number.isFinite(lngField)) {
            return { lat: latField, lng: lngField };
        }
        const eastingField = Number(road[`${prefix}_easting`]);
        const northingField = Number(road[`${prefix}_northing`]);
        if (Number.isFinite(eastingField) && Number.isFinite(northingField)) {
            return utm37ToLatLng(eastingField, northingField);
        }
        return null;
    }

    function extractEndpoints(road) {
        if (!road) { return {}; }
        const start = latLngFromPoint(road.start || road.start_point)
            || latLngFromRoadFields(road, "start")
            || latLngFromPoint(road);
        const end = latLngFromPoint(road.end || road.end_point)
            || latLngFromRoadFields(road, "end")
            || latLngFromPoint(road);
        return { start, end };
    }

    async function ensureRoadGeometry(road) {
        const flattened = getFlattenedGeometry(road?.route_geometry || road?.geometry || road?.alignment_geojson);
        if (flattened.length) {
            return { type: "LineString", coordinates: flattened };
        }

        const cached = root.__roadRouteGeometry;
        const { start, end } = extractEndpoints(road);
        if (!start || !end) {
            throw new Error("Road requires start and end coordinates.");
        }
        if (cached && cached.start && cached.end &&
            cached.start.lat === start.lat && cached.start.lng === start.lng &&
            cached.end.lat === end.lat && cached.end.lng === end.lng) {
            return cached.geometry;
        }
        const geometry = await fetchOSRMRoute(start.lat, start.lng, end.lat, end.lng);
        const flattenedRoute = getFlattenedGeometry(geometry);
        const normalized = flattenedRoute.length ? { type: "LineString", coordinates: flattenedRoute } : geometry;
        root.__roadRouteGeometry = { geometry: normalized, start, end };
        return normalized;
    }

    function fitMapToGeometry(map, layer) {
        if (!map || !layer) { return; }
        const bounds = layer.getBounds();
        if (bounds && bounds.isValid()) {
            map.fitBounds(bounds, { padding: [16, 16] });
        }
    }

    async function previewRoad(map, road, options) {
        const geometry = await ensureRoadGeometry(road);
        const target = options?.layerGroup || map;
        const routeLayer = geometry ? drawRouteLine(target, geometry, COLORS.road) : null;

        const { start, end } = extractEndpoints(road);
        const markers = [];
        if (start) { markers.push(root.L.marker([start.lat, start.lng]).addTo(target)); }
        if (end) { markers.push(root.L.marker([end.lat, end.lng]).addTo(target)); }

        fitMapToGeometry(map, routeLayer);
        return { geometry, routeLayer, startMarker: markers[0] || null, endMarker: markers[1] || null };
    }

    function toMeters(value) {
        return Number.isFinite(Number(value)) ? Number(value) * 1000 : null;
    }

    async function previewRoadSection(map, road, section, options) {
        const geometry = await ensureRoadGeometry(road);
        const target = options?.layerGroup || map;
        const roadLayer = geometry ? drawRouteLine(target, geometry, COLORS.road) : null;

        const coords = getFlattenedGeometry(geometry);
        const slice = sliceRouteByChainage(
            coords,
            Number(road?.length_km ?? road?.total_length_km),
            section?.start_chainage_km,
            section?.end_chainage_km,
        );
        const sectionLayer = slice.length ? drawRouteLine(target, { type: "LineString", coordinates: slice }, COLORS.section) : null;

        fitMapToGeometry(map, sectionLayer || roadLayer);
        return { geometry, roadLayer, sectionLayer };
    }

    async function previewRoadSegment(map, road, segment, options) {
        const geometry = await ensureRoadGeometry(road);
        const target = options?.layerGroup || map;
        const roadLayer = geometry ? drawRouteLine(target, geometry, COLORS.road) : null;

        const coords = getFlattenedGeometry(geometry);

        const sectionSlice = options?.section ? sliceRouteByChainage(
            coords,
            Number(road?.length_km ?? road?.total_length_km),
            options.section.start_chainage_km,
            options.section.end_chainage_km,
        ) : [];
        const sectionLayer = sectionSlice.length
            ? drawRouteLine(target, { type: "LineString", coordinates: sectionSlice }, COLORS.section)
            : null;

        const segmentSlice = sliceRouteByChainage(
            coords,
            Number(road?.length_km ?? road?.total_length_km),
            segment?.station_from_km,
            segment?.station_to_km,
        );
        const segmentLayer = segmentSlice.length ? drawRouteLine(
            target,
            { type: "LineString", coordinates: segmentSlice },
            COLORS.segment,
        ) : null;

        fitMapToGeometry(map, segmentLayer || sectionLayer || roadLayer);
        return { geometry, roadLayer, sectionLayer, segmentLayer };
    }

    root.MapPreview = {
        initMap,
        utm37ToLatLng,
        fetchOSRMRoute,
        computeCumulativeDistances,
        sliceRouteByChainage,
        sliceRouteByDistanceMeters,
        drawRouteLine,
        previewRoad,
        previewRoadSection,
        previewRoadSegment,
        // Legacy compatibility
        previewSection: previewRoadSection,
        previewSegment: previewRoadSegment,
        // Legacy compatibility
        utmToLatLng: utm37ToLatLng,
        getFlattenedGeometry,
    };
})(window);
