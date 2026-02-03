(function () {
  function colorFor(role) {
    switch (role) {
      case "road":
        return "#666";
      case "section":
        return "#1f77b4";
      case "section_current":
        return "#ff7f0e";
      case "segment":
        return "#2ca02c";
      case "segment_current":
        return "#d62728";
      case "structure":
        return "#9467bd";
      case "structure_current":
        return "#e377c2";
      default:
        return "#333";
    }
  }

  function weightFor(role) {
    if (role && role.endsWith("_current")) {
      return 6;
    }
    if (role === "road") {
      return 4;
    }
    return 3;
  }

  function pointRadiusFor(role) {
    return role && role.endsWith("_current") ? 9 : 6;
  }

  function render() {
    if (!window.GRMS_MAP_CFG) {
      return;
    }
    if (!window.L) {
      console.error("Leaflet is not loaded.");
      return;
    }

    var el = document.getElementById("grms-map");
    if (!el) {
      return;
    }

    var map = L.map("grms-map", { preferCanvas: true });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 20,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    var url =
      window.GRMS_MAP_CFG.endpoint +
      "?" +
      new URLSearchParams(window.GRMS_MAP_CFG.params);

    fetch(url)
      .then(function (r) {
        return r.json();
      })
      .then(function (fc) {
        var layer = L.geoJSON(fc, {
          style: function (feature) {
            var role =
              (feature.properties && feature.properties.role) || "x";
            return {
              color: colorFor(role),
              weight: weightFor(role),
              opacity: 0.95,
            };
          },
          pointToLayer: function (feature, latlng) {
            var role =
              (feature.properties && feature.properties.role) || "x";
            return L.circleMarker(latlng, {
              radius: pointRadiusFor(role),
              color: colorFor(role),
              weight: 2,
              fillOpacity: 0.85,
            });
          },
          onEachFeature: function (feature, lyr) {
            var p = feature.properties || {};
            lyr.bindPopup(
              "<b>" + (p.role || "") + "</b><br/>id=" + (p.id || "")
            );
          },
        }).addTo(map);

        var b = layer.getBounds();
        if (b && b.isValid && b.isValid()) {
          map.fitBounds(b, { padding: [20, 20] });
        } else {
          map.setView([14.0, 38.9], 8);
        }
      })
      .catch(function (err) {
        console.error("Map context fetch failed:", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})();
