// Reuse existing Ubuntu Chromium; no installation or global browser changes.
// Usage: node integrations/gateway/check_ui_browser.mjs <current gateway container IP>
import {spawn} from 'node:child_process';
import {readFileSync,mkdtempSync,rmSync,existsSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(fileURLToPath(new URL('../..',import.meta.url)));
const address=process.argv[2];
if(!/^\d+\.\d+\.\d+\.\d+$/.test(address||''))throw Error('Supply inspected container IPv4');
const settings=JSON.parse(readFileSync(join(root,'infra/agentgateway/projects/ui.json'),'utf8'));
const password=readFileSync(join(root,settings.password_file),'utf8').trim();
const binary='/home/developer/.cache/ms-playwright/chromium_headless_shell-1208/chrome-linux/headless_shell';
if(!existsSync(binary))throw Error('Existing browser unavailable; no auto install');
const profile=mkdtempSync(join(root,'infra/agentgateway/state/projects/browser-check-'));
const browser=spawn(binary,['--no-sandbox','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
let ws;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
try{
 const active=join(profile,'DevToolsActivePort');
 for(let i=0;i<50&&!existsSync(active);i++)await delay(100);
 const port=readFileSync(active,'utf8').split('\n')[0];
 const pages=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();
 ws=new WebSocket(pages[0].webSocketDebuggerUrl);
 await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
 let seq=0;const pending=new Map();
 function rpc(method,params={}){return new Promise((resolve,reject)=>{
  const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method))},10000);
  pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}));
 })}
 ws.onmessage=async e=>{
  const msg=JSON.parse(e.data);
  if(msg.id){const p=pending.get(msg.id);if(p){clearTimeout(p.timer);pending.delete(msg.id);msg.error?p.reject(Error(msg.error.message)):p.resolve(msg.result)}}
  else if(msg.method==='Fetch.authRequired')await rpc('Fetch.continueWithAuth',{requestId:msg.params.requestId,authChallengeResponse:{response:'ProvideCredentials',username:settings.username,password}});
  else if(msg.method==='Fetch.requestPaused')await rpc('Fetch.continueRequest',{requestId:msg.params.requestId});
 };
 await rpc('Page.enable');await rpc('Fetch.enable',{handleAuthRequests:true});
 await rpc('Page.navigate',{url:'http://'+address+':4001/ui'});
 let result;
 for(let i=0;i<30;i++){
  await delay(200);
  const probe=await rpc('Runtime.evaluate',{expression:`JSON.stringify({title:document.title,path:location.pathname,overview:document.body.innerText.includes('Gateway Overview'),readOnly:document.body.innerText.includes('Read-only mode'),editButtons:[...document.querySelectorAll('button,a')].filter(e=>/Set up gateways|Add gateway|Configure/i.test(e.innerText)).map(e=>({text:e.innerText,disabled:e.disabled===true}))})`,returnByValue:true});
  result=JSON.parse(probe.result.value);
  if(result.overview)break;
 }
 if(!result.overview||result.title!=='agentgateway'||result.readOnly||!result.editButtons.some(e=>!e.disabled))throw Error('Editable overview did not render');
 console.log(JSON.stringify({passed:true,...result,method:'existing isolated Chromium; private Basic auth; no remote tools'}));
}finally{
 ws?.close();browser.kill('SIGTERM');
 await new Promise(r=>{if(browser.exitCode!==null)r();else browser.once('exit',r)});
 rmSync(profile,{recursive:true,force:true});
}
