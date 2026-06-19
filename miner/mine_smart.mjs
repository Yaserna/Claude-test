// Made by Yaser for Janan
// AN SMART MINER v2 (anti-fatigue) -- ONE account, block-driven, robust.
// Strategy: skip to the quiet LATE window (START_FRAC=0.60 = last ~40% of the
// epoch, lowest competition = best reward per tap), mine ~90 baskets to the
// reset, then idle. Reward saturates, so 90 baskets = max reward with least load.
// Detects the epoch reset from the chain (block).
//
// ANTI-FATIGUE: the SDK degrades over long runs (stale sessions, empty baskets),
// so this process RESTARTS ITSELF FRESH every RESTART_EVERY baskets. Progress is
// saved to epoch_state_<name>.json so after a restart it resumes the SAME epoch
// at the SAME basket count (no double counting, no restart from zero).
// (Requires run_smart.sh, which relaunches node when it exits.)
//
// Change WHEN it mines with START_FRAC (0.60 = skip to the last 40%).
// Needs: bee_sdk.mjs, bee_sdk_bg.wasm, mining_keys_<name>.json, miner_address_<name>.txt
// Usage:  node mine_smart.mjs yasan1        (continuous)
//         node mine_smart.mjs yasan1 20 0   (20-min test, mine immediately)

import { readFile, appendFile, writeFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
const __dir = dirname(fileURLToPath(import.meta.url));
const __rawWrite = process.stdout.write.bind(process.stdout);
process.stdout.write = (c,...r)=>{ try{ if((typeof c==='string'?c:c.toString()).trim()==='Read miner events thread') return true; }catch{} return __rawWrite(c,...r); };
const __log = console.log.bind(console);
console.error = (...a)=>{ const s=String(a[0]??''); if(s.includes('Query miner events')||s.includes('pool timed out')||s.includes('GraphQL')) return; };
process.on('unhandledRejection', e => log('(ignored async) '+String(e).slice(0,120)));
process.on('uncaughtException',  e => log('(ignored uncaught) '+String(e).slice(0,120)));

// bee_sdk.mjs sets up the Node environment shims (window/Window/crypto) itself.
import { init, Wallet, Miner } from './bee_sdk.mjs';

// ---------------- config ----------------
const ENDPOINTS    = ['https://mainnet.ackinacki.org'];
const BACKEND      = 'https://app-backend.ackinacki.org/api/';
const APP_ID       = '0x0000000000000000000000000000000000000000000000000000000000000002';
const EPOCH_BLOCKS = 262000;
const START_FRAC   = 0.60;      // skip to the quiet LATE window (last ~40% of epoch)
const TARGET_BASKETS = 90;      // ~90 baskets = max reward (reward saturates)
const RESTART_EVERY  = 20;      // restart the process fresh after this many baskets (anti-fatigue)
const TAP_WINDOW_MS= 15000;
const TAP_GAP      = [280, 380];
const TARGET_5M    = 70;
const MAX_SESSIONS = 4;
const REWARD_MS    = 15000;
const IDLE_MS      = 60000;

const sleep = ms => new Promise(r=>setTimeout(r,ms));
const rand  = (a,b)=>Math.floor(Math.random()*(b-a)+a);
const ts    = () => new Date().toISOString().replace('T',' ').slice(0,19)+'Z';
let LOG=''; function log(...a){ const line=`[${ts()}] `+a.join(' '); __log(line); if(LOG) appendFile(LOG,line+'\n').catch(()=>{}); }

let WALLET=null, MFA=null, STATEFILE='';
async function readLocked(){ try{ const b=await WALLET.get_multifactor_balances({multifactor_address:MFA}); return BigInt(b?.popitgame?.['1']??'0'); }catch{ return null; } }
const toN = (raw)=> raw==null?'?':(Number(raw)/1e9).toFixed(6);
async function readData(miner){ try{ const d=await miner.get_miner_data(); return { tap_sum_5m:Number(d.tap_sum_5m??0), epoch_5m:Number(d.epoch_5m_start??0) }; }catch{ return null; } }
async function saveState(s){ try{ await writeFile(STATEFILE, JSON.stringify(s)); }catch{} }
function loadState(){ try{ if(existsSync(STATEFILE)) return JSON.parse(readFileSync(STATEFILE,'utf8')); }catch{} return null; }

let miner=null, rewardTimer=null, rewardPaused=false, MK=null, MINERADDR=null;
function startRewardTimer(){ rewardTimer=setInterval(()=>{ if(rewardPaused)return; try{ Promise.resolve(miner.get_reward()).catch(()=>{});}catch{} },REWARD_MS); }
async function rebuild(){
  try{ clearInterval(rewardTimer); }catch{}
  rewardPaused=true; await sleep(1500);
  try{ miner?.free?.(); }catch{}
  while(true){ try{ miner=await Miner.new(ENDPOINTS,APP_ID,MINERADDR,MK.public,MK.secret); break; }catch(e){ log('  rebuild retry 10s: '+String(e).slice(0,70)); await sleep(10000); } }
  rewardPaused=false; startRewardTimer();
}
async function runSession(){
  let done=false; rewardPaused=true;
  try{ miner.start(TAP_WINDOW_MS,(msg)=>{ try{ const {action,error}=JSON.parse(msg); if(error)return; if(action==='computation_completed') done=true; }catch{} }); }
  catch(e){ rewardPaused=false; await sleep(5000); return -1; }
  const end=Date.now()+TAP_WINDOW_MS-1000; let n=0;
  while(Date.now()<end && !done){ await sleep(rand(TAP_GAP[0],TAP_GAP[1])); if(done)break; try{ miner.add_tap(1,1); n++; }catch{ break; } }
  for(let i=0;i<15 && !done;i++) await sleep(1000);
  rewardPaused=false; await sleep(3000); return n;
}

async function main(){
  const NAME=process.argv[2]||'yasan1';
  const runMin=Number(process.argv[3])>0?Number(process.argv[3]):0;
  const startFrac=(process.argv[4]!==undefined && !isNaN(Number(process.argv[4])))?Number(process.argv[4]):START_FRAC;
  LOG=join(__dir,`smart_log_${NAME}.txt`);
  STATEFILE=join(__dir,`epoch_state_${NAME}.json`);
  log(`=== SMART MINER v2 name=${NAME} startFrac=${startFrac} target=${TARGET_BASKETS} restartEvery=${RESTART_EVERY} ${runMin?('('+runMin+'min test)'):''} ===`);
  MK=JSON.parse(await readFile(join(__dir,`mining_keys_${NAME}.json`),'utf8'));
  MINERADDR=(await readFile(join(__dir,`miner_address_${NAME}.txt`),'utf8')).trim();
  const wasmBytes=new Uint8Array(await readFile(new URL('./bee_sdk_bg.wasm',import.meta.url)));
  await init({module_or_path:wasmBytes});
  WALLET=new Wallet(ENDPOINTS,null,BACKEND,APP_ID);
  MFA=(await WALLET.check_name_availability(NAME)).multifactor_address;
  miner=await Miner.new(ENDPOINTS,APP_ID,MINERADDR,MK.public,MK.secret);
  startRewardTimer();

  const saved = loadState();           // resume after a fresh restart?
  let curEpoch=null, epochStartBal=null, baskets=0, localBaskets=0;
  const endAt=runMin>0?Date.now()+runMin*60000:Infinity;

  while(Date.now()<endAt){
   try{
    const d=await readData(miner);
    if(!d||!d.epoch_5m){ await sleep(5000); continue; }
    const B=d.epoch_5m, epochNo=Math.floor(B/EPOCH_BLOCKS), pos=(B%EPOCH_BLOCKS)/EPOCH_BLOCKS;

    if(curEpoch===null && saved && saved.epochNo===epochNo){
      curEpoch=epochNo; baskets=saved.baskets; epochStartBal=BigInt(saved.startBalRaw);
      log(`--- RESUMED epoch ${epochNo} at basket ${baskets}/${TARGET_BASKETS} (startLocked=${toN(epochStartBal)}) ---`);
    }
    if(epochNo!==curEpoch){
      if(curEpoch!==null){ const eb=await readLocked(); const r=(eb!=null&&epochStartBal!=null)?(eb-epochStartBal):null;
        log(`*** EPOCH ${curEpoch} DONE | baskets=${baskets} | reward=${r} (~${toN(r)} NACKL) ***`); }
      curEpoch=epochNo; epochStartBal=await readLocked(); baskets=0;
      await saveState({epochNo, baskets, startBalRaw:(epochStartBal??0n).toString()});
      log(`--- EPOCH ${epochNo} START | startLocked=${toN(epochStartBal)} NACKL | mine ${TARGET_BASKETS} baskets from ${(startFrac*100)|0}% ---`);
    }

    if(pos < startFrac){ log(`idle | epoch#${epochNo} pos=${(pos*100).toFixed(1)}% (waiting for ${(startFrac*100)|0}%)`); await sleep(IDLE_MS); continue; }
    if(baskets >= TARGET_BASKETS){ log(`done | epoch#${epochNo} pos=${(pos*100).toFixed(1)}% (${TARGET_BASKETS} baskets, idle until reset)`); await sleep(IDLE_MS); continue; }

    // ---- mine one battery ----
    let sess=0, filled=d.tap_sum_5m, fails=0;
    while(Date.now()<endAt && filled<TARGET_5M && sess<MAX_SESSIONS){
      const sent=await runSession();
      if(sent<0){ if(++fails>=5){ log('  stale -> rebuild'); await rebuild(); fails=0; } continue; }
      fails=0; sess++;
      const d2=await readData(miner); if(d2){ filled=d2.tap_sum_5m; if(d2.epoch_5m!==B) break; }
    }
    baskets++; localBaskets++;
    await saveState({epochNo:curEpoch, baskets, startBalRaw:(epochStartBal??0n).toString()});
    log(`basket ${baskets}/${TARGET_BASKETS} | epoch#${epochNo} pos=${(pos*100).toFixed(1)}% | filled ${filled}/${TARGET_5M}`);

    await rebuild();
    let w=Date.now();
    while(Date.now()<endAt){ await sleep(10000); const dw=await readData(miner); if(!dw)continue; if(dw.tap_sum_5m<TARGET_5M||dw.epoch_5m!==B)break; if(Date.now()-w>12*60000)break; }

    // ---- anti-fatigue: restart fresh after RESTART_EVERY baskets ----
    if(runMin===0 && localBaskets>=RESTART_EVERY){
      log(`[anti-fatigue] mined ${localBaskets} baskets -> restarting process FRESH (will resume at basket ${baskets})`);
      try{clearInterval(rewardTimer);}catch{}
      process.exit(0);   // run_smart.sh relaunches us; loadState() resumes this epoch
    }
   }catch(e){ log('  (loop error, recover): '+String(e).slice(0,90)); await rebuild(); await sleep(5000); }
  }
  try{clearInterval(rewardTimer);}catch{}
  log('=== run finished ==='); process.exit(0);
}

(async function supervise(){
  const forever=!(Number(process.argv[3])>0);
  while(true){ try{ await main(); return; }catch(e){ log('FATAL (restart 30s): '+String(e).slice(0,160)); if(!forever) process.exit(1); await sleep(30000); } }
})();
