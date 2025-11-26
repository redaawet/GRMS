function loadSectionGeometry(sectionId) {
    fetch(`/admin/grms/roadsection/${sectionId}/get_geometry/`)
        .then(r => r.json())
        .then(data => {
            map.eachLayer(layer => {
                if (!(layer instanceof L.TileLayer)) map.removeLayer(layer);
            });

            if (data.geometry) {
                const geom = JSON.parse(data.geometry);
                const coords = geom.coordinates.map(c => [c[1], c[0]]);
                const line = L.polyline(coords, {color: "#0050ff", weight: 6}).addTo(map);
                map.fitBounds(line.getBounds());
            } else {
                if (window.sectionStart) {
                    L.marker([sectionStart.lat, sectionStart.lng]).addTo(map);
                }
                if (window.sectionEnd) {
                    L.marker([sectionEnd.lat, sectionEnd.lng]).addTo(map);
                }
            }
        });
}
