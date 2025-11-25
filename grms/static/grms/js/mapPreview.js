(function (root) {
    "use strict";

    const STYLES = {
        road: { color: "#475569", weight: 4, opacity: 0.7 },
        section: { color: "#0ea5e9", weight: 6, opacity: 0.85 },
        segment: { color: "#f97316", weight: 7, opacity: 0.95 },
        roadBase: { color: "#94a3b8", weight: 3, opacity: 0.45 },
        sectionBase: { color: "#0ea5e9", weight: 5, opacity: 0.6 },
    };

    function utmToLatLng(easting, northing, zone = 37) {
        if (!Number.isFinite(easting) || !Number.isFinite(northing)) {
            return null;
        }

        const a = 6378137.0; // WGS84 major axis
        const e = 0.081819191; // eccentricity
        const e1sq = 0.006739497;
        const k0 = 0.9996;

        const x = easting - 500000.0;
        const y = northing;
        const m = y / k0;
        const mu = m / (a * (1.0 - Math.pow(e, 2) / 4.0 - 3.0 * Math.pow(e, 4) / 64.0 - 5.0 * Math.pow(e, 6) / 256.0));

        const e1 = (1 - Math.sqrt(1 - Math.pow(e, 2))) / (1 + Math.sqrt(1 - Math.pow(e, 2)));
        const j1 = (3 * e1) / 2 - (27 * Math.pow(e1, 3)) / 32.0;
        const j2 = (21 * Math.pow(e1, 2)) / 16 - (55 * Math.pow(e1, 4)) / 32.0;
        const j3 = (151 * Math.pow(e1, 3)) / 96.0;
        const j4 = (1097 * Math.pow(e1, 4)) / 512.0;

        const fp = mu + j1 * Math.sin(2 * mu) + j2 * Math.sin(4 * mu) + j3 * Math.sin(6 * mu) + j4 * Math.sin(8 * mu);

        const sinfp = Math.sin(fp);
        const cosfp = Math.cos(fp);
        const tanfp = Math.tan(fp);

        const c1 = e1sq * Math.pow(cosfp, 2);
        const t1 = Math.pow(tanfp, 2);
        const r1 = (a * (1 - Math.pow(e, 2))) / Math.pow(1 - Math.pow(e * sinfp, 2), 1.5);
        const n1 = a / Math.sqrt(1 - Math.pow(e * sinfp, 2));

        const d = x / (n1 * k0);

        const q1 = tanfp / (2 * r1 * n1 * Math.pow(k0, 2));
        const q2 = (5 + 3 * t1 + 10 * c1 - 4 * Math.pow(c1, 2) - 9 * e1sq) / 24.0;
        const q3 = (61 + 90 * t1 + 298 * c1 + 45 * Math.pow(t1, 2) - 3 * Math.pow(c1, 2) - 252 * e1sq) / 720.0;

        const lat = fp - q1 * (Math.pow(d, 2) - q2 * Math.pow(d, 4) + q3 * Math.pow(d, 6));
        const q4 = 1 / (cosfp * n1 * k0);
        const q5 = (1 + 2 * t1 + c1) / 6.0;
        const q6 = (5 - 2 * c1 + 28 * t1 - 3 * Math.pow(c1, 2) + 8 * e1sq + 24 * Math.pow(t1, 2)) / 120.0;

        const lon = (d - q5 * Math.pow(d, 3) + q6 * Math.pow(d, 5)) * q4;
        const lonOrigin = (zone - 1) * 6 - 180 + 3;

        return {
            lat: (lat * 180) / Math.PI,
            lng: lonOrigin + (lon * 180) / Math.PI,
        };
    }

    function haversineDistance(start, end) {
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
            const segment = haversineDistance(coords[i - 1], coords[i]);
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

    function slicePolylineByChainage(coords, startKm, endKm, roadTotalKm) {
        if (!Array.isArray(coords) || coords.length < 2) {
            return [];
        }

        const cumulative = computeCumulativeDistances(coords);
        const routeLength = cumulative[cumulative.length - 1];
        if (!routeLength) {
            return [];
        }

        const totalKm = Number(roadTotalKm);
        const effectiveRoadKm = totalKm > 0 ? totalKm : routeLength / 1000;

        const startRatio = Math.max(0, Math.min(1, (Number(startKm) || 0) / effectiveRoadKm));
        const endRatioRaw = Number.isFinite(endKm) ? (Number(endKm) || 0) / effectiveRoadKm : 1;
        const endRatio = Math.max(startRatio, Math.max(0, Math.min(1, endRatioRaw)));

        const startDistance = routeLength * startRatio;
        const endDistance = routeLength * endRatio;

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

    async function fetchRoadRoute(startLat, startLng, endLat, endLng) {
        const url = "https://router.project-osrm.org/route/v1/driving/" +
            encodeURIComponent(startLng) + "," + encodeURIComponent(startLat) + ";" +
            encodeURIComponent(endLng) + "," + encodeURIComponent(endLat) +
            "?overview=full&geometries=geojson";

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

    function toLatLng(point) {
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
            return utmToLatLng(Number(point.easting), Number(point.northing), point.zone || 37);
        }
        return null;
    }

    async function ensureRoadGeometry(road) {
        if (road && road._routeGeometry) {
            return road._routeGeometry;
        }
        const startPoint = toLatLng(road?.start || road?.start_point || road);
        const endPoint = toLatLng(road?.end || road?.end_point || road);
        if (!startPoint || !endPoint) {
            throw new Error("Road requires start and end coordinates.");
        }
        const geometry = await fetchRoadRoute(startPoint.lat, startPoint.lng, endPoint.lat, endPoint.lng);
        if (road) {
            road._routeGeometry = geometry;
            road._startPoint = startPoint;
            road._endPoint = endPoint;
        }
        return geometry;
    }

    function asLatLngs(coords) {
        return coords.map(function (coord) { return [coord[1], coord[0]]; });
    }

    function targetLayer(options, map) {
        return (options && options.layerGroup) || map;
    }

    async function previewRoad(map, road, options) {
        const geometry = await ensureRoadGeometry(road);
        const layerTarget = targetLayer(options, map);
        const routeLayer = root.L.geoJSON(geometry, { style: STYLES.road }).addTo(layerTarget);
        const startPoint = road?._startPoint || toLatLng(road.start || road);
        const endPoint = road?._endPoint || toLatLng(road.end || road);
        let startMarker = null;
        let endMarker = null;
        if (startPoint) {
            startMarker = root.L.marker([startPoint.lat, startPoint.lng]).addTo(layerTarget);
        }
        if (endPoint) {
            endMarker = root.L.marker([endPoint.lat, endPoint.lng]).addTo(layerTarget);
        }
        const bounds = routeLayer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [16, 16] });
        }
        return { geometry, routeLayer, startMarker, endMarker };
    }

    async function previewSection(map, road, section, options) {
        const geometry = await ensureRoadGeometry(road);
        const layerTarget = targetLayer(options, map);
        const roadLayer = root.L.geoJSON(geometry, { style: STYLES.roadBase }).addTo(layerTarget);

        const coords = geometry.coordinates;
        const slice = slicePolylineByChainage(
            coords,
            section?.start_chainage_km,
            section?.end_chainage_km,
            road?.length_km || road?.total_length_km || road?.road_length_km
        );
        const sectionLayer = slice.length
            ? root.L.geoJSON({ type: "LineString", coordinates: slice }, { style: STYLES.section })
                .addTo(layerTarget)
            : null;

        const bounds = (sectionLayer || roadLayer).getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [16, 16] });
        }
        return { geometry, roadLayer, sectionLayer };
    }

    async function previewSegment(map, road, section, segment, options) {
        const geometry = await ensureRoadGeometry(road);
        const layerTarget = targetLayer(options, map);
        const roadLayer = root.L.geoJSON(geometry, { style: STYLES.roadBase }).addTo(layerTarget);

        const coords = geometry.coordinates;
        const sectionSlice = slicePolylineByChainage(
            coords,
            section?.start_chainage_km,
            section?.end_chainage_km,
            road?.length_km || road?.total_length_km || road?.road_length_km
        );
        const sectionLayer = sectionSlice.length
            ? root.L.geoJSON({ type: "LineString", coordinates: sectionSlice }, { style: STYLES.sectionBase })
                .addTo(layerTarget)
            : null;

        const segmentSlice = slicePolylineByChainage(
            coords,
            segment?.station_from_km,
            segment?.station_to_km,
            road?.length_km || road?.total_length_km || road?.road_length_km
        );
        const segmentLayer = segmentSlice.length
            ? root.L.geoJSON({ type: "LineString", coordinates: segmentSlice }, { style: STYLES.segment })
                .addTo(layerTarget)
            : null;

        const boundsLayer = segmentLayer || sectionLayer || roadLayer;
        const bounds = boundsLayer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [16, 16] });
        }
        return { geometry, roadLayer, sectionLayer, segmentLayer };
    }

    root.MapPreview = {
        utmToLatLng,
        computeCumulativeDistances,
        slicePolylineByChainage,
        fetchRoadRoute,
        previewRoad,
        previewSection,
        previewSegment,
    };
})(window);
