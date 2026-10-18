'use strict';
(() => {
  const states={
    recorded:{title:'Recorded by backend',tone:'amber',message:'The help request is recorded. No contact has accepted it. No notification delivery is confirmed.'},
    accepted:{title:'Contact accepted',tone:'teal',message:'The authorized contact accepted this request. This acknowledges responsibility; it does not prove that help has arrived.'},
    unable_to_help:{title:'Contact unable to help',tone:'red',message:'The contact said they cannot help. No acceptance or arrival is implied.'},
    cancelled:{title:'Cancelled by user',tone:'',message:'The user cancelled this request. Earlier responses remain in the history.'}
  };
  const canRespond=(role,row)=>role==='contact' && row?.status==='recorded';
  const canCancel=(role,row)=>role==='owner' && !!row && row.status!=='cancelled';
  const localTest=id=>/^(local-test-|local-manual-|help-local-test-|ui-preview-)/.test(id);
  if(typeof module!=='undefined')module.exports={states,canRespond,canCancel,localTest};
  if(typeof document==='undefined')return;
  const el=id=>document.getElementById(id), contact=document.body.dataset.page==='contact';
  let code='',timer,rows=[],selected=null,role=null,online=false,busy=false,connectedOnce=false;
  const actionIds=new Map();
  const text=(id,value)=>{const target=el(id);if(target)target.textContent=value;};
  const feedback=(message,error=false)=>{text('feedback',message);el('feedback').dataset.tone=error?'error':'';};
  const stamp=value=>new Date(value).toLocaleString('en-US',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'});
  async function api(path,body){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
    try{
      const r=await fetch(path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+code,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)}),cache:'no-store',signal:controller.signal});
      const data=await r.json();
      if(r.status===401)throw new Error('This access code is not valid for the help service. Use a separate help role code.');
      if(r.status===403)throw new Error('This role is not allowed to take that action.');
      if(r.status===404)throw new Error('This request is not available to your role.');
      if(r.status===409)return {conflict:true,...data};
      if(!r.ok)throw new Error('The help service could not confirm the request. Refresh before trying again.');
      return data;
    }catch(error){
      if(error.name==='AbortError'||error instanceof TypeError)throw new Error('Connection interrupted. The result is not confirmed; no response was retried automatically.');
      throw error;
    }finally{clearTimeout(timeout);}
  }
  function controls(row){
    for(const id of ['accept','unable'])if(el(id))el(id).disabled=!online||busy||!canRespond(role,row);
    if(el('cancel'))el('cancel').disabled=!online||busy||!canCancel(role,row);
  }
  function render(){
    const row=rows.find(item=>item.event_id===selected),state=states[row?.status];
    text('count',`${rows.length} recent`);el('request-list').replaceChildren();
    if(!rows.length){const p=document.createElement('p');p.className='empty';p.textContent='No help requests are recorded for this role. A new help_request can arrive through the unchanged device inbox.';el('request-list').append(p);}
    for(const item of rows){
      const button=document.createElement('button');button.className='help-item';button.setAttribute('aria-pressed',String(item.event_id===selected));
      const badge=document.createElement('span');badge.className='badge '+(states[item.status]?.tone||'');badge.textContent=states[item.status]?.title||'State unconfirmed';
      const title=document.createElement('strong');title.textContent=(localTest(item.event_id)?'Local test':'Device event')+' · '+stamp(item.received_at);
      const subtitle=document.createElement('small');subtitle.textContent='Device '+item.device_id+' · '+item.event_id.slice(-8);
      button.append(badge,title,subtitle);button.onclick=()=>{selected=item.event_id;render();};el('request-list').append(button);
    }
    text('request-title',row?'Help request':'Choose a request');text('state',state?.title||'No request selected');el('state').className='badge '+(state?.tone||'');
    text('summary',state?.message||'Only an authorized contact response can mark a request as accepted.');el('summary').className='notice '+(state?.tone||'');
    text('source',row?`${localTest(row.event_id)?'Local test':'Device event'} · ${row.device_id} · Recorded ${stamp(row.received_at)}. HTTP receipt does not verify a BLE button press.`:'');
    el('history').replaceChildren();
    const labels={record:'Recorded from the device inbox',accept:'Contact accepted',unable:'Contact unable to help',cancel:'User cancelled'};
    for(const [index,entry] of (row?.history||[]).entries()){
      const li=document.createElement('li'),dot=document.createElement('span'),body=document.createElement('div'),title=document.createElement('span'),note=document.createElement('span');
      dot.className='step-dot';dot.textContent=String(index+1);title.className='step-title';
      title.textContent=entry.result==='applied'?labels[entry.command]||'Recorded action':'Action not applied';
      note.className='step-note';note.textContent=stamp(entry.at)+(entry.result==='rejected'?' · '+(entry.command==='cancel'?'Cancellation':'Contact response')+' refused because the request had already changed.':' · '+(entry.actor_role==='source'?'Backend record only':entry.actor_role==='owner'?'User access':'Separate contact access'));
      body.append(title,note);li.append(dot,body);el('history').append(li);
    }
    controls(row);
    text('permissions',contact?(canRespond(role,row)?'Choose only if you can take responsibility. No payment challenge or risk-policy step is required.':'Responses are available only for recorded requests assigned to this contact.'):
      role==='owner'?'Only your user access can cancel this request. Cancellation does not erase earlier contact responses.':'Display-only view. User access is required to cancel a request.');
    text('details',JSON.stringify(row||{},null,2));
  }
  async function refresh(){
    try{
      const data=await api('/api/help-requests');
      if(contact && data.role!=='contact')throw new Error('This is not contact access. User, display, and device access cannot respond as a contact.');
      role=data.role;rows=data.requests;online=true;
      if(!connectedOnce){selected=rows[0]?.event_id||null;connectedOnce=true;}
      el('access').classList.add('connected');text('connection','Updated '+new Date().toLocaleTimeString('en-US'));el('connection').className='badge teal';render();
    }catch(error){online=false;controls();el('access').classList.remove('connected');text('connection','State not confirmed');el('connection').className='badge red';throw error;}
  }
  async function connect(){
    if(el('access-code').value)code=el('access-code').value.trim();el('access-code').value='';
    if(!code){feedback('Enter the separate access code for this help role.',true);return;}
    try{await refresh();feedback(contact?'Contact access confirmed. Opening this page does not accept a request.':'Dashboard loaded. Only actual recorded responses appear here.');clearInterval(timer);timer=setInterval(()=>{if(!busy)refresh().catch(error=>feedback(error.message,true));},2000);}catch(error){feedback(error.message,true);}
  }
  async function act(command){
    const row=rows.find(item=>item.event_id===selected);
    if(!online||busy||!(command==='cancel'?canCancel(role,row):canRespond(role,row)))return;
    if(command==='cancel'&&!window.confirm('Cancel this help request? Its earlier history will remain recorded.'))return;
    busy=true;controls(row);const key=selected+'/'+command;
    if(!actionIds.has(key))actionIds.set(key,crypto.randomUUID());
    try{
      const body={action_id:actionIds.get(key),...(command==='cancel'?{}:{response:command})};
      const result=await api('/api/help-requests/'+encodeURIComponent(selected)+(command==='cancel'?'/cancel':'/responses'),body);
      if(result.request){rows=rows.map(item=>item.event_id===selected?result.request:item);render();}
      feedback(result.conflict?'The request already changed. Your action was not applied; its rejection is recorded.':result.duplicate?'This action was already recorded. The current request state is shown.':'Your action was recorded. The current request state is shown.',Boolean(result.conflict));
      await refresh();
    }catch(error){feedback(error.message,true);online=false;}
    finally{busy=false;controls(rows.find(item=>item.event_id===selected));}
  }
  el('connect').onclick=connect;
  for(const [id,command] of [['accept','accept'],['unable','unable'],['cancel','cancel']])if(el(id))el(id).onclick=()=>act(command);
  const fragment=new URLSearchParams(location.hash.slice(1)).get('token');
  if(fragment){code=fragment;history.replaceState(null,'',location.pathname);connect();}
})();
