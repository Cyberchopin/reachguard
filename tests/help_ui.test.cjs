const test = require('node:test');
const assert = require('node:assert/strict');
const {states, canRespond, canCancel, localTest} = require('../callgate/demo/help.js');
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
