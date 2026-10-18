'use strict';
const el = id => document.getElementById(id);
const role = document.querySelector('main').dataset.role;
const key = 'callgate-' + role;
const fragment = new URLSearchParams(location.hash.slice(1)).get('token');
if (fragment) {
  sessionStorage.setItem(key, fragment);
  history.replaceState(null, '', location.pathname);
}
let token = sessionStorage.getItem(key);
const stateNames = {UNVERIFIED:'Keep listening; identity is unverified', CHALLENGED:'Verify before acting',
  COOLING_OFF:'Pause and verify independently', BLOCKED:'Do not share sensitive information'};
const outcomeText = result => result.status === 'simulated_action_completed'
  ? 'Simulated action completed. No real payment was made.'
  : result.status === 'reviewer_denied' ? 'Contact denied this request. No simulated action was completed.' : 'No result has been confirmed.';
async function api(path, body) {
  if (!token) throw new Error('Open this role with its local access link. Your operator access does not authorize the contact role.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  let response;
  try {
    response = await fetch(path, {method:body === undefined ? 'GET' : 'POST',
      headers:{Authorization:'Bearer ' + token, 'Content-Type':'application/json'},
      ...(body === undefined ? {} : {body:JSON.stringify(body)}), cache:'no-store', signal:controller.signal});
  } catch (_) {
    throw new Error('Connection interrupted or timed out. The result is unconfirmed. Refresh to check; approvals are never retried automatically.');
  } finally { clearTimeout(timer); }
  if (!response.ok) {
    if (response.status === 401) throw new Error('This access link is invalid or out of date. Reopen the correct local role.');
    if (response.status === 403) throw new Error('Direct action was refused. Input alone cannot authorize a payment. No real payment was made.');
    if (response.status === 409) throw new Error('The request may have changed, expired, or already been used. Refresh before continuing.');
    if (response.status === 422) throw new Error('Check the destination, amount, and test text.');
    throw new Error('The verification service is unavailable or the result is unconfirmed. Refresh to check; approvals are not retried.');
  }
  return response.json();
}
function action(id, fn) {
  el(id).onclick = async () => {
    el(id).disabled = true;
    try { await fn(); } catch (error) { el('status').textContent = error.message; }
    finally { el(id).disabled = false; }
  };
}
if (role === 'participant') {
  let audio = null, participantRequest=null, participantConsent=false, participantPolicy='UNVERIFIED', serverPending=false;
  const updateControls=()=>{
    el('request').disabled=!participantConsent || participantPolicy!=='CHALLENGED' || !el('claimed-identity').value || serverPending || !!participantRequest || !!audio;
    el('ingest').disabled=!participantConsent || serverPending || !!audio;
    el('start-audio').disabled=!participantConsent || serverPending || !!audio;
  };
  const clearChallenge=()=>{participantRequest=null;el('challenge').textContent='';updateControls();};
  const checkSession=async()=>{
    try {const state=await api('/api/status');participantConsent=state.processing_allowed;participantPolicy=state.risk_state;serverPending=state.pending;
      if(!state.pending || state.outcome || state.authorization_denied)clearChallenge();updateControls();
    } catch(_){clearChallenge();el('request').disabled=true;el('ingest').disabled=true;el('start-audio').disabled=true;}
  };
  el('claimed-identity').onchange=updateControls;
  updateControls();
  if(token)checkSession();
  setInterval(()=>{
    if (!participantRequest) return;
    if (Date.now()>=participantRequest.expires_at*1000) {clearChallenge();el('challenge').textContent='Verification expired. The old code is no longer usable.';}
  },250);
  const closeAudio = s => {
    s?.stream?.getTracks().forEach(track => track.stop());
    s?.source?.disconnect(); s?.node?.disconnect();
    if (s?.context && s.context.state !== 'closed') s.context.close().catch(() => {});
    el('level').value = 0;
  };
  const finishAudio = message => {
    const s = audio; if (!s) return;
    clearTimeout(s.limitTimer);
    clearTimeout(s.drainTimer);
    closeAudio(s); s.ws?.close(); audio = null;
    el('start-audio').disabled = false; el('stop-audio').disabled = true;
    el('audio-status').textContent = message;updateControls();
  };
  const showRisk = result => {
    participantPolicy=result.state;clearChallenge();
    el('risk').textContent = stateNames[result.state] + ' · heuristic score ' + result.score + '/100';
    const explanations={UNVERIFIED:'No qualifying high-impact request was detected. There is no challenge to issue.',
      CHALLENGED:'A high-impact request was detected. A separate contact confirmation can be requested.',
      COOLING_OFF:'The request includes secrecy pressure. Pause; this policy does not allow an immediate confirmation.',
      BLOCKED:'The request asks for sensitive credentials. Contact confirmation cannot authorize it.'};
    el('policy-explanation').textContent=explanations[result.state];
    if (result.score === 0 && result.state !== 'UNVERIFIED') {
      el('policy-explanation').textContent='The transcript was corrected, but earlier safety restrictions remain. Corrections cannot clear this session’s restrictions.';
    }
    el('status').textContent = 'Evidence updated. Any previous pending verification is now invalid.';
  };
  const refreshMetrics = async () => {
    const m=await api('/api/metrics/summary');
    if (!m.sessions) { el('metrics-summary').textContent='No completed measurements in this run.'; return; }
    const pct=m.failure_rate === null ? 'no completed sample' : (100*m.failure_rate).toFixed(1)+'%';
    const latency=m.alert_samples ? 'Alert timing proxy P50 '+m.alert_proxy_p50_ms.toFixed(1)+' ms，P95 '+
      m.alert_proxy_p95_ms.toFixed(1)+' ms' : 'No alert timing samples';
    el('metrics-summary').textContent='Recent samples: '+m.sessions+'; completed: '+m.completed+'; failed: '+m.failed+
      '; cancelled: '+m.cancelled+'; disconnected: '+m.disconnected+'; failure rate: '+pct+' (denominator: '+m.failure_denominator+
      '); '+latency+' (valid samples: '+m.alert_samples+')。';
  };
  action('refresh-metrics', refreshMetrics);
  const download = (name, data) => {
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)], {type:'application/json'}));
    const link=document.createElement('a'); link.href=url; link.download=name;
    document.body.append(link); link.click(); link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  action('export-metrics', async () => download('callgate-measurements.json', await api('/api/metrics/export')));
  action('export-receipt', async () => download('callgate-receipt.json', await api('/api/receipt', {})));
  action('inspect-evidence', async () => {
    const view=await api('/api/evidence');
    el('evidence-summary').textContent='Current evidence graph: '+view.graph.nodes.length+' nodes, '+view.graph.edges.length+
      ' edges. Contributions: '+(view.contributions.map(c=>c.kind+' '+c.weight).join(' + ') || 'none')+
      '; heuristic score: '+view.score+' / 100 (not a probability). Policy: '+view.state+
      '. Restrictions can persist from earlier evidence.';
  });
  action('consent', async () => {
    await api('/api/processing-consent', {granted:true});participantConsent=true;updateControls();
    el('consent-status').textContent = 'Processing allowed for this test session.';
    el('status').textContent = 'You can submit fictional content or content you have permission to process.';
  });
  action('decline', async () => {
    const previous=audio;
    if (previous) closeAudio(previous);
    try { await api('/api/processing-consent', {granted:false});participantConsent=false;serverPending=false;updateControls(); }
    finally { if (previous && audio===previous) finishAudio('Microphone off.'); }
    el('consent-status').textContent = 'Processing stopped. Current evidence and pending verification cleared.';
    clearChallenge();
    el('risk').textContent = 'Not analyzed yet';
    el('live-transcript').textContent='Live transcript cleared.';
    el('evidence-summary').textContent='Current evidence cleared.';
    el('status').textContent = 'No verification is pending. No action was taken.';
  });
  action('new-session', async () => {
    const previous=audio;
    if (previous) closeAudio(previous);
    try { await api('/api/session/reset', {});participantConsent=false;serverPending=false;updateControls(); }
    finally { if (previous && audio===previous) finishAudio('Microphone off.'); }
    el('consent-status').textContent='The new session needs consent.';
    el('challenge').textContent=''; el('risk').textContent='Not analyzed yet';
    el('live-transcript').textContent='No live transcript yet.';
    el('evidence-summary').textContent='No evidence in this new session.';
    el('policy-explanation').textContent='Allow processing before starting this new test.';
    el('status').textContent='New session created. Earlier evidence, challenges, and results were cleared.';
  });
  action('ingest', async () => {
    const result = await api('/api/transcript', {segment_id:'s' + crypto.randomUUID(),
      text:el('transcript').value, language:el('language').value || 'en', start_ms:0, end_ms:1000, final:true});
    showRisk(result);
  });
  action('test-gateway', async () => {
    try {
      await api('/api/protected-action', {destination:el('destination').value,
        amount_cents:Number(el('amount').value)});
      el('gateway-result').textContent='Unexpected direct-action response. Check the local service before continuing.';
    } catch (error) {
      el('gateway-result').textContent=error.message;
    }
  });
  el('start-audio').onclick = async () => {
    if (audio) return;
    const s = {turns:new Map()}; audio = s; el('start-audio').disabled = true;
    el('live-transcript').textContent='Waiting for a transcript…';
    el('audio-status').textContent = 'Requesting microphone access…';
    try {
      const status=await api('/api/status');
      if (audio !== s) return;
      if (!status.processing_allowed) { finishAudio('Allow processing for this session before recording.'); return; }
      s.stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,
        echoCancellation:true,noiseSuppression:true},video:false});
      if (audio !== s) { closeAudio(s); return; }
      s.context = new AudioContext({sampleRate:16000});
      if (s.context.sampleRate !== 16000) throw new Error('sample-rate');
      await s.context.audioWorklet.addModule('/pcm-worklet.js');
      if (audio !== s) { closeAudio(s); return; }
      s.ws = new WebSocket(`ws://${location.host}/api/audio`);
      await new Promise((resolve,reject) => {
        const timer=setTimeout(()=>reject(new Error('timeout')),10000);
        s.ws.onopen=()=>{clearTimeout(timer);s.ws.send(JSON.stringify({type:'authenticate',token}));resolve();};
        s.ws.onerror=()=>{clearTimeout(timer);reject(new Error('connect'));};
        s.ws.onclose=()=>{clearTimeout(timer);reject(new Error('closed'));};
      });
      if (audio !== s) { closeAudio(s); s.ws.close(); return; }
      s.ws.onmessage = ({data}) => {
        if (audio !== s) return;
        const message=JSON.parse(data);
        if (message.error === 'processing_stopped') { finishAudio('Processing stopped. Microphone off.'); return; }
        if (message.error) { finishAudio(message.error === 'processing_consent_required'
          ? 'Allow processing for this session before recording.' : message.error === 'assemblyai_not_configured'
          ? 'Speech is not configured in this instance. Use test text instead.' : 'Speech connection failed. Use test text instead.'); return; }
        if (message.type === 'completed') { finishAudio('Recording finished.'); refreshMetrics().catch(()=>{}); return; }
        if (message.metrics) {
          const m=message.metrics;
          const cost=m.estimated_asr_cost_usd === null ? 'ASR price not configured' : 'Estimated ASR cost $'+m.estimated_asr_cost_usd;
          el('metrics').textContent='Audio received: '+(m.audio_received_ms/1000).toFixed(2)+' s; local policy processing: '+
            m.risk_engine_ms+' ms; alert timing proxy: '+(m.end_of_speech_to_alert_proxy_ms === null ?
            'no valid timestamps' : m.end_of_speech_to_alert_proxy_ms+' ms')+
            '; provider connection: '+(m.provider_connect_ms == null ? 'not measured' : m.provider_connect_ms.toFixed(1)+' ms')+
            '; first transcript wait: '+(m.provider_first_transcript_ms == null ? 'not measured' : m.provider_first_transcript_ms.toFixed(1)+' ms')+
            ' (includes speech and buffering, not inference alone); '+cost+'。';
        }
        if (message.transcript) {
          s.turns.set(message.transcript.segment_id, message.transcript);
          el('live-transcript').replaceChildren();
          for (const turn of s.turns.values()) {
            const line=document.createElement('div'); line.textContent=turn.text;
            el('live-transcript').append(line);
          }
        }
        if (message.risk) showRisk(message.risk);
      };
      s.ws.onclose=()=>{ if(audio===s) finishAudio('Speech connection closed.'); };
      s.source=s.context.createMediaStreamSource(s.stream);
      s.node=new AudioWorkletNode(s.context,'pcm-recorder');
      s.node.port.onmessage=({data})=>{
        if (audio !== s || s.stopping) return;
        if(data.level!==undefined) el('level').value=data.level;
        if(data.pcm && s.ws.readyState===WebSocket.OPEN) {
          if (s.ws.bufferedAmount > 64000) { finishAudio('Audio upload stalled. Microphone off.'); return; }
          s.ws.send(data.pcm);
        }
      };
      s.source.connect(s.node); s.node.connect(s.context.destination);
      el('stop-audio').disabled=false; el('audio-status').textContent='Recording. Select Stop when you finish speaking.';
      s.limitTimer=setTimeout(()=>{if(audio===s) el('stop-audio').click();},60000);
    } catch (_) { if (audio === s) finishAudio('The microphone could not start. Check permission or use test text.'); }
  };
  el('stop-audio').onclick = () => {
    const s=audio; if(!s) return;
    s.stopping=true; clearTimeout(s.limitTimer);
    s.stream?.getTracks().forEach(track=>track.stop());
    if(s.ws?.readyState===WebSocket.OPEN) s.ws.send('{"type":"stop"}');
    closeAudio(s);
    el('stop-audio').disabled=true; el('audio-status').textContent='Waiting for the final transcript…';
    s.drainTimer=setTimeout(()=>{if(audio===s) finishAudio('Final transcript timed out. Microphone off.');},15000);
  };
  setInterval(()=>{if(token)checkSession();},2000);
  window.addEventListener('pagehide', ()=>{if(audio) finishAudio('Page closed.');});
  action('load-contacts', async () => {
    const result = await api('/api/contacts');
    const select = el('claimed-identity');
    select.replaceChildren();
    for (const identity of result.identities) {
      const option = document.createElement('option');
      option.value = identity; option.textContent = ({'saved-family':'Family contact','saved-bank':'Bank contact'}[identity] || identity.replace(/[_-]/g,' ')); select.appendChild(option);
    }
    el('contact-status').textContent = result.identities.length
      ? 'Only the contact route configured at startup is used. This does not establish a person’s identity.'
      : 'No saved contacts in this instance. Use the current local launcher.';updateControls();
  });
  action('request', async () => {
    const body = {destination:el('destination').value, amount_cents:Number(el('amount').value)};
    if (el('claimed-identity').value) body.claimed_identity = el('claimed-identity').value;
    const result = await api('/api/request', body);serverPending=true;
    participantRequest=result.request;updateControls();
    el('challenge').textContent = 'One-time challenge: ' + result.out_of_band_challenge + '. Share it with the contact through a separate, agreed channel.';
    el('status').textContent = 'Waiting for the contact to review the action and enter the challenge. No action has been completed.';
  });
  action('refresh', async () => {
    const result = await api('/api/status');
    if (!result.pending || result.outcome || result.authorization_denied) clearChallenge();
    el('status').textContent = result.authorization_denied
      ? 'Authorization was denied or expired. Pause and use your saved contact details to verify independently.'
      : result.outcome ? outcomeText(result.outcome) : result.pending
      ? 'Waiting for contact. No action completed; expiration denies authorization for this session.' : 'No current verification request. No action was taken.';
  });
} else {
  let pending=null, busy=false, poll=null, pollBusy=false, terminal=false;
  const text=(id,value)=>{el(id).textContent=value;};
  const title=(heading,message,tone='')=>{text('review-heading',heading);text('status',message);el('review-notice').className='notice '+tone;};
  const seconds=()=>Math.max(0,Math.ceil(((pending?.expires_at||0)*1000-Date.now())/1000));
  const disable=()=>{const unavailable=busy||!pending||seconds()===0;el('approve').disabled=unavailable;el('deny').disabled=unavailable;el('challenge-response').disabled=unavailable;};
  const clearRequest=()=>{pending=null;el('challenge-response').value='';el('decision-controls').hidden=true;disable();};
  const tick=()=>{
    if (!pending) return;
    const left=seconds();text('expiry',`${Math.floor(left/60)}:${String(left%60).padStart(2,'0')} remaining`);
    if (left===0) {clearRequest();terminal=true;clearInterval(poll);title('Verification expired','The two-minute window ended. Do not reuse the old code. Ask the operator to check the current policy.','red');text('expiry','Expired');text('review-state','Verification expired');}
    disable();
  };
  text('endpoint','Local contact view · '+location.origin);
  action('apply-reviewer-entry',async()=>{
    let entry;try{entry=new URL(el('reviewer-entry').value.trim());}catch(_){throw new Error('Use the complete local contact access link, or open it with the local role launcher.');}
    if(entry.origin!==location.origin)throw new Error('This link belongs to a different local instance. Open the contact page at that link’s address.');
    const supplied=new URLSearchParams(entry.hash.slice(1)).get('token');
    if(!supplied)throw new Error('This link has no contact access. Use the local reviewer launcher.');
    token=supplied;sessionStorage.setItem(key,token);el('reviewer-entry').value='';clearRequest();terminal=false;
    title('Contact access ready','Select Check for a request to read this instance.');
  });
  async function loadReview(manual=false) {
    if(busy||pollBusy)return;
    pollBusy=true;
    const previous=pending;
    if(manual){text('status','Checking for a request…');el('refresh').disabled=true;}
    try {
      const bundle=await api('/api/pending');
      if(bundle===null){
        const expired=previous && previous.expires_at*1000<=Date.now();clearRequest();text('operation','No active request returned by this contact endpoint.');text('expiry','');
        if(expired)title('Verification expired','The request expired before a response was accepted. Do not reuse the old code.','red');
        else if(previous)title('Request no longer active','The request was cancelled or its content changed. No response is recorded here. Ask the operator to check its timeline.','amber');
        else if(!terminal || manual)title('No request waiting','There is no active request for this contact in this local instance. A request may have expired or been cancelled.');
        text('review-state','No active request');el('request-content').hidden=true;
      } else {
        if(!bundle?.request || !bundle.operation)throw new Error('The service returned an invalid response. The request state is not confirmed.');
        if(previous && previous.request_id!==bundle.request.request_id)el('challenge-response').value='';
        pending=bundle.request;terminal=false;el('request-content').hidden=false;el('decision-controls').hidden=false;
        text('review-amount',new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(bundle.operation.amount_cents/100));
        text('review-destination',bundle.operation.destination);
        text('review-contact',({'saved-family':'Family contact','saved-bank':'Bank contact'}[pending.claimed_identity]||pending.claimed_identity||'Legacy unbound contact'));
        text('review-source','Local ReachGuard session · configured contact route');
        text('operation',JSON.stringify({request_id:pending.request_id,session_id:pending.session_id,reviewer:pending.reviewer,claimed_identity:pending.claimed_identity,expires_at:pending.expires_at},null,2));
        text('review-state','Awaiting your decision');title('Review this request','Check the amount and destination through a separate trusted channel. Either decision is valid.','amber');tick();
      }
      text('review-connection','Last checked '+new Date().toLocaleTimeString('en-US'));
      if(manual && !terminal){clearInterval(poll);poll=setInterval(()=>loadReview(false).catch(()=>{}),2000);}
    } catch(error) {
      clearRequest();text('operation','Request read failed. This is not an empty-request result.');text('expiry','');el('request-content').hidden=true;
      const noAccess=/access|role|link|invalid|out of date/.test(error.message);
      title(noAccess?'Contact access required':'Connection unavailable',error.message,'red');text('review-state',noAccess?'Access not confirmed':'State not confirmed');
      text('review-connection','Could not confirm the request state');clearInterval(poll);
    } finally {pollBusy=false;el('refresh').disabled=false;disable();}
  }
  el('refresh').onclick=()=>loadReview(true);
  for(const [id,approved] of [['approve',true],['deny',false]]) {
    el(id).onclick=async()=>{
      if(!pending||busy||seconds()===0){tick();return;}
      const challenge=approved?el('challenge-response').value.trim():null;
      if(approved&&!/^\d{6}$/.test(challenge)){text('status','Enter the six-digit code shared through your separate channel before confirming.');return;}
      busy=true;clearInterval(poll);disable();
      try {
        const result=await api('/api/decide',{request_id:pending.request_id,approved,challenge_response:challenge});
        terminal=true;clearRequest();text('expiry','');
        const completed=result.status==='simulated_action_completed', denied=result.status==='reviewer_denied';
        text('review-state',completed?'Simulation completed':denied?'Request denied':'Result unconfirmed');
        title(completed?'Simulated action completed':denied?'Contact denied this request':'Result not confirmed',outcomeText(result),completed?'teal':'red');
      } catch(error) {terminal=true;clearRequest();title('Decision not confirmed',error.message+' Check the operator timeline before doing anything else.','red');}
      finally{busy=false;clearRequest();}
    };
  }
  setInterval(tick,250);
  if(token)title('Contact access ready','Select Check for a request. Nothing is approved automatically.');
}
if (role==='participant' && token) el('status').textContent='Local access is ready. Follow the steps for this test session.';
