(function (root) {
    "use strict";

    const STYLES = {
        road: { color: "#475569", weight: 4, opacity: 0.7 },
        section: { color: "#0ea5e9", weight: 6, opacity: 0.85 },
        segment: { color: "#f97316", weight: 7, opacity: 0.95 },
    };

    function toLeafletLatLngs(coordinates) {
        if (!Array.isArray(coordinates)) {
            return [];
        }
        return coordinates.map(function (point) {
            return [point[1], point[0]];
        });
    }

    function haversineDistanceMeters(start, end) {
        const toRadians = Math.PI / 180;
        const dLat = (end[1] - start[1]) * toRadians;
        const dLng = (end[0] - start[0]) * toRadians;
        const lat1 = start[1] * toRadians;
        const lat2 = end[1] * toRadians;
        const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return 6371000 * c; // Earth radius in meters
    }

    function interpolateLonLat(start, end, fraction) {
        return [
            start[0] + (end[0] - start[0]) * fraction,
            start[1] + (end[1] - start[1]) * fraction,
        ];
    }

    function sliceLineStringByChainage(geometry, startChainage, endChainage) {
        const coordinates = geometry?.coordinates || geometry;
        if (!Array.isArray(coordinates) || coordinates.length < 2) {
            return { type: "LineString", coordinates: [] };
        }

        let clampedStart = Math.max(0, Number(startChainage) || 0);
        const totalLength = coordinates.slice(1).reduce(function (distance, point, index) {
            return distance + haversineDistanceMeters(coordinates[index], point);
        }, 0);
        let clampedEnd = Number.isFinite(endChainage) ? Math.min(Number(endChainage), totalLength) : totalLength;
        clampedEnd = Math.max(clampedStart, clampedEnd);

        const sliced = [];
        let traversed = 0;

        for (let i = 0; i < coordinates.length - 1; i += 1) {
            const segmentStart = coordinates[i];
            const segmentEnd = coordinates[i + 1];
            const segmentLength = haversineDistanceMeters(segmentStart, segmentEnd);
            const nextDistance = traversed + segmentLength;

            if (nextDistance < clampedStart) {
                traversed = nextDistance;
                continue;
            }

            if (!sliced.length) {
                const startFraction = segmentLength === 0 ? 0 : (clampedStart - traversed) / segmentLength;
                sliced.push(interpolateLonLat(segmentStart, segmentEnd, startFraction));
            }

            if (nextDistance <= clampedEnd) {
                sliced.push(segmentEnd);
                traversed = nextDistance;
                continue;
            }

            const endFraction = segmentLength === 0 ? 0 : (clampedEnd - traversed) / segmentLength;
            sliced.push(interpolateLonLat(segmentStart, segmentEnd, endFraction));
            break;
        }

        return { type: "LineString", coordinates: sliced };
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
        if (!geometry || geometry.type !== "LineString") {
            throw new Error(payload?.message || "OSRM returned an invalid route.");
        }
        return { type: "LineString", coordinates: geometry.coordinates };
    }

    function ensureMapBounds(map, polyline) {
        if (!map || !polyline) {
            return;
        }
        const bounds = polyline.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [16, 16] });
        }
    }

    function drawPolyline(map, geometry, style) {
        if (!map || !geometry || !Array.isArray(geometry.coordinates)) {
            return null;
        }
        const latlngs = toLeafletLatLngs(geometry.coordinates);
        if (!latlngs.length || !root.L) {
            return null;
        }
        return root.L.polyline(latlngs, style).addTo(map);
    }

    async function ensureRoadGeometry(road) {
        if (road?.route_geometry?.type === "LineString") {
            return road.route_geometry;
        }
        if (!road || !Number.isFinite(road.start_lat) || !Number.isFinite(road.start_lng) ||
            !Number.isFinite(road.end_lat) || !Number.isFinite(road.end_lng)) {
            throw new Error("Road requires numeric start/end coordinates.");
        }
        const geometry = await fetchRoadRoute(road.start_lat, road.start_lng, road.end_lat, road.end_lng);
        road.route_geometry = geometry;
        return geometry;
    }

    async function previewRoad(map, road) {
        const geometry = await ensureRoadGeometry(road);
        const roadLine = drawPolyline(map, geometry, STYLES.road);
        ensureMapBounds(map, roadLine);
        return { roadLine: roadLine };
    }

    async function previewRoadSection(map, road, section) {
        const geometry = await ensureRoadGeometry(road);
        const roadLine = drawPolyline(map, geometry, STYLES.road);
        const sectionGeometry = sliceLineStringByChainage(
            geometry,
            section?.start_chainage,
            section?.end_chainage
        );
        const sectionLine = drawPolyline(map, sectionGeometry, STYLES.section);
        ensureMapBounds(map, sectionLine || roadLine);
        return { roadLine: roadLine, sectionLine: sectionLine };
    }

    async function previewRoadSegment(map, road, section, segment) {
        const geometry = await ensureRoadGeometry(road);
        const roadLine = drawPolyline(map, geometry, STYLES.road);
        const sectionGeometry = sliceLineStringByChainage(
            geometry,
            section?.start_chainage,
            section?.end_chainage
        );
        const sectionLine = drawPolyline(map, sectionGeometry, Object.assign({}, STYLES.section, { weight: 5, opacity: 0.7 }));
        const segmentGeometry = sliceLineStringByChainage(
            geometry,
            segment?.start_chainage,
            segment?.end_chainage
        );
        const segmentLine = drawPolyline(map, segmentGeometry, STYLES.segment);
        ensureMapBounds(map, segmentLine || sectionLine || roadLine);
        return { roadLine: roadLine, sectionLine: sectionLine, segmentLine: segmentLine };
    }

    function normalisePoint(point) {
        if (!point) {
            return null;
        }
        if (Number.isFinite(point.lat) && Number.isFinite(point.lng)) {
            return { lat: Number(point.lat), lng: Number(point.lng) };
        }
        if (Number.isFinite(point.latitude) && Number.isFinite(point.longitude)) {
            return { lat: Number(point.latitude), lng: Number(point.longitude) };
        }
        if (Number.isFinite(point.easting) && Number.isFinite(point.northing) && root.MapPreview && root.MapPreview.utm37ToLatLng) {
            return root.MapPreview.utm37ToLatLng(Number(point.easting), Number(point.northing));
        }
        return null;
    }

    function loadRoadLine(map, start, end, options) {
        if (!map || !root.L) {
            return null;
        }

        const startPoint = normalisePoint(start);
        const endPoint = normalisePoint(end);
        if (!startPoint || !endPoint) {
            return null;
        }

        const latLngs = [
            [startPoint.lat, startPoint.lng],
            [endPoint.lat, endPoint.lng],
        ];
        const target = options && options.layerGroup ? options.layerGroup : map;
        const polyline = root.L.polyline(latLngs, Object.assign({ weight: 5, color: "#475569" }, options && options.style)).addTo(target);
        if (!options || options.fit !== false) {
            ensureMapBounds(map, polyline);
        }
        return polyline;
    }

    root.RoadPreview = {
        fetchRoadRoute: fetchRoadRoute,
        previewRoad: previewRoad,
        previewRoadSection: previewRoadSection,
        previewRoadSegment: previewRoadSegment,
        sliceLineStringByChainage: sliceLineStringByChainage,
        loadRoadLine: loadRoadLine,
    };
})(window);
