/* ─────────────────────────────────────────────
   MedRoute — Emergency Ambulance Dispatch
   Frontend JavaScript
   Port of app.py logic + Canvas visualisation
   ──────────────────────────────────────────── */

'use strict';

/* ── Data (mirrors app.py) ── */
const GRAPH = {
  A: { B: 4, C: 2 },
  B: { A: 4, D: 5 },
  C: { A: 2, D: 8 },
  D: { B: 5, C: 8 },
};

const HOSPITALS = [
  { name: 'City Care Hospital',     beds: 5, specialization: 'Cardiology',   node: 'D' },
  { name: 'Sunrise Hospital',       beds: 0, specialization: 'Cardiology',   node: 'B' },
  { name: 'General Care Hospital',  beds: 8, specialization: 'General',      node: 'C' },
  { name: 'Bone and Joint Hospital',beds: 3, specialization: 'Orthopaedics', node: 'B' },
];

/* ── Dijkstra ── */
function dijkstra(graph, start, end) {
  const queue = [[0, start, [start]]];   // [dist, node, path]
  const visited = new Set();

  while (queue.length) {
    queue.sort((a, b) => a[0] - b[0]);
    const [dist, cur, path] = queue.shift();
    if (visited.has(cur)) continue;
    visited.add(cur);
    if (cur === end) return { distance: dist, route: path };
    for (const [nb, w] of Object.entries(graph[cur])) {
      if (!visited.has(nb)) {
        queue.push([dist + w, nb, [...path, nb]]);
      }
    }
  }
  return null;
}

/* ── Specialization map ── */
function getSpecialization(type) {
  const t = type.toLowerCase();
  if (t === 'cardiac')      return 'Cardiology';
  if (t === 'orthopaedic')  return 'Orthopaedics';
  return 'General';
}

/* ── Core: find best hospital ── */
function findHospital(location, emergencyType) {
  const spec = getSpecialization(emergencyType);
  const candidates = [];

  for (const h of HOSPITALS) {
    if (h.beds > 0 && h.specialization === spec) {
      const result = dijkstra(GRAPH, location, h.node);
      if (!result) continue;
      const copy = { ...h, distance: result.distance, route: result.route };
      const distScore = 10 - copy.distance;
      copy.score = 0.7 * distScore + 0.3 * copy.beds;
      candidates.push(copy);
    }
  }

  if (!candidates.length) return null;
  candidates.sort((a, b) => b.score - a.score);
  return candidates[0];
}

/* ────────────────────────────────────────────
   CANVAS — Node positions (normalised 0–1)
   ──────────────────────────────────────────── */
const NODE_POSITIONS = {
  A: { x: 0.15, y: 0.2  },
  B: { x: 0.85, y: 0.2  },
  C: { x: 0.85, y: 0.8  },
  D: { x: 0.15, y: 0.8  },
};

const EDGES = [
  ['A', 'B', 4],
  ['A', 'C', 2],
  ['B', 'D', 5],
  ['C', 'D', 8],
];

/* ── Canvas utility ── */
function canvasCoord(canvas, key) {
  const p = NODE_POSITIONS[key];
  return {
    x: p.x * (canvas.width  - 48) + 24,
    y: p.y * (canvas.height - 48) + 24,
  };
}

/* ── Hero network canvas (animated idle) ── */
(function heroCanvas() {
  const canvas = document.getElementById('networkCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let t = 0;

  function drawHero() {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    /* edges */
    EDGES.forEach(([a, b, weight]) => {
      const pa = canvasCoord(canvas, a);
      const pb = canvasCoord(canvas, b);
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.strokeStyle = 'rgba(255,255,255,0.07)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      /* weight label */
      const mx = (pa.x + pb.x) / 2;
      const my = (pa.y + pb.y) / 2;
      ctx.fillStyle = 'rgba(255,255,255,0.2)';
      ctx.font = '11px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(weight + ' km', mx, my - 6);
    });

    /* animated pulse packet */
    const edgeIdx = Math.floor(t / 120) % EDGES.length;
    const [ea, eb] = EDGES[edgeIdx];
    const pct = (t % 120) / 120;
    const from = canvasCoord(canvas, ea);
    const to   = canvasCoord(canvas, eb);
    const px = from.x + (to.x - from.x) * pct;
    const py = from.y + (to.y - from.y) * pct;

    // trail
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(px, py);
    ctx.strokeStyle = 'rgba(230,57,80,0.45)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // packet dot
    ctx.beginPath();
    ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#e63950';
    ctx.shadowColor = '#e63950';
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.shadowBlur = 0;

    /* nodes */
    Object.entries(NODE_POSITIONS).forEach(([key]) => {
      const pos = canvasCoord(canvas, key);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 18, 0, Math.PI * 2);
      ctx.fillStyle = '#181b22';
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#e8eaf0';
      ctx.font = '600 14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(key, pos.x, pos.y);
      ctx.textBaseline = 'alphabetic';
    });

    /* hospital labels */
    HOSPITALS.forEach(h => {
      if (h.beds === 0) return;
      const pos = canvasCoord(canvas, h.node);
      const tagW = 20, tagH = 14;
      const tagX = pos.x - tagW / 2;
      const tagY = pos.y - 34;

      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(tagX, tagY, tagW, tagH, 3);
      } else {
        ctx.rect(tagX, tagY, tagW, tagH);
      }
      ctx.fillStyle = 'rgba(20, 184, 166, 0.15)';
      ctx.strokeStyle = '#14b8a6';
      ctx.lineWidth = 1;
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#14b8a6';
      ctx.font = '700 9px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('H', pos.x, tagY + tagH / 2);
      ctx.textBaseline = 'alphabetic';
    });

    t++;
    requestAnimationFrame(drawHero);
  }
  drawHero();
})();

/* ── Result route canvas ── */
function drawResultCanvas(routeNodes, fromNode) {
  const canvas = document.getElementById('resultCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  /* all edges dim */
  EDGES.forEach(([a, b]) => {
    const pa = canvasCoord(canvas, a);
    const pb = canvasCoord(canvas, b);
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });

  /* highlight route edges */
  for (let i = 0; i < routeNodes.length - 1; i++) {
    const pa = canvasCoord(canvas, routeNodes[i]);
    const pb = canvasCoord(canvas, routeNodes[i + 1]);
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.strokeStyle = '#e63950';
    ctx.lineWidth = 2.5;
    ctx.shadowColor = '#e63950';
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    /* arrow head */
    const angle = Math.atan2(pb.y - pa.y, pb.x - pa.x);
    const mx = (pa.x + pb.x) / 2;
    const my = (pa.y + pb.y) / 2;
    const al = 10, aw = 6;
    ctx.beginPath();
    ctx.moveTo(mx + al * Math.cos(angle), my + al * Math.sin(angle));
    ctx.lineTo(mx + aw * Math.cos(angle - Math.PI * 0.75), my + aw * Math.sin(angle - Math.PI * 0.75));
    ctx.lineTo(mx + aw * Math.cos(angle + Math.PI * 0.75), my + aw * Math.sin(angle + Math.PI * 0.75));
    ctx.closePath();
    ctx.fillStyle = '#e63950';
    ctx.fill();
  }

  /* nodes */
  Object.entries(NODE_POSITIONS).forEach(([key]) => {
    const pos = canvasCoord(canvas, key);
    const isRoute  = routeNodes.includes(key);
    const isStart  = key === fromNode;
    const isEnd    = key === routeNodes[routeNodes.length - 1];

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, isRoute ? 20 : 16, 0, Math.PI * 2);
    ctx.fillStyle = isEnd ? '#e63950' : isStart ? '#14b8a6' : isRoute ? '#2d3142' : '#181b22';
    ctx.strokeStyle = isRoute ? (isEnd ? '#e63950' : isStart ? '#14b8a6' : 'rgba(255,255,255,0.2)') : 'rgba(255,255,255,0.07)';
    ctx.lineWidth = isRoute ? 2 : 1;
    if (isEnd) { ctx.shadowColor = '#e63950'; ctx.shadowBlur = 16; }
    else if (isStart) { ctx.shadowColor = '#14b8a6'; ctx.shadowBlur = 12; }
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    ctx.fillStyle = isRoute ? '#fff' : 'rgba(255,255,255,0.3)';
    ctx.font = `${isRoute ? '600' : '400'} 13px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(key, pos.x, pos.y);
    ctx.textBaseline = 'alphabetic';
  });

  /* legend */
  const legend = [
    { color: '#14b8a6', label: 'Patient location' },
    { color: '#e63950', label: 'Hospital' },
  ];
  legend.forEach((l, i) => {
    ctx.beginPath();
    ctx.arc(16, h - 28 + i * 18, 5, 0, Math.PI * 2);
    ctx.fillStyle = l.color;
    ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(l.label, 26, h - 24 + i * 18);
  });
}

/* ────────────────────────────────────────────
   HOSPITAL GRID render
   ──────────────────────────────────────────── */
function renderHospitalGrid() {
  const grid = document.getElementById('hospitalGrid');
  if (!grid) return;
  grid.innerHTML = '';

  HOSPITALS.forEach(h => {
    const card = document.createElement('div');
    card.className = 'hosp-card';
    const noBeds = h.beds === 0;
    card.innerHTML = `
      <div class="hosp-card__header">
        <div class="hosp-card__node">Node ${h.node}</div>
        <div class="hosp-card__status ${noBeds ? 'hosp-card__status--full' : 'hosp-card__status--available'}">
          <span class="status-dot"></span>
          ${noBeds ? 'No Beds' : h.beds + ' Available'}
        </div>
      </div>
      <div class="hosp-card__name">${h.name}</div>
      <div class="hosp-card__meta">
        <span class="tag tag--spec">${h.specialization}</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

/* ────────────────────────────────────────────
   SEVERITY SLIDER
   ──────────────────────────────────────────── */
const severitySlider  = document.getElementById('severity');
const severityDisplay = document.getElementById('severityDisplay');
const severityLabels  = ['Low', 'Medium', 'High'];

function updateSeverity() {
  const val = +severitySlider.value - 1;
  severityDisplay.textContent = severityLabels[val];
  const colors = ['#22c55e', '#f59e0b', '#e63950'];
  severityDisplay.style.color = colors[val];
}
severitySlider.addEventListener('input', updateSeverity);
updateSeverity();

/* ────────────────────────────────────────────
   FORM SUBMIT
   ──────────────────────────────────────────── */
const form           = document.getElementById('dispatchForm');
const dispatchBtn    = document.getElementById('dispatchBtn');
const resultSection  = document.getElementById('resultSection');
const noResultSection= document.getElementById('noResultSection');

function showSection(el) {
  resultSection.hidden  = true;
  noResultSection.hidden= true;
  el.hidden = false;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setLoading(on) {
  const text   = dispatchBtn.querySelector('.btn__text');
  const loader = dispatchBtn.querySelector('.btn__loader');
  text.hidden   = on;
  loader.hidden = !on;
  dispatchBtn.disabled = on;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const location = document.getElementById('location').value;
  const emergency = form.querySelector('input[name="emergency"]:checked')?.value;
  const severityVal = severityLabels[+severitySlider.value - 1];

  if (!location) { flashError('Please select a location.'); return; }
  if (!emergency) { flashError('Please select an emergency type.'); return; }

  setLoading(true);
  /* Simulated async delay for UX */
  await new Promise(r => setTimeout(r, 900));
  setLoading(false);

  const result = findHospital(location, emergency);

  if (!result) {
    showSection(noResultSection);
    return;
  }

  /* populate result */
  document.getElementById('rHospitalName').textContent = result.name;
  document.getElementById('rSpec').textContent  = result.specialization;
  document.getElementById('rBeds').textContent  = result.beds + ' beds available';

  /* route */
  const routeEl = document.getElementById('rRoute');
  routeEl.innerHTML = result.route.map((n, i) =>
    `<span class="route-node">${n}</span>` +
    (i < result.route.length - 1 ? `<span class="route-arrow">›</span>` : '')
  ).join('');

  document.getElementById('rDistance').textContent = result.distance + ' km';
  document.getElementById('rETA').textContent      = (result.distance * 2) + ' min';
  document.getElementById('rScore').textContent    = result.score.toFixed(2);

  /* draw canvas */
  drawResultCanvas(result.route, location);
  showSection(resultSection);
});

/* ── Reset buttons ── */
document.getElementById('resetBtn').addEventListener('click', () => {
  resultSection.hidden = true;
  form.reset();
  updateSeverity();
  document.getElementById('dispatch').scrollIntoView({ behavior: 'smooth' });
});
document.getElementById('resetBtn2').addEventListener('click', () => {
  noResultSection.hidden = true;
  form.reset();
  updateSeverity();
  document.getElementById('dispatch').scrollIntoView({ behavior: 'smooth' });
});

/* ── Simple inline error flash ── */
function flashError(msg) {
  const existing = document.querySelector('.form-error');
  if (existing) existing.remove();
  const el = document.createElement('p');
  el.className = 'form-error';
  el.textContent = msg;
  el.style.cssText = 'color:#e63950;font-size:13px;margin-top:-12px;margin-bottom:12px;';
  dispatchBtn.before(el);
  setTimeout(() => el.remove(), 3500);
}

/* ────────────────────────────────────────────
   INIT
   ──────────────────────────────────────────── */
renderHospitalGrid();
