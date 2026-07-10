// Proxy pool manager for the AN miner fleet.
// Scrapes free HTTP proxies from public sources, then VALIDATES each one by
// tunneling a real HTTPS request (CONNECT) to the Acki Nacki mainnet endpoint.
// Only proxies that actually reach that host are kept, sorted by latency, in
// proxies_live.json. If fleet.txt exists (one wallet name per line) it also
// assigns a DISTINCT sticky proxy to each wallet in assignments.json and only
// rotates a wallet's proxy when its current one dies.
// Free proxies are short-lived, so sources are re-scraped and the live pool is
// re-validated continuously.
//
// Run:  node proxy_pool.mjs
// Output files (same dir): proxies_live.json, assignments.json

import { writeFile, rename } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import { request, ProxyAgent } from 'undici';

const __dir = dirname(fileURLToPath(import.meta.url));

// ---------------- config ----------------
const TEST_URL         = 'https://mainnet.ackinacki.org/'; // the host miners talk to
const VALIDATE_TIMEOUT = 7000;       // ms allowed per proxy check
const VALIDATE_CONC    = 120;        // concurrent checks
const MIN_LIVE_WARN    = 10;         // warn if fewer live than this
const REFRESH_MS       = 30 * 60000; // re-scrape sources every 30 min
const REVALIDATE_MS    = 3 * 60000;  // re-check the live pool every 3 min
const LIVE_FILE        = join(__dir, 'proxies_live.json');
const ASSIGN_FILE      = join(__dir, 'assignments.json');
const FLEET_FILE       = join(__dir, 'fleet.txt'); // optional: wallet names, one per line

// Free HTTP-proxy sources (raw ip:port lists + free APIs). Dead entries are
// filtered out by the validator, so it is fine if many are stale.
const SOURCES = [
  'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
  'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
  'https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt',
  'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
  'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
  'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
  'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&ssl=all',
  'https://www.proxy-list.download/api/v1/get?type=http',
  'https://www.proxy-list.download/api/v1/get?type=https',
];

const ts    = () => new Date().toISOString().replace('T', ' ').slice(0, 19) + 'Z';
const log   = (...a) => console.log(`[${ts()}]`, ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const IPPORT = /\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})\b/g;

async function scrapeSources() {
  const set = new Set();
  await Promise.all(SOURCES.map(async (url) => {
    try {
      const { statusCode, body } = await request(url, {
        method: 'GET',
        headersTimeout: 15000, bodyTimeout: 15000,
        signal: AbortSignal.timeout(20000),
      });
      const text = await body.text();
      if (statusCode >= 400) return;
      let m, n = 0;
      while ((m = IPPORT.exec(text)) !== null) { set.add(`${m[1]}:${m[2]}`); n++; }
      log(`source ok (${n}) ${url.split('/').slice(2, 3)}`);
    } catch (e) {
      log(`source FAIL ${String(e).slice(0, 50)} ${url.split('/').slice(2, 3)}`);
    }
  }));
  return [...set];
}

// Returns latency in ms if the proxy can tunnel HTTPS to TEST_URL, else null.
async function check(hostport) {
  const agent = new ProxyAgent(`http://${hostport}`);
  const t0 = Date.now();
  try {
    const { statusCode, body } = await request(TEST_URL, {
      dispatcher: agent, method: 'GET',
      headersTimeout: VALIDATE_TIMEOUT, bodyTimeout: VALIDATE_TIMEOUT,
      signal: AbortSignal.timeout(VALIDATE_TIMEOUT),
    });
    await body.dump();
    await agent.close().catch(() => {});
    return statusCode > 0 ? Date.now() - t0 : null; // any status => CONNECT tunnel worked
  } catch {
    await agent.close().catch(() => {});
    return null;
  }
}

async function validateAll(list) {
  const live = [];
  let idx = 0, done = 0;
  async function worker() {
    while (idx < list.length) {
      const hp = list[idx++];
      const ms = await check(hp);
      done++;
      if (ms != null) live.push({ proxy: `http://${hp}`, ms });
    }
  }
  await Promise.all(Array.from({ length: VALIDATE_CONC }, worker));
  live.sort((a, b) => a.ms - b.ms);
  return live;
}

function loadFleet() {
  try { if (existsSync(FLEET_FILE)) return readFileSync(FLEET_FILE, 'utf8').split('\n').map(s => s.trim()).filter(s => s && !s.startsWith('#')); }
  catch {}
  return [];
}
function loadJson(file) { try { if (existsSync(file)) return JSON.parse(readFileSync(file, 'utf8')); } catch {} return null; }

async function writeAtomic(file, obj) {
  const tmp = file + '.tmp';
  await writeFile(tmp, JSON.stringify(obj, null, 2));
  await rename(tmp, file);
}

// Keep each wallet on its proxy while it is still live; assign a fresh, unused
// live proxy to any wallet whose proxy died or that has none yet.
function buildAssignments(prev, names, live) {
  const livePool = live.map(p => p.proxy);
  const liveSet = new Set(livePool);
  const used = new Set();
  const out = {};
  for (const n of names) {
    const p = prev?.[n];
    if (p && liveSet.has(p) && !used.has(p)) { out[n] = p; used.add(p); }
  }
  const free = livePool.filter(p => !used.has(p));
  let fi = 0;
  for (const n of names) {
    if (out[n]) continue;
    out[n] = fi < free.length ? free[fi++] : null;
    if (out[n]) used.add(out[n]);
  }
  return out;
}

let RAW = [];      // last scraped candidates
let POOL = [];     // last validated live proxies

async function publish() {
  await writeAtomic(LIVE_FILE, { updated: ts(), count: POOL.length, proxies: POOL });
  const names = loadFleet();
  if (names.length) {
    const assignments = buildAssignments(loadJson(ASSIGN_FILE)?.assignments, names, POOL);
    const assigned = Object.values(assignments).filter(Boolean).length;
    await writeAtomic(ASSIGN_FILE, { updated: ts(), assigned, total: names.length, assignments });
    log(`assignments: ${assigned}/${names.length} wallets have a proxy`);
    if (assigned < names.length) log(`  WARNING: ${names.length - assigned} wallet(s) have NO live proxy`);
  }
}

async function fullCycle() {
  log('scraping sources...');
  RAW = await scrapeSources();
  log(`candidates: ${RAW.length} unique  ->  validating against ${TEST_URL} ...`);
  POOL = await validateAll(RAW);
  log(`LIVE: ${POOL.length} proxies${POOL.length ? `  (fastest ${POOL[0].ms}ms, slowest ${POOL[POOL.length - 1].ms}ms)` : ''}`);
  if (POOL.length < MIN_LIVE_WARN) log(`  WARNING: only ${POOL.length} live proxies (< ${MIN_LIVE_WARN}).`);
  await publish();
}

// Re-check only the already-live pool (cheap, keeps the file fresh between scrapes).
async function revalidate() {
  if (!POOL.length) return;
  log(`re-validating ${POOL.length} live proxies...`);
  POOL = await validateAll(POOL.map(p => p.proxy.replace('http://', '')));
  log(`still live: ${POOL.length}`);
  await publish();
}

async function main() {
  log('=== PROXY POOL MANAGER ===');
  log(`fleet: ${loadFleet().length} wallet name(s) in fleet.txt`);
  await fullCycle();
  let sinceRefresh = 0;
  while (true) {
    await sleep(REVALIDATE_MS);
    sinceRefresh += REVALIDATE_MS;
    if (sinceRefresh >= REFRESH_MS) { sinceRefresh = 0; await fullCycle(); }
    else { await revalidate(); }
  }
}

main().catch(e => { log('FATAL', String(e).slice(0, 200)); process.exit(1); });
