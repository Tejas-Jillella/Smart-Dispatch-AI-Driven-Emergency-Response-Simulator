import geopandas as gpd
import folium
import json
import random
import requests
from branca.element import Element


FACILITY_LAYERS = [
    {
        "name": "Fire Stations",
        "url": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Safety_WebMercator/MapServer/6/query",
        "icon_color": "red",
        "icon": "fire",
        "prefix": "fa",
        "js_key": "fire",
    },
    {
        "name": "Police Stations",
        "url": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Safety_WebMercator/MapServer/11/query",
        "icon_color": "blue",
        "icon": "shield",
        "prefix": "fa",
        "js_key": "police",
    },
    {
        "name": "Hospitals",
        "url": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Health_WebMercator/MapServer/4/query",
        "icon_color": "green",
        "icon": "plus-square",
        "prefix": "fa",
        "js_key": "hospital",
    },
]


def fetch_facility_features(url):
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("features", [])
    except requests.RequestException as exc:
        print(f"Warning: failed to fetch facility layer from {url}: {exc}")
        return []


def random_traffic_level():
    return random.choices(
        ["LOW", "MEDIUM", "HIGH"],
        weights=[0.6, 0.3, 0.1],
        k=1,
    )[0]

# Load datasets
boundary = gpd.read_file("data/boundary.geojson")
roads = gpd.read_file("data/roads.geojson")
signals = gpd.read_file("data/signals.geojson")

# Align coordinate systems
roads = roads.to_crs(boundary.crs)
signals = signals.to_crs(boundary.crs)

# Clip to DC
roads = gpd.clip(roads, boundary)
signals = gpd.clip(signals, boundary)

# Convert to WGS84 (Leaflet expects EPSG:4326)
boundary = boundary.to_crs(epsg=4326)
roads = roads.to_crs(epsg=4326)
signals = signals.to_crs(epsg=4326)

# Convert to JSON-safe dicts (Timestamp-safe)
boundary_json = json.loads(boundary.to_json(default=str))
roads_json = json.loads(roads.to_json(default=str))
signals_json = json.loads(signals.to_json(default=str))

for feature in roads_json["features"]:
    properties = feature.setdefault("properties", {})
    properties["trafficLevel"] = random_traffic_level()

# Create map
m = folium.Map(location=[38.9, -77.03], zoom_start=12, tiles="OpenStreetMap")

# Add boundary
boundary_layer = folium.GeoJson(
    boundary_json,
    name="Boundary",
    style_function=lambda _: {"color": "black", "weight": 2, "fillOpacity": 0},
).add_to(m)

# Add roads (this can be heavy)
roads_layer = folium.GeoJson(
    roads_json,
    name="Roads",
    style_function=lambda feature: {
        "weight": 1,
        "color": {
            "LOW": "#5b5b5b",
            "MEDIUM": "#f2b66d",
            "HIGH": "#e99a9a",
        }.get(feature["properties"].get("trafficLevel"), "#5b5b5b"),
    },
).add_to(m)

# Add facilities as toggleable layers
facility_coordinates = {"police": [], "fire": [], "hospital": []}
layer_control_defs = [
    {"label": "Boundary", "js_name": boundary_layer.get_name()},
    {"label": "Roads", "js_name": roads_layer.get_name()},
]
for facility in FACILITY_LAYERS:
    feature_group = folium.FeatureGroup(name=facility["name"])
    for feature in fetch_facility_features(facility["url"]):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue

        lon, lat = coordinates[:2]
        facility_coordinates[facility["js_key"]].append([lat, lon])
        properties = feature.get("properties") or {}
        popup_text = properties.get("NAME") or facility["name"]

        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(
                color=facility["icon_color"],
                icon=facility["icon"],
                prefix=facility["prefix"],
            ),
        ).add_to(feature_group)

    feature_group.add_to(m)
    layer_control_defs.append(
        {"label": facility["name"], "js_name": feature_group.get_name()}
    )

# Add signals as dots
signals_layer = folium.FeatureGroup(name="Signals")
for feat in signals_json["features"]:
    lon, lat = feat["geometry"]["coordinates"]
    folium.CircleMarker(
        location=[lat, lon],
        radius=2,
        color="red",
        fill=True,
        fill_opacity=0.8,
    ).add_to(signals_layer)
signals_layer.add_to(m)
layer_control_defs.append({"label": "Signals", "js_name": signals_layer.get_name()})

# Add fixed incident marker
folium.Marker(
    location=[38.9072, -77.0369],
    popup="Simulated Emergency Incident",
).add_to(m)

# Add a client-side simulation button
button_html = f"""
<div id='control-panel' style='position: fixed; top: 12px; left: 12px; z-index: 9999; width: 280px; color: #f3f4f6; background: rgba(17, 24, 39, 0.82); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; backdrop-filter: blur(8px); box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);'>
    <div style='padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);'>
        <strong style='font-size: 14px;'>Control Panel</strong>
    </div>
    <div style='padding: 12px;'>
        <div style='border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 10px;'>
            <button onclick='toggleSection("incident-section-content")' style='width: 100%; display: flex; align-items: center; justify-content: space-between; border: 0; background: transparent; color: #f3f4f6; cursor: pointer; padding: 0; font-size: 13px; font-weight: 600;'>
                <span>Incident Controls</span>
                <span>▾</span>
            </button>
            <div id='incident-section-content' style='display: block; margin-top: 10px;'>
                <input id='incident-input' type='text' placeholder='Describe incident' style='width: 100%; box-sizing: border-box; padding: 9px 10px; margin-bottom: 10px; display: block; border-radius: 8px; border: 1px solid rgba(255,255,255,0.14); background: rgba(255,255,255,0.08); color: #f9fafb;' />
                <button onclick='simulateEmergency()' style='width: 100%; padding: 10px 12px; cursor: pointer; border: 0; border-radius: 8px; background: #2563eb; color: white; font-weight: 600;'>
                    Simulate Emergency
                </button>
                <div id='dispatch-panel' style='margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.08); display: none;'></div>
            </div>
        </div>
        <div style='border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 10px;'>
            <button onclick='toggleSection("layers-section-content")' style='width: 100%; display: flex; align-items: center; justify-content: space-between; border: 0; background: transparent; color: #f3f4f6; cursor: pointer; padding: 0; font-size: 13px; font-weight: 600;'>
                <span>Map Layers</span>
                <span>▾</span>
            </button>
            <div id='layers-section-content' style='display: block; margin-top: 10px;'>
                <div id='layer-toggles' style='display: grid; gap: 6px;'></div>
            </div>
        </div>
        <div style='border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 10px;'>
            <div style='font-size: 13px; line-height: 1.45; color: #d1d5db;'>
                <div><b>Active incidents:</b> <span id='status-active-incidents'>0</span></div>
                <div><b>Units responding:</b> <span id='status-responding-units'>0</span></div>
                <div><b>Last event:</b> <span id='status-last-event'>None</span></div>
            </div>
        </div>
        <div>
            <button onclick='toggleSection("responders-section-content")' style='width: 100%; display: flex; align-items: center; justify-content: space-between; border: 0; background: transparent; color: #f3f4f6; cursor: pointer; padding: 0; font-size: 13px; font-weight: 600;'>
                <span>Active Responders</span>
                <span>▾</span>
            </button>
            <div id='responders-section-content' style='display: block; margin-top: 10px; max-height: 220px; overflow-y: auto; padding-right: 4px;'>
                <div id='status-panel-content' style='font-size: 13px; line-height: 1.45; color: #d1d5db;'>No active responders.</div>
            </div>
        </div>
    </div>
</div>

<script>
window.leafletMap = null;
window.mapClickBound = false;
window.incidentMarker = null;
window.incidentLocation = null;
window.incidentCounter = 0;
window.activeIncidents = [];
window.signalsLayer = null;
window.trafficSignals = [];
window.prioritySignals = new Map();
window.globalSignalPhase = 0;
window.signalCycleTimer = null;
window.activeResponderStates = [];
window.policeFacilities = {json.dumps(facility_coordinates["police"])};
window.fireFacilities = {json.dumps(facility_coordinates["fire"])};
window.hospitalFacilities = {json.dumps(facility_coordinates["hospital"])};
window.layerControlDefs = {json.dumps(layer_control_defs)};
window.layerRegistry = {{}};
window.statusSummary = {{
    activeIncidents: 0,
    respondingUnits: 0,
    lastEvent: "None"
}};

function toggleSection(sectionId) {{
    var section = document.getElementById(sectionId);
    if (!section) {{
        return;
    }}
    section.style.display = section.style.display === "none" ? "block" : "none";
}}

function showDispatchPanel(html) {{
    var panel = document.getElementById("dispatch-panel");
    panel.innerHTML = html;
    panel.style.display = "block";
}}

function showStatusPanel(html) {{
    var panel = document.getElementById("status-panel-content");
    panel.innerHTML = html;
}}

function updateStatusCounts() {{
    window.statusSummary.activeIncidents = window.activeIncidents.filter(function(incident) {{
        return incident.status !== "RESOLVED";
    }}).length;
    window.statusSummary.respondingUnits = window.activeResponderStates.filter(function(state) {{
        return state.status !== "AVAILABLE" && state.status !== "RETURN_FAILED";
    }}).length;
    renderStatusSummary();
}}

function renderStatusSummary() {{
    var activeIncidents = document.getElementById("status-active-incidents");
    var respondingUnits = document.getElementById("status-responding-units");
    var lastEvent = document.getElementById("status-last-event");
    if (activeIncidents) {{
        activeIncidents.textContent = String(window.statusSummary.activeIncidents);
    }}
    if (respondingUnits) {{
        respondingUnits.textContent = String(window.statusSummary.respondingUnits);
    }}
    if (lastEvent) {{
        lastEvent.textContent = window.statusSummary.lastEvent;
    }}
}}

function setStatusEvent(message) {{
    window.statusSummary.lastEvent = message;
    renderStatusSummary();
}}

function toggleMapLayer(jsName, visible) {{
    var map = window.leafletMap;
    var layer = window.layerRegistry[jsName];
    if (!map || !layer) {{
        return;
    }}

    if (visible) {{
        if (!map.hasLayer(layer)) {{
            map.addLayer(layer);
        }}
        return;
    }}

    if (map.hasLayer(layer)) {{
        map.removeLayer(layer);
    }}
}}

function renderLayerToggles() {{
    var container = document.getElementById("layer-toggles");
    if (!container) {{
        return;
    }}

    container.innerHTML = window.layerControlDefs.map(function(layerDef) {{
        return (
            "<label style='display:flex; align-items:center; gap:8px; font-size:13px; color:#e5e7eb;'>" +
            "<input type='checkbox' checked onchange='toggleMapLayer(&quot;" + layerDef.js_name + "&quot;, this.checked)'>" +
            '<span>' + layerDef.label + "</span>" +
            "</label>"
        );
    }}).join("");
}}

function formatTitleCase(value) {{
    if (!value) {{
        return "";
    }}
    return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}}

function pointDistance(lat1, lng1, lat2, lng2) {{
    var dLat = lat1 - lat2;
    var dLng = lng1 - lng2;
    return Math.sqrt(dLat * dLat + dLng * dLng);
}}

function nearestFacility(lat, lng, facilities) {{
    if (!facilities || !facilities.length) {{
        return null;
    }}

    var match = facilities[0];
    var bestDistance = pointDistance(lat, lng, match[0], match[1]);
    facilities.forEach(function(facility) {{
        var distance = pointDistance(lat, lng, facility[0], facility[1]);
        if (distance < bestDistance) {{
            match = facility;
            bestDistance = distance;
        }}
    }});
    return match;
}}

function responderFacilities(responder) {{
    if (responder === "police") {{
        return window.policeFacilities;
    }}
    if (responder === "fire department") {{
        return window.fireFacilities;
    }}
    return window.hospitalFacilities;
}}

function responderIcon(responder) {{
    if (responder === "police") {{
        return L.AwesomeMarkers.icon({{
            icon: "shield",
            markerColor: "blue",
            prefix: "fa"
        }});
    }}
    if (responder === "fire department") {{
        return L.AwesomeMarkers.icon({{
            icon: "fire",
            markerColor: "red",
            prefix: "fa"
        }});
    }}
    return L.AwesomeMarkers.icon({{
        icon: "plus-square",
        markerColor: "green",
        prefix: "fa"
    }});
}}

function incidentIcon() {{
    return L.AwesomeMarkers.icon({{
        icon: "exclamation-triangle",
        markerColor: "orange",
        prefix: "fa"
    }});
}}

function removeFixedIncidentMarker(map) {{
    map.eachLayer(function(layer) {{
        if (layer instanceof L.Marker && !(layer instanceof L.CircleMarker)) {{
            var latLng = layer.getLatLng();
            if (Math.abs(latLng.lat - 38.9072) < 0.00001 && Math.abs(latLng.lng - (-77.0369)) < 0.00001) {{
                map.removeLayer(layer);
            }}
        }}
    }});
}}

function bindMapClickHandler(map) {{
    if (window.mapClickBound) {{
        return;
    }}

    map.on("click", function(e) {{
        if (window.incidentMarker) {{
            map.removeLayer(window.incidentMarker);
        }}

        window.incidentLocation = [e.latlng.lat, e.latlng.lng];
        window.incidentMarker = L.marker(window.incidentLocation, {{
            icon: incidentIcon()
        }})
            .addTo(map)
            .bindPopup("Emergency Location")
            .openPopup();
    }});

    window.mapClickBound = true;
}}

function routeColor(responder) {{
    if (responder === "police") {{
        return "#2563eb";
    }}
    if (responder === "fire department") {{
        return "#dc2626";
    }}
    return "#059669";
}}

function applySignalState(signal, state) {{
    var visuals = {{
        NS_GREEN: {{
            symbol: "↑↓",
            color: "#1f8f3a"
        }},
        EW_GREEN: {{
            symbol: "←→",
            color: "#ca8a04"
        }},
        YELLOW: {{
            symbol: "⚠",
            color: "#d4a017"
        }}
    }};
    var visual = visuals[state];
    if (signal.state === state) {{
        return;
    }}
    signal.state = state;
    signal.marker.setIcon(L.divIcon({{
        className: "traffic-signal-icon",
        html:
            "<div style='width:24px; height:24px; line-height:24px; text-align:center; font-size:14px; font-weight:bold; border:1px solid " + visual.color + "; border-radius:999px; background:white; color:" + visual.color + ";'>" +
            visual.symbol +
            "</div>",
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    }}));
}}

function signalStateForPhase(signal) {{
    var phase = (window.globalSignalPhase + ((signal.index || 0) % 2) * 2) % 4;
    if (phase === 0) {{
        return "NS_GREEN";
    }}
    if (phase === 2) {{
        return "EW_GREEN";
    }}
    return "YELLOW";
}}

function latLngToMeters(point, origin) {{
    var avgLat = ((point.lat + origin.lat) / 2) * Math.PI / 180;
    return {{
        x: (point.lng - origin.lng) * 111320 * Math.cos(avgLat),
        y: (point.lat - origin.lat) * 110540
    }};
}}

function closestRouteSegmentInfo(routeCoordinates, signalLatLng) {{
    if (!routeCoordinates || routeCoordinates.length < 2) {{
        return null;
    }}

    var bestInfo = null;
    for (var i = 0; i < routeCoordinates.length - 1; i++) {{
        var startLatLng = L.latLng(routeCoordinates[i][0], routeCoordinates[i][1]);
        var endLatLng = L.latLng(routeCoordinates[i + 1][0], routeCoordinates[i + 1][1]);
        var origin = startLatLng;
        var start = latLngToMeters(startLatLng, origin);
        var end = latLngToMeters(endLatLng, origin);
        var point = latLngToMeters(signalLatLng, origin);
        var dx = end.x - start.x;
        var dy = end.y - start.y;
        var segmentLengthSquared = dx * dx + dy * dy;
        var t = 0;
        if (segmentLengthSquared > 0) {{
            t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / segmentLengthSquared;
            t = Math.max(0, Math.min(1, t));
        }}
        var projX = start.x + dx * t;
        var projY = start.y + dy * t;
        var distX = point.x - projX;
        var distY = point.y - projY;
        var distance = Math.sqrt(distX * distX + distY * distY);
        if (!bestInfo || distance < bestInfo.distance) {{
            bestInfo = {{
                distance: distance,
                segmentIndex: i,
                orientation: getTravelOrientation(routeCoordinates[i], routeCoordinates[i + 1])
            }};
        }}
    }}

    return bestInfo;
}}

function clearResponderPrioritySignals(state) {{
    if (!state.prioritySignals || !state.prioritySignals.length) {{
        state.prioritySignals = [];
        return;
    }}

    state.prioritySignals.forEach(function(priorityInfo) {{
        var entry = window.prioritySignals.get(priorityInfo.signal.index);
        if (!entry) {{
            return;
        }}
        entry.delete(state.id);
        if (!entry.size) {{
            window.prioritySignals.delete(priorityInfo.signal.index);
        }}
    }});
    state.prioritySignals = [];
}}

function registerRoutePrioritySignals(state) {{
    clearResponderPrioritySignals(state);
    state.prioritySignals = [];

    if (!state.route || state.route.length < 2) {{
        return;
    }}

    window.trafficSignals.forEach(function(signal) {{
        var segmentInfo = closestRouteSegmentInfo(state.route, signal.latLng);
        if (segmentInfo && segmentInfo.distance <= 40) {{
            state.prioritySignals.push({{
                signal: signal,
                segmentIndex: segmentInfo.segmentIndex,
                orientation: segmentInfo.orientation,
                isPriority: true
            }});
        }}
    }});
}}

function syncResponderSignalPriority(state) {{
    if (!state.prioritySignals || !state.prioritySignals.length || !state.route.length) {{
        return;
    }}

    var currentPoint = L.latLng(
        state.route[Math.min(state.routeIndex, state.route.length - 1)][0],
        state.route[Math.min(state.routeIndex, state.route.length - 1)][1]
    );

    state.prioritySignals.forEach(function(priorityInfo) {{
        var distance = currentPoint.distanceTo(priorityInfo.signal.latLng);
        var passed = state.routeIndex >= priorityInfo.segmentIndex + 1;
        var entry = window.prioritySignals.get(priorityInfo.signal.index);

        if (!passed && distance <= 60) {{
            if (!entry) {{
                entry = new Map();
                window.prioritySignals.set(priorityInfo.signal.index, entry);
            }}
            entry.set(
                state.id,
                priorityInfo.orientation === "NS" ? "NS_GREEN" : "EW_GREEN"
            );
            return;
        }}

        if (entry) {{
            entry.delete(state.id);
            if (!entry.size) {{
                window.prioritySignals.delete(priorityInfo.signal.index);
            }}
        }}
    }});
}}

function registerTrafficSignals() {{
    if (window.trafficSignals.length || !window.signalsLayer) {{
        return;
    }}
    window.signalsLayer.eachLayer(function(layer) {{
        if (
            layer instanceof L.CircleMarker &&
            layer.options &&
            layer.options.radius === 2 &&
            layer.options.color === "red"
        ) {{
            var latLng = layer.getLatLng();
            window.signalsLayer.removeLayer(layer);
            var marker = L.marker(latLng, {{
                interactive: false
            }}).addTo(window.signalsLayer);
            var signal = {{
                index: window.trafficSignals.length,
                marker: marker,
                latLng: latLng,
                state: null
            }};
            applySignalState(signal, signalStateForPhase(signal));
            window.trafficSignals.push(signal);
        }}
    }});
}}

function updateSignalStates() {{
    if (!window.trafficSignals.length) {{
        return;
    }}

    window.trafficSignals.forEach(function(signal) {{
        var priorityEntry = window.prioritySignals.get(signal.index);
        if (priorityEntry && priorityEntry.size) {{
            applySignalState(signal, priorityEntry.values().next().value);
            return;
        }}
        applySignalState(signal, signalStateForPhase(signal));
    }});
}}

function startSignalSimulation() {{
    if (window.signalCycleTimer) {{
        return;
    }}
    updateSignalStates();
    window.signalCycleTimer = window.setInterval(function() {{
        window.globalSignalPhase = (window.globalSignalPhase + 1) % 4;
        updateSignalStates();
    }}, 1000);
}}

function getTravelOrientation(startPoint, endPoint) {{
    var latDelta = Math.abs(endPoint[0] - startPoint[0]);
    var lngDelta = Math.abs(endPoint[1] - startPoint[1]);
    return latDelta >= lngDelta ? "NS" : "EW";
}}

function getNearbySignalControl(startPoint, endPoint) {{
    if (!window.trafficSignals.length) {{
        return null;
    }}

    var start = L.latLng(startPoint[0], startPoint[1]);
    var end = L.latLng(endPoint[0], endPoint[1]);
    var orientation = getTravelOrientation(startPoint, endPoint);
    var closestSignal = null;
    var closestDistance = Infinity;

    window.trafficSignals.forEach(function(signal) {{
        var distance = Math.min(
            start.distanceTo(signal.latLng),
            end.distanceTo(signal.latLng)
        );
        if (distance <= 30 && distance < closestDistance) {{
            closestSignal = signal;
            closestDistance = distance;
        }}
    }});

    if (!closestSignal) {{
        return null;
    }}

    if (closestSignal.state === "YELLOW") {{
        return "slow";
    }}

    if (
        (orientation === "NS" && closestSignal.state === "EW_GREEN") ||
        (orientation === "EW" && closestSignal.state === "NS_GREEN")
    ) {{
        return "stop";
    }}

    return "go";
}}

function clearRouteHighlights(incident) {{
    if (!incident || !incident.routeHighlightMarkers) {{
        return;
    }}
    incident.routeHighlightMarkers.forEach(function(marker) {{
        window.leafletMap.removeLayer(marker);
    }});
    incident.routeHighlightMarkers = [];
}}

function interpolateAlongRoute(routeCoordinates, markerCount) {{
    var segments = [];
    var totalDistance = 0;

    for (var i = 0; i < routeCoordinates.length - 1; i++) {{
        var start = L.latLng(routeCoordinates[i][0], routeCoordinates[i][1]);
        var end = L.latLng(routeCoordinates[i + 1][0], routeCoordinates[i + 1][1]);
        var distance = start.distanceTo(end);
        segments.push({{
            start: start,
            end: end,
            distance: distance
        }});
        totalDistance += distance;
    }}

    if (!totalDistance || markerCount < 2) {{
        return routeCoordinates;
    }}

    var points = [];
    for (var j = 0; j < markerCount; j++) {{
        var targetDistance = (totalDistance * j) / (markerCount - 1);
        var traversed = 0;

        for (var k = 0; k < segments.length; k++) {{
            var segment = segments[k];
            var nextTraversed = traversed + segment.distance;
            if (targetDistance <= nextTraversed || k === segments.length - 1) {{
                var progress = segment.distance === 0 ? 0 : (targetDistance - traversed) / segment.distance;
                var lat = segment.start.lat + (segment.end.lat - segment.start.lat) * progress;
                var lng = segment.start.lng + (segment.end.lng - segment.start.lng) * progress;
                points.push([lat, lng]);
                break;
            }}
            traversed = nextTraversed;
        }}
    }}

    return points;
}}

function animateSignals(routeCoordinates, incident) {{
    clearRouteHighlights(incident);
    interpolateAlongRoute(routeCoordinates, 8).forEach(function(point, index) {{
        window.setTimeout(function() {{
            var marker = L.circleMarker(point, {{
                radius: 5,
                color: "green",
                fillColor: "green",
                fillOpacity: 0.9
            }}).addTo(window.leafletMap);
            incident.routeHighlightMarkers.push(marker);
        }}, index * 250);
    }});
}}

function replaceResponderRouteLayer(state, route) {{
    if (state.routeLayer) {{
        window.leafletMap.removeLayer(state.routeLayer);
        if (state.incident) {{
            state.incident.routeLayers = state.incident.routeLayers.filter(function(layer) {{
                return layer !== state.routeLayer;
            }});
        }}
    }}

    state.routeLayer = L.polyline(route, {{
        color: routeColor(state.responder),
        weight: 4
    }}).addTo(window.leafletMap);
    if (state.incident) {{
        state.incident.routeLayers.push(state.routeLayer);
    }}
}}

function markIncidentResolved(incident) {{
    if (!incident || incident.status === "RESOLVED") {{
        return;
    }}
    incident.status = "RESOLVED";
    clearRouteHighlights(incident);
    updateStatusCounts();
}}

async function startResponderReturn(state) {{
    state.onSceneTimer = null;
    state.status = "RETURNING";
    setStatusEvent(formatTitleCase(state.responder) + " returning to base");
    updateStatusCounts();
    renderResponderStatus();

    try {{
        var returnRoute = await fetchRoute(state.incidentLocation, state.homeFacility);
        state.route = returnRoute;
        state.routeIndex = 0;
        state.etaSeconds = estimateEtaSeconds(returnRoute);
        replaceResponderRouteLayer(state, returnRoute);
        registerRoutePrioritySignals(state);
        syncResponderSignalPriority(state);
        animateResponderPath(state);
    }} catch (error) {{
        state.status = "RETURN_FAILED";
        clearResponderPrioritySignals(state);
        setStatusEvent(formatTitleCase(state.responder) + " return route failed");
        updateStatusCounts();
        renderResponderStatus();
        showStatusPanel(
            showStatusPanelContent(window.activeResponderStates.filter(function(responderState) {{
                return responderState.status !== "AVAILABLE";
            }})) +
            "<div style='margin-top:10px; color:#fca5a5;'>Return route failed for " +
            formatTitleCase(state.responder) +
            ": " + String(error.message || error) +
            "</div>"
        );
    }}
}}

function animateResponderPath(state) {{
    if (!state.route.length) {{
        return;
    }}

    function step() {{
        syncResponderSignalPriority(state);
        if (state.routeIndex >= state.route.length - 1) {{
            state.marker.setLatLng(state.route[state.route.length - 1]);
            state.animationId = null;
            if (state.status === "EN_ROUTE") {{
                state.status = "ON_SCENE";
                state.etaSeconds = 0;
                setStatusEvent(formatTitleCase(state.responder) + " on scene");
                updateStatusCounts();
                renderResponderStatus();
                state.onSceneTimer = window.setTimeout(function() {{
                    startResponderReturn(state);
                }}, 8000 + Math.floor(Math.random() * 7001));
                return;
            }}

            if (state.status === "RETURNING") {{
                state.status = "AVAILABLE";
                state.etaSeconds = 0;
                clearResponderPrioritySignals(state);
                if (state.routeLayer) {{
                    window.leafletMap.removeLayer(state.routeLayer);
                    if (state.incident) {{
                        state.incident.routeLayers = state.incident.routeLayers.filter(function(layer) {{
                            return layer !== state.routeLayer;
                        }});
                    }}
                    state.routeLayer = null;
                }}
                state.marker.setLatLng(state.homeFacility);
                if (state.incident) {{
                    state.incident.respondersReturned += 1;
                    if (state.incident.respondersReturned >= state.incident.responders.length) {{
                        markIncidentResolved(state.incident);
                        setStatusEvent("Incident resolved");
                    }} else {{
                        setStatusEvent(formatTitleCase(state.responder) + " available at station");
                    }}
                }} else {{
                    setStatusEvent(formatTitleCase(state.responder) + " available at station");
                }}
                updateStatusCounts();
                renderResponderStatus();
                return;
            }}

            renderResponderStatus();
            return;
        }}

        var currentPoint = state.route[state.routeIndex];
        var nextPoint = state.route[state.routeIndex + 1];
        var signalControl = getNearbySignalControl(currentPoint, nextPoint);
        var delay = 60;

        if (signalControl === "stop") {{
            state.marker.setLatLng(currentPoint);
            state.animationId = window.setTimeout(step, 250);
            return;
        }}

        if (signalControl === "slow") {{
            delay = 180;
        }}

        state.marker.setLatLng(nextPoint);
        state.routeIndex += 1;
        syncResponderSignalPriority(state);
        state.animationId = window.setTimeout(step, delay);
    }}

    step();
}}

function renderResponderStatus() {{
    var visibleStates = window.activeResponderStates.filter(function(state) {{
        return state.status !== "AVAILABLE";
    }});
    if (!visibleStates.length) {{
        showStatusPanel("No active responders.");
        return;
    }}

    var html = showStatusPanelContent(visibleStates);
    showStatusPanel(html);
}}

function showStatusPanelContent(states) {{
    return states.map(function(state) {{
        var details = "<div>Status: " + state.status + "</div>";
        if (state.status === "EN_ROUTE" || state.status === "RETURNING") {{
            details += "<div>ETA: " + state.etaSeconds + "s</div>";
        }} else if (state.status === "ON_SCENE") {{
            details += "<div>ETA: On scene</div>";
        }} else if (state.status === "AVAILABLE") {{
            details += "<div>ETA: At station</div>";
        }}
        return (
            "<div style='padding-bottom: 10px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>" +
            "<div><b>" + formatTitleCase(state.responder) + "</b></div>" +
            details +
            "</div>"
        );
    }}).join("");
}}

function estimateEtaSeconds(route) {{
    if (!route || route.length < 2) {{
        return 0;
    }}
    return Math.max(1, Math.round((route.length - 1) * 0.06));
}}

async function fetchDispatch(incidentText) {{
    const response = await fetch("http://127.0.0.1:5050/dispatch", {{
        method: "POST",
        headers: {{
            "Content-Type": "application/json"
        }},
        body: JSON.stringify({{ incident: incidentText }})
    }});

    if (!response.ok) {{
        throw new Error(await response.text());
    }}

    return response.json();
}}

async function fetchRoute(start, end) {{
    const url =
        "https://router.project-osrm.org/route/v1/driving/" +
        start[1] + "," + start[0] + ";" + end[1] + "," + end[0] +
        "?overview=full&geometries=geojson";

    const response = await fetch(url);
    if (!response.ok) {{
        throw new Error("OSRM route request failed");
    }}

    const data = await response.json();
    const coordinates = (((data.routes || [])[0] || {{}}).geometry || {{}}).coordinates || [];
    if (!coordinates.length) {{
        throw new Error("No route returned");
    }}

    return coordinates.map(function(coord) {{
        return [coord[1], coord[0]];
    }});
}}

function waitForMap() {{
    var map = window["{m.get_name()}"];
    var roadLayer = window["{roads_layer.get_name()}"];
    var signalsLayer = window["{signals_layer.get_name()}"];
    if (!map || !roadLayer || !signalsLayer) {{
        window.setTimeout(waitForMap, 100);
        return;
    }}

    window.leafletMap = map;
    window.signalsLayer = signalsLayer;
    window.layerControlDefs.forEach(function(layerDef) {{
        var layer = window[layerDef.js_name];
        if (layer) {{
            window.layerRegistry[layerDef.js_name] = layer;
        }}
    }});
    renderLayerToggles();
    removeFixedIncidentMarker(map);
    bindMapClickHandler(map);
    registerTrafficSignals();
    startSignalSimulation();
    renderStatusSummary();
}}

window.onload = function() {{
    waitForMap();
}};

async function simulateEmergency() {{
    const map = window.leafletMap;
    const text = document.getElementById("incident-input").value || "Unspecified";

    if (!map) {{
        showDispatchPanel("<b>Error:</b><br>Map not ready");
        return;
    }}

    if (!window.incidentLocation) {{
        showDispatchPanel("<b>Error:</b><br>Click the map first");
        return;
    }}

    showDispatchPanel("<b>Dispatching...</b>");

    try {{
        const dispatch = await fetchDispatch(text);
        showDispatchPanel(
            "<b>AI Decision</b><br>" +
            "<b>Incident:</b> " + text +
            "<br><b>Responders:</b> " + formatTitleCase((dispatch.responders || []).join(", ")) +
            "<br><b>Priority:</b> " + formatTitleCase(dispatch.priority || "") +
            "<br><b>Reason:</b> " + (dispatch.reason || "")
        );

        const responders = dispatch.responders || [];
        if (!responders.length) {{
            throw new Error("No responders returned");
        }}

        const incident = {{
            id: "incident-" + (++window.incidentCounter),
            location: window.incidentLocation.slice(),
            marker: window.incidentMarker,
            routeHighlightMarkers: [],
            routeLayers: [],
            responders: [],
            respondersReturned: 0,
            status: "ACTIVE"
        }};
        window.activeIncidents.push(incident);
        window.incidentMarker = null;
        window.incidentLocation = null;
        setStatusEvent("Units dispatched");

        const responderStates = await Promise.all(
            responders.map(async function(responder, index) {{
                const facility = nearestFacility(
                    incident.location[0],
                    incident.location[1],
                    responderFacilities(responder)
                );
                if (!facility) {{
                    throw new Error("No facility found for " + responder);
                }}

                const route = await fetchRoute(facility, incident.location);
                return {{
                    id: incident.id + "-" + index + "-" + responder,
                    incident: incident,
                    responder: responder,
                    homeFacility: facility,
                    incidentLocation: incident.location.slice(),
                    route: route,
                    routeIndex: 0,
                    status: "EN_ROUTE",
                    etaSeconds: estimateEtaSeconds(route),
                    marker: null,
                    animationId: null,
                    onSceneTimer: null,
                    routeLayer: null,
                    prioritySignals: []
                }};
            }})
        );

        incident.responders = responderStates;
        window.activeResponderStates = window.activeResponderStates.concat(responderStates);
        updateStatusCounts();
        renderResponderStatus();

        responderStates.forEach(function(state, index) {{
            replaceResponderRouteLayer(state, state.route);
            registerRoutePrioritySignals(state);

            if (index === 0) {{
                map.fitBounds(state.routeLayer.getBounds());
                animateSignals(state.route, incident);
            }}

            state.marker = L.marker(state.route[0], {{
                icon: responderIcon(state.responder)
            }}).addTo(map);
            syncResponderSignalPriority(state);
            animateResponderPath(state);
        }});
    }} catch (e) {{
        showDispatchPanel("<b>Error:</b><br>" + e);
    }}
}}
</script>
"""
m.get_root().html.add_child(Element(button_html))

m.save("dc_map.html")
print("Saved: dc_map.html")
