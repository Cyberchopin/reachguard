'use strict';
(() => {
  const localManualIds = new Set(['-983168']); // Operator-classified local manual result; see the build log.
  const localTest = event => localManualIds.has(event.event_id) || /^(local-manual-|local-test-|ngrok-check-|smoke-|ui-preview-)/.test(event.event_id);
  const contactName = id => ({'saved-family':'Family contact','saved-bank':'Bank contact'}[id] || (id || 'Not selected').replace(/[_-]/g,' '));
  const reasonText = reason => {
    if (!reason) return '';
    const matches = [
      ['求助意图','Help intent recorded. This demo has not notified a contact.'],
      ['尚未绑定','Confirm your session, device, contact, and simulated action in Session setup.'],
      ['绑定会话已结束','The bound session has ended. Bind this session again.'],
      ['不匹配','This event belongs to a different device. Check the device in Session setup.'],
      ['尚未同意','Allow this test session before processing content.'],
      ['只有 CHALLENGED','The current policy does not allow a confirmation request. Review the evidence.'],
      ['授权已被拒绝','Authorization was denied or expired in this session. Pause and verify independently.'],
      ['已有待回应','Another verification is already waiting for a response. It will not be replaced.'],
      ['停止录音','Finish recording before requesting verification.'],
      ['已失效','This request is no longer active. Use a new event when the policy permits it.'],
      ['创建结果尚未确认','The creation result is uncertain. This event will not be retried automatically.'],
      ['session changed','The session changed. Confirm the current session again.'],
      ['challenged conversation','The policy does not allow confirmation for this request.'],
      ['another confirmation','A verification is already waiting for a response.'],
      ['consent required','Allow processing for this test session first.'],
      ['rate exceeded','Too many requests. Wait before using a new event.']
    ];
    const found = matches.find(([key]) => reason.includes(key));
    return found ? found[1] : /[\u3400-\u9fff]/.test(reason) ? 'This request is unavailable. Review Session setup and Developer details.' : reason;
  };
  const remaining = (request, clock=Date.now()) => Math.max(0, Math.ceil(((request?.expires_at || 0)*1000-clock)/1000));
  function decision(data, row, clock=Date.now()) {
    const context=data?.context || {};
    if (!row) return {title:'Not requested',message:'Choose an event to begin. New events never start verification automatically.',canRequest:false,tone:''};
    if (row.event.event_type==='help_request') return {title:'Help requested',message:'A help intent was recorded. No verification or contact notification was sent.',canRequest:false,tone:'amber'};
    if (row.status==='completed') {
      const succeeded=row.outcome?.status==='simulated_action_completed', denied=row.outcome?.status==='reviewer_denied';
      if (!succeeded && !denied) return {title:'Result not confirmed',message:'The result details are not available. Do not assume approval or denial; check the recorded timeline.',canRequest:false,tone:'red'};
      return {title:succeeded?'Simulated action completed':'Contact denied this request',message:succeeded?'The signed confirmation was accepted for this simulated action. No real payment was made.':'The contact denied this request. No simulated action was completed. Pause and check independently.',canRequest:false,tone:succeeded?'teal':'red'};
    }
    const active=row.status==='request_created' && context.pending && row.request?.session_id===context.session_id && remaining(row.request,clock)>0;
    if (active) return {title:'Waiting for contact',message:'A verification request is ready in the separate contact view. No notification delivery is claimed.',canRequest:false,tone:'amber',active:true};
    if (row.request && remaining(row.request,clock)===0) return {title:'Verification expired',message:'The two-minute window has ended. This event cannot create another request. Follow the current policy before using a new event.',canRequest:false,tone:'red'};
    if (row.status==='no_longer_pending' || row.status==='request_created') return {title:'Request no longer active',message:'The request was cancelled, replaced, or invalidated. Do not use its old code. New content invalidates pending verification.',canRequest:false,tone:'red'};
    if (row.status==='claimed' || row.status==='refused') return {title:row.status==='claimed'?'Result not confirmed':'Request not created',message:reasonText(row.reason)||'This event has already been handled. It will not create a second request.',canRequest:false,tone:'red'};
    return {title:row.reason?'Not ready to verify':'Ready to request verification',message:reasonText(row.reason)||'Ask the saved contact to review this exact simulated action through the separate contact view.',canRequest:!row.reason && context.processing_allowed && context.risk_state==='CHALLENGED' && !context.pending && !context.authorization_denied,tone:row.reason?'':'teal'};
  }
  const exports={localTest,contactName,reasonText,remaining,decision};
  if (typeof module!=='undefined') module.exports=exports;
  if (typeof document==='undefined') return;
  const el=id=>document.getElementById(id);
  let credential='', pollTimer, clockTimer, data=null, selectedId=null, selectedOnce=false, hydrated=false, online=false, busy=false, lastSync=null;
  const setText=(id,value)=>{el(id).textContent=value;};
  function notice(message,error=false) {setText('status',message); el('status').dataset.tone=error?'error':'';}
  async function api(path,body) {
    if (!credential) throw new Error('Connect with your local operator access code first.');
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),8000);
    try {
      const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+credential,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)}),cache:'no-store',signal:controller.signal});
      if (!response.ok) {
        if (response.status===401) throw new Error('This access code is not valid for the operator workspace. Check your local role access.');
        if (response.status===422) throw new Error('Check the contact, destination, and amount. Use whole USD cents.');
        let detail='';try {detail=(await response.json()).detail;}catch(_){}
        throw new Error(typeof detail==='string'?reasonText(detail):'The request could not be confirmed. Refresh before taking another action.');
      }
      return await response.json();
    } catch(error) {
      if (error.name==='AbortError' || error instanceof TypeError) throw new Error('Connection interrupted. The result is not confirmed. No request will be retried automatically.');
      throw error;
    } finally {clearTimeout(timeout);}
  }
  const selected=()=>data?.events.find(row=>row.event.event_id===selectedId);
  const amount = cents => Number.isInteger(cents)?new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(cents/100):'—';
  const time = stamp => new Date(stamp).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  function updateDecision() {
    const row=selected(), state=decision(data,row);
    setText('verification-status',state.title);
    setText('decision-notice',online?state.message:'Connect to refresh the actual request state. Challenge codes are hidden while disconnected.');
    el('decision-notice').className='notice '+(online?state.tone:'');
    el('request-verification').disabled=!online || busy || !state.canRequest;
    setText('request-verification',state.active?'Waiting for contact':'Request verification');
    setText('action-reason',state.active?'Open the contact view and share the code through a separate, agreed channel.':state.canRequest?'This creates a scoped request. It does not approve the simulated action.':state.message);
    const usable=online && state.active && /^\d{6}$/.test(row?.out_of_band_challenge || '');
    el('challenge-panel').hidden=!usable;
    setText('challenge-code',usable?row.out_of_band_challenge:'');
    const seconds=remaining(row?.request);
    setText('challenge-time',usable?`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')} remaining`:'');
  }
  function renderTimeline(row) {
    const list=el('timeline');list.replaceChildren();
    const names={event_received:'Event received',verification_request_created:'Verification request created',contact_responded:'Contact response accepted',simulated_operation_result:'Simulated action result'};
    if (!row?.timeline?.length) {const li=document.createElement('li');li.className='empty';li.textContent='Only steps that actually happened will appear here.';list.append(li);return;}
    for (const [index,stage] of row.timeline.entries()) {
      const li=document.createElement('li'), dot=document.createElement('span'), body=document.createElement('div'), title=document.createElement('span'), note=document.createElement('span'), stamp=document.createElement('span');
      dot.className='step-dot';dot.textContent=String(index+1);title.className='step-title';title.textContent=names[stage.stage] || 'Recorded step';
      note.className='step-note';note.textContent=stage.stage==='event_received'?(localTest(row.event)?'Local test · manually generated event':'Device event · received through the HTTP inbox; hardware origin not verified'):stage.stage==='verification_request_created'?'Bound to the selected contact and simulated action':stage.stage==='contact_responded'?(stage.approved?'Signed approval accepted for this request':'Signed denial accepted for this request'):stage.result?.status==='simulated_action_completed'?'Simulated action completed. No real payment was made.':'No simulated action was completed.';
      stamp.className='step-time';stamp.textContent=time(stage.at);body.append(title,note,stamp);li.append(dot,body);list.append(li);
    }
  }
  function render() {
    const context=data.context;
    if (!selectedOnce) {selectedId=(data.events.find(row=>row.status==='request_created' && context.pending) || data.events[0])?.event.event_id || null;selectedOnce=true;}
    const options=[...el('event-select').options].map(option=>option.value).join('|'), ids=data.events.map(row=>row.event.event_id).join('|');
    if (options!==ids) el('event-select').replaceChildren(...data.events.map(row=>new Option(`${localTest(row.event)?'Local test':'Device event'} · ${time(row.event.received_at)} · ${row.event.event_type==='help_request'?'Help':'Verification'} · ${row.event.event_id.slice(-8)}`,row.event.event_id)));
    el('event-select').value=selectedId || '';
    const row=selected(), binding=row?.binding || data.binding;
    const value=amount(binding?.amount_cents);el('operation-amount').replaceChildren(document.createTextNode(value));const currency=document.createElement('small');currency.textContent='USD';el('operation-amount').append(currency);
    setText('operation-destination',binding?.destination || 'Not configured');setText('operation-contact',contactName(binding?.claimed_identity));
    setText('event-count',`${data.events.length} recent event${data.events.length===1?'':'s'}`);
    setText('event-source',row?(localTest(row.event)?'Local test':'Device event'):'No event selected');
    setText('event-kind',row?(row.event.event_type==='help_request'?'Help intent':'Verification intent'):'');
    setText('event-note',row?(row.event.event_type==='verify_request'?'The user requested confirmation from a trusted contact.':'The user requested help. No delivery or response is implied.'):'Choose an event. Your selection stays fixed when new events arrive.');
    el('help-notice').hidden=row?.event.event_type!=='help_request';renderTimeline(row);
    setText('consent-note',context.processing_allowed?'Processing allowed for this session.':'Processing is not allowed. Give consent before analyzing test content.');
    el('consent').disabled=!online || context.processing_allowed || busy;el('decline').disabled=!online || !context.processing_allowed || busy;
    el('ingest').disabled=!online || !context.processing_allowed || busy || context.pending;
    setText('text-hint',context.pending?'Finish this verification before submitting more content. New content would invalidate it.':!context.processing_allowed?'Allow this test session in Session setup before analyzing.':'Analyze fictional content. A new submission invalidates an outstanding request.');
    el('bind').disabled=!online || busy || !context.processing_allowed || context.pending;
    el('reset').disabled=!online || busy;
    if (!hydrated) {
      el('session').replaceChildren(new Option('Current local session',context.session_id));
      el('contact').replaceChildren(...data.contacts.map(id=>new Option(contactName(id),id)));
      if (data.binding) {el('device').value=data.binding.device_id;el('contact').value=data.binding.claimed_identity;el('destination').value=data.binding.destination;el('amount').value=data.binding.amount_cents;}
      hydrated=true;
    } else if (el('session').value!==context.session_id) el('session').replaceChildren(new Option('Current local session',context.session_id));
    setText('binding-note',data.binding?.session_id===context.session_id?'This session and proposed action are explicitly bound. Changes below require confirmation.':'No valid binding for this session. Confirm the device, contact, and action.');
    setText('device-note',`HTTP event inbox read successfully at ${lastSync.toLocaleTimeString('en-US')}. No BLE connection or button press is observed by this page.`);
    const safeRow=row?Object.fromEntries(Object.entries(row).filter(([key])=>key!=='out_of_band_challenge')):null;
    setText('context',JSON.stringify(context,null,2));setText('binding',JSON.stringify(data.binding,null,2));setText('event-details',JSON.stringify(safeRow,null,2));
    if (online) {el('access').classList.add('connected');el('connection').className='badge teal';setText('connection','Workspace synced');}
    updateDecision();
  }
  async function refresh() {
    try {
      const snapshot=await api('/api/fusion');data=snapshot;online=true;lastSync=new Date();render();await evidence();
    } catch(error) {online=false;el('access').classList.remove('connected');el('connection').className='badge red';setText('connection','Connection unavailable');updateDecision();throw error;}
  }
  async function evidence() {
    try {
      const view=await api('/api/evidence');el('evidence').replaceChildren();
      const labels={money:'Payment request',urgency:'Pressure to act now',secrecy:'Secrecy pressure',credentials:'Sensitive information',authority:'Authority claim',remote_access:'Remote access',injection:'Instruction tampering'};
      for (const item of view.contributions) {const chip=document.createElement('span');chip.className='chip';chip.textContent=labels[item.kind] || item.kind;el('evidence').append(chip);}
      if (!view.contributions.length) {const chip=document.createElement('span');chip.className='chip';chip.textContent='No qualifying current evidence';el('evidence').append(chip);}
      const excerpts=view.graph.nodes.filter(node=>node.type==='segment').length;
      setText('evidence-source',`Source: ${excerpts} transcript excerpt${excerpts===1?'':'s'} from this session · rule-based extraction. Restrictions can persist after corrections.`);
    } catch(_) {setText('evidence-source','Evidence could not be loaded. This is not a clear risk assessment.');}
  }
  async function run(fn) {if(busy)return;busy=true;updateDecision();try {await fn();}catch(error){notice(error.message,true);}finally{busy=false;if(data)render();else updateDecision();}}
  async function connect() {
    if(el('token').value)credential=el('token').value.trim();el('token').value='';
    await refresh();notice('Workspace connected. Choose a device event; nothing is processed automatically.');
    clearInterval(pollTimer);clearInterval(clockTimer);pollTimer=setInterval(()=>run(refresh),2000);clockTimer=setInterval(updateDecision,250);
  }
  el('connect').onclick=()=>run(connect);el('connect-again').onclick=()=>run(async()=>{await refresh();});
  el('disconnect').onclick=()=>{clearInterval(pollTimer);clearInterval(clockTimer);credential='';online=false;data=null;selectedId=null;selectedOnce=false;hydrated=false;el('access').classList.remove('connected');setText('connection','Not connected');setText('challenge-code','');el('challenge-panel').hidden=true;el('timeline').replaceChildren();setText('context','Disconnected.');setText('binding','');setText('event-details','');setText('operation-destination','Not loaded');setText('operation-contact','Not loaded');el('request-verification').disabled=true;for(const id of ['consent','decline','ingest','bind','reset'])el(id).disabled=true;notice('This page is disconnected. The server-side binding and requests are unchanged.');};
  el('setup-nav').onclick=()=>{el('setup').open=true;};el('setup-action').onclick=()=>{el('setup').open=true;};
  el('event-select').onchange=()=>{selectedId=el('event-select').value;render();};
  el('consent').onclick=()=>run(async()=>{await api('/api/processing-consent',{granted:true});await refresh();notice('Processing allowed for this test session. Analyze fictional content next.');});
  el('decline').onclick=()=>run(async()=>{await api('/api/processing-consent',{granted:false});await refresh();notice('Processing stopped. The current evidence and pending request were cleared.');});
  el('reset').onclick=()=>run(async()=>{if(!window.confirm('End this session? Its evidence and pending verification will be cleared.'))return;await api('/api/session/reset',{});hydrated=false;await refresh();notice('A new session is ready. Allow processing and confirm a new binding.');});
  el('ingest').onclick=()=>run(async()=>{await api('/api/transcript',{segment_id:crypto.randomUUID(),text:el('text').value,start_ms:0,end_ms:1,final:true});await refresh();setText('text-source','Local test text · analyzed in this session');notice('Test text analyzed. Confirm the simulated action in Session setup.');});
  el('bind').onclick=()=>run(async()=>{await api('/api/fusion/binding',{session_id:el('session').value,device_id:el('device').value,claimed_identity:el('contact').value,destination:el('destination').value,amount_cents:Number(el('amount').value)});await refresh();notice('Session and simulated action bound. Select an event to request verification.');});
  el('request-verification').onclick=()=>run(async()=>{const row=selected();if(!decision(data,row).canRequest)return;const result=await api('/api/fusion/process',{event_id:row.event.event_id});await refresh();notice(result.status==='request_created'?'Verification created. Open the contact view and use the separate challenge code.':reasonText(result.reason)||'This event has already been handled. Check its timeline.');});
  const entryCode=new URLSearchParams(location.hash.slice(1)).get('token');
  if(entryCode){credential=entryCode;history.replaceState(null,'',location.pathname);run(connect);}
})();
