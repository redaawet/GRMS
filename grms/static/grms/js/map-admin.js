(function () {
    "use strict";

    function parseJSONScript(id) {
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

    function clampFraction(value) {
        if (!Number.isFinite(value)) {
            return null;
        }
        return Math.max(0, Math.min(1, value));
    }

    function interpolatePoint(start, end, fraction) {
        const clamped = clampFraction(fraction);
        if (!start || !end || clamped === null) {
            return null;
        }
        return [
            start.lat + (end.lat - start.lat) * clamped,
            start.lng + (end.lng - start.lng) * clamped,
        ];
    }

    function formatBounds(bounds) {
        if (!bounds || !bounds.northeast || !bounds.southwest) {
            return null;
        }
        return [
            [bounds.southwest.lat, bounds.southwest.lng],
            [bounds.northeast.lat, bounds.northeast.lng],
        ];
    }

    const DEFAULT_MAP_REGION = {
        formatted_address: "UTM Zone 37N (Ethiopia)",
        center: { lat: 9.0, lng: 39.0 },
        viewport: {
            northeast: { lat: 15.0, lng: 42.0 },
            southwest: { lat: 3.0, lng: 36.0 },
        },
    };

    function initMapAdmin() {
        const config = parseJSONScript("map-admin-config");
        const panel = document.getElementById("map-panel");
        const refreshButton = document.getElementById("map-panel-refresh");
        const statusEl = document.getElementById("map-panel-status");
        const viewport = document.getElementById("map-panel-viewport");

        if (!config || !panel || !viewport) {
            return;
        }

        if (!window.L) {
            if (statusEl) {
                statusEl.textContent = "Leaflet failed to load.";
                statusEl.className = "road-map-panel__status error";
            }
            return;
        }

        let map;
        let overlay;

        function showStatus(message, level) {
            if (!statusEl) {
                return;
            }
            statusEl.textContent = message || "";
            statusEl.className = "road-map-panel__status" + (level ? " " + level : "");
        }

        function ensureMapContainer() {
            const existing = viewport.querySelector("#map-view");
            if (existing) {
                return existing;
            }
            viewport.innerHTML = "";
            const mapNode = document.createElement("div");
            mapNode.id = "map-view";
            mapNode.className = "road-map";
            mapNode.style.minHeight = "360px";
            viewport.appendChild(mapNode);
            return mapNode;
        }

        function addViewport(region) {
            if (!region || !overlay) {
                return null;
            }
            const bounds = formatBounds(region.viewport || region.bounds);
            if (!bounds) {
                return null;
            }
            const rectangle = L.rectangle(bounds, { color: "#22c55e", weight: 2, dashArray: "6 4", fillOpacity: 0.05 });
            rectangle.addTo(overlay);
            return bounds;
        }

        function drawRange(startPoint, endPoint, options) {
            if (!startPoint || !endPoint || !overlay) {
                return;
            }
            L.polyline([startPoint, endPoint], options).addTo(overlay);
        }

        function renderMap(payload) {
            const mapNode = ensureMapContainer();
            const mapRegion = (payload && payload.map_region) || DEFAULT_MAP_REGION;
            const center = (mapRegion && mapRegion.center) || DEFAULT_MAP_REGION.center;

            const roadStart = (payload && payload.start) || (config.road && config.road.start);
            const roadEnd = (payload && payload.end) || (config.road && config.road.end);
            const roadLength = (config.road && config.road.length_km) || (payload && payload.road_length_km) || null;

            if (!map) {
                map = L.map(mapNode).setView([center.lat, center.lng], mapRegion.zoom || 7);
                L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    maxZoom: 18,
                    attribution: "&copy; OpenStreetMap contributors",
                }).addTo(map);
                overlay = L.layerGroup().addTo(map);
            } else if (overlay) {
                overlay.clearLayers();
            }

            const viewportBounds = addViewport(mapRegion);

            let roadLine;
            if (roadStart && roadEnd && overlay) {
                roadLine = L.polyline(
                    [
                        [roadStart.lat, roadStart.lng],
                        [roadEnd.lat, roadEnd.lng],
                    ],
                    { color: "#6b7280", weight: 4 }
                ).addTo(overlay);
                map.fitBounds(roadLine.getBounds(), { padding: [30, 30] });
            } else if (viewportBounds) {
                map.fitBounds(viewportBounds, { padding: [24, 24] });
            }

            if (!roadLine || !roadLength || roadLength <= 0) {
                return;
            }

            const sectionStartFraction = config.section && clampFraction(config.section.start_chainage_km / roadLength);
            const sectionEndFraction = config.section && clampFraction(config.section.end_chainage_km / roadLength);
            if (sectionStartFraction !== null && sectionEndFraction !== null) {
                drawRange(
                    interpolatePoint(roadStart, roadEnd, sectionStartFraction),
                    interpolatePoint(roadStart, roadEnd, sectionEndFraction),
                    { color: "#0ea5e9", weight: 6 }
                );
            }

            if (config.scope === "segment" && config.segment) {
                const segmentStart = clampFraction(config.segment.station_from_km / roadLength);
                const segmentEnd = clampFraction(config.segment.station_to_km / roadLength);
                if (segmentStart !== null && segmentEnd !== null) {
                    drawRange(
                        interpolatePoint(roadStart, roadEnd, segmentStart),
                        interpolatePoint(roadStart, roadEnd, segmentEnd),
                        { color: "#f97316", weight: 7 }
                    );
                }
            }
        }

        function buildQueryString() {
            const params = new URLSearchParams();
            const adminFields = config.admin_fields || {};
            const defaults = config.default_admin_selection || {};

            if (adminFields.zone_override) {
                const zone = document.getElementById(adminFields.zone_override);
                if (zone && zone.value) {
                    params.append("zone_id", zone.value);
                }
            } else if (defaults.zone_id) {
                params.append("zone_id", defaults.zone_id);
            }

            if (adminFields.woreda_override) {
                const woreda = document.getElementById(adminFields.woreda_override);
                if (woreda && woreda.value) {
                    params.append("woreda_id", woreda.value);
                }
            } else if (defaults.woreda_id) {
                params.append("woreda_id", defaults.woreda_id);
            }

            const query = params.toString();
            if (!query) {
                return "";
            }
            const base = panel.dataset.mapContextUrl || "";
            return (base.indexOf("?") === -1 ? "?" : "&") + query;
        }

        function fetchMapContext() {
            const baseUrl = panel.dataset.mapContextUrl;
            if (!baseUrl) {
                showStatus("Map context is not available.", "error");
                return;
            }
            const query = buildQueryString();
            showStatus("Loading map context…");
            fetch(baseUrl + query, { credentials: "same-origin" })
                .then(function (response) {
                    if (!response.ok) {
                        return response.json().catch(function () { return {}; }).then(function (payload) {
                            const detail = payload.detail || "Unable to load map context.";
                            throw new Error(detail);
                        });
                    }
                    return response.json();
                })
                .then(function (payload) {
                    showStatus("Map context loaded.", "success");
                    renderMap(payload);
                })
                .catch(function (err) {
                    showStatus(err.message, "error");
                });
        }

        if (refreshButton) {
            refreshButton.addEventListener("click", function () {
                fetchMapContext();
            });
        }

        fetchMapContext();
    }

    document.addEventListener("DOMContentLoaded", initMapAdmin);
})();
