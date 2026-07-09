// One-time key setup for a NEW server.
// Uses the raw wasm export gen_mining_keys (not wrapped by the old glue) to get
// fresh mining keys + the official wallet-app deep link
// (https://links.gosh.sh/deeplinks/wallet/v2/set-mining-keys?payload=...).
// Scan/open the link with the Acki Nacki wallet app, then this script waits for
// the chain to show the new key and writes the two files the miner needs:
//   mining_keys_<name>.json  and  miner_address_<name>.txt
// Usage:  node setup_keys.mjs yasan1

import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import { init, Wallet } from './bee_sdk.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const ENDPOINTS = ['https://mainnet.ackinacki.org'];
const BACKEND   = 'https://app-backend.ackinacki.org/api/';
const APP_ID    = '0x' + '0'.repeat(63) + '2';
const NAME = process.argv[2] || 'yasan1';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const hex64 = v => typeof v === 'bigint' ? v.toString(16).padStart(64, '0')
                 : String(v ?? '').replace(/^0x/, '').toLowerCase();

const wasmBytes = new Uint8Array(await readFile(new URL('./bee_sdk_bg.wasm', import.meta.url)));
const wasmX = await init({ module_or_path: wasmBytes });

const wallet = new Wallet(ENDPOINTS, null, BACKEND, APP_ID);
const mfa = (await wallet.check_name_availability(NAME)).multifactor_address;
console.log(`[ok] wallet ${NAME} -> multifactor: ${mfa}`);

// Reuse existing keys if present (the app may already have approved them);
// only generate a fresh pair on the very first run.
const keyFile0 = join(__dir, `mining_keys_${NAME}.json`);
let pub, sec;
if (existsSync(keyFile0)) {
  ({ public: pub, secret: sec } = JSON.parse(await readFile(keyFile0, 'utf8')));
  console.log('[ok] reusing existing keys from ' + keyFile0);
} else {
  const keys = await Promise.resolve(wasmX.gen_mining_keys());
  pub = keys.public; sec = keys.secret;
}

// Rebuild the deep link with the mining app_id in the payload (the raw export
// called without args leaves app_id empty).
const payload = Buffer.from(JSON.stringify({ pubkey: pub, app_id: APP_ID })).toString('base64url');
const link = `https://links.gosh.sh/deeplinks/wallet/v2/set-mining-keys?payload=${payload}`;

const keyFile = keyFile0;
await writeFile(keyFile, JSON.stringify({ public: pub, secret: sec }));
console.log(`[ok] new keys saved -> ${keyFile}`);
console.log(`[ok] public: ${pub}\n`);

console.log('================ SCAN / OPEN THIS WITH THE WALLET APP ================');
console.log(link);
console.log('=======================================================================\n');
try {
  const { default: qr } = await import('qrcode-terminal');
  qr.generate(link, { small: true });
} catch {}

// owner_public may be a string/bigint OR a map of registered mining pubkeys —
// collect every hex-ish value recursively and check ours is among them.
function collectPubs(v, out = new Set()) {
  if (v == null) return out;
  if (typeof v === 'bigint') out.add(hex64(v));
  else if (typeof v === 'number') out.add(BigInt(v).toString(16).padStart(64, '0'));
  else if (typeof v === 'string') {
    const s = v.replace(/^0x/, '').toLowerCase();
    if (/^[0-9a-f]{64}$/.test(s)) out.add(s);
    else if (/^\d+$/.test(v)) { try { out.add(BigInt(v).toString(16).padStart(64, '0')); } catch {} }
  } else if (Array.isArray(v)) v.forEach(x => collectPubs(x, out));
  else if (typeof v === 'object') for (const [k, val] of Object.entries(v)) { collectPubs(k, out); collectPubs(val, out); }
  return out;
}

console.log('waiting for the wallet app to confirm the new key on-chain (checks every 10s)...');
while (true) {
  try {
    const d = await wallet.get_miner_details_by_multifactor_address(mfa);
    const found = collectPubs(d?.owner_public);
    if (found.has(pub.toLowerCase())) {
      const addrFile = join(__dir, `miner_address_${NAME}.txt`);
      await writeFile(addrFile, d.address + '\n');
      console.log(`\n[DONE] key confirmed on-chain`);
      console.log(`[DONE] miner address ${d.address} -> ${addrFile}`);
      console.log(`\nnext:  node mine_smart.mjs ${NAME} 20 0   (20-min test)`);
      process.exit(0);
    }
    console.log(`  on-chain keys: [${[...found].map(p => p.slice(0, 10)).join(', ') || 'none'}] — ours ${pub.slice(0, 10)} not there yet`);
  } catch (e) {
    console.log('  (no miner yet / query error, retry) ' + String(e).slice(0, 80));
  }
  await sleep(10000);
}
