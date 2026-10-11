/**
 * Hazard IQ - Urban Hazard Intelligence Map Module v2.0
 *
 * NEW in v2:
 *  - Heat Hotspots with configurable circular risk zones
 *  - Cooling Spots (parks, shaded forests, air-conditioned malls)
 *  - Relief Spots (health facilities, water points, cooling centres)
 *  - Vegetation Coverage indicator
 *  - Layer visibility toggles
 *  - Dashboard summary cards
 *
 * All new dataset entries are DEMO / ILLUSTRATIVE data.
 * Existing incident dataset and coordinates are unchanged.
 */

(function () {
  'use strict';

  /* =========================================================================
     Delhi Geographic Constants
     ========================================================================= */
  const DELHI_CONFIG = {
    center: [28.6139, 77.2090],
    initialZoom: 11,
    minZoom: 9,
    maxZoom: 18,
    tileLayerUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
  };

  /* =========================================================================
     Data Paths
     ========================================================================= */
  const INCIDENT_DATA_PATHS   = ['src/data/incidents.json', 'data/incidents.json'];
  const COOLING_DATA_PATHS    = ['src/data/cooling_spots.json', 'data/cooling_spots.json'];
  const RELIEF_DATA_PATHS     = ['src/data/relief_spots.json', 'data/relief_spots.json'];
  const HOTSPOT_DATA_PATHS    = ['src/data/heat_hotspots.json', 'data/heat_hotspots.json'];
  const VEGETATION_DATA_PATHS = ['src/data/vegetation.json', 'data/vegetation.json'];

  /* =========================================================================
     Embedded Fallback Datasets
     ========================================================================= */
  const FALLBACK_INCIDENTS = [
    { id: "INC-DEL-001", name: "Demo Heat - Connaught Place", latitude: 28.6315, longitude: 77.2167, mode: "heat", severity: 3 },
    { id: "INC-DEL-002", name: "Demo Heat - Chandni Chowk", latitude: 28.6506, longitude: 77.2303, mode: "heat", severity: 4 },
    { id: "INC-DEL-003", name: "Demo Heat - Nehru Place", latitude: 28.5494, longitude: 77.2536, mode: "heat", severity: 3 },
    { id: "INC-DEL-004", name: "Demo Heat - Anand Vihar ISBT", latitude: 28.6469, longitude: 77.3160, mode: "heat", severity: 5 },
    { id: "INC-DEL-005", name: "Demo Heat - Rohini Sector 10", latitude: 28.7166, longitude: 77.1189, mode: "heat", severity: 2 },
    { id: "INC-DEL-006", name: "Demo Heat - Karol Bagh", latitude: 28.6517, longitude: 77.1906, mode: "heat", severity: 3 },
    { id: "INC-DEL-007", name: "Demo Heat - Okhla Industrial Area", latitude: 28.5355, longitude: 77.2732, mode: "heat", severity: 5 },
    { id: "INC-DEL-008", name: "Demo Heat - Dwarka Sector 14", latitude: 28.5921, longitude: 77.0378, mode: "heat", severity: 2 },
    { id: "INC-DEL-009", name: "Demo Heat - Janakpuri District Centre", latitude: 28.6297, longitude: 77.0797, mode: "heat", severity: 3 },
    { id: "INC-DEL-010", name: "Demo Heat - Narela Industrial Area", latitude: 28.8527, longitude: 77.0931, mode: "heat", severity: 4 },
    { id: "INC-DEL-011", name: "Demo Monsoon - Minto Bridge Underpass", latitude: 28.6341, longitude: 77.2248, mode: "monsoon", severity: 5, depthCm: 85 },
    { id: "INC-DEL-012", name: "Demo Monsoon - ITO Junction Ring Road", latitude: 28.6294, longitude: 77.2434, mode: "monsoon", severity: 4, depthCm: 40 },
    { id: "INC-DEL-013", name: "Demo Monsoon - Dhaula Kuan Underpass", latitude: 28.5923, longitude: 77.1611, mode: "monsoon", severity: 3, depthCm: 30 },
    { id: "INC-DEL-014", name: "Demo Monsoon - Zakhira Underpass", latitude: 28.6698, longitude: 77.1602, mode: "monsoon", severity: 4, depthCm: 60 },
    { id: "INC-DEL-015", name: "Demo Monsoon - Pul Prahladpur Underpass", latitude: 28.5028, longitude: 77.2912, mode: "monsoon", severity: 5, depthCm: 75 },
    { id: "INC-DEL-016", name: "Demo Monsoon - Kashmere Gate Ring Road", latitude: 28.6675, longitude: 77.2285, mode: "monsoon", severity: 4, depthCm: 50 },
    { id: "INC-DEL-017", name: "Demo Monsoon - Mayur Vihar Phase 1", latitude: 28.6078, longitude: 77.2965, mode: "monsoon", severity: 2, depthCm: 20 },
    { id: "INC-DEL-018", name: "Demo Monsoon - Azadpur Underpass", latitude: 28.7072, longitude: 77.1772, mode: "monsoon", severity: 3, depthCm: 35 },
    { id: "INC-DEL-019", name: "Demo Monsoon - AIIMS Ring Road Loop", latitude: 28.5672, longitude: 77.2100, mode: "monsoon", severity: 2, depthCm: 15 },
    { id: "INC-DEL-020", name: "Demo Monsoon - Najafgarh Drain Road", latitude: 28.6092, longitude: 76.9856, mode: "monsoon", severity: 3, depthCm: 25 }
  ];

  const FALLBACK_COOLING = [
    { id: "COOL-001", name: "Lodhi Garden [DEMO]", category: "park", locality: "Lodhi Colony, South Delhi", latitude: 28.5933, longitude: 77.2239, coolingNote: "Large heritage park with dense canopy shade.", dataStatus: "demo_sample" },
    { id: "COOL-002", name: "Sanjay Van Forest Reserve [DEMO]", category: "forest_shade", locality: "Vasant Kunj", latitude: 28.5498, longitude: 77.1576, coolingNote: "Dense urban forest reserve providing substantial shade.", dataStatus: "demo_sample" },
    { id: "COOL-003", name: "Select CITYWALK Mall [DEMO]", category: "mall", locality: "Saket, South Delhi", latitude: 28.5274, longitude: 77.2192, coolingNote: "Air-conditioned mall. DEMO — verify access hours independently.", dataStatus: "demo_sample" }
  ];

  const FALLBACK_RELIEF = [
    { id: "RELIEF-001", name: "AIIMS Trauma Centre [DEMO]", category: "health_facility", locality: "Ansari Nagar, South Delhi", latitude: 28.5665, longitude: 77.2100, assistance: "Major public hospital. DEMO entry — verify services independently.", dataStatus: "demo_sample" },
    { id: "RELIEF-002", name: "Safdarjung Hospital [DEMO]", category: "health_facility", locality: "Safdarjung, New Delhi", latitude: 28.5687, longitude: 77.2063, assistance: "Government hospital. DEMO entry.", dataStatus: "demo_sample" }
  ];

  const FALLBACK_HOTSPOTS = [
    { id: "HOT-001", name: "Okhla Industrial Zone [DEMO]", riskLevel: "critical", riskScore: 5, radiusMeters: 1200, latitude: 28.5355, longitude: 77.2732, description: "Industrial area with high heat load. Illustrative risk zone.", dataStatus: "illustrative_demo" },
    { id: "HOT-002", name: "Chandni Chowk Market [DEMO]", riskLevel: "high", riskScore: 4, radiusMeters: 800, latitude: 28.6506, longitude: 77.2303, description: "Dense commercial market. Illustrative risk zone.", dataStatus: "illustrative_demo" },
    { id: "HOT-003", name: "Connaught Place Core [DEMO]", riskLevel: "moderate", riskScore: 3, radiusMeters: 600, latitude: 28.6315, longitude: 77.2167, description: "CBD paved surfaces. Illustrative risk zone.", dataStatus: "illustrative_demo" }
  ];

  const FALLBACK_VEGETATION = {
    dataStatus: "illustrative_demo",
    coverageArea: "NCT Delhi (~1484 sq km)",
    referenceYear: "2024 (illustrative estimate)",
    overallPercentage: 20.2,
    districts: []
  };

  /* =========================================================================
     Layer State
     ========================================================================= */
  let mapInstance = null;
  let incidentsLayerGroup = null;
  let hotspotMarkersGroup = null;
  let hotspotCirclesGroup = null;
  let coolingLayerGroup   = null;
  let reliefLayerGroup    = null;

  let demoIncidents    = [];
  const citizenReports = [];
  let coolingSpotsData = [];
  let reliefSpotsData  = [];
  let heatHotspotsData = [];
  let vegetationData   = null;

  let currentActiveMode = 'heat';
  let selectionMarker   = null;

  const layerVisibility = {
    incidents: true,
    hotspots:  true,
    cooling:   true,
    relief:    true,
    vegetation: true
  };

  /* =========================================================================
     Risk Level Config for Hotspot Circles
     ========================================================================= */
  const RISK_CONFIG = {
    critical: { color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.13, weight: 2.5, dashArray: null },
    high:     { color: '#f97316', fillColor: '#f97316', fillOpacity: 0.10, weight: 2,   dashArray: null },
    moderate: { color: '#f59e0b', fillColor: '#f59e0b', fillOpacity: 0.08, weight: 1.5, dashArray: '6,4' },
    low:      { color: '#84cc16', fillColor: '#84cc16', fillOpacity: 0.06, weight: 1.5, dashArray: '4,6' }
  };

  /* =========================================================================
     Generic Data Loader
     ========================================================================= */
  async function loadJsonData(paths, fallback, label) {
    for (const path of paths) {
      try {
        const resp = await fetch(path);
        if (resp.ok) {
          const data = await resp.json();
          if (data && (Array.isArray(data) ? data.length > 0 : true)) {
            console.log('[Hazard IQ] Loaded ' + label + ' from ' + path);
            return data;
          }
        }
      } catch (_) { /* fall through */ }
    }
    console.info('[Hazard IQ] Using embedded fallback for ' + label);
    return fallback;
  }

  /* =========================================================================
     HTML Escape
     ========================================================================= */
  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = String(text || '');
    return d.innerHTML;
  }

  /* =========================================================================
     Icon Factories
     ========================================================================= */
  function createPinIcon(mode) {
    const isHeat     = mode === 'heat';
    const pinColor   = isHeat ? '#f97316' : '#22d3ee';
    const glowColor  = isHeat ? 'rgba(249,115,22,0.45)' : 'rgba(34,211,238,0.4)';
    const pulseColor = isHeat ? 'rgba(249,115,22,0.25)' : 'rgba(34,211,238,0.2)';
    const borderColor= isHeat ? '#fb923c' : '#67e8f9';
    const pulseClass = isHeat ? 'pin-pulse-heat' : 'pin-pulse-monsoon';

    const iconSvg = isHeat
      ? '<svg viewBox="0 0 24 24" width="12" height="12" fill="white"><path d="M12 2C8.5 8 6 11 6 14a6 6 0 0012 0c0-3-2.5-6-6-12z" opacity="0.9"/><path d="M12 8c-1.5 3-2.5 4.5-2.5 6a2.5 2.5 0 005 0C14.5 12.5 13.5 11 12 8z" fill="rgba(255,200,100,0.9)"/></svg>'
      : '<svg viewBox="0 0 24 24" width="12" height="12" fill="white"><path d="M12 2C9 6 6 9 6 12.5a6 6 0 0012 0C18 9 15 6 12 2z" opacity="0.9"/><circle cx="10" cy="14" r="1.5" fill="rgba(180,240,255,0.8)"/></svg>';

    return L.divIcon({
      html: '<div class="incident-pin-wrapper"><div class="pin-pulse-ring ' + pulseClass + '" style="--pulse-color:' + pulseColor + ';"></div><div class="incident-pin" style="background:linear-gradient(160deg,' + borderColor + ',' + pinColor + ');box-shadow:0 2px 12px ' + glowColor + ',0 0 0 2px rgba(255,255,255,0.12);">' + iconSvg + '</div><div class="pin-tip" style="border-top-color:' + pinColor + ';"></div></div>',
      className: '', iconSize: [28, 38], iconAnchor: [14, 38], popupAnchor: [0, -40]
    });
  }

  function createCoolingIcon(category) {
    const cfg = {
      park:         { emoji: '\uD83C\uDF33', bg: '#14532d', border: '#22c55e', glow: 'rgba(34,197,94,0.5)' },
      forest_shade: { emoji: '\uD83C\uDF32', bg: '#064e3b', border: '#10b981', glow: 'rgba(16,185,129,0.5)' },
      mall:         { emoji: '\uD83C\uDFEC', bg: '#1e3a5f', border: '#60a5fa', glow: 'rgba(96,165,250,0.5)' }
    };
    const c = cfg[category] || cfg.park;
    return L.divIcon({
      html: '<div class="custom-icon cooling-icon" style="background:' + c.bg + ';border-color:' + c.border + ';box-shadow:0 0 12px ' + c.glow + ';">' + c.emoji + '</div>',
      className: '', iconSize: [34, 34], iconAnchor: [17, 34], popupAnchor: [0, -36]
    });
  }

  function createReliefIcon(category) {
    const cfg = {
      health_facility: { emoji: '\uD83C\uDFE5', bg: '#7f1d1d', border: '#f87171', glow: 'rgba(248,113,113,0.5)' },
      water_point:     { emoji: '\uD83D\uDCA7', bg: '#1e3a5f', border: '#38bdf8', glow: 'rgba(56,189,248,0.5)' },
      cooling_centre:  { emoji: '\u2744\uFE0F',  bg: '#1e1b4b', border: '#818cf8', glow: 'rgba(129,140,248,0.5)' }
    };
    const c = cfg[category] || cfg.health_facility;
    return L.divIcon({
      html: '<div class="custom-icon relief-icon" style="background:' + c.bg + ';border-color:' + c.border + ';box-shadow:0 0 12px ' + c.glow + ';">' + c.emoji + '</div>',
      className: '', iconSize: [34, 34], iconAnchor: [17, 34], popupAnchor: [0, -36]
    });
  }

  /* =========================================================================
     Atmospheric Telemetry (unchanged from v1)
     ========================================================================= */
  function getAtmosphericTelemetry(incident) {
    if (incident.mode === 'heat') {
      const sev = incident.severity || 3;
      const latOffset = (Math.abs(incident.latitude * 10) % 1) * 1.5;
      const temp = (40.5 + sev * 0.8 + latOffset).toFixed(1);
      const humidity = Math.max(18, Math.round(36 - sev * 3));
      const lngOffset = (Math.abs(incident.longitude * 10) % 1) * 6;
      const wind = (7.5 + lngOffset).toFixed(1);
      return { temp: temp + '\u00B0C', humidity: humidity + '%', wind: wind + ' km/h' };
    } else {
      const sev = incident.severity || 3;
      const depth = incident.depthCm != null ? incident.depthCm + ' cm' : '30 cm';
      const humidity = Math.min(96, Math.round(80 + sev * 3)) + '%';
      const lngOffset = (Math.abs(incident.longitude * 10) % 1) * 8;
      const wind = (16.0 + lngOffset).toFixed(1);
      return { depth: depth, humidity: humidity, wind: wind + ' km/h' };
    }
  }

  /* =========================================================================
     Popup HTML Builders
     ========================================================================= */
  function buildIncidentPopupHtml(incident) {
    const isHeat    = incident.mode === 'heat';
    const tel       = getAtmosphericTelemetry(incident);
    const isCitizen = incident.id && incident.id.toString().startsWith('CITIZEN-');
    const badgeText = isHeat ? '\uD83D\uDD25 Heat Hotspot' : '\uD83C\uDF27\uFE0F Monsoon Flood';
    const badgeClass= isHeat ? 'popup-badge-heat' : 'popup-badge-monsoon';
    const sevLabel  = incident.severity ? incident.severity + '/5 Severity' : 'Unrated';
    const coords    = Number(incident.latitude).toFixed(4) + '\u00B0N, ' + Number(incident.longitude).toFixed(4) + '\u00B0E';

    var m = isHeat
      ? '<div class="popup-metrics-grid"><div class="metric-item"><span class="metric-label">\uD83C\uDF21\uFE0F Temp</span><span class="metric-val temp-val">' + tel.temp + '</span></div><div class="metric-item"><span class="metric-label">\uD83D\uDCA7 Humidity</span><span class="metric-val humidity-val">' + tel.humidity + '</span></div><div class="metric-item"><span class="metric-label">\uD83D\uDCA8 Wind</span><span class="metric-val wind-val">' + tel.wind + '</span></div></div>'
      : '<div class="popup-metrics-grid"><div class="metric-item"><span class="metric-label">\uD83C\uDF0A Depth</span><span class="metric-val depth-val">' + tel.depth + '</span></div><div class="metric-item"><span class="metric-label">\uD83D\uDCA7 Humidity</span><span class="metric-val humidity-val">' + tel.humidity + '</span></div><div class="metric-item"><span class="metric-label">\uD83D\uDCA8 Wind</span><span class="metric-val wind-val">' + tel.wind + '</span></div></div>';

    return '<div class="incident-popup-card"><div class="popup-header"><span class="popup-badge ' + badgeClass + '">' + badgeText + '</span><h3 class="popup-title">' + escapeHtml(incident.name || 'Unnamed Incident') + '</h3></div>' + m + '<p class="popup-desc">' + escapeHtml(incident.description || 'Observed urban environmental stress.') + '</p><div class="popup-footer"><span>' + sevLabel + (isCitizen ? ' &bull; Citizen Report' : '') + '</span><span>' + coords + '</span></div></div>';
  }

  function buildHotspotPopupHtml(h) {
    const riskColors = { critical: '#ef4444', high: '#f97316', moderate: '#f59e0b', low: '#84cc16' };
    const color = riskColors[h.riskLevel] || '#f59e0b';
    const radiusKm = (h.radiusMeters / 1000).toFixed(1);
    return '<div class="incident-popup-card"><div class="popup-header"><span class="popup-badge" style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '55;">\u26A0\uFE0F Heat Hotspot</span><h3 class="popup-title">' + escapeHtml(h.name) + '</h3></div><div class="popup-metrics-grid"><div class="metric-item"><span class="metric-label">Risk</span><span class="metric-val" style="color:' + color + '">' + escapeHtml(h.riskLevel.toUpperCase()) + '</span></div><div class="metric-item"><span class="metric-label">Score</span><span class="metric-val temp-val">' + h.riskScore + '/5</span></div><div class="metric-item"><span class="metric-label">Radius</span><span class="metric-val humidity-val">' + radiusKm + ' km</span></div></div><p class="popup-desc">' + escapeHtml(h.description || '') + '</p><div class="popup-footer"><span class="demo-tag">\u26A0\uFE0F Illustrative zone \u2014 not scientifically validated</span><span>' + Number(h.latitude).toFixed(4) + '\u00B0N</span></div></div>';
  }

  function buildCoolingPopupHtml(s) {
    var catLabels = { park: '\uD83C\uDF33 Park / Green Space', forest_shade: '\uD83C\uDF32 Forest / Shaded Area', mall: '\uD83C\uDFEC Air-Conditioned Mall' };
    var catLabel  = catLabels[s.category] || s.category;
    return '<div class="incident-popup-card"><div class="popup-header"><span class="popup-badge" style="background:rgba(34,197,94,0.15);color:#4ade80;border:1px solid rgba(34,197,94,0.35);">' + catLabel + '</span><h3 class="popup-title">' + escapeHtml(s.name) + '</h3></div><p class="popup-desc" style="margin-top:8px"><strong style="color:#94a3b8;font-size:0.7rem">LOCALITY</strong><br>' + escapeHtml(s.locality || 'Delhi') + '</p><p class="popup-desc">' + escapeHtml(s.coolingNote || '') + '</p><div class="popup-footer"><span class="demo-tag">\uD83D\uDCCB Demo/Sample entry</span><span>' + Number(s.latitude).toFixed(4) + '\u00B0N</span></div></div>';
  }

  function buildReliefPopupHtml(r) {
    var catLabels = { health_facility: '\uD83C\uDFE5 Health Facility', water_point: '\uD83D\uDCA7 Water Point', cooling_centre: '\u2744\uFE0F Cooling Centre' };
    var catLabel  = catLabels[r.category] || r.category;
    var isIllust  = r.dataStatus === 'illustrative_demo';
    return '<div class="incident-popup-card"><div class="popup-header"><span class="popup-badge" style="background:rgba(248,113,113,0.15);color:#fca5a5;border:1px solid rgba(248,113,113,0.35);">' + catLabel + '</span><h3 class="popup-title">' + escapeHtml(r.name) + '</h3></div><p class="popup-desc" style="margin-top:8px"><strong style="color:#94a3b8;font-size:0.7rem">LOCALITY</strong><br>' + escapeHtml(r.locality || 'Delhi') + '</p><p class="popup-desc">' + escapeHtml(r.assistance || '') + '</p><div class="popup-footer"><span class="demo-tag">' + (isIllust ? '\u26A0\uFE0F Illustrative \u2014 not verified' : '\uD83D\uDCCB Demo/Sample entry') + '</span><span>' + Number(r.latitude).toFixed(4) + '\u00B0N</span></div></div>';
  }

  /* =========================================================================
     Dashboard
     ========================================================================= */
  function updateDashboard() {
    var hotCount  = document.getElementById('dash-hotspot-count');
    var coolCount = document.getElementById('dash-cooling-count');
    var relCount  = document.getElementById('dash-relief-count');
    var vegPct    = document.getElementById('dash-veg-pct');
    if (hotCount)  hotCount.textContent  = heatHotspotsData.length;
    if (coolCount) coolCount.textContent = coolingSpotsData.length;
    if (relCount)  relCount.textContent  = reliefSpotsData.length;
    if (vegPct && vegetationData) vegPct.textContent = vegetationData.overallPercentage + '%';
  }

  /* =========================================================================
     Render: Heat Hotspot Circles + Markers
     ========================================================================= */
  function renderHeatHotspots(map) {
    if (!map) return;
    if (!hotspotMarkersGroup) {
      hotspotMarkersGroup = L.layerGroup().addTo(map);
      hotspotCirclesGroup = L.layerGroup().addTo(map);
    } else {
      hotspotMarkersGroup.clearLayers();
      hotspotCirclesGroup.clearLayers();
    }
    if (!layerVisibility.hotspots) return;

    heatHotspotsData.forEach(function (h) {
      var lat = Number(h.latitude), lng = Number(h.longitude);
      if (isNaN(lat) || isNaN(lng)) return;
      var rc = RISK_CONFIG[h.riskLevel] || RISK_CONFIG.moderate;

      var circle = L.circle([lat, lng], {
        radius: h.radiusMeters, color: rc.color, fillColor: rc.fillColor,
        fillOpacity: rc.fillOpacity, weight: rc.weight, dashArray: rc.dashArray, interactive: false
      });
      hotspotCirclesGroup.addLayer(circle);

      var markerIcon = L.divIcon({
        html: '<div class="hotspot-marker-pin" style="border-color:' + rc.color + ';box-shadow:0 0 14px ' + rc.color + '88;">\u26A0\uFE0F</div>',
        className: '', iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -18]
      });
      var marker = L.marker([lat, lng], { icon: markerIcon, zIndexOffset: 50 });
      marker.bindPopup(buildHotspotPopupHtml(h), { maxWidth: 300, className: 'delhi-popup' });
      hotspotMarkersGroup.addLayer(marker);
    });
  }

  /* =========================================================================
     Render: Cooling Spots
     ========================================================================= */
  function renderCoolingSpots(map) {
    if (!map) return;
    if (!coolingLayerGroup) {
      coolingLayerGroup = L.layerGroup().addTo(map);
    } else {
      coolingLayerGroup.clearLayers();
    }
    if (!layerVisibility.cooling) return;

    coolingSpotsData.forEach(function (s) {
      var lat = Number(s.latitude), lng = Number(s.longitude);
      if (isNaN(lat) || isNaN(lng)) return;
      var marker = L.marker([lat, lng], { icon: createCoolingIcon(s.category), riseOnHover: true });
      marker.bindPopup(buildCoolingPopupHtml(s), { maxWidth: 300, className: 'delhi-popup' });
      coolingLayerGroup.addLayer(marker);
    });
  }

  /* =========================================================================
     Render: Relief Spots
     ========================================================================= */
  function renderReliefSpots(map) {
    if (!map) return;
    if (!reliefLayerGroup) {
      reliefLayerGroup = L.layerGroup().addTo(map);
    } else {
      reliefLayerGroup.clearLayers();
    }
    if (!layerVisibility.relief) return;

    reliefSpotsData.forEach(function (r) {
      var lat = Number(r.latitude), lng = Number(r.longitude);
      if (isNaN(lat) || isNaN(lng)) return;
      var marker = L.marker([lat, lng], { icon: createReliefIcon(r.category), riseOnHover: true });
      marker.bindPopup(buildReliefPopupHtml(r), { maxWidth: 300, className: 'delhi-popup' });
      reliefLayerGroup.addLayer(marker);
    });
  }

  /* =========================================================================
     Vegetation Card
     ========================================================================= */
  function renderVegetationCard() {
    if (!vegetationData) return;
    var pctEl  = document.getElementById('veg-overall-pct');
    var areaEl = document.getElementById('veg-area');
    var yearEl = document.getElementById('veg-year');
    var barEl  = document.getElementById('veg-bar-fill');
    var listEl = document.getElementById('veg-district-list');
    if (pctEl)  pctEl.textContent  = vegetationData.overallPercentage + '%';
    if (areaEl) areaEl.textContent = vegetationData.coverageArea || '';
    if (yearEl) yearEl.textContent = vegetationData.referenceYear || '';
    if (barEl)  barEl.style.width  = Math.min(100, vegetationData.overallPercentage) + '%';

    if (listEl && Array.isArray(vegetationData.districts)) {
      listEl.innerHTML = '';
      vegetationData.districts.forEach(function (d) {
        var pct   = d.percentage;
        var color = pct >= 25 ? '#22c55e' : pct >= 15 ? '#84cc16' : '#f59e0b';
        var li    = document.createElement('div');
        li.className = 'veg-district-row';
        li.innerHTML = '<span class="veg-district-name">' + escapeHtml(d.name) + '</span><div class="veg-district-bar-wrap"><div class="veg-district-bar" style="width:' + Math.min(100, pct) + '%;background:' + color + '"></div></div><span class="veg-district-pct" style="color:' + color + '">' + pct + '%</span>';
        listEl.appendChild(li);
      });
    }
  }

  /* =========================================================================
     Incident Mode Switcher
     ========================================================================= */
  function getAllIncidents() {
    return [].concat(demoIncidents, citizenReports);
  }

  function updateMarkersForCurrentMode() {
    if (!mapInstance) return;
    var all     = getAllIncidents();
    var heatCnt = all.filter(function (i) { return i.mode === 'heat'; }).length;
    var monCnt  = all.filter(function (i) { return i.mode === 'monsoon'; }).length;
    var bH = document.getElementById('badge-heat-count');
    var bM = document.getElementById('badge-monsoon-count');
    if (bH) bH.textContent = heatCnt;
    if (bM) bM.textContent = monCnt;

    var filtered = all.filter(function (i) { return i.mode === currentActiveMode; });
    renderIncidentMarkers(mapInstance, filtered);

    var noticeEl   = document.getElementById('no-incidents-notice');
    var noticeText = document.getElementById('no-incidents-text');
    if (noticeEl && noticeText) {
      if (filtered.length === 0) {
        noticeText.textContent = 'No incidents for ' + (currentActiveMode === 'heat' ? 'Heat Incidents' : 'Monsoon / Flood') + '. Submit one using the form.';
        noticeEl.style.display = 'flex';
      } else {
        noticeEl.style.display = 'none';
      }
    }
  }

  function renderIncidentMarkers(map, incidents) {
    if (!map || !Array.isArray(incidents)) return;
    if (!incidentsLayerGroup) {
      incidentsLayerGroup = L.layerGroup().addTo(map);
    } else {
      incidentsLayerGroup.clearLayers();
    }
    if (!layerVisibility.incidents) return;

    var seenIds = new Set();
    incidents.forEach(function (inc) {
      if (!inc.id || seenIds.has(inc.id)) return;
      seenIds.add(inc.id);
      var lat = Number(inc.latitude), lng = Number(inc.longitude);
      if (isNaN(lat) || isNaN(lng)) return;
      var marker = L.marker([lat, lng], { icon: createPinIcon(inc.mode), riseOnHover: true });
      marker.bindPopup(buildIncidentPopupHtml(inc), { maxWidth: 300, className: 'delhi-popup' });
      incidentsLayerGroup.addLayer(marker);
    });
  }

  function setMapMode(mode) {
    if (mode !== 'heat' && mode !== 'monsoon') return;
    currentActiveMode = mode;
    var bH = document.getElementById('btn-mode-heat');
    var bM = document.getElementById('btn-mode-monsoon');
    if (bH && bM) {
      if (mode === 'heat') {
        bH.classList.add('active');    bH.setAttribute('aria-selected', 'true');
        bM.classList.remove('active'); bM.setAttribute('aria-selected', 'false');
      } else {
        bM.classList.add('active');    bM.setAttribute('aria-selected', 'true');
        bH.classList.remove('active'); bH.setAttribute('aria-selected', 'false');
      }
    }
    var modeTag = document.getElementById('active-mode-indicator');
    if (modeTag) modeTag.textContent = mode === 'heat' ? 'Active: Heat Incidents' : 'Active: Monsoon / Flood';
    updateMarkersForCurrentMode();
  }

  function initModeToggle() {
    var bH = document.getElementById('btn-mode-heat');
    var bM = document.getElementById('btn-mode-monsoon');
    if (bH) bH.addEventListener('click', function () { setMapMode('heat'); });
    if (bM) bM.addEventListener('click', function () { setMapMode('monsoon'); });
  }

  /* =========================================================================
     Layer Toggle Controls
     ========================================================================= */
  function initLayerToggles(map) {
    var defs = [
      { id: 'toggle-incidents', key: 'incidents', refresh: function () { updateMarkersForCurrentMode(); } },
      { id: 'toggle-hotspots',  key: 'hotspots',  refresh: function () { renderHeatHotspots(map); } },
      { id: 'toggle-cooling',   key: 'cooling',   refresh: function () { renderCoolingSpots(map); } },
      { id: 'toggle-relief',    key: 'relief',    refresh: function () { renderReliefSpots(map); } }
    ];
    defs.forEach(function (def) {
      var btn = document.getElementById(def.id);
      if (!btn) return;
      btn.addEventListener('click', function () {
        layerVisibility[def.key] = !layerVisibility[def.key];
        btn.classList.toggle('layer-btn-off', !layerVisibility[def.key]);
        btn.setAttribute('aria-pressed', String(layerVisibility[def.key]));
        def.refresh();
      });
    });

    var vegToggle = document.getElementById('toggle-vegetation');
    var vegCard   = document.getElementById('veg-info-card');
    if (vegToggle && vegCard) {
      vegToggle.addEventListener('click', function () {
        layerVisibility.vegetation = !layerVisibility.vegetation;
        vegCard.style.display = layerVisibility.vegetation ? 'block' : 'none';
        vegToggle.classList.toggle('layer-btn-off', !layerVisibility.vegetation);
        vegToggle.setAttribute('aria-pressed', String(layerVisibility.vegetation));
      });
    }
  }

  /* =========================================================================
     Form Alerts
     ========================================================================= */
  function showFormAlert(msg, type) {
    var el = document.getElementById('form-alert');
    if (!el) return;
    el.className = 'form-alert ' + (type === 'error' ? 'alert-error' : type === 'success' ? 'alert-success' : 'alert-info');
    el.textContent = msg;
    el.style.display = 'block';
  }
  function hideFormAlert() {
    var el = document.getElementById('form-alert');
    if (el) { el.style.display = 'none'; el.textContent = ''; }
  }

  /* =========================================================================
     Location Selection
     ========================================================================= */
  function handleLocationSelect(lat, lng, map) {
    var latIn = document.getElementById('report-lat');
    var lngIn = document.getElementById('report-lng');
    if (latIn) latIn.value = lat;
    if (lngIn) lngIn.value = lng;
    var locDisp  = document.getElementById('location-display');
    var coordsTxt= document.getElementById('coords-text');
    if (coordsTxt) coordsTxt.textContent = '\uD83D\uDCCD ' + lat.toFixed(4) + '\u00B0 N, ' + lng.toFixed(4) + '\u00B0 E';
    if (locDisp)  locDisp.classList.add('has-coords');

    if (!selectionMarker) {
      selectionMarker = L.circleMarker([lat, lng], {
        radius: 10, fillColor: '#f59e0b', color: '#b45309', weight: 3, opacity: 1, fillOpacity: 0.9
      }).addTo(map);
    } else {
      selectionMarker.setLatLng([lat, lng]);
    }
    selectionMarker.bindPopup('<strong>\uD83D\uDCCD Selected Location</strong><br>' + lat.toFixed(4) + '\u00B0 N, ' + lng.toFixed(4) + '\u00B0 E').openPopup();
    var rp = document.getElementById('report-panel');
    if (rp && rp.classList.contains('panel-collapsed')) rp.classList.remove('panel-collapsed');
    hideFormAlert();
  }

  /* =========================================================================
     Citizen Reporting
     ========================================================================= */
  function initCitizenReporting(map) {
    map.on('click', function (e) { handleLocationSelect(e.latlng.lat, e.latlng.lng, map); });

    var geoBtn = document.getElementById('geo-btn');
    if (geoBtn) {
      geoBtn.addEventListener('click', function () {
        if (!navigator.geolocation) { showFormAlert('Geolocation not supported by your browser.', 'error'); return; }
        showFormAlert('Detecting location...', 'info');
        geoBtn.disabled = true;
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            geoBtn.disabled = false;
            handleLocationSelect(pos.coords.latitude, pos.coords.longitude, map);
            map.flyTo([pos.coords.latitude, pos.coords.longitude], 14, { duration: 1.2 });
            showFormAlert('\uD83D\uDCCD Location detected: ' + pos.coords.latitude.toFixed(4) + '\u00B0 N, ' + pos.coords.longitude.toFixed(4) + '\u00B0 E', 'info');
          },
          function (err) {
            geoBtn.disabled = false;
            var msgs = {};
            msgs[err.PERMISSION_DENIED]   = 'Location permission denied. Please allow access or click the map.';
            msgs[err.POSITION_UNAVAILABLE]= 'Location unavailable. Please click the map to choose.';
            msgs[err.TIMEOUT]             = 'Location request timed out. Please try again.';
            showFormAlert(msgs[err.code] || 'Unable to retrieve your location.', 'error');
          },
          { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
      });
    }

    var toggleBtn   = document.getElementById('toggle-panel-btn');
    var panelHeader = document.getElementById('panel-header');
    var reportPanel = document.getElementById('report-panel');
    if (toggleBtn && reportPanel) toggleBtn.addEventListener('click', function (e) { e.stopPropagation(); reportPanel.classList.toggle('panel-collapsed'); });
    if (panelHeader && reportPanel) panelHeader.addEventListener('click', function () { reportPanel.classList.toggle('panel-collapsed'); });

    var typeSelect = document.getElementById('incident-type');
    var depthGroup = document.getElementById('depth-group');
    var depthInput = document.getElementById('incident-depth');
    if (typeSelect && depthGroup) {
      typeSelect.addEventListener('change', function () {
        depthGroup.style.opacity = typeSelect.value === 'heat' ? '0.4' : '1';
        if (typeSelect.value === 'heat' && depthInput) depthInput.value = '';
      });
    }

    var incidentForm = document.getElementById('incident-form');
    if (incidentForm) {
      incidentForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var latVal  = parseFloat(document.getElementById('report-lat').value);
        var lngVal  = parseFloat(document.getElementById('report-lng').value);
        var typeVal = document.getElementById('incident-type').value;
        var nameVal = document.getElementById('incident-name').value.trim();
        var descVal = document.getElementById('incident-description').value.trim();
        var sevVal  = document.getElementById('incident-severity').value;
        var dVal    = document.getElementById('incident-depth').value.trim();

        if (isNaN(latVal) || isNaN(lngVal)) { showFormAlert('Please select an incident location on the map or use GPS.', 'error'); return; }
        if (!typeVal || (typeVal !== 'heat' && typeVal !== 'monsoon')) { showFormAlert('Please select an incident type.', 'error'); return; }
        if (!nameVal) { showFormAlert('Please enter an incident name.', 'error'); return; }
        if (!descVal) { showFormAlert('Please enter a description.', 'error'); return; }

        var parsedSev = null;
        if (sevVal !== '') {
          parsedSev = parseInt(sevVal, 10);
          if (isNaN(parsedSev) || parsedSev < 1 || parsedSev > 5) { showFormAlert('Severity must be between 1 and 5.', 'error'); return; }
        }
        var parsedDepth = null;
        if (dVal !== '') {
          parsedDepth = parseFloat(dVal);
          if (isNaN(parsedDepth) || parsedDepth < 0) { showFormAlert('Water depth must be a non-negative number.', 'error'); return; }
        }

        var newReport = { id: 'CITIZEN-' + Date.now(), name: nameVal, latitude: latVal, longitude: lngVal, mode: typeVal, description: descVal, severity: parsedSev, depthCm: parsedDepth, photoUrl: null, verificationStatus: 'unverified_citizen_report' };
        citizenReports.push(newReport);
        updateMarkersForCurrentMode();
        if (selectionMarker) { map.removeLayer(selectionMarker); selectionMarker = null; }
        incidentForm.reset();
        document.getElementById('report-lat').value = '';
        document.getElementById('report-lng').value = '';
        var ct = document.getElementById('coords-text');
        if (ct) ct.textContent = 'No location selected (click map or GPS)';
        var ld = document.getElementById('location-display');
        if (ld) ld.classList.remove('has-coords');
        if (depthGroup) depthGroup.style.opacity = '1';
        var targetLabel = newReport.mode === 'heat' ? 'Heat Incidents' : 'Monsoon / Flood';
        showFormAlert(newReport.mode === currentActiveMode ? '\u2705 Report submitted! Marker added to map (session only).' : '\u2705 Report submitted under "' + targetLabel + '" \u2014 switch mode to view.', 'success');
      });
    }
  }

  /* =========================================================================
     Main Init
     ========================================================================= */
  async function initDelhiMap() {
    var mapEl = document.getElementById('map');
    if (!mapEl) { console.error('[Hazard IQ] #map container not found.'); return null; }
    if (mapEl.clientHeight === 0) console.warn('[Hazard IQ] #map has 0 height — check CSS.');

    var map = L.map('map', {
      center: DELHI_CONFIG.center, zoom: DELHI_CONFIG.initialZoom,
      minZoom: DELHI_CONFIG.minZoom, maxZoom: DELHI_CONFIG.maxZoom,
      zoomControl: true, preferCanvas: true
    });
    mapInstance = map;

    L.tileLayer(DELHI_CONFIG.tileLayerUrl, { maxZoom: 19, attribution: DELHI_CONFIG.attribution }).addTo(map);

    var zoomDisplay   = document.getElementById('zoom-display');
    var coordsDisplay = document.getElementById('coords-display');
    var recenterBtn   = document.getElementById('recenter-btn');

    map.on('zoomend',   function () { if (zoomDisplay) zoomDisplay.textContent = 'Zoom: ' + map.getZoom() + 'x'; });
    map.on('mousemove', function (e) { if (coordsDisplay) coordsDisplay.textContent = e.latlng.lat.toFixed(4) + '\u00B0 N, ' + e.latlng.lng.toFixed(4) + '\u00B0 E'; });
    map.on('mouseout',  function () { if (coordsDisplay) coordsDisplay.textContent = DELHI_CONFIG.center[0].toFixed(4) + '\u00B0 N, ' + DELHI_CONFIG.center[1].toFixed(4) + '\u00B0 E'; });
    if (recenterBtn) recenterBtn.addEventListener('click', function () { map.flyTo(DELHI_CONFIG.center, DELHI_CONFIG.initialZoom, { duration: 1.2 }); });
    window.addEventListener('resize', function () { map.invalidateSize(); });
    window.addEventListener('orientationchange', function () { setTimeout(function () { map.invalidateSize(); }, 200); });

    // Load all datasets
    var results = await Promise.all([
      loadJsonData(INCIDENT_DATA_PATHS,   FALLBACK_INCIDENTS,  'incidents'),
      loadJsonData(COOLING_DATA_PATHS,    FALLBACK_COOLING,    'cooling_spots'),
      loadJsonData(RELIEF_DATA_PATHS,     FALLBACK_RELIEF,     'relief_spots'),
      loadJsonData(HOTSPOT_DATA_PATHS,    FALLBACK_HOTSPOTS,   'heat_hotspots'),
      loadJsonData(VEGETATION_DATA_PATHS, FALLBACK_VEGETATION, 'vegetation')
    ]);
    demoIncidents    = results[0];
    coolingSpotsData = results[1];
    reliefSpotsData  = results[2];
    heatHotspotsData = results[3];
    vegetationData   = results[4];

    // Render layers
    initModeToggle();
    updateMarkersForCurrentMode();
    renderHeatHotspots(map);
    renderCoolingSpots(map);
    renderReliefSpots(map);
    renderVegetationCard();
    updateDashboard();
    initLayerToggles(map);
    initCitizenReporting(map);

    window.delhiMap       = map;
    window.citizenReports = citizenReports;
    window.demoIncidents  = demoIncidents;
    window.setMapMode     = setMapMode;

    console.log('[Hazard IQ v2.0] All layers initialized successfully.');
    return map;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDelhiMap);
  } else {
    initDelhiMap();
  }
})();
