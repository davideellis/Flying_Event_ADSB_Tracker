let map;
let trackedMarkers = [];
let trafficMarkers = [];
let airportMarkers = [];
let polylines = [];
const trackedTailNumbers = new Set();
const trafficHistory = new Map();
const trafficHistoryWindowMs = 2 * 60 * 1000;

async function loadEvent() {
  const [eventResponse, trafficResponse] = await Promise.all([
    fetch(`/api/public/events/${window.eventSlug}`),
    fetch(`/api/public/events/${window.eventSlug}/traffic`),
  ]);

  if (!eventResponse.ok) return;
  const eventPayload = await eventResponse.json();
  const trafficPayload = trafficResponse.ok ? await trafficResponse.json() : { traffic: [] };
  renderMap(eventPayload, trafficPayload.traffic || []);
  renderTrackedAircraftBoard(eventPayload);
}

function renderMap(payload, traffic) {
  if (!map) {
    map = L.map('map').setView([window.eventCenter.lat, window.eventCenter.lon], window.eventCenter.zoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
  }

  clearLayers();
  renderEventAirport(payload.event);
  payload.aircraft.forEach((aircraft) => renderTrackedAircraft(aircraft));

  const showAll = document.getElementById('show-all-aircraft')?.checked;
  if (showAll) {
    updateTrafficHistory(traffic);
    traffic
      .filter((aircraft) => !trackedTailNumbers.has(aircraft.tail_number))
      .forEach((aircraft) => renderAreaTrafficAircraft(aircraft));
  }
}

function renderTrackedAircraftBoard(payload) {
  const headerRow = document.getElementById('tracked-aircraft-header-row');
  const tableBody = document.getElementById('tracked-aircraft-body');
  if (!headerRow || !tableBody) {
    return;
  }

  const showPassenger = Boolean(payload.event.show_passenger_name_public);
  headerRow.innerHTML = `
    <th>Tail</th>
    <th>State</th>
    <th>Speed</th>
    <th>Altitude</th>
    ${showPassenger ? '<th>Passenger</th>' : ''}
  `;

  if (!payload.aircraft.length) {
    tableBody.innerHTML = `<tr><td colspan="${showPassenger ? 5 : 4}">No aircraft configured.</td></tr>`;
    return;
  }

  const rows = payload.aircraft
    .slice()
    .sort((left, right) => left.tail_number.localeCompare(right.tail_number))
    .map((aircraft) => {
      const lastSeen = aircraft.last_seen || {};
      const passengerCell = showPassenger
        ? `<td>${aircraft.current_passenger_name || ''}</td>`
        : '';
      return `
        <tr>
          <td><strong>${escapeHtml(aircraft.tail_number)}</strong></td>
          <td>${escapeHtml(aircraft.state)}</td>
          <td>${formatSpeed(lastSeen.ground_speed_kt)}</td>
          <td>${formatAltitude(lastSeen.altitude_ft)}</td>
          ${passengerCell}
        </tr>
      `;
    })
    .join('');

  tableBody.innerHTML = rows;
}

function clearLayers() {
  trackedMarkers.forEach((marker) => marker.remove());
  trafficMarkers.forEach((marker) => marker.remove());
  airportMarkers.forEach((marker) => marker.remove());
  polylines.forEach((polyline) => polyline.remove());
  trackedMarkers = [];
  trafficMarkers = [];
  airportMarkers = [];
  polylines = [];
  trackedTailNumbers.clear();
}

function renderEventAirport(event) {
  const marker = L.marker(
    [event.latitude, event.longitude],
    {
      icon: createAirportIcon(),
      zIndexOffset: 500,
    }
  ).addTo(map);
  marker.bindPopup(`
    <strong>Event Airport</strong><br>
    ${event.airport_name || event.airport_code || 'Airport TBD'}<br>
    ${event.latitude.toFixed(6)}, ${event.longitude.toFixed(6)}
  `);
  bindLabel(marker, event.airport_name || event.airport_code || 'Event Airport', 'airport-label', [0, -20]);
  airportMarkers.push(marker);
}

function renderTrackedAircraft(aircraft) {
  trackedTailNumbers.add(aircraft.tail_number);
  const lastSeen = aircraft.last_seen || {};
  if (lastSeen.latitude != null && lastSeen.longitude != null) {
    const marker = L.marker(
      [lastSeen.latitude, lastSeen.longitude],
      {
        icon: createAircraftIcon({
          heading: lastSeen.heading_deg,
          variant: aircraft.has_current_passenger ? 'tracked-active' : 'tracked',
        }),
      }
    ).addTo(map);
    marker.bindPopup(`
      <strong>${escapeHtml(aircraft.tail_number)}</strong><br>
      ${escapeHtml(aircraft.state)}<br>
      Speed: ${formatSpeed(lastSeen.ground_speed_kt)}<br>
      Alt: ${formatAltitude(lastSeen.altitude_ft)}
      ${aircraft.current_passenger_name ? `<br>Passenger: ${escapeHtml(aircraft.current_passenger_name)}` : ''}
    `);
    bindLabel(marker, buildAircraftLabel(aircraft.tail_number, lastSeen.ground_speed_kt, lastSeen.altitude_ft), 'tracked-label');
    trackedMarkers.push(marker);
  }

  if (aircraft.current_track.length > 1) {
    const currentLine = L.polyline(aircraft.current_track.map((point) => [point.lat, point.lon]), {
      color: '#0f7a5b',
      weight: 4,
    }).addTo(map);
    polylines.push(currentLine);
  }

  aircraft.archived_tracks.forEach((track) => {
    if (track.length > 1) {
      const archivedLine = L.polyline(track.map((point) => [point.lat, point.lon]), {
        color: '#d17f21',
        weight: 2,
        opacity: 0.55,
        dashArray: '6 6',
      }).addTo(map);
      polylines.push(archivedLine);
    }
  });
}

function renderAreaTrafficAircraft(aircraft) {
  const history = trafficHistory.get(aircraft.tail_number) || [];
  if (history.length > 1) {
    const trail = L.polyline(history.map((point) => [point.latitude, point.longitude]), {
      color: '#4d6072',
      weight: 2,
      opacity: 0.55,
    }).addTo(map);
    polylines.push(trail);
  }

  const marker = L.marker(
    [aircraft.latitude, aircraft.longitude],
    {
      icon: createAircraftIcon({
        heading: aircraft.heading_deg,
        variant: 'traffic',
      }),
    }
  ).addTo(map);
  marker.bindPopup(`
    <strong>${escapeHtml(aircraft.tail_number)}</strong><br>
    Area traffic<br>
    Speed: ${formatSpeed(aircraft.ground_speed_kt)}<br>
    Alt: ${formatAltitude(aircraft.altitude_ft)}
  `);
  bindLabel(marker, buildAircraftLabel(aircraft.tail_number, aircraft.ground_speed_kt, aircraft.altitude_ft), 'traffic-label');
  trafficMarkers.push(marker);
}

function updateTrafficHistory(traffic) {
  const cutoff = Date.now() - trafficHistoryWindowMs;
  const seenTailNumbers = new Set();

  traffic.forEach((aircraft) => {
    const observedAt = Date.parse(aircraft.observed_at);
    const history = trafficHistory.get(aircraft.tail_number) || [];
    seenTailNumbers.add(aircraft.tail_number);
    history.push({
      latitude: aircraft.latitude,
      longitude: aircraft.longitude,
      observedAt: Number.isNaN(observedAt) ? Date.now() : observedAt,
    });
    trafficHistory.set(
      aircraft.tail_number,
      dedupeAndPruneHistory(history, cutoff)
    );
  });

  Array.from(trafficHistory.keys()).forEach((tailNumber) => {
    const history = dedupeAndPruneHistory(trafficHistory.get(tailNumber) || [], cutoff);
    if (history.length === 0 && !seenTailNumbers.has(tailNumber)) {
      trafficHistory.delete(tailNumber);
      return;
    }
    trafficHistory.set(tailNumber, history);
  });
}

function dedupeAndPruneHistory(history, cutoff) {
  return history
    .filter((point) => point.observedAt >= cutoff)
    .filter((point, index, points) => {
      if (index === 0) return true;
      const previous = points[index - 1];
      return previous.latitude !== point.latitude || previous.longitude !== point.longitude;
    });
}

function createAircraftIcon({ heading, variant }) {
  const rotation = Number.isFinite(heading) ? heading : 0;
  const svg = `
    <div class="aircraft-marker aircraft-marker-${variant}" style="transform: rotate(${rotation}deg)">
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 2 L19 11 L29 14 L29 18 L19 17 L17 30 L15 30 L13 17 L3 18 L3 14 L13 11 Z"></path>
      </svg>
    </div>
  `;

  return L.divIcon({
    className: 'aircraft-div-icon',
    html: svg,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function createAirportIcon() {
  const svg = `
    <div class="airport-marker">
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 2 L19.6 11.2 L29.5 11.8 L21.8 18.1 L24.5 28 L16 22.6 L7.5 28 L10.2 18.1 L2.5 11.8 L12.4 11.2 Z"></path>
      </svg>
    </div>
  `;

  return L.divIcon({
    className: 'airport-div-icon',
    html: svg,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function bindLabel(marker, text, className, offset = [0, -16]) {
  marker.bindTooltip(text, {
    permanent: true,
    direction: 'top',
    offset,
    className: `aircraft-label ${className}`,
  });
}

function bindFullscreenToggle(buttonId, panelId, activeClass) {
  const button = document.getElementById(buttonId);
  const panel = document.getElementById(panelId);
  if (!button || !panel) {
    return;
  }

  button.addEventListener('click', () => {
    const panels = Array.from(document.querySelectorAll('.panel-fullscreen'));
    const isActive = panel.classList.contains(activeClass);
    panels.forEach((item) => item.classList.remove('panel-fullscreen-active'));
    document.getElementById('map-card')?.classList.remove('panel-fullscreen-active');
    document.getElementById('tracked-aircraft-card')?.classList.remove('panel-fullscreen-active');
    if (!isActive) {
      panel.classList.add('panel-fullscreen-active');
    }
    updateFullscreenButtons();
    if (panelId === 'map-card') {
      window.setTimeout(() => map?.invalidateSize(), 120);
    }
  });
}

function updateFullscreenButtons() {
  const mapButton = document.getElementById('toggle-map-fullscreen');
  const aircraftButton = document.getElementById('toggle-aircraft-fullscreen');
  const mapActive = document.getElementById('map-card')?.classList.contains('panel-fullscreen-active');
  const aircraftActive = document.getElementById('tracked-aircraft-card')?.classList.contains('panel-fullscreen-active');
  if (mapButton) {
    mapButton.textContent = mapActive ? 'Exit full screen' : 'Full screen map';
  }
  if (aircraftButton) {
    aircraftButton.textContent = aircraftActive ? 'Exit full screen' : 'Full screen aircraft';
  }
}

function buildAircraftLabel(tailNumber, speed, altitude) {
  return `${tailNumber} ${formatSpeed(speed)} ${formatAltitude(altitude)}`;
}

function formatSpeed(speed) {
  return speed == null ? '--kt' : `${Math.round(speed)}kt`;
}

function formatAltitude(altitude) {
  return altitude == null ? '--ft' : `${Math.round(altitude)}ft`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

if (document.getElementById('map')) {
  document.getElementById('show-all-aircraft')?.addEventListener('change', loadEvent);
  bindFullscreenToggle('toggle-map-fullscreen', 'map-card', 'panel-fullscreen-active');
  bindFullscreenToggle('toggle-aircraft-fullscreen', 'tracked-aircraft-card', 'panel-fullscreen-active');
  loadEvent();
  setInterval(loadEvent, 10000);
}
