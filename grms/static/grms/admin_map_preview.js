(() => {
  const mapEl = document.getElementById("grms-map");
  if (!mapEl || !window.L) {
    return;
  }

  const endpoint = mapEl.dataset.endpoint;
  if (!endpoint) {
    return;
  }

  const map = L.map(mapEl, { zoomControl: true });

  if (window.GRMS_DISABLE_BASEMAP !== true) {
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);
  }

  const styles = {
    road: { color: "#666", weight: 2, opacity: 0.7 },
    section: { color: "#2b6cb0", weight: 3, opacity: 0.8 },
    section_current: { color: "#2b6cb0", weight: 5, opacity: 1 },
    segment: { color: "#2f855a", weight: 3, opacity: 0.8 },
    segment_current: { color: "#2f855a", weight: 5, opacity: 1 },
  };

  const boundsByRole = {};

  const registerBounds = (role, layer) => {
    if (!layer) {
      return;
    }
    let bounds = null;
    if (typeof layer.getBounds === "function") {
      bounds = layer.getBounds();
    } else if (typeof layer.getLatLng === "function") {
      bounds = L.latLngBounds([layer.getLatLng()]);
    }
    if (bounds) {
      boundsByRole[role] = bounds;
    }
  };

  fetch(endpoint, { credentials: "same-origin" })
    .then((response) => response.json())
    .then((data) => {
      const layer = L.geoJSON(data, {
        style: (feature) => styles[feature?.properties?.role] || { weight: 3, opacity: 0.8 },
        pointToLayer: (feature, latlng) => {
          const role = feature?.properties?.role;
          const radius = role === "structure_current" ? 8 : 5;
          return L.circleMarker(latlng, {
            radius,
            weight: role === "structure_current" ? 2 : 1,
            opacity: 1,
            fillOpacity: role === "structure_current" ? 0.9 : 0.6,
          });
        },
        onEachFeature: (feature, featureLayer) => {
          const role = feature?.properties?.role;
          if (role) {
            registerBounds(role, featureLayer);
          }
        },
      }).addTo(map);

      if (layer && layer.getBounds && layer.getBounds().isValid()) {
        let fitBounds =
          boundsByRole.segment_current ||
          boundsByRole.structure_current ||
          boundsByRole.section_current ||
          boundsByRole.road;
        if (!fitBounds || !fitBounds.isValid()) {
          fitBounds = layer.getBounds();
        }
        map.fitBounds(fitBounds, { padding: [24, 24] });
      } else {
        map.setView([0, 0], 2);
      }
    })
    .catch(() => {
      map.setView([0, 0], 2);
    });
})();
