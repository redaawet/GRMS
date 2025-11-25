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
            function sliceByChainage(polyline, chStart, chEnd, totalLen) {
                const s = Math.floor((chStart / totalLen) * (polyline.length - 1));
                const e = Math.floor((chEnd / totalLen) * (polyline.length - 1));
                return polyline.slice(s, e + 1);
            }

            const result = { roadLayer: null, sectionLayer: null };
            try {
                const layerGroup = overlay;
                const roadResponse = await fetch(config.api.route, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        start: config.road.start,
                        end: config.road.end,
                        mode: config.default_travel_mode
                    })
                });

                const roadData = await roadResponse.json();
                const roadCoords = roadData.geometry.coordinates.map(c => [c[1], c[0]]);
                result.roadLayer = L.polyline(roadCoords, { color: "#666", weight: 4 }).addTo(layerGroup);
                window._roadPolyline = roadCoords;

                let sectionCoords = null;

                if (config.section?.points?.start && config.section?.points?.end) {
                    const sectionResponse = await fetch(config.api.route, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            start: config.section.points.start,
                            end: config.section.points.end,
                            mode: config.default_travel_mode
                        })
                    });

                    const sectionData = await sectionResponse.json();
                    sectionCoords = sectionData.geometry.coordinates.map(c => [c[1], c[0]]);
                    result.sectionLayer = L.polyline(sectionCoords, { color: "#00aaff", weight: 7 }).addTo(layerGroup);
                } else if (Array.isArray(window._roadPolyline) && window._roadPolyline.length
                    && Number.isFinite(config.section?.start_chainage_km) && Number.isFinite(config.section?.end_chainage_km)
                ) {
                    const sectionCoordsByChainage = sliceByChainage(
                        window._roadPolyline,
                        config.section.start_chainage_km,
                        config.section.end_chainage_km,
                        config.road.length_km
                    );

                    sectionCoords = sectionCoordsByChainage;
                    result.sectionLayer = L.polyline(sectionCoordsByChainage, {
                        color: "#00aaff",
                        weight: 7
                    }).addTo(layerGroup);
                }

                if (sectionCoords && sectionCoords.length) {
                    map.fitBounds(L.polyline(sectionCoords).getBounds());
                }

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
