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

        const mapSetup = window.MapPreview.createPreviewMap(mapNode, config.map_region);
        const { map, overlay } = mapSetup;
        let activeLayers = [];

        const notice = document.createElement('div');
        notice.className = 'map-notice';
        Object.assign(notice.style, {
            marginTop: '8px',
            padding: '8px 12px',
            borderRadius: '4px',
            border: '1px solid #f59e0b',
            background: '#fffbeb',
            color: '#92400e',
            display: 'none',
        });
        mapNode.insertAdjacentElement('afterend', notice);

        function showNotice(message) {
            notice.textContent = message;
            notice.style.display = 'block';
        }

        function hideNotice() {
            notice.textContent = '';
            notice.style.display = 'none';
        }

        function clearLayers() {
            window.MapPreview.clearOverlay(overlay);
            activeLayers = [];
        }

        async function renderMapPreview() {
            clearLayers();
            if (!window.MapPreview) {
                return;
            }

            try {
                hideNotice();
                const result = await window.MapPreview.loadAndRenderSection(
                    config.section?.id,
                    config.section.start_chainage_km,
                    config.section.end_chainage_km,
                    {
                        container: mapNode,
                        mapRegion: config.map_region,
                        road: config.road,
                        section: config.section,
                        api: config.api,
                        default_travel_mode: config.default_travel_mode,
                        layerGroup: overlay,
                        map,
                    },
                );

                if (!result.sectionLayer) {
                    showNotice("No geometry available — save the record first.");
                    return;
                }

                hideNotice();
                activeLayers = [result.roadLayer, result.sectionLayer, ...(result.markers || [])].filter(Boolean);
            } catch (err) {
                console.error('Unable to render section preview', err);
                showNotice("No geometry available — save the record first.");
            }
        }

        renderMapPreview();
    }

    document.addEventListener('DOMContentLoaded', function () {
        initLengthPreview();
        drawMap();
    });
})();
