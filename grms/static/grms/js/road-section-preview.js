function loadSectionGeometry(sectionId) {
    fetch(`/admin/grms/roadsection/${sectionId}/get_geometry/`)
        .then(r => r.json())
        .then(data => {
            map.eachLayer(layer => {
                if (!(layer instanceof L.TileLayer)) map.removeLayer(layer);
            });

            const rawGeometry = data.geometry;
            const geometry = typeof rawGeometry === "string" ? JSON.parse(rawGeometry) : rawGeometry;
            const startPoint = data.start_point;
            const endPoint = data.end_point;

            if (geometry && geometry.coordinates) {
                const coords = geometry.coordinates.map(c => [c[1], c[0]]);
                const line = L.polyline(coords, {color: "#0050ff", weight: 6}).addTo(map);

                if (startPoint && Number.isFinite(startPoint.lat) && Number.isFinite(startPoint.lng)) {
                    L.marker([startPoint.lat, startPoint.lng]).addTo(map);
                }
                if (endPoint && Number.isFinite(endPoint.lat) && Number.isFinite(endPoint.lng)) {
                    L.marker([endPoint.lat, endPoint.lng]).addTo(map);
                }

                map.fitBounds(line.getBounds());
                return;
            }

            const fallbackStart = window.sectionStart;
            const fallbackEnd = window.sectionEnd;
            if (fallbackStart) {
                L.marker([fallbackStart.lat, fallbackStart.lng]).addTo(map);
            }
            if (fallbackEnd) {
                L.marker([fallbackEnd.lat, fallbackEnd.lng]).addTo(map);
            }
        });
}
