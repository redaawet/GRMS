(function () {
  "use strict";

  var DEFAULT_MAP_CENTER = window.DEFAULT_MAP_CENTER ?? [13.5, 39.5];

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function toCenter(center) {
    if (Array.isArray(center) && center.length >= 2) {
      var lat = Number(center[0]);
      var lng = Number(center[1]);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        return { lat: lat, lng: lng, zoom: 7 };
      }
      return null;
    }
    if (
      center &&
      typeof center === "object" &&
      Number.isFinite(center.lat) &&
      Number.isFinite(center.lng)
    ) {
      return {
        lat: Number(center.lat),
        lng: Number(center.lng),
        zoom: Number(center.zoom || 7),
      };
    }
    return null;
  }

  function setDefaultView(map) {
    var center = toCenter(DEFAULT_MAP_CENTER);
    if (!center) {
      return;
    }
    map.setView([center.lat, center.lng], center.zoom || 7);
  }

  function normalizeFeatures(features) {
    if (!Array.isArray(features)) {
      return [];
    }
    return features.filter(function (feature) {
      return feature && feature.geometry;
    });
  }

  function featureCollection(features) {
    return { type: "FeatureCollection", features: features || [] };
  }

  function featureById(features, id) {
    if (!Array.isArray(features) || id == null) {
      return null;
    }
    return (
      features.find(function (feature) {
        return feature && feature.properties && feature.properties.id === id;
      }) || null
    );
  }

  function getBoundsForFeature(feature) {
    if (!feature || !feature.geometry || !window.L) {
      return null;
    }
    var layer = L.geoJSON(feature);
    if (!layer || !layer.getBounds) {
      return null;
    }
    var bounds = layer.getBounds();
    if (bounds && bounds.isValid && bounds.isValid()) {
      return bounds;
    }
    return null;
  }

  function bindAdminClick(layer, feature) {
    var url = feature && feature.properties && feature.properties.admin_url;
    if (!url) {
      return;
    }
    layer.on("click", function () {
      window.location.href = url;
    });
  }

  function renderMap(map, payload) {
    var road = payload && payload.road;
    var sections = normalizeFeatures(payload && payload.sections);
    var segments = normalizeFeatures(payload && payload.segments);
    var structures = normalizeFeatures(payload && payload.structures);

    var sectionPalette = [
      "#2563eb",
      "#10b981",
      "#f59e0b",
      "#ec4899",
      "#8b5cf6",
      "#14b8a6",
      "#f97316",
    ];
    var segmentPalette = [
      "#0ea5e9",
      "#f97316",
      "#22c55e",
      "#e11d48",
      "#a855f7",
      "#facc15",
    ];

    sections.forEach(function (feature, index) {
      feature.properties = feature.properties || {};
      feature.properties._color =
        sectionPalette[index % sectionPalette.length];
    });
    segments.forEach(function (feature, index) {
      feature.properties = feature.properties || {};
      feature.properties._color =
        segmentPalette[index % segmentPalette.length];
    });

    var roadLayer = road && road.geometry
      ? L.geoJSON(road, {
          style: { color: "#0f172a", weight: 5, opacity: 0.8 },
          onEachFeature: function (feature, layer) {
            bindAdminClick(layer, feature);
          },
        })
      : null;

    var sectionLayer =
      sections.length > 0
        ? L.geoJSON(featureCollection(sections), {
            style: function (feature) {
              var isCurrent =
                feature &&
                feature.properties &&
                feature.properties.id === payload.current_section_id;
              var color =
                (feature &&
                  feature.properties &&
                  feature.properties._color) ||
                "#94a3b8";
              return {
                color: isCurrent ? "#1d4ed8" : color,
                weight: isCurrent ? 6 : 4,
                opacity: 0.9,
              };
            },
            onEachFeature: function (feature, layer) {
              bindAdminClick(layer, feature);
            },
          })
        : null;

    var segmentLayer =
      segments.length > 0
        ? L.geoJSON(featureCollection(segments), {
            style: function (feature) {
              var isCurrent =
                feature &&
                feature.properties &&
                feature.properties.id === payload.current_segment_id;
              var color =
                (feature &&
                  feature.properties &&
                  feature.properties._color) ||
                "#94a3b8";
              return {
                color: isCurrent ? "#dc2626" : color,
                weight: isCurrent ? 6 : 4,
                opacity: 0.9,
              };
            },
            onEachFeature: function (feature, layer) {
              bindAdminClick(layer, feature);
            },
          })
        : null;

    var structureLayer =
      structures.length > 0
        ? L.geoJSON(featureCollection(structures), {
            pointToLayer: function (feature, latlng) {
              var props = feature && feature.properties ? feature.properties : {};
              var isCurrent = props.id === payload.current_structure_id;
              var kind = (props.kind || "").toLowerCase();
              var baseColor = "#10b981";
              if (kind === "bridge") {
                baseColor = "#2563eb";
              } else if (kind === "culvert") {
                baseColor = "#f97316";
              }
              var color = isCurrent ? "#dc2626" : baseColor;
              return L.circleMarker(latlng, {
                radius: isCurrent ? 8 : 5,
                color: color,
                weight: isCurrent ? 3 : 2,
                fillColor: color,
                fillOpacity: 0.9,
              });
            },
            onEachFeature: function (feature, layer) {
              bindAdminClick(layer, feature);
            },
          })
        : null;

    if (roadLayer) {
      roadLayer.addTo(map);
    }
    if (sectionLayer) {
      sectionLayer.addTo(map);
    }
    if (segmentLayer) {
      segmentLayer.addTo(map);
    }
    if (structureLayer) {
      structureLayer.addTo(map);
    }

    var mode = payload && payload.mode;
    var currentFeature = null;
    var parentFeature = null;

    if (mode === "section") {
      currentFeature = featureById(sections, payload.current_section_id);
      parentFeature = road;
    } else if (mode === "segment") {
      currentFeature = featureById(segments, payload.current_segment_id);
      parentFeature = payload.section || null;
    } else if (mode === "structure") {
      currentFeature = featureById(structures, payload.current_structure_id);
      parentFeature = payload.segment || payload.section || null;
    }

    var bounds =
      getBoundsForFeature(currentFeature) ||
      getBoundsForFeature(parentFeature) ||
      getBoundsForFeature(road);

    if (bounds && bounds.isValid && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [20, 20] });
    } else {
      setDefaultView(map);
    }
  }

  function init() {
    var container = document.getElementById("asset-context-map");
    if (!container) {
      return;
    }

    if (container.dataset.mapInitialized) {
      return;
    }
    container.dataset.mapInitialized = "true";

    if (!window.L) {
      console.error(
        "Asset context map requires Leaflet (window.L) but it was not found."
      );
      return;
    }

    var contextUrl = container.dataset.contextUrl;
    if (!contextUrl) {
      console.error("Asset context map missing data-context-url.");
      return;
    }

    var map = L.map(container);
    setDefaultView(map);

    var blankLayer = L.layerGroup().addTo(map);
    var baseLayers = { Blank: blankLayer };
    var layerControl = L.control
      .layers(baseLayers, null, { collapsed: true })
      .addTo(map);

    var offlineTilesUrl = window.GRMS_OFFLINE_TILES_URL;
    if (offlineTilesUrl) {
      var offlineLayer = L.tileLayer(offlineTilesUrl, { maxZoom: 19 });
      layerControl.addBaseLayer(offlineLayer, "Offline");

      var offlineStart = Date.now();
      var offlineErrored = false;
      var offlineTimeout = setTimeout(function () {
        if (offlineErrored && map.hasLayer(offlineLayer)) {
          map.removeLayer(offlineLayer);
        }
      }, 2500);

      offlineLayer.once("tileload", function () {
        clearTimeout(offlineTimeout);
      });
      offlineLayer.once("tileerror", function () {
        offlineErrored = true;
        if (Date.now() - offlineStart < 2500 && map.hasLayer(offlineLayer)) {
          map.removeLayer(offlineLayer);
        }
      });
      map.addLayer(offlineLayer);
    }

    var onlineLayer = L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors",
      }
    );

    function enableOnlineLayer() {
      if (layerControl && onlineLayer) {
        layerControl.addBaseLayer(onlineLayer, "Online");
      }
    }

    if (window.GRMS_ONLINE_STATUS_URL) {
      fetch(window.GRMS_ONLINE_STATUS_URL, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (resp) {
          return resp.ok ? resp.json() : null;
        })
        .then(function (payload) {
          if (payload && payload.online === true) {
            enableOnlineLayer();
          }
        })
        .catch(function () {});
    } else if (typeof navigator !== "undefined" && navigator.onLine) {
      enableOnlineLayer();
    }

    fetch(contextUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (resp) {
        if (!resp.ok) {
          throw new Error("Context response " + resp.status);
        }
        return resp.json();
      })
      .then(function (payload) {
        renderMap(map, payload || {});
        window.__GRMS_MAP_CONTEXT_LOADED = true;
        window.__GRMS_MAP_READY = true;
      })
      .catch(function (err) {
        console.error("Failed to load asset context map", err);
      });

    function scheduleInvalidate() {
      setTimeout(function () {
        map.invalidateSize();
      }, 0);
    }

    window.addEventListener("load", scheduleInvalidate);

    if (window.django && window.django.jQuery) {
      window.django
        .jQuery(document)
        .on("click", ".collapse-toggle", scheduleInvalidate);
    }
  }

  ready(init);
})();
