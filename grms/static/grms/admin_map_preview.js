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

  const onlineTiles = mapEl.dataset.onlineTiles || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const onlineAttribution = mapEl.dataset.onlineAttribution || "&copy; OpenStreetMap contributors";
  const offlineTiles = mapEl.dataset.offlineTiles || "";
  const offlineAttribution = mapEl.dataset.offlineAttribution || "Offline tiles";

  const makeLayer = (url, attribution) => {
    if (!url) {
      return null;
    }
    return L.tileLayer(url, { attribution, maxZoom: 19 });
  };

  const onlineLayer = makeLayer(onlineTiles, onlineAttribution);
  const offlineLayer = makeLayer(offlineTiles, offlineAttribution);
  let baseLayer = null;

  const setBaseLayer = (mode) => {
    if (window.GRMS_DISABLE_BASEMAP === true) {
      return;
    }
    if (baseLayer) {
      map.removeLayer(baseLayer);
    }
    baseLayer = mode === "offline" ? offlineLayer : onlineLayer;
    if (baseLayer) {
      baseLayer.addTo(map);
    }
  };

  if (window.GRMS_DISABLE_BASEMAP !== true) {
    const LayerControl = L.Control.extend({
      onAdd: function () {
        const container = L.DomUtil.create("div", "grms-layer-control");
        const button = L.DomUtil.create("button", "grms-layer-btn", container);
        button.type = "button";
        const icon = L.DomUtil.create("span", "grms-layer-icon", button);
        icon.setAttribute("aria-hidden", "true");
        const menu = L.DomUtil.create("div", "grms-layer-menu", container);

        const addOption = (id, label, checked, disabled) => {
          const wrapper = L.DomUtil.create("label", "", menu);
          const input = L.DomUtil.create("input", "", wrapper);
          input.type = "radio";
          input.name = "grms-base-layer";
          input.value = id;
          input.checked = checked;
          input.disabled = disabled;
          wrapper.appendChild(document.createTextNode(" " + label));
          input.addEventListener("change", () => setBaseLayer(id));
        };

        addOption("offline", "Offline", Boolean(offlineLayer), !offlineLayer);
        addOption("online", "Online", !offlineLayer, !onlineLayer);

        button.addEventListener("click", () => {
          menu.classList.toggle("is-open");
        });

        L.DomEvent.disableClickPropagation(container);
        return container;
      },
      onRemove: function () {},
    });

    map.addControl(new LayerControl({ position: "topright" }));
  }

  setBaseLayer(offlineLayer ? "offline" : "online");

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
