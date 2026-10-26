/* ─────────────────────────────────────────────────────────────
   MedRoute — Emergency Ambulance Dispatch & Recommendation System
   Client Application Controller & API Integration
   Powers 6 views: Dashboard, Dispatch, Network, Hospitals,
   Ambulances, and Incident History with live SQL persistence.
   ───────────────────────────────────────────────────────────── */

'use strict';

/* ── Backend API Configuration ── */
function getApiBaseUrl() {
  if (window.location.protocol === 'file:') {
    return 'http://127.0.0.1:5000';
  }
  if (window.location.port === '5000') {
    return '';
  }
  return 'http://127.0.0.1:5000';
}

const API_BASE = getApiBaseUrl();

/* ── Application State ── */
const state = {
  activeTab: 'dashboard',
  nodes: [],
  network: null,
  hospitals: [],
  ambulances: [],
  history: [],
  lastDispatchResult: null,
  activeRoute: null
};

/* ── Node Screen Coordinates for Canvas (Normalised 0.0 - 1.0) ── */
const NODE_COORDINATES = {
  A: { x: 0.35, y: 0.50, label: 'A: Downtown' },
  B: { x: 0.65, y: 0.22, label: 'B: North Hub' },
  C: { x: 0.85, y: 0.55, label: 'C: East Junction' },
  D: { x: 0.50, y: 0.85, label: 'D: South Medical' },
  E: { x: 0.15, y: 0.68, label: 'E: West Suburb' },
  F: { x: 0.45, y: 0.32, label: 'F: Central Expwy' },
  G: { x: 0.15, y: 0.20, label: 'G: Tech Corridor' },
  H: { x: 0.90, y: 0.20, label: 'H: Airport Hwy' }
};

/* ─────────────────────────────────────────────────────────────
   TOAST NOTIFICATIONS
   ───────────────────────────────────────────────────────────── */
function showToast(message, type = 'success', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <span class="toast__icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <span class="toast__msg">${escapeHtml(message)}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  }[m]));
}

/* ─────────────────────────────────────────────────────────────
   NAVIGATION TABS
   ───────────────────────────────────────────────────────────── */
function initNavigation() {
  const tabs = document.querySelectorAll('.nav__tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });

  document.getElementById('btnQuickDispatch')?.addEventListener('click', () => switchTab('dispatch'));
  document.getElementById('btnViewAllHistory')?.addEventListener('click', () => switchTab('history'));
  document.getElementById('btnOpenNetworkTab')?.addEventListener('click', () => switchTab('network'));

  // Handle URL hash
  const hash = window.location.hash.replace('#', '');
  if (['dashboard', 'dispatch', 'network', 'hospitals', 'ambulances', 'history'].includes(hash)) {
    switchTab(hash);
  }
}

function switchTab(tabId) {
  state.activeTab = tabId;
  window.location.hash = tabId;

  document.querySelectorAll('.nav__tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });

  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.toggle('active', sec.id === `view-${tabId}`);
  });

  // Trigger view refresh
  if (tabId === 'dashboard') loadDashboardStats();
  if (tabId === 'hospitals') loadHospitalsTable();
  if (tabId === 'ambulances') loadAmbulancesTable();
  if (tabId === 'history') loadHistoryTable();
  if (tabId === 'network') {
    requestAnimationFrame(() => renderNetworkCanvas('networkVisualCanvas', state.activeRoute));
  }
}

/* ─────────────────────────────────────────────────────────────
   API DATA FETCHING & SYNCHRONIZATION
   ───────────────────────────────────────────────────────────── */
async function apiGet(endpoint) {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || errData.message || `HTTP ${res.status}`);
  }
  return await res.json();
}

async function apiPost(endpoint, payload) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || data.message || `HTTP ${res.status}`);
  }
  return data;
}

async function apiPatch(endpoint, payload) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || data.message || `HTTP ${res.status}`);
  }
  return data;
}

async function apiDelete(endpoint) {
  const res = await fetch(`${API_BASE}${endpoint}`, { method: 'DELETE' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || data.message || `HTTP ${res.status}`);
  }
  return data;
}

/* ─────────────────────────────────────────────────────────────
   BACKEND HEALTH CHECK & POPULATE NODES
   ───────────────────────────────────────────────────────────── */
async function checkBackendConnection() {
  const badge = document.getElementById('backendBadge');
  const badgeText = document.getElementById('backendBadgeText');

  try {
    const health = await apiGet('/api/health');
    if (health.status === 'online') {
      badge.className = 'nav__badge nav__badge--connected';
      badgeText.textContent = 'API & DB Connected';
      badge.title = `Connected to MedRoute Flask API (${health.timestamp})`;
      return true;
    }
  } catch (err) {
    badge.className = 'nav__badge nav__badge--offline';
    badgeText.textContent = 'API Offline';
    badge.title = 'Backend offline. Run "python app.py" to start server.';
    return false;
  }
}

async function loadRoadNetworkData() {
  try {
    const data = await apiGet('/api/network');
    state.network = data;
    state.nodes = data.nodes || [];

    // Populate Location Dropdowns
    const nodeSelects = [
      document.getElementById('inputLocation'),
      document.getElementById('routeFinderStart'),
      document.getElementById('routeFinderTarget'),
      document.getElementById('addHospNode'),
      document.getElementById('addAmbNode')
    ];

    nodeSelects.forEach(select => {
      if (!select) return;
      const currentVal = select.value;
      select.innerHTML = '<option value="" disabled selected>Select node...</option>';
      state.nodes.forEach(n => {
        const opt = document.createElement('option');
        opt.value = n.node_id;
        opt.textContent = `Node ${n.node_id} — ${n.name}`;
        select.appendChild(opt);
      });
      if (currentVal) select.value = currentVal;
    });

    if (document.getElementById('inputLocation')) {
      document.getElementById('inputLocation').value = 'A';
    }
    if (document.getElementById('routeFinderStart')) {
      document.getElementById('routeFinderStart').value = 'A';
    }
    if (document.getElementById('routeFinderTarget')) {
      document.getElementById('routeFinderTarget').value = 'D';
    }

    // Render Canvas
    renderNetworkCanvas('dashboardMiniCanvas');
    renderNetworkCanvas('networkVisualCanvas');
  } catch (err) {
    console.warn('Could not load network data:', err);
  }
}

/* ─────────────────────────────────────────────────────────────
   VIEW 1: DASHBOARD
   ───────────────────────────────────────────────────────────── */
async function loadDashboardStats() {
  try {
    const stats = await apiGet('/api/stats');

    document.getElementById('statHospitals').textContent = stats.total_hospitals;
    document.getElementById('statBeds').textContent = stats.total_beds_available;
    document.getElementById('statAmbulances').textContent = stats.available_ambulances;
    document.getElementById('statAmbulancesSub').textContent = `${stats.dispatched_ambulances} Dispatched / ${stats.total_ambulances} Total`;
    document.getElementById('statDispatches').textContent = stats.total_dispatches;

    // Populate recent dispatches table
    const tableBody = document.getElementById('recentDispatchesTable');
    if (!tableBody) return;

    if (!stats.recent_dispatches || stats.recent_dispatches.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" class="table-loading">No incident dispatches recorded yet.</td></tr>';
      return;
    }

    tableBody.innerHTML = stats.recent_dispatches.map(r => {
      const disp = r.dispatch || {};
      const statusClass = r.status === 'Completed' ? 'badge-status--available' : 'badge-status--dispatched';
      return `
        <tr>
          <td><strong style="font-family:var(--mono)">#${r.request_id}</strong></td>
          <td><span class="tag tag--node">Node ${r.patient_location_node}</span></td>
          <td><span class="badge-status ${r.severity === 'High' ? 'badge-status--critical' : 'badge-status--dispatched'}">${r.severity}</span></td>
          <td>${r.required_specialization}</td>
          <td>${disp.hospital_name || '&mdash;'}</td>
          <td style="font-family:var(--mono)">${disp.estimated_travel_time_minutes ? disp.estimated_travel_time_minutes + ' min' : '&mdash;'}</td>
          <td><span class="badge-status ${statusClass}">${r.status}</span></td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load dashboard stats:', err);
  }
}

/* ─────────────────────────────────────────────────────────────
   VIEW 2: EMERGENCY DISPATCH CONSOLE
   ───────────────────────────────────────────────────────────── */
function initDispatchForm() {
  const form = document.getElementById('dispatchForm');
  const severitySlider = document.getElementById('inputSeverity');
  const severityDisplay = document.getElementById('severityDisplay');
  const severityLabels = ['Low Severity', 'Medium Urgency', 'High (Critical)'];
  const severityColors = ['#22c55e', '#f59e0b', '#ef4444'];

  severitySlider.addEventListener('input', () => {
    const idx = +severitySlider.value - 1;
    severityDisplay.textContent = severityLabels[idx];
    severityDisplay.style.color = severityColors[idx];
    severitySlider.style.accentColor = severityColors[idx];
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const location = document.getElementById('inputLocation').value;
    const emergency = form.querySelector('input[name="emergency"]:checked')?.value;
    const severityIdx = +severitySlider.value - 1;
    const severity = ['Low', 'Medium', 'High'][severityIdx];
    const callerName = document.getElementById('inputCallerName').value;
    const callerPhone = document.getElementById('inputCallerPhone').value;

    if (!location) {
      showToast('Please select a patient location node.', 'error');
      return;
    }
    if (!emergency) {
      showToast('Please select an emergency clinical specialization.', 'error');
      return;
    }

    setDispatchLoading(true);

    try {
      const result = await apiPost('/api/dispatch', {
        location,
        emergency_type: emergency,
        severity,
        caller_name: callerName,
        caller_phone: callerPhone
      });

      state.lastDispatchResult = result;
      displayDispatchResult(result);
      showToast(`Recommended: ${result.recommended.name}`, 'success');

      // Update active route on canvas
      state.activeRoute = result.recommended.route;
      renderNetworkCanvas('dashboardMiniCanvas', state.activeRoute);
      renderNetworkCanvas('networkVisualCanvas', state.activeRoute);
    } catch (err) {
      displayDispatchNoResult(err.message);
      showToast(err.message, 'error');
    } finally {
      setDispatchLoading(false);
    }
  });

  // Confirm Dispatch button
  document.getElementById('btnConfirmDispatch')?.addEventListener('click', async () => {
    if (!state.lastDispatchResult) return;

    try {
      const res = await apiPost('/api/dispatch/confirm', {
        location: state.lastDispatchResult.patient_node,
        emergency_type: state.lastDispatchResult.required_specialization,
        severity: state.lastDispatchResult.severity,
        recommended: state.lastDispatchResult.recommended,
        assigned_ambulance: state.lastDispatchResult.assigned_ambulance,
        all_candidates: state.lastDispatchResult.all_candidates
      });

      showToast(`Dispatch #${res.request_id} recorded in SQL database!`, 'success');
      loadDashboardStats();

      // Disable button to prevent double-confirm
      const btn = document.getElementById('btnConfirmDispatch');
      btn.disabled = true;
      btn.innerHTML = '✓ Dispatch Confirmed in SQL DB';
    } catch (err) {
      showToast('Failed to confirm dispatch: ' + err.message, 'error');
    }
  });

  document.getElementById('btnCancelDispatch')?.addEventListener('click', resetDispatchView);
  document.getElementById('btnResetDispatch')?.addEventListener('click', resetDispatchView);
}

function setDispatchLoading(loading) {
  const btn = document.getElementById('btnDispatchSubmit');
  const text = btn.querySelector('.btn__text');
  const loader = btn.querySelector('.btn__loader');
  btn.disabled = loading;
  text.hidden = loading;
  loader.hidden = !loading;
}

function displayDispatchResult(data) {
  document.getElementById('dispatchPlaceholder').hidden = true;
  document.getElementById('dispatchNoResult').hidden = true;
  const resultCard = document.getElementById('dispatchResultCard');
  resultCard.hidden = false;

  const rec = data.recommended;

  document.getElementById('rHospitalName').textContent = rec.name;
  document.getElementById('rHospitalAddress').textContent = rec.address || `Located at Node ${rec.node_id}`;
  document.getElementById('rScore').textContent = rec.suitability_score.toFixed(1);

  document.getElementById('rSpec').textContent = rec.specialization;
  document.getElementById('rBeds').textContent = `${rec.beds_available} / ${rec.total_beds} beds available`;
  document.getElementById('rNode').textContent = `Node ${rec.node_id}`;

  document.getElementById('rReasoning').textContent = rec.reasoning;
  document.getElementById('rDistance').textContent = `${rec.distance_km} km`;
  document.getElementById('rETA').textContent = `${rec.travel_time_minutes} min`;

  // Route sequence pills
  const routeSeqEl = document.getElementById('rRouteSequence');
  routeSeqEl.innerHTML = rec.route.map((node, i) =>
    `<span class="route-node-pill">${node}</span>` +
    (i < rec.route.length - 1 ? `<span class="route-arrow-icon">&rarr;</span>` : '')
  ).join('');

  // Score factor cards
  const breakdown = rec.score_breakdown || {};
  const scoreGrid = document.getElementById('scoreFactorsGrid');
  scoreGrid.innerHTML = `
    <div class="score-factor-card">
      <span class="score-factor-card__name">Distance</span>
      <span class="score-factor-card__val">${breakdown.distance_score ?? 100}%</span>
    </div>
    <div class="score-factor-card">
      <span class="score-factor-card__name">Traffic Speed</span>
      <span class="score-factor-card__val">${breakdown.traffic_score ?? 100}%</span>
    </div>
    <div class="score-factor-card">
      <span class="score-factor-card__name">Beds Cap</span>
      <span class="score-factor-card__val">${breakdown.bed_score ?? 100}%</span>
    </div>
    <div class="score-factor-card">
      <span class="score-factor-card__name">Specialty</span>
      <span class="score-factor-card__val">${breakdown.specialization_score ?? 100}%</span>
    </div>
  `;

  // Assigned Ambulance
  const amb = data.assigned_ambulance;
  const ambNumber = document.getElementById('rAmbNumber');
  const ambEta = document.getElementById('rAmbEta');
  if (amb) {
    ambNumber.textContent = `${amb.vehicle_number} (Station: Node ${amb.current_node})`;
    ambEta.textContent = `• ETA to Patient: ${amb.eta_to_patient_minutes} min`;
  } else {
    ambNumber.textContent = 'No Available Ambulance in Fleet';
    ambEta.textContent = '• Manual dispatch required';
  }

  // Reset confirm button
  const confirmBtn = document.getElementById('btnConfirmDispatch');
  confirmBtn.disabled = false;
  confirmBtn.innerHTML = `
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
    Confirm &amp; Record Dispatch in Database
  `;

  // Alternative Candidates Table
  const altTbody = document.getElementById('alternativesTableBody');
  const alts = (data.all_candidates || []).slice(1);
  if (alts.length === 0) {
    altTbody.innerHTML = '<tr><td colspan="7" class="table-loading">No other eligible hospitals with open beds found for this specialty.</td></tr>';
  } else {
    altTbody.innerHTML = alts.map((c, idx) => `
      <tr>
        <td><strong>#${idx + 2}</strong></td>
        <td><strong>${c.name}</strong></td>
        <td><span class="tag tag--node">Node ${c.node_id}</span></td>
        <td>${c.beds_available} beds</td>
        <td style="font-family:var(--mono)">${c.distance_km} km</td>
        <td style="font-family:var(--mono)">${c.travel_time_minutes} min</td>
        <td><span style="font-family:var(--mono);font-weight:700;color:var(--teal)">${c.suitability_score.toFixed(1)}</span></td>
      </tr>
    `).join('');
  }

  resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayDispatchNoResult(message) {
  document.getElementById('dispatchPlaceholder').hidden = true;
  document.getElementById('dispatchResultCard').hidden = true;
  const noResult = document.getElementById('dispatchNoResult');
  noResult.hidden = false;
  document.getElementById('noResultExplanation').textContent = message;
}

function resetDispatchView() {
  document.getElementById('dispatchResultCard').hidden = true;
  document.getElementById('dispatchNoResult').hidden = true;
  document.getElementById('dispatchPlaceholder').hidden = false;
  state.lastDispatchResult = null;
  state.activeRoute = null;
  renderNetworkCanvas('dashboardMiniCanvas');
  renderNetworkCanvas('networkVisualCanvas');
}

/* ─────────────────────────────────────────────────────────────
   VIEW 3: INTERACTIVE NETWORK CANVAS & ROUTE VISUALIZER
   ───────────────────────────────────────────────────────────── */
function renderNetworkCanvas(canvasId, highlightedRoute = null) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  if (!state.network || !state.network.edges) return;

  const edges = state.network.edges;
  const routeNodes = highlightedRoute || [];

  // Helper for coordinates
  function getPos(nodeKey) {
    const p = NODE_COORDINATES[nodeKey] || { x: 0.5, y: 0.5 };
    const pad = 44;
    return {
      x: p.x * (w - pad * 2) + pad,
      y: p.y * (h - pad * 2) + pad
    };
  }

  // 1. Draw Edges
  edges.forEach(e => {
    const p1 = getPos(e.source_node);
    const p2 = getPos(e.destination_node);

    const isRouteEdge = routeNodes.length > 1 &&
      routeNodes.some((n, idx) => (
        (n === e.source_node && routeNodes[idx + 1] === e.destination_node) ||
        (n === e.destination_node && routeNodes[idx + 1] === e.source_node)
      ));

    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);

    if (isRouteEdge) {
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 4;
      ctx.shadowColor = '#ef4444';
      ctx.shadowBlur = 12;
      ctx.stroke();
      ctx.shadowBlur = 0;
    } else {
      ctx.lineWidth = 2;
      if (e.traffic_level === 'High') ctx.strokeStyle = 'rgba(239, 68, 68, 0.45)';
      else if (e.traffic_level === 'Medium') ctx.strokeStyle = 'rgba(245, 158, 11, 0.45)';
      else ctx.strokeStyle = 'rgba(34, 197, 94, 0.35)';
      ctx.stroke();
    }

    // Edge label (distance)
    const mx = (p1.x + p2.x) / 2;
    const my = (p1.y + p2.y) / 2;
    ctx.fillStyle = isRouteEdge ? '#fff' : 'rgba(255, 255, 255, 0.35)';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${e.distance_km}km`, mx, my - 4);
  });

  // 2. Draw Nodes
  Object.keys(NODE_COORDINATES).forEach(key => {
    const pos = getPos(key);
    const isStart = routeNodes[0] === key;
    const isEnd = routeNodes[routeNodes.length - 1] === key && routeNodes.length > 1;
    const isRoute = routeNodes.includes(key);

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, isRoute ? 20 : 16, 0, Math.PI * 2);

    if (isStart) {
      ctx.fillStyle = '#14b8a6';
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2.5;
    } else if (isEnd) {
      ctx.fillStyle = '#ef4444';
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2.5;
    } else if (isRoute) {
      ctx.fillStyle = '#38bdf8';
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
    } else {
      ctx.fillStyle = '#191d2d';
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1.5;
    }

    ctx.fill();
    ctx.stroke();

    // Node ID text
    ctx.fillStyle = '#fff';
    ctx.font = '600 12px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(key, pos.x, pos.y);

    // Node Name Tag
    ctx.font = '10px "Inter", sans-serif';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.fillText(NODE_COORDINATES[key].label.split(':')[1].trim(), pos.x, pos.y + 26);
  });
}

function initRouteFinder() {
  document.getElementById('btnFindPath')?.addEventListener('click', async () => {
    const start = document.getElementById('routeFinderStart').value;
    const target = document.getElementById('routeFinderTarget').value;

    if (!start || !target) {
      showToast('Select origin and target nodes.', 'warning');
      return;
    }
    if (start === target) {
      showToast('Origin and target are the same node.', 'warning');
      return;
    }

    try {
      const res = await apiPost('/api/route', {
        start: start,
        target: target,
        optimize_by: 'travel_time'
      });

      const stepsContainer = document.getElementById('pathStepsContainer');
      const summaryDesc = document.getElementById('pathSummaryDesc');

      state.activeRoute = res.route;
      renderNetworkCanvas('networkVisualCanvas', state.activeRoute);

      summaryDesc.innerHTML = `
        <strong>Route:</strong> Node ${res.start_node} (${res.start_name}) &rarr; Node ${res.target_node} (${res.target_name})<br/>
        <span style="color:var(--green);font-family:var(--mono);font-size:12px">Total Distance: ${res.total_distance_km} km &bull; Est. Travel Time: ${res.total_travel_time_minutes} min (Avg Traffic: ${res.average_traffic})</span>
      `;

      if (!res.steps || res.steps.length === 0) {
        stepsContainer.innerHTML = '<p style="color:var(--text-muted);font-size:13px">Direct arrival or no intermediate steps.</p>';
      } else {
        stepsContainer.innerHTML = res.steps.map((step, idx) => `
          <div class="path-step-card">
            <span class="path-step-segment">Step ${idx + 1}: Node ${step.from} &rarr; Node ${step.to}</span>
            <span class="path-step-metrics">${step.distance_km} km &bull; ${step.travel_time_minutes} min (${step.traffic_level} Traffic)</span>
          </div>
        `).join('');
      }

      showToast(`Calculated route: ${res.route.join(' → ')} (${res.total_distance_km} km, ${res.total_travel_time_minutes} min)`, 'success');
    } catch (err) {
      showToast('Could not calculate path: ' + err.message, 'error');
    }
  });
}

/* ─────────────────────────────────────────────────────────────
   VIEW 4: HOSPITAL MANAGEMENT
   ───────────────────────────────────────────────────────────── */
async function loadHospitalsTable() {
  const tbody = document.getElementById('hospitalsTableBody');
  if (!tbody) return;

  try {
    const data = await apiGet('/api/hospitals');
    state.hospitals = data.hospitals || [];

    if (state.hospitals.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="table-loading">No hospitals found in database.</td></tr>';
      return;
    }

    tbody.innerHTML = state.hospitals.map(h => `
      <tr>
        <td style="font-family:var(--mono)">#${h.hospital_id}</td>
        <td><strong>${escapeHtml(h.name)}</strong></td>
        <td><span class="tag tag--node">Node ${h.node_id}</span></td>
        <td>${h.specializations.map(s => `<span class="tag tag--spec" style="font-size:10px;margin-right:4px">${s}</span>`).join('')}</td>
        <td>
          <strong style="color:${h.beds_available > 0 ? 'var(--green)' : 'var(--accent)'}">${h.beds_available}</strong> / ${h.total_beds}
        </td>
        <td>
          <span class="badge-status ${h.is_active ? 'badge-status--available' : 'badge-status--critical'}">
            ${h.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>${h.contact_number || '&mdash;'}</td>
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn btn--sm btn--ghost" onclick="openEditBedsModal(${h.hospital_id}, '${escapeHtml(h.name)}', ${h.beds_available})">Edit Beds</button>
            <button class="btn btn--sm btn--ghost" onclick="toggleHospitalStatus(${h.hospital_id})">${h.is_active ? 'Deactivate' : 'Activate'}</button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-loading" style="color:var(--accent)">Failed to load hospitals: ${err.message}</td></tr>`;
  }
}

function initHospitalModals() {
  // Add Hospital
  document.getElementById('btnOpenAddHospitalModal')?.addEventListener('click', () => {
    document.getElementById('modalAddHospital').hidden = false;
  });

  document.getElementById('formAddHospital')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('addHospName').value;
    const node_id = document.getElementById('addHospNode').value;
    const beds = +document.getElementById('addHospBeds').value;
    const total_beds = +document.getElementById('addHospTotalBeds').value;
    const contact = document.getElementById('addHospContact').value;
    const address = document.getElementById('addHospAddress').value;

    const checkedSpecs = Array.from(
      document.querySelectorAll('#addHospSpecialties input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    try {
      await apiPost('/api/hospitals', {
        name,
        node_id,
        beds_available: beds,
        total_beds,
        contact_number: contact,
        address,
        specializations: checkedSpecs
      });

      showToast(`Hospital '${name}' registered to database!`, 'success');
      document.getElementById('modalAddHospital').hidden = true;
      e.target.reset();
      loadHospitalsTable();
      loadDashboardStats();
    } catch (err) {
      showToast('Error registering hospital: ' + err.message, 'error');
    }
  });

  // Edit Beds Form
  document.getElementById('formEditBeds')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('editBedsHospitalId').value;
    const count = +document.getElementById('editBedsCount').value;

    try {
      await apiPatch(`/api/hospitals/${id}/beds`, { beds_available: count });
      showToast(`Bed capacity updated to ${count}!`, 'success');
      document.getElementById('modalEditBeds').hidden = true;
      loadHospitalsTable();
      loadDashboardStats();
    } catch (err) {
      showToast('Error updating beds: ' + err.message, 'error');
    }
  });
}

window.openEditBedsModal = function(id, name, currentBeds) {
  document.getElementById('editBedsHospitalId').value = id;
  document.getElementById('editBedsHospitalName').textContent = name;
  document.getElementById('editBedsCount').value = currentBeds;
  document.getElementById('modalEditBeds').hidden = false;
};

window.toggleHospitalStatus = async function(id) {
  try {
    const res = await apiDelete(`/api/hospitals/${id}`);
    showToast(res.message, 'success');
    loadHospitalsTable();
    loadDashboardStats();
  } catch (err) {
    showToast('Could not toggle status: ' + err.message, 'error');
  }
};

/* ─────────────────────────────────────────────────────────────
   VIEW 5: AMBULANCE MANAGEMENT
   ───────────────────────────────────────────────────────────── */
async function loadAmbulancesTable() {
  const tbody = document.getElementById('ambulancesTableBody');
  if (!tbody) return;

  try {
    const data = await apiGet('/api/ambulances');
    state.ambulances = data.ambulances || [];

    if (state.ambulances.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="table-loading">No ambulances found in fleet.</td></tr>';
      return;
    }

    tbody.innerHTML = state.ambulances.map(a => {
      let statusClass = 'badge-status--available';
      if (a.status === 'Dispatched') statusClass = 'badge-status--dispatched';
      if (a.status === 'Maintenance' || a.status === 'Unavailable') statusClass = 'badge-status--maintenance';

      return `
        <tr>
          <td><strong style="font-family:var(--mono)">${escapeHtml(a.vehicle_number)}</strong></td>
          <td><span class="tag tag--node">Node ${a.current_node}</span></td>
          <td>${a.driver_name || '&mdash;'}</td>
          <td>${a.contact_number || '&mdash;'}</td>
          <td>
            <select class="form-select-sm" onchange="changeAmbulanceStatus(${a.ambulance_id}, this.value)">
              <option value="Available" ${a.status === 'Available' ? 'selected' : ''}>Available</option>
              <option value="Dispatched" ${a.status === 'Dispatched' ? 'selected' : ''}>Dispatched</option>
              <option value="Maintenance" ${a.status === 'Maintenance' ? 'selected' : ''}>Maintenance</option>
              <option value="Unavailable" ${a.status === 'Unavailable' ? 'selected' : ''}>Unavailable</option>
            </select>
          </td>
          <td style="font-size:12px;color:var(--text-dim)">${new Date(a.last_updated).toLocaleTimeString()}</td>
          <td>
            <span class="badge-status ${statusClass}">${a.status}</span>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="table-loading" style="color:var(--accent)">Failed to load ambulances: ${err.message}</td></tr>`;
  }
}

window.changeAmbulanceStatus = async function(id, newStatus) {
  try {
    await apiPatch(`/api/ambulances/${id}/status`, { status: newStatus });
    showToast(`Ambulance status updated to '${newStatus}'!`, 'success');
    loadAmbulancesTable();
    loadDashboardStats();
  } catch (err) {
    showToast('Status update failed: ' + err.message, 'error');
  }
};

function initAmbulanceModals() {
  document.getElementById('btnOpenAddAmbulanceModal')?.addEventListener('click', () => {
    document.getElementById('modalAddAmbulance').hidden = false;
  });

  document.getElementById('formAddAmbulance')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const vehicle_number = document.getElementById('addAmbNumber').value;
    const current_node = document.getElementById('addAmbNode').value;
    const driver_name = document.getElementById('addAmbDriver').value;
    const contact_number = document.getElementById('addAmbContact').value;
    const status = document.getElementById('addAmbStatus').value;

    try {
      await apiPost('/api/ambulances', {
        vehicle_number,
        current_node,
        driver_name,
        contact_number,
        status
      });

      showToast(`Ambulance '${vehicle_number}' registered!`, 'success');
      document.getElementById('modalAddAmbulance').hidden = true;
      e.target.reset();
      loadAmbulancesTable();
      loadDashboardStats();
    } catch (err) {
      showToast('Error registering ambulance: ' + err.message, 'error');
    }
  });
}

/* ─────────────────────────────────────────────────────────────
   VIEW 6: EMERGENCY HISTORY
   ───────────────────────────────────────────────────────────── */
async function loadHistoryTable() {
  const tbody = document.getElementById('historyTableBody');
  if (!tbody) return;

  const search = document.getElementById('historySearchInput')?.value || '';
  const severity = document.getElementById('historySeverityFilter')?.value || '';
  const specialty = document.getElementById('historySpecialtyFilter')?.value || '';

  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (severity) params.append('severity', severity);
  if (specialty) params.append('specialization', specialty);

  try {
    const data = await apiGet(`/api/history?${params.toString()}`);
    state.history = data.requests || [];

    if (state.history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="table-loading">No matching incident records found.</td></tr>';
      return;
    }

    tbody.innerHTML = state.history.map(r => {
      const d = r.dispatch || {};
      const dateStr = new Date(r.request_timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
      return `
        <tr>
          <td><strong style="font-family:var(--mono)">#${r.request_id}</strong></td>
          <td style="font-size:12px;color:var(--text-dim)">${dateStr}</td>
          <td><span class="tag tag--node">Node ${r.patient_location_node}</span></td>
          <td><span class="badge-status ${r.severity === 'High' ? 'badge-status--critical' : 'badge-status--dispatched'}">${r.severity}</span></td>
          <td>${r.required_specialization}</td>
          <td><strong>${d.hospital_name || '&mdash;'}</strong></td>
          <td style="font-family:var(--mono)">${d.total_distance_km ? d.total_distance_km + ' km' : '&mdash;'}</td>
          <td style="font-family:var(--mono)">${d.estimated_travel_time_minutes ? d.estimated_travel_time_minutes + ' min' : '&mdash;'}</td>
          <td>${d.ambulance_vehicle || '&mdash;'}</td>
          <td>
            <button class="btn btn--sm btn--ghost" onclick="viewIncidentDetails(${r.request_id})">Details</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" class="table-loading" style="color:var(--accent)">Failed to load history: ${err.message}</td></tr>`;
  }
}

function initHistoryFilters() {
  document.getElementById('historySearchInput')?.addEventListener('input', debounce(loadHistoryTable, 300));
  document.getElementById('historySeverityFilter')?.addEventListener('change', loadHistoryTable);
  document.getElementById('historySpecialtyFilter')?.addEventListener('change', loadHistoryTable);
}

function debounce(fn, delay) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

window.viewIncidentDetails = function(requestId) {
  const incident = state.history.find(r => r.request_id === requestId);
  if (!incident) return;

  const d = incident.dispatch || {};
  document.getElementById('modalIncidentTitle').textContent = `Emergency Dispatch Record #${incident.request_id}`;

  const body = document.getElementById('modalIncidentBody');
  body.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div><strong>Patient Node:</strong> Node ${incident.patient_location_node}</div>
        <div><strong>Severity:</strong> ${incident.severity}</div>
        <div><strong>Specialization:</strong> ${incident.required_specialization}</div>
        <div><strong>Status:</strong> ${incident.status}</div>
        <div><strong>Caller:</strong> ${incident.caller_name || 'N/A'} (${incident.caller_phone || 'N/A'})</div>
        <div><strong>Time:</strong> ${new Date(incident.request_timestamp).toLocaleString()}</div>
      </div>
      <hr style="border:none;border-top:1px solid var(--border)" />
      <div>
        <h4 style="margin-bottom:6px">Recommended Destination</h4>
        <p style="font-size:16px"><strong>${d.hospital_name || 'N/A'}</strong> (Node ${d.hospital_node || 'N/A'})</p>
        <p style="font-size:13px;color:var(--text-muted);margin-top:4px">${d.selection_reasoning || 'No details recorded.'}</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:10px">
        <div class="result-stat-box">
          <span class="stat-box__label">Route</span>
          <span class="stat-box__val">${(d.route || []).join(' → ')}</span>
        </div>
        <div class="result-stat-box">
          <span class="stat-box__label">Distance</span>
          <span class="stat-box__val">${d.total_distance_km} km</span>
        </div>
        <div class="result-stat-box">
          <span class="stat-box__label">Travel Time</span>
          <span class="stat-box__val stat-box__val--highlight">${d.estimated_travel_time_minutes} min</span>
        </div>
      </div>
      <div>
        <strong>Assigned Ambulance:</strong> ${d.ambulance_vehicle || 'None'}
      </div>
    </div>
  `;

  document.getElementById('modalIncidentDetails').hidden = false;
};

/* ─────────────────────────────────────────────────────────────
   GLOBAL MODAL CLOSING LOGIC
   ───────────────────────────────────────────────────────────── */
function initModals() {
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal').hidden = true;
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal:not([hidden])').forEach(m => m.hidden = true);
    }
  });
}

/* ─────────────────────────────────────────────────────────────
   APPLICATION BOOTSTRAP
   ───────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  initNavigation();
  initDispatchForm();
  initRouteFinder();
  initHospitalModals();
  initAmbulanceModals();
  initHistoryFilters();
  initModals();

  await checkBackendConnection();
  await loadRoadNetworkData();
  await loadDashboardStats();

  // Periodic health ping
  setInterval(checkBackendConnection, 15000);
});
