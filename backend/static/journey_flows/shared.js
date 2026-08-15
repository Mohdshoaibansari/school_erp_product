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

// Helper: HTML escape string to prevent injection and rendering errors
function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Helper: Mask sensitive keys in environment variable rails
function maskValue(key, val) {
  if (!val) return '';
  if (/TOKEN|PASSWORD|SECRET|KEY/i.test(key)) {
    return val.length > 8 ? val.slice(0, 4) + '…' + val.slice(-4) : '••••••••';
  }
  return val;
}

// Backwards compatibility for older flow pages calling injectEnvRail()
function injectEnvRail(elementId = 'store-panel') {
  renderEnvRail(elementId);
  renderDebugDrawer();
}

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
  const base = (STORE.API_BASE_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');
  for (const surface of surfaces) {
    if (!force && LOOKUP_CACHE[surface] && LOOKUP_CACHE[surface].length > 0) {
      results[surface] = LOOKUP_CACHE[surface];
      continue;
    }
    const url = base + '/api/v1/lookups/' + surface;
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
// ---------------------------------------------------------------------------
// Test console shell — scenario-driven state + lightweight auth/context UI.
// The flow HTML remains the API source of truth; this layer only prepares and
// selects local test context for those existing flows.
// ---------------------------------------------------------------------------

const ACTORS = {
  platform: { label: 'Platform Owner', token: 'PLATFORM_TOKEN', refresh: 'PLATFORM_REFRESH_TOKEN', email: 'PLATFORM_EMAIL', password: 'PLATFORM_PASSWORD', host: '' },
  director: { label: 'Client Director', token: 'DIRECTOR_TOKEN', refresh: 'DIRECTOR_REFRESH_TOKEN', email: 'DIRECTOR_EMAIL', password: 'DIRECTOR_PASSWORD', host: 'CLIENT_SLUG' },
  admin: { label: 'Institute Admin', token: 'ADMIN_TOKEN', refresh: 'ADMIN_REFRESH_TOKEN', email: 'ADMIN_EMAIL', password: 'ADMIN_PASSWORD', host: 'CLIENT_SLUG' },
  teacher: { label: 'Teacher', token: 'TEACHER_TOKEN', refresh: 'TEACHER_REFRESH_TOKEN', email: 'TEACHER_EMAIL', password: 'TEACHER_PASSWORD', host: 'CLIENT_SLUG' },
  student: { label: 'Student', token: 'STUDENT_TOKEN', refresh: 'STUDENT_REFRESH_TOKEN', email: 'STUDENT_EMAIL', password: 'STUDENT_PASSWORD', host: 'CLIENT_SLUG' },
  parent: { label: 'Parent', token: 'PARENT_TOKEN', refresh: 'PARENT_REFRESH_TOKEN', email: 'PARENT_EMAIL', password: 'PARENT_PASSWORD', host: 'CLIENT_SLUG' },
  principal: { label: 'Principal', token: 'PRINCIPAL_TOKEN', refresh: 'PRINCIPAL_REFRESH_TOKEN', email: 'PRINCIPAL_EMAIL', password: 'PRINCIPAL_PASSWORD', host: 'CLIENT_SLUG' },
  hod: { label: 'HOD', token: 'HOD_TOKEN', refresh: 'HOD_REFRESH_TOKEN', email: 'HOD_EMAIL', password: 'HOD_PASSWORD', host: 'CLIENT_SLUG' },
  staff: { label: 'Staff', token: 'STAFF_TOKEN', refresh: 'STAFF_REFRESH_TOKEN', email: 'STAFF_EMAIL', password: 'STAFF_PASSWORD', host: 'CLIENT_SLUG' }
};

const ROLE_PASSWORDS = {
  director: 'Director@123', admin: 'Admin@123', teacher: 'Teacher@123',
  student: 'Student@123', parent: 'Parent@123', principal: 'Principal@123',
  hod: 'HOD@123', staff: 'Staff@123'
};

const SCENARIO_KEY = 'journey_flow_scenarios';
const ACTIVE_SCENARIO_KEY = 'journey_flow_active_scenario';
const ACTIVE_INSTITUTION_KEY = 'journey_flow_active_institution';
const ACTIVE_ACTOR_KEY = 'journey_flow_active_actor';

function getScenarios() {
  try { return JSON.parse(localStorage.getItem(SCENARIO_KEY) || '[]'); } catch (e) { return []; }
}
function saveScenarios(items) { localStorage.setItem(SCENARIO_KEY, JSON.stringify(items)); }
function activeScenarioId() { return localStorage.getItem(ACTIVE_SCENARIO_KEY) || ''; }
function activeInstitutionId() { return localStorage.getItem(ACTIVE_INSTITUTION_KEY) || ''; }
function activeActor() { return localStorage.getItem(ACTIVE_ACTOR_KEY) || 'platform'; }
function setActiveScenario(id) { localStorage.setItem(ACTIVE_SCENARIO_KEY, id || ''); }
function setActiveInstitution(id) { localStorage.setItem(ACTIVE_INSTITUTION_KEY, id || ''); }
function setActiveActor(id) { localStorage.setItem(ACTIVE_ACTOR_KEY, id || 'platform'); }

function currentScenario() {
  return getScenarios().find(s => s.id === activeScenarioId()) || null;
}
function currentInstitution() {
  const s = currentScenario();
  return s?.institutions?.find(i => i.id === activeInstitutionId()) || null;
}
function scenarioId(prefix='s') { return prefix + Date.now().toString(36) + Math.random().toString(36).slice(2,6); }
function slugify(v) { return String(v || '').toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,''); }
function emailDomain(slug) { return slugify(slug) + '.test'; }

function seedScenarioContext(scenario, institutionId) {
  if (!scenario) return;
  const inst = scenario.institutions?.find(i => i.id === (institutionId || activeInstitutionId())) || scenario.institutions?.[0] || null;
  const d = scenario.director;
  const vars = {
    CLIENT_DISPLAY_NAME: scenario.client.name,
    CLIENT_SLUG: scenario.client.slug,
    DIRECTOR_EMAIL: d.email,
    DIRECTOR_NAME: d.name,
    DIRECTOR_PASSWORD: d.password
  };
  if (inst) {
    Object.assign(vars, {
      INST_ID: inst.backendId || STORE.INST_ID || '',
      INST_NAME: inst.name,
      INST_LEGAL_NAME: inst.name + ' Society',
      INST_CODE: inst.code,
      INST_EMAIL_DOMAIN: inst.domain,
      ADMIN_EMAIL: inst.users.admin.email,
      ADMIN_NAME: inst.users.admin.name,
      ADMIN_PASSWORD: inst.users.admin.password,
      TEACHER_EMAIL: inst.users.teacher.email,
      TEACHER_NAME: inst.users.teacher.name,
      TEACHER_PASSWORD: inst.users.teacher.password,
      STUDENT_EMAIL: inst.users.student.email,
      STUDENT_NAME: inst.users.student.name,
      STUDENT_PASSWORD: inst.users.student.password,
      PARENT_EMAIL: inst.users.parent.email,
      PARENT_NAME: inst.users.parent.name,
      PARENT_PASSWORD: inst.users.parent.password,
      PRINCIPAL_EMAIL: inst.users.principal.email,
      PRINCIPAL_NAME: inst.users.principal.name,
      PRINCIPAL_PASSWORD: inst.users.principal.password,
      HOD_EMAIL: inst.users.hod.email,
      HOD_NAME: inst.users.hod.name,
      HOD_PASSWORD: inst.users.hod.password,
      STAFF_EMAIL: inst.users.staff.email,
      STAFF_NAME: inst.users.staff.name,
      STAFF_PASSWORD: inst.users.staff.password
    });
    setActiveInstitution(inst.id);
  }
  Object.entries(vars).forEach(([k,v]) => { if (v !== undefined && v !== null && v !== '') STORE[k] = String(v); });
  saveStore();
}

function createScenario(clientName, bootstrapMode) {
  const name = clientName.trim();
  if (!name) { alert('Enter a client name.'); return; }
  const slug = slugify(name);
  const domain = emailDomain(slug);
  const directorEmail = `director@${domain}`;
  const scenario = {
    id: scenarioId(), name,
    createdAt: new Date().toISOString(),
    status: bootstrapMode ? 'bootstrap-ready' : 'prepared',
    bootstrapMode: !!bootstrapMode,
    client: { name, slug },
    director: { name: 'Test Director', email: directorEmail, password: ROLE_PASSWORDS.director },
    institutions: []
  };
  if (bootstrapMode) {
    const instName = name + ' School';
    const instSlug = slugify(instName);
    const instDomain = emailDomain(slug + '-school');
    const mk = role => ({ name: role === 'admin' ? 'Institute Admin' : role[0].toUpperCase()+role.slice(1)+' User', email: `${role}@${instDomain}`, password: ROLE_PASSWORDS[role] });
    scenario.institutions.push({ id: scenarioId('i'), name: instName, type: 'School', code: slug.split('-').map(x=>x[0]).join('').slice(0,5).toUpperCase() || 'SCH', domain: instDomain, backendId:'', status:'prepared', users:{admin:mk('admin'),teacher:mk('teacher'),student:mk('student'),parent:mk('parent'),principal:mk('principal'),hod:mk('hod'),staff:mk('staff')} });
  }
  const scenarios = getScenarios(); scenarios.push(scenario); saveScenarios(scenarios);
  setActiveScenario(scenario.id); setActiveInstitution(''); setActiveActor('director');
  seedScenarioContext(scenario);
  renderScenarioShell();
  closeScenarioWizard();
  showToast(bootstrapMode ? 'Scenario prepared for standard happy-path bootstrap.' : 'Scenario prepared. Create an institution when you are ready.');
}

function createInstitutionFromScenario(name, type) {
  const s = currentScenario();
  if (!s) { alert('Create or select a scenario first.'); return; }
  const n = name.trim(); if (!n) { alert('Enter an institution name.'); return; }
  const slug = slugify(n);
  const code = slug.split('-').map(x=>x[0]).join('').slice(0,5).toUpperCase() || 'INST';
  const domain = emailDomain(s.client.slug + '-' + slug);
  const id = scenarioId('i');
  const mk = role => ({ name: role === 'admin' ? 'Institute Admin' : role[0].toUpperCase()+role.slice(1)+' User', email: `${role}@${domain}`, password: ROLE_PASSWORDS[role] });
  const inst = { id, name:n, type:type || 'School', code, domain, backendId:'', status:'prepared', users:{admin:mk('admin'),teacher:mk('teacher'),student:mk('student'),parent:mk('parent'),principal:mk('principal'),hod:mk('hod'),staff:mk('staff')} };
  const scenarios = getScenarios(); const target = scenarios.find(x=>x.id===s.id);
  target.institutions = target.institutions || []; target.institutions.push(inst); saveScenarios(scenarios);
  setActiveInstitution(id); seedScenarioContext(target,id); renderScenarioShell(); closeInstitutionModal();
  showToast(`${n} prepared under ${target.client.name}.`);
}

function deleteScenarioLocal(id) {
  const s = getScenarios().find(x=>x.id===id);
  if (!s || !confirm(`Delete local scenario “${s.name}”? Backend data will not be changed.`)) return;
  const remaining=getScenarios().filter(x=>x.id!==id); saveScenarios(remaining);
  if (activeScenarioId()===id) {
    const next=remaining[0];
    if(next){ setActiveScenario(next.id); setActiveInstitution(next.institutions?.[0]?.id || ''); setActiveActor('director'); seedScenarioContext(next); }
    else { setActiveScenario(''); setActiveInstitution(''); setActiveActor('platform'); clearNonPlatformContext(); }
  }
  renderScenarioShell();
}
function clearNonPlatformContext() {
  const keep = new Set(['API_BASE_URL','PLATFORM_EMAIL','PLATFORM_PASSWORD','PLATFORM_TOKEN','PLATFORM_REFRESH_TOKEN','PLATFORM_USER_ID']);
  Object.keys(STORE).forEach(k=>{ if(!keep.has(k)) delete STORE[k]; }); saveStore();
}

function selectScenario(id) {
  const s = getScenarios().find(x=>x.id===id); if (!s) return;
  setActiveScenario(id); setActiveInstitution(s.institutions?.[0]?.id || '');
  seedScenarioContext(s); renderScenarioShell(); maybeAutoLogin();
}
function selectInstitution(id) {
  const s=currentScenario(); if(!s) return;
  setActiveInstitution(id); seedScenarioContext(s,id); renderScenarioShell(); maybeAutoLogin();
}
function selectActor(id) { setActiveActor(id); renderScenarioShell(); maybeAutoLogin(); }

function hasToken(actorKey) { const a=ACTORS[actorKey]; return !!(a && STORE[a.token]); }
function maybeAutoLogin() {
  const actor=activeActor();
  if (hasToken(actor)) return;
  const a=ACTORS[actor]; if (a && STORE[a.email] && STORE[a.password]) loginAs(actor, true);
}

function updateIndicator() {
  const ind=document.getElementById('store-indicator'); if(ind) ind.textContent=Object.keys(STORE).length+' vars';
}
function renderEnvRail(elementId) {
  const el=document.getElementById(elementId); if(!el) return;
  const rows=Object.entries(STORE).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>`<div class="env-row"><div class="env-key" title="${esc(k)}">${esc(k)}</div><div class="env-value" title="${esc(v)}">${esc(maskValue(k,v))}</div><button class="icon-btn danger" title="Remove ${esc(k)}" onclick="removeEnvVar('${esc(k)}')">×</button></div>`).join('');
  el.innerHTML=`<div class="rail-head"><div><div class="eyebrow">DEBUG</div><h3>Environment</h3></div><span class="count-pill">${Object.keys(STORE).length}</span></div><div class="env-add"><input id="env-key-input" placeholder="KEY_NAME"><input id="env-value-input" placeholder="value"><button class="btn btn-small" onclick="addEnvVar('env-key-input','env-value-input')">Add</button></div><div class="env-list">${rows||'<div class="empty-state">No runtime variables yet.</div>'}</div><div class="rail-footer"><button class="btn btn-ghost" onclick="confirmReset()">Reset all</button><span>localStorage</span></div>`;
  updateIndicator();
}
function renderStorePanel(elementId){ renderEnvRail(elementId); }
function addEnvVar(keyId='env-key-input', valId='env-value-input'){
  const kEl=document.getElementById(keyId)||document.getElementById('env-key-input');
  const vEl=document.getElementById(valId)||document.getElementById('env-value-input');
  const key=(kEl?.value||'').trim().toUpperCase();
  if(!/^[A-Z_][A-Z0-9_]*$/.test(key)){alert('Use an ENV-style key, e.g. CLIENT_SLUG');return;}
  STORE[key]=vEl?.value??'';saveStore();renderEnvRail('store-panel');renderDebugDrawer();
}
function removeEnvVar(key){ if(!confirm('Remove '+key+'?'))return; delete STORE[key];saveStore();renderEnvRail('store-panel');renderDebugDrawer(); }
function confirmReset(){ if(confirm('Reset all local test variables, scenarios and cached lookups?')) clearStore(); }
function clearStore(){ Object.keys(STORE).forEach(k=>delete STORE[k]); localStorage.removeItem('journey_flow_store');localStorage.removeItem(SCENARIO_KEY);localStorage.removeItem(ACTIVE_SCENARIO_KEY);localStorage.removeItem(ACTIVE_INSTITUTION_KEY);localStorage.removeItem(ACTIVE_ACTOR_KEY);Object.keys(LOOKUP_CACHE).forEach(k=>delete LOOKUP_CACHE[k]);localStorage.removeItem('journey_flow_lookups');location.reload(); }

function setDefaults(){
  const defaults={API_BASE_URL:'http://127.0.0.1:8001',PLATFORM_EMAIL:'admin@school-erp.com',PLATFORM_PASSWORD:'Shoby@123'};
  Object.entries(defaults).forEach(([k,v])=>{if(STORE[k]===undefined)STORE[k]=v;}); saveStore();
  // One-time cleanup of the old Greenwood seed so only Platform Owner remains hardcoded.
  if(!localStorage.getItem('journey_flow_v3_migrated')){
    const legacy=['CLIENT_DISPLAY_NAME','CLIENT_SLUG','DIRECTOR_EMAIL','DIRECTOR_PASSWORD','INST_NAME','INST_LEGAL_NAME','INST_CODE','INST_EMAIL_DOMAIN','ADMIN_EMAIL','ADMIN_NAME','ADMIN_PASSWORD','TEACHER_EMAIL','TEACHER_NAME','TEACHER_PASSWORD','STUDENT_EMAIL','STUDENT_NAME','STUDENT_PASSWORD'];
    if(!getScenarios().length) legacy.forEach(k=>delete STORE[k]);
    localStorage.setItem('journey_flow_v3_migrated','1'); saveStore();
  }
}

function authResult(actor,ok,message){ const el=document.getElementById('auth-result'); if(el){el.className='auth-result '+(ok?'success':'error');el.textContent=message;} }
async function loginAs(actorKey,silent=false){
  const a=ACTORS[actorKey]; if(!a)return;
  if(actorKey!=='platform'){ const s=currentScenario(); if(!s){if(!silent)authResult(actorKey,false,'Create/select a scenario first.');return;} seedScenarioContext(s,activeInstitutionId()); }
  const email=STORE[a.email]||'',password=STORE[a.password]||'';
  if(!email||!password){if(!silent)authResult(actorKey,false,'Set '+a.email+' and '+a.password+' in Environment.');return;}
  const base=STORE.API_BASE_URL||'http://127.0.0.1:8001'; const headers={'Content-Type':'application/json'}; if(a.host&&STORE[a.host])headers.Host=STORE[a.host]+'.localhost';
  if(!silent)authResult(actorKey,true,'Signing in as '+a.label+'…');
  try{const r=await fetch(base+'/api/auth/login',{method:'POST',headers,body:JSON.stringify({email,password})});const text=await r.text();let data={};try{data=JSON.parse(text)}catch(e){};if(!r.ok){if(!silent)authResult(actorKey,false,(data.detail||data.message||'Login failed')+' ('+r.status+')');return;}if(data.access_token)STORE[a.token]=data.access_token;if(data.refresh_token)STORE[a.refresh]=data.refresh_token;if(data.user?.id)STORE[actorKey.toUpperCase()+'_ID']=String(data.user.id);saveStore();renderEnvRail('store-panel');renderScenarioShell();if(!silent)authResult(actorKey,true,'✓ '+a.label+' logged in — fresh access token stored.');}catch(e){if(!silent)authResult(actorKey,false,'Cannot reach backend at '+base);}
}
async function refreshAs(actorKey){ const a=ACTORS[actorKey],refresh=STORE[a?.refresh]; if(!refresh){authResult(actorKey,false,'No refresh token available. Use Login / Re-login.');return;} const base=STORE.API_BASE_URL||'http://127.0.0.1:8001';try{const r=await fetch(base+'/api/auth/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:refresh})});const data=await r.json().catch(()=>({}));if(!r.ok){authResult(actorKey,false,'Refresh failed ('+r.status+'). Use Login / Re-login.');return;}if(data.access_token)STORE[a.token]=data.access_token;if(data.refresh_token)STORE[a.refresh]=data.refresh_token;saveStore();renderEnvRail('store-panel');renderScenarioShell();authResult(actorKey,true,'✓ Fresh access token stored.');}catch(e){authResult(actorKey,false,'Refresh request failed.');} }
function updateQuickLoginField(actorKey,fieldKey,value){const a=ACTORS[actorKey];if(!a)return;STORE[a[fieldKey]]=value;saveStore();}

function renderContextBar(){
  let el=document.getElementById('test-context-bar'); if(!el)return;
  const scenarios=getScenarios(),s=currentScenario(),inst=currentInstitution(),actor=activeActor(),a=ACTORS[actor],token=!!STORE[a?.token];
  el.innerHTML=`<div class="context-group"><span class="context-label">SCENARIO</span><select onchange="selectScenario(this.value)"><option value="">${scenarios.length?'Select scenario':'No scenarios yet'}</option>${scenarios.map(x=>`<option value="${x.id}" ${x.id===s?.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select><button class="context-add" onclick="openScenarioWizard()">+ New</button>${s?`<button class="context-delete" title="Delete local scenario" onclick="deleteScenarioLocal('${s.id}')">×</button>`:''}</div><div class="context-group"><span class="context-label">INSTITUTION</span><select ${!s?'disabled':''} onchange="selectInstitution(this.value)"><option value="">${s?(s.institutions?.length?'Select institution':'No institutions yet'):'Select scenario first'}</option>${(s?.institutions||[]).map(x=>`<option value="${x.id}" ${x.id===inst?.id?'selected':''}>${esc(x.name)} · ${esc(x.type)}</option>`).join('')}</select>${s?`<button class="context-add" onclick="openInstitutionModal()">+ New</button>`:''}</div><div class="context-group"><span class="context-label">ACTOR</span><select onchange="selectActor(this.value)">${Object.entries(ACTORS).map(([k,x])=>`<option value="${k}" ${k===actor?'selected':''}>${x.label}</option>`).join('')}</select></div><div class="context-status ${token?'ready':''}">${token?'● Token ready':'○ No token'}</div><div class="context-auth"><button class="btn btn-secondary btn-small" onclick="openQuickLogin()">Quick Login</button><button class="btn btn-ghost btn-small" onclick="toggleDebugDrawer()">ENV / Debug</button></div>`;
}

function openQuickLogin(){ document.getElementById('quick-login-drawer')?.classList.add('open'); renderQuickLoginDrawer(); }
function renderQuickLoginDrawer(){ const el=document.getElementById('quick-login-drawer');if(!el)return;const actor=activeActor(),a=ACTORS[actor],email=STORE[a.email]||'',pw=STORE[a.password]||'',token=!!STORE[a.token];el.innerHTML=`<div class="drawer-head"><div><div class="eyebrow">SESSION</div><h3>${a.label}</h3></div><button class="icon-btn" onclick="closeQuickLogin()">×</button></div><div class="drawer-note">Credentials are editable. Defaults are generated by the active scenario; Platform Owner remains the only hardcoded account.</div><label>Username / email<input value="${esc(email)}" oninput="updateQuickLoginField('${actor}','email',this.value)"></label><label>Password<input type="password" value="${esc(pw)}" oninput="updateQuickLoginField('${actor}','password',this.value)"></label><div class="drawer-actions"><button class="btn btn-secondary" ${token?'':'disabled'} onclick="refreshAs('${actor}')">Refresh token</button><button class="btn btn-primary" onclick="loginAs('${actor}')">${token?'Re-login / Fresh token':'Login'}</button></div><div id="auth-result" class="auth-result"></div>`;}
function closeQuickLogin(){document.getElementById('quick-login-drawer')?.classList.remove('open');}
function renderScenarioShell(){ renderContextBar(); renderQuickLoginDrawer(); updateIndicator(); }
function toggleDebugDrawer(){ document.getElementById('debug-drawer')?.classList.toggle('open'); }
function injectShell(){
  const header=document.querySelector('.header');
  if(header&&!document.getElementById('test-context-bar')){const bar=document.createElement('div');bar.id='test-context-bar';bar.className='test-context-bar';header.insertAdjacentElement('afterend',bar);}
  if(!document.getElementById('quick-login-drawer')){const d=document.createElement('aside');d.id='quick-login-drawer';d.className='side-drawer';document.body.appendChild(d);}
  if(!document.getElementById('debug-drawer')){const d=document.createElement('aside');d.id='debug-drawer';d.className='debug-drawer';d.innerHTML='<div class="drawer-head"><div><div class="eyebrow">DEBUG</div><h3>Environment</h3></div><button class="icon-btn" onclick="toggleDebugDrawer()">×</button></div><div id="debug-env-content"></div>';document.body.appendChild(d);}
  if(!document.getElementById('scenario-wizard')){document.body.insertAdjacentHTML('beforeend',`<div id="scenario-wizard" class="wizard-backdrop"><div class="wizard wizard-small"><div class="wizard-head"><div><div class="eyebrow">NEW TEST CONTEXT</div><h3>Create scenario</h3><p>Only enter the client name. Director credentials and downstream identities are generated automatically.</p></div><button class="wizard-close" onclick="closeScenarioWizard()">×</button></div><div class="field"><label>Client name</label><input id="wiz-client-name" placeholder="e.g. Sunrise Education"></div><div class="bootstrap-choice"><label class="choice"><input type="radio" name="bootstrap-mode" value="prepare" checked><span><strong>Prepare data only</strong><small>Create local test data without calling the backend.</small></span></label><label class="choice"><input type="radio" name="bootstrap-mode" value="bootstrap"><span><strong>Bootstrap complete happy path</strong><small>Prepare the standard Client → Director → Institution → Users journey.</small></span></label></div><div class="wizard-actions"><button class="btn btn-secondary" onclick="closeScenarioWizard()">Cancel</button><button class="btn btn-primary" onclick="submitScenarioWizard()">Create scenario</button></div></div></div>`);}
  if(!document.getElementById('institution-modal')){document.body.insertAdjacentHTML('beforeend',`<div id="institution-modal" class="wizard-backdrop"><div class="wizard wizard-small"><div class="wizard-head"><div><div class="eyebrow">ACTIVE CLIENT</div><h3>Create institution</h3><p>The new institution becomes active automatically.</p></div><button class="wizard-close" onclick="closeInstitutionModal()">×</button></div><div class="field"><label>Institution name</label><input id="wiz-inst-name" placeholder="e.g. Sunrise College"></div><div class="field"><label>Institution type</label><select id="wiz-inst-type"><option>School</option><option>College</option><option>University</option><option>Institute</option></select></div><div class="wizard-actions"><button class="btn btn-secondary" onclick="closeInstitutionModal()">Cancel</button><button class="btn btn-primary" onclick="submitInstitution()">Prepare institution</button></div></div></div>`);}
}
function renderDebugDrawer(){ const el=document.getElementById('debug-env-content');if(!el)return; const rows=Object.entries(STORE).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>`<div class="env-row"><div class="env-key">${esc(k)}</div><div class="env-value">${esc(maskValue(k,v))}</div><button class="icon-btn danger" onclick="removeEnvVar('${esc(k)}')">×</button></div>`).join('');el.innerHTML=`<div class="env-add"><input id="debug-env-key-input" placeholder="KEY_NAME"><input id="debug-env-value-input" placeholder="value"><button class="btn btn-small" onclick="addEnvVar('debug-env-key-input','debug-env-value-input')">Add</button></div><div class="env-list">${rows||'<div class="empty-state">No variables.</div>'}</div><div class="rail-footer"><button class="btn btn-ghost" onclick="confirmReset()">Reset all</button><span>${Object.keys(STORE).length} vars</span></div>`;}
function openScenarioWizard(){document.getElementById('scenario-wizard')?.classList.add('open');document.getElementById('wiz-client-name')?.focus();}
function closeScenarioWizard(){document.getElementById('scenario-wizard')?.classList.remove('open');}
function openInstitutionModal(){if(!currentScenario()){alert('Create/select a scenario first.');return;}document.getElementById('institution-modal')?.classList.add('open');document.getElementById('wiz-inst-name')?.focus();}
function closeInstitutionModal(){document.getElementById('institution-modal')?.classList.remove('open');}
function submitScenarioWizard(){const name=document.getElementById('wiz-client-name')?.value||'';const mode=document.querySelector('input[name="bootstrap-mode"]:checked')?.value==='bootstrap';createScenario(name,mode);}
function submitInstitution(){createInstitutionFromScenario(document.getElementById('wiz-inst-name')?.value||'',document.getElementById('wiz-inst-type')?.value||'School');}
function showToast(message){let t=document.getElementById('test-toast');if(!t){t=document.createElement('div');t.id='test-toast';document.body.appendChild(t);}t.textContent=message;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2800);}

function initFlowShell(){ setDefaults(); injectShell(); renderScenarioShell(); renderEnvRail('store-panel'); renderDebugDrawer(); }

// Backwards-compatible names used by the previous launcher markup.
function openWizard(){openScenarioWizard();}
function closeWizard(){closeScenarioWizard();}
function prepareScenario(){submitScenarioWizard();}

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
  renderScenarioShell();
}

// Existing flow runner is kept deliberately simple; only the shell around it is redesigned.

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFlowShell);
else initFlowShell();
