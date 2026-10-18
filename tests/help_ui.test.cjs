const test = require('node:test');
const assert = require('node:assert/strict');
const {states, canRespond, canCancel, localTest, rotationText, progress} = require('../callgate/demo/help.js');
test('only an assigned contact UI can respond while recorded', () => {
  assert.equal(canRespond('contact', {status:'recorded'}), true);
  for (const role of ['owner','dashboard','device']) assert.equal(canRespond(role,{status:'recorded'}),false);
  for (const status of ['accepted','unable_to_help','cancelled']) assert.equal(canRespond('contact',{status}),false);
});
test('only owner can cancel; cancelled is terminal', () => {
  for(const status of ['recorded','accepted','unable_to_help']) assert.equal(canCancel('owner',{status}),true);
  assert.equal(canCancel('owner',{status:'cancelled'}),false);
  assert.equal(canCancel('contact',{status:'recorded'}),false);
  assert.equal(canCancel('dashboard',{status:'recorded'}),false);
});
test('receipt and acceptance claims stay distinct', () => {
  assert.match(states.recorded.message,/No contact has accepted/);
  assert.match(states.accepted.message,/does not prove that help has arrived/);
  assert.equal(localTest('local-test-synthetic-1'),true);
  assert.equal(localTest('nano-01-alarm-1'),false);
});
test('rotation text only while a rotating request is still recorded', () => {
  const rotation={contacts:['a','b','c'],position:1,round:2};
  assert.match(rotationText({status:'recorded',rotation}),/step 2 of 3, round 2\. No contact has accepted yet/);
  assert.equal(rotationText({status:'accepted',rotation}),null);
  assert.equal(rotationText({status:'recorded',rotation:null}),null);
});
test('progress announces only new steps, per role', () => {
  const rotation={contacts:['d','s','d','s','n'],position:1,round:1};
  const h=(seq,command,actor_id,reason)=>({seq,command,actor_id,reason,result:'applied'});
  const row={event_id:'e1',device_id:'nano-01',rotation,history:[h(1,'record','device-inbox'),h(2,'notify','d','round 1, step 1 of 5')]};
  const first=progress(new Map(),[row],'owner','o');
  assert.deepEqual(first.messages,['New help request from nano-01.','Contact 1 notified (round 1, step 1 of 5).']);
  row.history.push(h(3,'timeout','d'),h(4,'notify','s','round 1, step 2 of 5'));
  const second=progress(first.seen,[row],'owner','o');
  assert.deepEqual(second.messages,['Contact 1: no acceptance in time.','Contact 2 notified (round 1, step 2 of 5).']);
  assert.deepEqual(progress(second.seen,[row],'owner','o').messages,[]);
  // A contact hears only their own turn.
  assert.deepEqual(progress(first.seen,[row],'contact','s').messages,['It is your turn: someone needs help. Open the request and choose a response.']);
  assert.deepEqual(progress(first.seen,[row],'contact','n').messages,[]);
  row.history.push({...h(5,'accept','s'),actor_role:'contact'},{...h(6,'unable','x'),result:'rejected'});
  assert.deepEqual(progress(second.seen,[row],'dashboard','v').messages,['Contact 2 accepted. This does not mean help has arrived.']);
});
