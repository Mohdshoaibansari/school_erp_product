// shared.js — env var store + step runner for journey_flows UI
// Auto-chain: each step's response can store values into env vars that
// subsequent steps reference via $VAR_NAME placeholders.

const STORE = {};

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

// Render the env var store panel
function renderStorePanel(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = '<h4>Env Variables</h4><table style="border-collapse:collapse;font-size:12px;">' +
    Object.entries(STORE).map(([k, v]) =>
      `<tr><td style="padding:2px 8px;color:#666;">${k}</td><td style="padding:2px 8px;font-family:monospace;">${(v || '').substring(0, 80)}${(v || '').length > 80 ? '...' : ''}</td></tr>`
    ).join('') + '</table>' +
    '<button onclick="clearStore()" style="margin-top:8px;font-size:11px;">Clear Store</button>';
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
  // Re-render store panel if present
  renderStorePanel('store-panel');
}