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
        const lengthField = document.querySelector('#id_length_km');
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
                    if (lengthField) {
                        lengthField.value = length.toFixed(3);
                    }
                    return;
                }
            }
            if (lengthField) {
                lengthField.value = '';
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
                L.rectangle(bounds, { color: '#22c55e', weight: 2, dashArray: '6 4', fillOpacity: 0.05 })
                    .addTo(map);
                map.fitBounds(bounds, { padding: [20, 20] });
            }
        }

        const overlay = L.layerGroup().addTo(map);
        let activeLayers = [];

        function clearLayers() {
            activeLayers.forEach(layer => overlay.removeLayer(layer));
            activeLayers = [];
        }

        async function renderMapPreview() {
            clearLayers();
            if (!window.MapPreview) {
                return;
            }
            try {
                const result = await window.MapPreview.previewRoadSection(
                    map,
                    config.road,
                    config.section,
                    { layerGroup: overlay }
                );
                activeLayers = [result.roadLayer, result.sectionLayer].filter(Boolean);
            } catch (err) {
                console.error('Unable to render section preview', err);
                const fallback = L.marker([config.map_region.center.lat, config.map_region.center.lng]).addTo(overlay);
                fallback.bindPopup('Map preview unavailable — missing road coordinates.');
                activeLayers.push(fallback);
            }
        }

        renderMapPreview();
    }

    document.addEventListener('DOMContentLoaded', function () {
        initLengthPreview();
        drawMap();
    });
})();
