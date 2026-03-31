let map;
let trackedMarkers = [];
let trafficMarkers = [];
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
  payload.aircraft.forEach((aircraft) => renderTrackedAircraft(aircraft));

  const showAll = document.getElementById('show-all-aircraft')?.checked;
  if (showAll) {
    updateTrafficHistory(traffic);
    traffic
      .filter((aircraft) => !trackedTailNumbers.has(aircraft.tail_number))
      .forEach((aircraft) => renderAreaTrafficAircraft(aircraft));
  }
}

function clearLayers() {
  trackedMarkers.forEach((marker) => marker.remove());
  trafficMarkers.forEach((marker) => marker.remove());
  polylines.forEach((polyline) => polyline.remove());
  trackedMarkers = [];
  trafficMarkers = [];
  polylines = [];
  trackedTailNumbers.clear();
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
      <strong>${aircraft.tail_number}</strong><br>
      ${aircraft.state}<br>
      Speed: ${formatSpeed(lastSeen.ground_speed_kt)}<br>
      Alt: ${formatAltitude(lastSeen.altitude_ft)}
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
    <strong>${aircraft.tail_number}</strong><br>
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

function bindLabel(marker, text, className) {
  marker.bindTooltip(text, {
    permanent: true,
    direction: 'top',
    offset: [0, -16],
    className: `aircraft-label ${className}`,
  });
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

if (document.getElementById('map')) {
  document.getElementById('show-all-aircraft')?.addEventListener('change', loadEvent);
  loadEvent();
  setInterval(loadEvent, 10000);
}
