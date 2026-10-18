const test=require('node:test');
const assert=require('node:assert/strict');
const {localTest,reasonText,remaining,decision}=require('../callgate/demo/device-fusion.js');
const clock=1000000;
const data={context:{session_id:'session',processing_allowed:true,risk_state:'CHALLENGED',pending:false,authorization_denied:false}};
const event={event_id:'local-manual-example',event_type:'verify_request'};
const waiting={event,status:'request_created',request:{session_id:'session',expires_at:1120},out_of_band_challenge:'123456'};

test('an eligible intent enables only an explicit verification request',()=>{
  const state=decision(data,{event,status:'intent_received',reason:null},clock);
  assert.equal(state.canRequest,true);assert.equal(state.active,undefined);
});
test('a help intent never enables verification',()=>{
  assert.equal(decision(data,{event:{...event,event_type:'help_request'},status:'intent_received'},clock).canRequest,false);
});
test('a valid pending request exposes active-code state only for the same session',()=>{
  assert.equal(decision({...data,context:{...data.context,pending:true}},waiting,clock).active,true);
  assert.notEqual(decision({...data,context:{...data.context,session_id:'other',pending:true}},waiting,clock).active,true);
  assert.notEqual(decision(data,waiting,clock).active,true);
});
test('expiry uses the original expiry and disables the old code immediately',()=>{
  const state=decision({...data,context:{...data.context,pending:true}},waiting,1120000);
  assert.equal(state.title,'Verification expired');assert.notEqual(state.active,true);assert.equal(state.canRequest,false);
  assert.equal(remaining(waiting.request,1120001),0);
});
test('a cancelled or content-invalidated request cannot reuse its code',()=>{
  const state=decision(data,{...waiting,status:'no_longer_pending'},clock);
  assert.equal(state.title,'Request no longer active');assert.notEqual(state.active,true);
});
for (const [outcome,title] of [['simulated_action_completed','Simulated action completed'],['reviewer_denied','Contact denied this request']]) {
  test('actual outcome rendered without an active challenge: '+outcome,()=>{
    const state=decision(data,{...waiting,status:'completed',outcome:{status:outcome}},clock);
    assert.equal(state.title,title);assert.equal(state.canRequest,false);assert.notEqual(state.active,true);
  });
}
test('ambiguous claims never enable re-creation',()=>{
  const state=decision(data,{event,status:'claimed',reason:'创建结果尚未确认'},clock);
  assert.equal(state.canRequest,false);assert.match(state.message,/uncertain/);
});
test('source labels distinguish documented local tests without claiming BLE hardware',()=>{
  for(const id of ['local-manual-reviewer-check-a','smoke-a','ngrok-check-a','-983168'])assert.equal(localTest({...event,event_id:id}),true);
  assert.equal(localTest({...event,event_id:'nano-live-42'}),false);
});
test('legacy backend refusals have user-facing English text',()=>{
  for(const reason of ['尚未绑定 CallGate 会话','绑定会话已结束','设备不匹配','只有 CHALLENGED','已有待回应核验请求','尚未同意','未知失败']) {
    assert.doesNotMatch(reasonText(reason),/[\u3400-\u9fff]/);
  }
});
test('no consent, wrong policy, pending or denied session keeps creation disabled',()=>{
  for(const change of [{processing_allowed:false},{risk_state:'BLOCKED'},{pending:true},{authorization_denied:true}]) {
    assert.equal(decision({...data,context:{...data.context,...change}},{event,status:'intent_received',reason:null},clock).canRequest,false);
  }
});

test('a missing result is never invented as a contact denial or approval',()=>{
  const state=decision(data,{...waiting,status:'completed',outcome:null},clock);
  assert.equal(state.title,'Result not confirmed');assert.notEqual(state.active,true);assert.equal(state.canRequest,false);
});
