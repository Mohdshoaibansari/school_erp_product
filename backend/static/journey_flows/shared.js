// shared.js — env var store + step runner for journey_flows UI
// Auto-chain: each step's response can store values into env vars that
// subsequent steps reference via $VAR_NAME placeholders.

const STORE = {};

/*
 * Persistence: env vars are stored in localStorage under 'journey_flow_store'.
 * They survive reloads and even restarting the browser — so you can run Flow 1,
 * switch flows, come back, and the IDs are still there. To wipe everything,
 * click the red "Reset All" button in the header (top right of any flow page).
 */

// Helper: store all variables in localStorage so they survive page reloads
function loadStore() {
  try {
    const s = localStorage.getItem('journey_flow_store');
    if (s) Object.assign(STORE, JSON.parse(s));
  } catch (e) {}
}

function saveStore() {
  try {
    localStorage.setItem('journey_flow_store', JSON.stringify(STORE));
  } catch (e) {}
}

loadStore();

// Substitute $VAR_NAME in a string with stored values
function substitute(text) {
  return text.replace(/\$([A-Z_][A-Z0-9_]*)/g, (_, name) => {
    return STORE[name] !== undefined ? STORE[name] : `$${name}`;
  });
}

// Apply extraction rules: e.g. [{var: 'CLIENT_ID', path: 'id'}, {var: 'TOKEN', path: 'access_token'}]
function applyExtractions(data, extractions) {
  if (!extractions) return;
  for (const ext of extractions) {
    const value = resolvePath(data, ext.path);
    if (value !== undefined) {
      STORE[ext.var] = String(value);
      console.log(`[flow] stored ${ext.var} = ${value}`);
    }
  }
  saveStore();
}

// Resolve a dotted path like "access_token" or "user.id" or "data.0.id"
function resolvePath(obj, path) {
  const parts = path.split('.');
  let cur = obj;
  for (const p of parts) {
    if (cur === null || cur === undefined) return undefined;
    if (/^\d+$/.test(p)) cur = cur[parseInt(p, 10)];
    else cur = cur[p];
  }
  return cur;
}

// Pretty-print JSON
function prettyJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return String(obj);
  }
}

// Render the env var store panel (right sidebar on flow pages)
function renderStorePanel(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const rows = Object.entries(STORE)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => {
      const val = String(v || '');
      const shown = val.length > 80 ? val.substring(0, 80) + '...' : val;
      return `<tr><td style="padding:2px 8px;color:#9ca3af;">${k}</td><td style="padding:2px 8px;font-family:monospace;color:#e5e7eb;word-break:break-all;">${shown}</td></tr>`;
    }).join('');
  el.innerHTML = '<h4>Env Variables</h4>' +
    (rows ? `<table style="border-collapse:collapse;font-size:12px;width:100%;">${rows}</table>` : '<div style="color:#9ca3af;font-size:12px;">No vars stored yet</div>') +
    '<button onclick="confirmReset()" style="margin-top:10px;background:#7f1d1d;color:#fecaca;border:1px solid #991b1b;padding:5px 12px;font-size:11px;border-radius:3px;cursor:pointer;width:100%;">Reset All Env Vars</button>';
  updateIndicator();
}

// Auto-inject a reset button + indicator into every flow page header.
// This runs once on DOMContentLoaded — no per-page edits needed.
function _injectHeaderActions() {
  const header = document.querySelector('.header');
  if (!header) return;
  if (header.querySelector('.header-actions')) { return; }
  const backLink = header.querySelector('.back-link');
  const actions = document.createElement('div');
  actions.className = 'header-actions';
  actions.innerHTML =
    '<span class="store-indicator" id="store-indicator">0 vars</span>' +
    '<button class="reset-btn" onclick="confirmReset()">Reset All</button>';
  // Insert after back link (or at end if no back link)
  if (backLink) header.insertBefore(actions, backLink);
  else header.appendChild(actions);
  updateIndicator();
}

function updateIndicator() {
  const ind = document.getElementById('store-indicator');
  if (!ind) return;
  const n = Object.keys(STORE).length;
  ind.textContent = n + ' env var' + (n === 1 ? '' : 's') + ' stored';
  ind.title = 'Vars: ' + Object.keys(STORE).sort().join(', ');
}

function confirmReset() {
  if (confirm('Reset ALL env vars?\n\nThis wipes ALL stored IDs, tokens, and the Supabase service key from this browser. You will need to set them again.')) {
    clearStore();
  }
}

function clearStore() {
  Object.keys(STORE).forEach(k => delete STORE[k]);
  localStorage.removeItem('journey_flow_store');
  location.reload();
}

// Run a single step
// step = {
//   method: 'POST',
//   url: 'http://127.0.0.1:8000/api/auth/login',  // may contain $VARS
//   headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer $TOKEN', 'Host': '$HOST' },
//   body: '{"email":"...","password":"..."}',  // string, may contain $VARS
//   extractions: [{ var: 'TOKEN', path: 'access_token' }],
// }
async function runStep(step, resultElId) {
  const resultEl = document.getElementById(resultElId);
  if (!resultEl) return;

  resultEl.innerHTML = '<em>Running...</em>';

  const url = substitute(step.url);
  const headers = {};
  for (const [k, v] of Object.entries(step.headers || {})) {
    headers[k] = substitute(v);
  }
  const body = step.body ? substitute(step.body) : undefined;

  const log = [];
  log.push(`<div style="color:#888;">→ ${step.method} ${url}</div>`);
  log.push(`<div style="color:#888;font-size:11px;">${Object.entries(headers).map(([k, v]) => `${k}: ${v.substring(0, 50)}${v.length > 50 ? '...' : ''}`).join(' | ')}</div>`);
  if (body) log.push(`<div style="color:#888;font-size:11px;">body: ${body.substring(0, 120)}${body.length > 120 ? '...' : ''}</div>`);

  try {
    const fetchOpts = { method: step.method, headers };
    if (body && step.method !== 'GET' && step.method !== 'DELETE') {
      fetchOpts.body = body;
    }
    const resp = await fetch(url, fetchOpts);
    const respText = await resp.text();
    let respJson = null;
    try { respJson = JSON.parse(respText); } catch (e) {}

    log.push(`<div style="margin-top:6px;color:${resp.ok ? '#0a0' : '#a00'};font-weight:bold;">← ${resp.status} ${resp.statusText}</div>`);
    log.push(`<pre style="background:#f5f5f5;padding:8px;border-radius:4px;overflow:auto;max-height:300px;font-size:11px;">${respJson ? prettyJson(respJson) : respText}</pre>`);

    if (resp.ok && step.extractions) {
      applyExtractions(respJson || {}, step.extractions);
      log.push(`<div style="color:#0a0;font-size:11px;margin-top:6px;">✓ extracted: ${step.extractions.map(e => e.var).join(', ')}</div>`);
    }
  } catch (e) {
    log.push(`<div style="color:#a00;font-weight:bold;">✗ Error: ${e.message}</div>`);
    log.push(`<div style="font-size:11px;color:#a00;">Is the backend running on http://127.0.0.1:8000?</div>`);
  }

  resultEl.innerHTML = log.join('');
  // Re-render store panel + indicator after every step
  renderStorePanel('store-panel');
}

// Auto-inject header actions on every page that includes this script
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _injectHeaderActions);
} else {
  _injectHeaderActions();
}