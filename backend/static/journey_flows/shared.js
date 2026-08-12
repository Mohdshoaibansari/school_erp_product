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
    const url = 'http://127.0.0.1:8001/api/v1/lookups/' + surface;
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
  // Allow API_BASE_URL to override the hardcoded localhost target in the legacy flow definitions.
  if (STORE.API_BASE_URL) result = result.replace('http://127.0.0.1:8001', String(STORE.API_BASE_URL).replace(/\/$/, ''));
  // Then substitute $LOOKUP references
  result = substituteLookup(result);
  return result;
}

/**
 * Guard: check that required env vars are set before running a step.
 * Returns true if all vars present; false + shows error if any missing.
 *
 * Usage in onclick handlers:
 *   if (!requireVars(['CLIENT_ID', 'INST_ID'], 'result-5')) return;
 *   runStep({...}, 'result-5');
 */
function requireVars(vars, resultElId) {
  const missing = vars.filter(v => STORE[v] === undefined || STORE[v] === '' || STORE[v] === null);
  if (missing.length === 0) return true;
  const el = document.getElementById(resultElId);
  if (el) {
    el.innerHTML = '<div style="color:#dc2626;font-weight:bold;">' +
      '⚠ Missing env var' + (missing.length > 1 ? 's' : '') + ': ' +
      missing.map(v => '<code>' + v + '</code>').join(', ') +
      '.<br>Run the prerequisite steps/flows first, then re-run this step.' +
      '</div>' +
      '<div style="color:#666;font-size:11px;margin-top:4px;">' +
      'Current env vars: ' + Object.keys(STORE).sort().join(', ') +
      '</div>';
  }
  return false;
}

// Apply extraction rules: e.g. [{var: 'CLIENT_ID', path: 'id'}, {var: 'TOKEN', path: 'access_token'}]
function applyExtractions(data, extractions) {
  if (!extractions) return;
  for (const ext of extractions) {
    const value = resolvePath(data, ext.path);
    if (value !== undefined) {
      STORE[ext.var] = String(value);
      console.log('[flow] stored ' + ext.var + ' = ' + value);
    } else {
      console.warn('[flow] extraction returned undefined: ' + ext.path);
    }
  }
  saveStore();
}

// Resolve a dotted path like "access_token" or "user.id" or "data.0.id"
// Supports filter syntax: "[field=value]" finds array item matching predicate.
function resolvePath(obj, path) {
  // Tokenize: split on dots, but keep "[...]" as a single token.
  const parts = [];
  let depth = 0;
  let buf = '';
  for (let i = 0; i < path.length; i++) {
    const ch = path[i];
    if (ch === '[') {
      if (depth > 0) buf += ch;  // nested bracket — keep as content
      else buf = '[';            // opening bracket — start filter token
      depth++;
    } else if (ch === ']') {
      depth--;
      if (depth === 0) {
        buf += ']';              // closing bracket — end filter token
        parts.push(buf);
        buf = '';
      } else {
        buf += ch;
      }
    } else if (ch === '.' && depth === 0) {
      if (buf.length > 0) {
        parts.push(buf);
        buf = '';
      }
    } else {
      buf += ch;
    }
  }
  if (buf.length > 0) parts.push(buf);

  let cur = obj;
  for (const p of parts) {
    if (cur === null || cur === undefined) return undefined;
    if (p.startsWith('[') && p.endsWith(']')) {
      const inner = p.slice(1, -1);
      const predicates = inner.split(',').map(s => {
        const eq = s.indexOf('=');
        return { field: s.substring(0, eq), value: s.substring(eq + 1) };
      });
      if (!Array.isArray(cur)) return undefined;
      cur = cur.find(item => {
        if (item === null || typeof item !== 'object') return false;
        return predicates.every(pred => String(item[pred.field]) === pred.value);
      });
      if (cur === undefined) return undefined;
    } else if (/^\d+$/.test(p)) {
      cur = cur[parseInt(p, 10)];
    } else {
      cur = cur[p];
    }
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

// ---------------------------------------------------------------------------
// Test UI shell — intentionally lightweight. All state remains in localStorage.
// ---------------------------------------------------------------------------

const ACTORS = {
  platform: { label: 'Platform Owner', token: 'PLATFORM_TOKEN', refresh: 'PLATFORM_REFRESH_TOKEN', email: 'PLATFORM_EMAIL', password: 'PLATFORM_PASSWORD', host: '' },
  director: { label: 'Client Director', token: 'DIRECTOR_TOKEN', refresh: 'DIRECTOR_REFRESH_TOKEN', email: 'DIRECTOR_EMAIL', password: 'DIRECTOR_PASSWORD', host: 'CLIENT_SLUG' },
  admin: { label: 'Institute Admin', token: 'ADMIN_TOKEN', refresh: 'ADMIN_REFRESH_TOKEN', email: 'ADMIN_EMAIL', password: 'ADMIN_PASSWORD', host: 'CLIENT_SLUG' },
  teacher: { label: 'Teacher', token: 'TEACHER_TOKEN', refresh: 'TEACHER_REFRESH_TOKEN', email: 'TEACHER_EMAIL', password: 'TEACHER_PASSWORD', host: 'CLIENT_SLUG' },
  student: { label: 'Student', token: 'STUDENT_TOKEN', refresh: 'STUDENT_REFRESH_TOKEN', email: 'STUDENT_EMAIL', password: 'STUDENT_PASSWORD', host: 'CLIENT_SLUG' },
  parent: { label: 'Parent', token: 'PARENT_TOKEN', refresh: 'PARENT_REFRESH_TOKEN', email: 'PARENT_EMAIL', password: 'PARENT_PASSWORD', host: 'CLIENT_SLUG' }
};

function esc(v) {
  return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function maskValue(key, value) {
  const v = String(value ?? '');
  const secret = /TOKEN|PASSWORD|KEY|SECRET/i.test(key);
  if (!secret) return v.length > 42 ? v.slice(0, 42) + '…' : v;
  if (!v) return '';
  return v.length <= 12 ? '••••••••' : v.slice(0, 5) + '••••••••' + v.slice(-4);
}

function updateIndicator() {
  const ind = document.getElementById('store-indicator');
  if (ind) ind.textContent = Object.keys(STORE).length + ' vars';
}

function renderEnvRail(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const rows = Object.entries(STORE).sort(([a],[b]) => a.localeCompare(b)).map(([k,v]) => `
    <div class="env-row">
      <div class="env-key" title="${esc(k)}">${esc(k)}</div>
      <div class="env-value" title="${esc(v)}">${esc(maskValue(k,v))}</div>
      <button class="icon-btn danger" title="Remove ${esc(k)}" onclick="removeEnvVar('${esc(k)}')">×</button>
    </div>`).join('');
  el.innerHTML = `
    <div class="rail-head"><div><div class="eyebrow">RUNTIME</div><h3>Environment</h3></div><span class="count-pill">${Object.keys(STORE).length}</span></div>
    <div class="env-add">
      <input id="env-key-input" placeholder="KEY_NAME" autocomplete="off">
      <input id="env-value-input" placeholder="value" autocomplete="off">
      <button class="btn btn-small" onclick="addEnvVar()">Add</button>
    </div>
    <div class="env-list">${rows || '<div class="empty-state">No variables yet.<br>Add one above or use the flow setup wizard.</div>'}</div>
    <div class="rail-footer">
      <button class="btn btn-ghost" onclick="confirmReset()">Reset all</button>
      <span>localStorage</span>
    </div>`;
  updateIndicator();
}

function renderStorePanel(elementId) {
  renderEnvRail(elementId);
}

function addEnvVar() {
  const kEl = document.getElementById('env-key-input');
  const vEl = document.getElementById('env-value-input');
  const key = (kEl?.value || '').trim().toUpperCase();
  if (!/^[A-Z_][A-Z0-9_]*$/.test(key)) { alert('Use an ENV-style key, e.g. CLIENT_SLUG'); return; }
  STORE[key] = vEl?.value ?? '';
  saveStore();
  renderEnvRail('store-panel');
}

function removeEnvVar(key) {
  if (!confirm('Remove ' + key + '?')) return;
  delete STORE[key];
  saveStore();
  renderEnvRail('store-panel');
}

function confirmReset() {
  if (confirm('Reset all test variables and cached lookups?')) clearStore();
}

function clearStore() {
  Object.keys(STORE).forEach(k => delete STORE[k]);
  localStorage.removeItem('journey_flow_store');
  Object.keys(LOOKUP_CACHE).forEach(k => delete LOOKUP_CACHE[k]);
  localStorage.removeItem('journey_flow_lookups');
  location.reload();
}

function setDefaults() {
  const defaults = {
    API_BASE_URL: 'http://127.0.0.1:8001',
    PLATFORM_EMAIL: 'admin@school-erp.com', PLATFORM_PASSWORD: 'Shoby@123',
    CLIENT_DISPLAY_NAME: 'Greenwood', CLIENT_SLUG: 'greenwood',
    DIRECTOR_EMAIL: 'director@greenwood.com', DIRECTOR_PASSWORD: 'Director@123',
    INST_NAME: 'Greenwood High School', INST_LEGAL_NAME: 'Greenwood High School Society', INST_CODE: 'GHS', INST_EMAIL_DOMAIN: 'greenwoodhigh.com',
    ADMIN_EMAIL: 'admin@greenwoodhigh.com', ADMIN_NAME: 'Anita Verma', ADMIN_PASSWORD: 'Admin@123',
    TEACHER_EMAIL: 'teacher@greenwoodhigh.com', TEACHER_NAME: 'Rahul Sharma', TEACHER_PASSWORD: 'Teacher@123',
    STUDENT_EMAIL: 'student@greenwoodhigh.com', STUDENT_NAME: 'Arjun Kumar', STUDENT_PASSWORD: 'Student@123'
  };
  Object.entries(defaults).forEach(([k,v]) => { if (STORE[k] === undefined) STORE[k] = v; });
  saveStore();
}

function authResult(actor, ok, message) {
  const el = document.getElementById('auth-result');
  if (!el) return;
  el.className = 'auth-result ' + (ok ? 'success' : 'error');
  el.textContent = message;
}

async function loginAs(actorKey) {
  const a = ACTORS[actorKey];
  if (!a) return;
  const email = STORE[a.email] || '';
  const password = STORE[a.password] || '';
  if (!email || !password) { authResult(actorKey, false, 'Set ' + a.email + ' and ' + a.password + ' in Environment.'); return; }
  const base = STORE.API_BASE_URL || 'http://127.0.0.1:8001';
  const headers = {'Content-Type':'application/json'};
  if (a.host && STORE[a.host]) headers.Host = STORE[a.host] + '.localhost';
  authResult(actorKey, true, 'Signing in as ' + a.label + '…');
  try {
    const r = await fetch(base + '/api/auth/login', {method:'POST', headers, body:JSON.stringify({email,password})});
    const text = await r.text();
    let data = {}; try { data = JSON.parse(text); } catch(e) {}
    if (!r.ok) { authResult(actorKey, false, (data.detail || data.message || 'Login failed') + ' (' + r.status + ')'); return; }
    if (data.access_token) STORE[a.token] = data.access_token;
    if (data.refresh_token) STORE[a.refresh] = data.refresh_token;
    if (data.user?.id) STORE[actorKey.toUpperCase() + '_ID'] = String(data.user.id);
    saveStore();
    renderEnvRail('store-panel');
    renderAuthBar();
    authResult(actorKey, true, '✓ ' + a.label + ' logged in — fresh access token stored.');
  } catch (e) { authResult(actorKey, false, 'Cannot reach backend at ' + base); }
}

async function refreshAs(actorKey) {
  const a = ACTORS[actorKey];
  const refresh = STORE[a.refresh];
  if (!refresh) { authResult(actorKey, false, 'No refresh token available. Use Login / Re-login.'); return; }
  const base = STORE.API_BASE_URL || 'http://127.0.0.1:8001';
  try {
    const r = await fetch(base + '/api/auth/refresh', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({refresh_token:refresh})});
    const data = await r.json().catch(()=>({}));
    if (!r.ok) { authResult(actorKey, false, 'Refresh failed (' + r.status + '). Use Login / Re-login.'); return; }
    if (data.access_token) STORE[a.token] = data.access_token;
    if (data.refresh_token) STORE[a.refresh] = data.refresh_token;
    saveStore(); renderEnvRail('store-panel'); renderAuthBar();
    authResult(actorKey, true, '✓ Fresh access token stored.');
  } catch(e) { authResult(actorKey, false, 'Refresh request failed.'); }
}

function updateQuickLoginField(actorKey, fieldKey, value) {
  const a = ACTORS[actorKey];
  if (!a) return;
  STORE[a[fieldKey]] = value;
  saveStore();
}

function renderAuthBar() {
  let bar = document.getElementById('global-auth-bar');
  if (!bar) return;
  const current = bar.querySelector('#actor-select')?.value || 'platform';
  const a = ACTORS[current];
  const hasToken = !!STORE[a.token];
  const hasRefresh = !!STORE[a.refresh];
  const email = STORE[a.email] || '';
  const password = STORE[a.password] || '';
  bar.innerHTML = `
    <div class="auth-left">
      <div class="eyebrow">SESSION</div>
      <div class="auth-title">Quick login</div>
      <select id="actor-select" class="actor-select" onchange="renderAuthBar()">
        ${Object.entries(ACTORS).map(([k,x]) => `<option value="${k}" ${k===current?'selected':''}>${x.label}</option>`).join('')}
      </select>
      <span class="session-chip ${hasToken?'live':''}">${hasToken?'● token ready':'○ not logged in'}</span>
    </div>
    <div class="auth-credentials">
      <input id="quick-login-email" class="quick-login-input" type="text" value="${esc(email)}" placeholder="Username / email" autocomplete="off"
        oninput="updateQuickLoginField('${current}','email',this.value)" title="Username / email">
      <input id="quick-login-password" class="quick-login-input password" type="password" value="${esc(password)}" placeholder="Password" autocomplete="off"
        oninput="updateQuickLoginField('${current}','password',this.value)" title="Password">
    </div>
    <div class="auth-details">
      ${a.host ? `<span>Host: ${esc(STORE[a.host] || 'CLIENT_SLUG not set')}.localhost</span>` : '<span>Platform scope</span>'}
    </div>
    <div class="auth-actions">
      ${hasRefresh ? `<button class="btn btn-secondary" onclick="refreshAs('${current}')">Refresh</button>` : ''}
      <button class="btn btn-primary" onclick="loginAs('${current}')">${hasToken?'Re-login / Fresh token':'Login'}</button>
    </div>
    <div id="auth-result" class="auth-result"></div>`;
}

function injectAuthBar() {
  if (document.getElementById('global-auth-bar')) return;
  const header = document.querySelector('.header');
  if (!header) return;
  const bar = document.createElement('section');
  bar.id = 'global-auth-bar';
  bar.className = 'global-auth-bar';
  header.insertAdjacentElement('afterend', bar);
  renderAuthBar();
}

function injectEnvRail() {
  const panel = document.getElementById('store-panel');
  if (panel) { panel.classList.add('env-rail'); renderEnvRail('store-panel'); return; }
  const layout = document.querySelector('.layout');
  if (!layout) return;
  const rail = document.createElement('aside');
  rail.id = 'store-panel'; rail.className = 'env-rail';
  layout.insertBefore(rail, layout.firstChild);
  renderEnvRail('store-panel');
}

function initFlowShell() {
  // Defaults are intentionally only seeded on first visit. User edits always win.
  setDefaults();
  injectAuthBar();
  injectEnvRail();
}

function prepareScenario() {
  const get = id => document.getElementById(id)?.value.trim();
  const client = get('wiz-client-name') || 'Greenwood';
  const slug = get('wiz-client-slug') || client.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const directorEmail = get('wiz-director-email') || ('director@' + slug + '.com');
  const directorPassword = get('wiz-director-password') || 'Director@123';
  const inst = get('wiz-inst-name') || (client + ' High School');
  const code = get('wiz-inst-code') || slug.slice(0,3).toUpperCase();
  const domain = directorEmail.split('@')[1] || (slug + '.com');
  Object.assign(STORE, {
    CLIENT_DISPLAY_NAME: client, CLIENT_SLUG: slug,
    DIRECTOR_EMAIL: directorEmail, DIRECTOR_PASSWORD: directorPassword,
    INST_NAME: inst, INST_LEGAL_NAME: inst + ' Society', INST_CODE: code, INST_EMAIL_DOMAIN: domain,
    ADMIN_EMAIL: 'admin@' + domain, ADMIN_NAME: 'Institute Admin', ADMIN_PASSWORD: 'Admin@123',
    TEACHER_EMAIL: 'teacher@' + domain, TEACHER_NAME: 'Teacher User', TEACHER_PASSWORD: 'Teacher@123',
    STUDENT_EMAIL: 'student@' + domain, STUDENT_NAME: 'Student User', STUDENT_PASSWORD: 'Student@123'
  });
  saveStore();
  closeWizard();
  renderEnvRail('store-panel');
  renderAuthBar();
  const status = document.getElementById('setup-status');
  if (status) status.textContent = 'Test data prepared. Flow steps will now use these values.';
}

function openWizard() { document.getElementById('setup-wizard')?.classList.add('open'); }
function closeWizard() { document.getElementById('setup-wizard')?.classList.remove('open'); }



// Run one API step from the flow definition.
async function runStep(step, resultElId) {
  const resultEl = document.getElementById(resultElId);
  if (!resultEl) return;
  resultEl.innerHTML = '<em>Running…</em>';
  const url = substitute(step.url);
  const headers = {};
  for (const [k,v] of Object.entries(step.headers || {})) headers[k] = substitute(v);
  const body = step.body ? substitute(step.body) : undefined;
  try {
    const opts = {method:step.method, headers};
    if (body && step.method !== 'GET' && step.method !== 'DELETE') opts.body = body;
    const resp = await fetch(url, opts);
    const text = await resp.text();
    let data = null; try { data = JSON.parse(text); } catch(e) {}
    const statusClass = resp.ok ? 'api-ok' : 'api-error';
    let html = `<div class="request-line">→ ${esc(step.method)} ${esc(url)}</div>`;
    html += `<div class="response-status ${statusClass}">← ${resp.status} ${esc(resp.statusText)}</div>`;
    html += `<pre class="response-json">${esc(data ? prettyJson(data) : text)}</pre>`;
    if (resp.ok && step.extractions) {
      const resolved = step.extractions.map(ext => ({var:ext.var, path:substitute(ext.path)}));
      applyExtractions(data || {}, resolved);
      html += `<div class="extract-ok">✓ Stored: ${resolved.map(x=>esc(x.var)).join(', ')}</div>`;
    }
    if (resp.ok && step.fetchLookups?.length) {
      const token = data?.access_token || STORE.PLATFORM_TOKEN || STORE.TOKEN || '';
      try { await fetchLookups(token, step.fetchLookups); html += `<div class="extract-ok">✓ Lookups cached: ${step.fetchLookups.join(', ')}</div>`; } catch(e) {}
    }
    resultEl.innerHTML = html;
  } catch(e) {
    resultEl.innerHTML = `<div class="api-error">✕ ${esc(e.message)}</div><div class="result-help">Is the backend running at ${esc(STORE.API_BASE_URL || 'http://127.0.0.1:8001')}?</div>`;
  }
  renderEnvRail('store-panel');
  renderAuthBar();
}

// Existing flow runner is kept deliberately simple; only the shell around it is redesigned.

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFlowShell);
else initFlowShell();
