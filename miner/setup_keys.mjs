// One-time key setup for a NEW server.
// Generates fresh mining keys + a deep link. Scan/open the link with the
// Acki Nacki wallet app to bind the new key to the wallet, then this script
// waits until the chain shows the new key and writes both files the miner needs:
//   mining_keys_<name>.json  and  miner_address_<name>.txt
// Usage:  node setup_keys.mjs yasan1

import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import { init, Wallet, Crypto } from './bee_sdk.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const ENDPOINTS = ['https://mainnet.ackinacki.org'];
const BACKEND   = 'https://app-backend.ackinacki.org/api/';
const APP_ID    = '0x' + '0'.repeat(63) + '2';
const NAME = process.argv[2] || 'yasan1';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const wasmBytes = new Uint8Array(await readFile(new URL('./bee_sdk_bg.wasm', import.meta.url)));
await init({ module_or_path: wasmBytes });

const wallet = new Wallet(ENDPOINTS, null, BACKEND, APP_ID);
const mfa = (await wallet.check_name_availability(NAME)).multifactor_address;
console.log(`[ok] wallet ${NAME} -> multifactor: ${mfa}`);

const crypto = new Crypto(ENDPOINTS);
const keys = await Promise.resolve(crypto.gen_mining_keys());
const pub = keys.public, sec = keys.secret, link = keys.deep_link;

const keyFile = join(__dir, `mining_keys_${NAME}.json`);
await writeFile(keyFile, JSON.stringify({ public: pub, secret: sec }));
console.log(`[ok] new keys saved -> ${keyFile}`);
console.log(`[ok] public: ${pub}\n`);

console.log('================ SCAN / OPEN THIS WITH THE WALLET APP ================');
console.log(link);
console.log('=======================================================================\n');
try {
  const { default: qr } = await import('qrcode-terminal');
  qr.generate(link, { small: true });
} catch { console.log('(npm i qrcode-terminal  for a QR code; or send the link to your phone and tap it)\n'); }

console.log('waiting for the wallet app to confirm the new key on-chain...');
while (true) {
  try {
    const d = await wallet.get_miner_details_by_multifactor_address(mfa);
    const op = d?.owner_public?.replace(/^0x/, '');
    if (op && op.toLowerCase() === pub.replace(/^0x/, '').toLowerCase()) {
      const addrFile = join(__dir, `miner_address_${NAME}.txt`);
      await writeFile(addrFile, d.address + '\n');
      console.log(`\n[DONE] key confirmed on-chain`);
      console.log(`[DONE] miner address ${d.address} -> ${addrFile}`);
      console.log(`\nnext:  node mine_smart.mjs ${NAME} 20 0   (20-min test)`);
      process.exit(0);
    }
    console.log(`  still old/absent key on-chain (owner_public=${(op || 'none').slice(0, 12)}...) — waiting 10s`);
  } catch (e) {
    console.log('  (query error, retry 10s) ' + String(e).slice(0, 80));
  }
  await sleep(10000);
}
