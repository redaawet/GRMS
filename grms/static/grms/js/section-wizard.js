(function () {
    "use strict";

    function roundTo3(value) {
        if (Number.isFinite(value)) {
            return Math.round(value * 1000) / 1000;
        }
        return null;
    }

    function initLengthPreview() {
        const startInput = document.querySelector('#id_start_chainage_km');
        const endInput = document.querySelector('#id_end_chainage_km');
        const target = document.getElementById('length-preview');
        if (!startInput || !endInput || !target) {
            return;
        }

        function updateLength() {
            const start = parseFloat(startInput.value);
            const end = parseFloat(endInput.value);
            if (Number.isFinite(start) && Number.isFinite(end)) {
                const length = roundTo3(end - start);
                if (length !== null && length > 0) {
                    target.textContent = `${length.toFixed(3)} km`;
                    return;
                }
            }
            target.textContent = "Enter start and end chainages to auto-calculate.";
        }

        startInput.addEventListener('input', updateLength);
        endInput.addEventListener('input', updateLength);
        updateLength();
    }

    function getConfig(id) {
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

    function interpolatePoint(start, end, fraction) {
        if (!start || !end) {
            return null;
        }
        const clamped = Math.max(0, Math.min(1, fraction));
        return [
            start.lat + (end.lat - start.lat) * clamped,
            start.lng + (end.lng - start.lng) * clamped,
        ];
    }

    function drawMap() {
        const mapNode = document.getElementById('section-map');
        const config = getConfig('section-map-config');
        if (!mapNode || !config || !window.L) {
            return;
        }

        const map = L.map(mapNode).setView(
            [config.map_region.center.lat, config.map_region.center.lng],
            7
        );

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map);

        if (config.map_region && config.map_region.viewport) {
            const { northeast, southwest } = config.map_region.viewport;
            if (northeast && southwest) {
                const bounds = L.latLngBounds(
                    [southwest.lat, southwest.lng],
                    [northeast.lat, northeast.lng]
                );
                L.rectangle(bounds, { color: '#9ca3af', weight: 1, dashArray: '4 4' }).addTo(map);
                map.fitBounds(bounds, { padding: [20, 20] });
            }
        }

        const start = config.road.start;
        const end = config.road.end;
        if (start && end) {
            const roadLine = L.polyline(
                [
                    [start.lat, start.lng],
                    [end.lat, end.lng],
                ],
                { color: '#6b7280', weight: 4 }
            ).addTo(map);
            map.fitBounds(roadLine.getBounds(), { padding: [30, 30] });

            const lengthKm = config.road.length_km;
            const sectionStartKm = config.section.start_chainage_km;
            const sectionEndKm = config.section.end_chainage_km;
            if (lengthKm && sectionStartKm != null && sectionEndKm != null && lengthKm > 0) {
                const startFraction = sectionStartKm / lengthKm;
                const endFraction = sectionEndKm / lengthKm;
                const sectionStart = interpolatePoint(start, end, startFraction);
                const sectionEnd = interpolatePoint(start, end, endFraction);
                if (sectionStart && sectionEnd) {
                    L.polyline([sectionStart, sectionEnd], { color: '#0ea5e9', weight: 6 }).addTo(map);
                }
            }
        } else {
            const fallback = L.marker([config.map_region.center.lat, config.map_region.center.lng]).addTo(map);
            fallback.bindPopup('Map preview unavailable — missing road coordinates.');
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initLengthPreview();
        drawMap();
    });
})();
