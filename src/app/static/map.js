let map;
let trackedMarkers = [];
let trafficMarkers = [];
let polylines = [];
const trackedTailNumbers = new Set();

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

  trackedMarkers.forEach(marker => marker.remove());
  trafficMarkers.forEach(marker => marker.remove());
  polylines.forEach(polyline => polyline.remove());
  trackedMarkers = [];
  trafficMarkers = [];
  polylines = [];
  trackedTailNumbers.clear();

  payload.aircraft.forEach((aircraft) => {
    trackedTailNumbers.add(aircraft.tail_number);
    if (aircraft.last_seen.latitude != null && aircraft.last_seen.longitude != null) {
      const marker = L.marker([aircraft.last_seen.latitude, aircraft.last_seen.longitude]).addTo(map);
      marker.bindPopup(`<strong>${aircraft.tail_number}</strong><br>${aircraft.state}`);
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
  });

  const showAll = document.getElementById('show-all-aircraft')?.checked;
  if (showAll) {
    traffic
      .filter((aircraft) => !trackedTailNumbers.has(aircraft.tail_number))
      .forEach((aircraft) => {
        const marker = L.circleMarker([aircraft.latitude, aircraft.longitude], {
          radius: 5,
          color: '#4d6072',
          fillColor: '#4d6072',
          fillOpacity: 0.65,
        }).addTo(map);
        marker.bindPopup(`<strong>${aircraft.tail_number}</strong><br>Area traffic`);
        trafficMarkers.push(marker);
      });
  }
}

if (document.getElementById('map')) {
  document.getElementById('show-all-aircraft')?.addEventListener('change', loadEvent);
  loadEvent();
  setInterval(loadEvent, 10000);
}
