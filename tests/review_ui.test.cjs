// Run with node --test tests/review_ui.test.cjs. No browser microphone or network.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../callgate/demo/review-ui.js'), 'utf8');

function harness({allowed=true, media}={}) {
  const elements = new Map();
  const el = id => {
    if (!elements.has(id)) elements.set(id, {textContent:'', value:'', disabled:false,
      replaceChildren(){}, append(){}, remove(){}});
    return elements.get(id);
  };
  let captures=0, contexts=0;
  const requests=[];
  const context = {
    document:{querySelector:()=>({dataset:{role:'participant'}}), getElementById:el},
    window:{addEventListener(){}},
    location:{hash:'',host:'127.0.0.1:8766'},
    sessionStorage:{getItem:()=> 'test-token'},
    URLSearchParams, AbortController,
    setTimeout:()=>1, clearTimeout(){}, setInterval:()=>1, clearInterval(){},
    fetch:async (url, options)=>{
      requests.push([url, options.method]);
      return {ok:true,json:async()=>({processing_allowed:allowed})};
    },
    navigator:{mediaDevices:{getUserMedia:()=>{captures++; return media();}}},
    AudioContext:function(){contexts++; throw new Error('unexpected audio context');}
  };
  vm.runInNewContext(source, context);
  return {el,requests,get captures(){return captures;},get contexts(){return contexts;}};
}

test('missing consent never opens the physical microphone', async()=>{
  const h=harness({allowed:false});
  await h.el('start-audio').onclick();
  assert.equal(h.captures,0);
  assert.match(h.el('audio-status').textContent,/Allow processing/);
});

for (const action of ['decline','new-session']) {
  test(action+' during permission prompt releases a late microphone grant', async()=>{
    let resolve, stopped=0;
    const h=harness({media:()=>new Promise(r=>{resolve=r;})});
    const start=h.el('start-audio').onclick();
    await new Promise(r=>setImmediate(r));
    await h.el(action).onclick();
    resolve({getTracks:()=>[{stop(){stopped++;}}]});
    await start;
    assert.equal(stopped,1);
    assert.equal(h.contexts,0);
    assert.equal(h.el('start-audio').disabled,true);
  });
}
