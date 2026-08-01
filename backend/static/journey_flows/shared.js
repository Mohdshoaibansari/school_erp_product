// shared.js — env var store + step runner + lookup cache for journey_flows UI
// Auto-chain: each step's response can store values into env vars that
// subsequent steps reference via $VAR_NAME placeholders.
//
// Lookup cache: avoids hardcoding UUIDs (legal_entity_type_id, role_id, etc.)
// by fetching them once from the API and caching in memory + localStorage.
// Pages call fetchLookups() after login, then reference by name:
//   $LOOKUP.roles.client_director  → the UUID for role "client_director"
//   $LOOKUP.legal-entity-types.Pvt Ltd  → UUID for legal entity "Pvt Ltd"

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

// ---------------------------------------------------------------------------
// Lookup cache — avoids hardcoding UUIDs that change per environment
// ---------------------------------------------------------------------------
const LOOKUP_CACHE = {};

function loadLookupCache() {
  try {
    const s = localStorage.getItem('journey_flow_lookups');
    if (s) Object.assign(LOOKUP_CACHE, JSON.parse(s));
  } catch (e) {}
}

function saveLookupCache() {
  try {
    localStorage.setItem('journey_flow_lookups', JSON.stringify(LOOKUP_CACHE));
  } catch (e) {}
}

loadLookupCache();

/**
 * Fetch lookup tables from the API and cache them.
 * Surfaces: 'roles', 'legal-entity-types', 'user-categories', 'institution-types', 'org-unit-types'
 *
 * Usage:
 *   const lookups = await fetchLookups(token, ['roles', 'legal-entity-types']);
 *   // Then $LOOKUP.roles.client_director resolves automatically in steps
 *
 * Cached results survive page reloads. Pass force=true to bypass cache.
 */
async function fetchLookups(token, surfaces, force) {
  const results = {};
  for (const surface of surfaces) {
    if (!force && LOOKUP_CACHE[surface] && LOOKUP_CACHE[surface].length > 0) {
      results[surface] = LOOKUP_CACHE[surface];
      continue;
    }
    const url = 'http://127.0.0.1:8000/api/v1/lookups/' + surface;
    try {
      const resp = await fetch(url, {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (resp.ok) {
        const data = await resp.json();
        LOOKUP_CACHE[surface] = data;
        saveLookupCache();
        results[surface] = data;
        console.log('[lookups] fetched ' + surface + ': ' + data.length + ' items');
      } else {
        console.warn('[lookups] ' + surface + ' returned ' + resp.status);
        results[surface] = LOOKUP_CACHE[surface] || [];
      }
    } catch (e) {
      console.warn('[lookups] error fetching ' + surface + ': ' + e.message);
      results[surface] = LOOKUP_CACHE[surface] || [];
    }
  }
  // Store resolved lookups on window so runStep can access them
  window._resolvedLookups = results;
  return results;
}

/**
 * Find a lookup item by name (case-insensitive match on .name or .code).
 * Returns the whole item or null.
 */
function lookupByName(items, name) {
  if (!items || !items.length) return null;
  const lower = name.toLowerCase();
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const itemName = (item.name || item.code || '').toLowerCase();
    if (itemName === lower) return item;
  }
  return null;
}

/**
 * Replace $LOOKUP.surface.name with the UUID from the cached lookups.
 * Uses window._resolvedLookups if available, otherwise falls back to LOOKUP_CACHE.
 */
function substituteLookup(text) {
  if (!text || typeof text !== 'string') return text;
  const lookups = window._resolvedLookups || LOOKUP_CACHE;
  if (!lookups) return text;

  return text.replace(/\$LOOKUP\.([\w-]+)\.([\w .]+)/g, (match, surface, name) => {
    const items = lookups[surface];
    if (!items) {
      console.warn('[lookups] surface not loaded: ' + surface);
      return match;
    }
    const item = lookupByName(items, name);
    if (item && item.id) {
      console.log('[lookups] resolved ' + match + ' → ' + item.id);
      return item.id;
    }
    console.warn('[lookups] not found: ' + surface + ' / ' + name);
    return match;
  });
}

// ---------------------------------------------------------------------------

// Substitute $VAR_NAME in a string with stored values, then $LOOKUP references
function substitute(text) {
  if (!text || typeof text !== 'string') return text;
  // First substitute $VAR placeholders
  let result = text.replace(/\$([A-Z_][A-Z0-9_]*)/g, (_, name) => {
    return STORE[name] !== undefined ? STORE[name] : '$' + name;
  });
  // Then substitute $LOOKUP references
  result = substituteLookup(result);
  return result;
}

// Apply extraction rules: e.g. [{var: 'CLIENT_ID', path: 'id'}, {var: 'TOKEN', path: 'access_token'}]
function applyExtractions(data, extractions) {
  if (!extractions) return;
  for (const ext of extractions) {
    const value = resolvePath(data, ext.path);
    if (value !== undefined) {
      STORE[ext.var] = String(value);
      console.log('[flow] stored ' + ext.var + ' = ' + value);
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
      return '<tr><td style="padding:2px 8px;color:#9ca3af;">' + k + '</td><td style="padding:2px 8px;font-family:monospace;color:#e5e7eb;word-break:break-all;">' + shown + '</td></tr>';
    }).join('');
  el.innerHTML = '<h4>Env Variables</h4>' +
    (rows ? '<table style="border-collapse:collapse;font-size:12px;width:100%;">' + rows + '</table>' : '<div style="color:#9ca3af;font-size:12px;">No vars stored yet</div>') +
    '<button onclick="confirmReset()" style="margin-top:10px;background:#7f1d1d;color:#fecaca;border:1px solid #991b1b;padding:5px 12px;font-size:11px;border-radius:3px;cursor:pointer;width:100%;">Reset All Env Vars</button>';
  updateIndicator();
}

// Auto-inject a reset button + indicator into every flow page header.
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
  if (confirm('Reset ALL env vars and lookups?\n\nThis wipes ALL stored IDs, tokens, lookups, and the Supabase service key from this browser. You will need to set them again.')) {
    clearStore();
  }
}

function clearStore() {
  Object.keys(STORE).forEach(k => delete STORE[k]);
  localStorage.removeItem('journey_flow_store');
  // Also clear lookups
  Object.keys(LOOKUP_CACHE).forEach(k => delete LOOKUP_CACHE[k]);
  localStorage.removeItem('journey_flow_lookups');
  location.reload();
}

// Run a single step
// step = {
//   method: 'POST',
//   url: 'http://127.0.0.1:8000/api/auth/login',  // may contain $VARS and $LOOKUP
//   headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer $TOKEN' },
//   body: '{"email":"...","password":"..."}',  // string, may contain $VARS and $LOOKUP
//   extractions: [{ var: 'TOKEN', path: 'access_token' }],
//   fetchLookups: ['roles', 'legal-entity-types'],  // if set, fetches these after success
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
  log.push('<div style="color:#888;">→ ' + step.method + ' ' + url + '</div>');
  log.push('<div style="color:#888;font-size:11px;">' + Object.entries(headers).map(([k, v]) => k + ': ' + v.substring(0, 50) + (v.length > 50 ? '...' : '')).join(' | ') + '</div>');
  if (body) log.push('<div style="color:#888;font-size:11px;">body: ' + body.substring(0, 120) + (body.length > 120 ? '...' : '') + '</div>');

  try {
    const fetchOpts = { method: step.method, headers };
    if (body && step.method !== 'GET' && step.method !== 'DELETE') {
      fetchOpts.body = body;
    }
    const resp = await fetch(url, fetchOpts);
    const respText = await resp.text();
    let respJson = null;
    try { respJson = JSON.parse(respText); } catch (e) {}

    log.push('<div style="margin-top:6px;color:' + (resp.ok ? '#0a0' : '#a00') + ';font-weight:bold;">← ' + resp.status + ' ' + resp.statusText + '</div>');
    log.push('<pre style="background:#f5f5f5;padding:8px;border-radius:4px;overflow:auto;max-height:300px;font-size:11px;">' + (respJson ? prettyJson(respJson) : respText) + '</pre>');

    if (resp.ok && step.extractions) {
      applyExtractions(respJson || {}, step.extractions);
      log.push('<div style="color:#0a0;font-size:11px;margin-top:6px;">✓ extracted: ' + step.extractions.map(e => e.var).join(', ') + '</div>');
    }

    // After a successful step, fetch lookups if requested
    if (resp.ok && step.fetchLookups && step.fetchLookups.length > 0) {
      const token = (respJson && respJson.access_token) || STORE['TOKEN'] || '';
      try {
        const lu = await fetchLookups(token, step.fetchLookups);
        if (lu && Object.keys(lu).length > 0) {
          log.push('<div style="color:#0a0;font-size:11px;margin-top:6px;">✓ lookups loaded: ' + step.fetchLookups.join(', ') + '</div>');
        }
      } catch (e) {
        log.push('<div style="color:#a80;font-size:11px;">⚠ lookup fetch failed: ' + e.message + '</div>');
      }
    }
  } catch (e) {
    log.push('<div style="color:#a00;font-weight:bold;">✗ Error: ' + e.message + '</div>');
    log.push('<div style="font-size:11px;color:#a00;">Is the backend running on http://127.0.0.1:8000?</div>');
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
