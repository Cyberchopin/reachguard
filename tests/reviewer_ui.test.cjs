const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function harness(response) {
  const elements=new Map(), storage=new Map([['callgate-reviewer','old-test-token']]);
  const el=id=>{if(!elements.has(id))elements.set(id,{textContent:'',value:'',disabled:false});return elements.get(id);};
  const calls=[];
  vm.runInNewContext(fs.readFileSync('callgate/demo/review-ui.js','utf8'),{
    document:{querySelector:()=>({dataset:{role:'reviewer'}}),getElementById:el},
    location:{hash:'',origin:'http://127.0.0.1:8782'},
    sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
    URL,URLSearchParams,AbortController,setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},
    fetch:async(path,options)=>{calls.push({path,options});if(response instanceof Error)throw response;
      return {ok:response.status===200,status:response.status,json:async()=>response.body};}
  });
  return {el,calls};
}
test('reviewer shows exact request and contact from its own origin',async()=>{
  const h=harness({status:200,body:{request:{request_id:'same-request-id',session_id:'same-session',reviewer:'family',claimed_identity:'saved-family',expires_at:2000000000},operation:{destination:'fictional-wallet',amount_cents:100}}});
  await h.el('refresh').onclick();
  assert.match(h.el('operation').textContent,/same-request-id/);
  assert.match(h.el('operation').textContent,/family/);
  assert.match(h.el('endpoint').textContent,/8782/);
  assert.equal(h.el('approve').disabled,false);
});
for(const response of [{status:401},{status:503},new Error('offline')]) {
  test('API or credential failure is never displayed as no request: '+(response.status||'network'),async()=>{
    const h=harness(response);await h.el('refresh').onclick();
    assert.match(h.el('operation').textContent,/read failed/);
    assert.doesNotMatch(h.el('operation').textContent,/No active request/);
    assert.equal(h.el('approve').disabled,true);
    assert.ok(h.el('status').textContent);
  });
}
test('only a successful null response is described as empty',async()=>{
  const h=harness({status:200,body:null});await h.el('refresh').onclick();
  assert.match(h.el('status').textContent,/no active request/i);
  assert.equal(h.el('approve').disabled,true);
});
test('local role link replaces stale credential but wrong-instance link is rejected',async()=>{
  const h=harness({status:200,body:null});
  h.el('reviewer-entry').value='http://127.0.0.1:8767/#token=wrong-instance-test-token';
  await h.el('apply-reviewer-entry').onclick();
  assert.match(h.el('status').textContent,/different local instance/);
  h.el('reviewer-entry').value='http://127.0.0.1:8782/#token=current-test-token';
  await h.el('apply-reviewer-entry').onclick();await h.el('refresh').onclick();
  assert.equal(h.el('reviewer-entry').value,'');
  assert.equal(h.calls[0].options.headers.Authorization,'Bearer current-test-token');
});
