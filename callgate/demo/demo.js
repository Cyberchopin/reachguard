const $ = id => document.getElementById(id);
const labels = {UNVERIFIED:'继续听，身份尚未核实', CHALLENGED:'先核验，再操作', COOLING_OFF:'暂停操作，独立核验', BLOCKED:'不要分享密码或验证码'};
const reasons = {UNVERIFIED:'目前没有触发行动提醒；这不代表已验证安全。', CHALLENGED:'听到了高影响操作请求。请通过你原本知道的联系方式核实。', COOLING_OFF:'转账或其他高影响请求伴随保密要求。请先离开这段通话，再独立核实。', BLOCKED:'听到了索取密码或验证码的请求。请勿提供。'};
const audioErrors = {assemblyai_not_configured:'语音服务尚未配置。', network_permission:'本地服务的联网权限不可用。', stream_timeout:'语音连接等待超时。', provider_auth:'语音服务拒绝了身份验证。', provider_limit:'语音服务达到使用或并发限制。', network_connection:'本地服务无法连接语音服务。'};
let active = null;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function closeMic(s) {
  s.stream?.getTracks().forEach(track => track.stop());
  s.source?.disconnect(); s.node?.disconnect();
  if (s.context && s.context.state !== 'closed') s.context.close().catch(() => {});
  $('level').value = 0;
}
function finish(s, message) {
  if (active !== s) return;
  clearTimeout(s.timer); closeMic(s);
  s.ws?.close(); active = null;
  $('start').disabled = false; $('stop').disabled = true;
  $('status').textContent = message;
}
function showUpdate(s, message) {
  if (!message.transcript || !message.risk) return;
  const t = message.transcript, r = message.risk;
  if (t.text.trim()) s.turns.set(t.segment_id, t);
  $('transcript').replaceChildren();
  for (const turn of s.turns.values()) {
    const line = document.createElement('div');
    line.textContent = turn.text; line.className = turn.final ? '' : 'partial';
    $('transcript').append(line);
  }
  $('guardian').textContent = labels[r.state] || '等待结果';
  $('reason').textContent = reasons[r.state] || '';
  $('risk').dataset.alert = String(r.state !== 'UNVERIFIED');
  $('score').textContent = `风险参考分：${r.score}/100（不是诈骗概率）`;
  if (s.lastState !== r.state) {
    const item = document.createElement('li');
    item.textContent = `${(t.end_ms/1000).toFixed(1)} 秒 · ${labels[r.state]}`;
    $('timeline').append(item); s.lastState = r.state;
  }
}
async function stop() {
  const s = active;
  if (!s || s.stopping) return;
  s.stopping = true; $('stop').disabled = true; clearTimeout(s.timer);
  // Stop the physical device immediately; flush the final partial PCM frame.
  s.stream?.getTracks().forEach(track => track.stop());
  $('status').textContent = '麦克风已关闭，正在接收最后的转录…';
  if (s.node) {
    await Promise.race([new Promise(resolve => { s.flushed = resolve; s.node.port.postMessage('flush'); }), sleep(300)]);
  }
  closeMic(s);
  if (active !== s) return;
  try {
    // Trailing silence triggers provider end-of-turn without recording more audio.
    for (let i=0;i<25 && s.ws.readyState===WebSocket.OPEN;i++) {
      s.ws.send(new ArrayBuffer(3200)); await sleep(100);
    }
    if (active !== s) return;
    if (s.ws.readyState !== WebSocket.OPEN) throw new Error('closed');
    s.ws.send('{"type":"stop"}');
    s.timer = setTimeout(() => finish(s, '测试已停止，最后的转录等待超时。可以重新测试。'), 15000);
  } catch { finish(s, '连接已断开，麦克风已关闭。请重新测试。'); }
}
$('stop').onclick = stop;
$('start').onclick = async () => {
  if (active) return;
  const s = {turns:new Map(), stopping:false}; active = s;
  $('start').disabled = true; $('transcript').textContent = '等待声音…';
  $('timeline').replaceChildren(); $('score').textContent = '';
  $('guardian').textContent = '等待测试'; $('risk').dataset.alert = 'false';
  $('status').textContent = '请在浏览器提示中允许使用麦克风…';
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('unsupported');
    s.stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
    if (active !== s) { closeMic(s); return; }
    s.context = new AudioContext({sampleRate:16000});
    if (s.context.sampleRate !== 16000) throw new Error('sample-rate');
    await s.context.resume();
    await s.context.audioWorklet.addModule('/demo-assets/pcm-worklet.js');
    s.ws = new WebSocket(`ws://${location.host}/v1/stream/audio`);
    s.ws.onmessage = ({data}) => {
      if (active !== s) return;
      const message = JSON.parse(data);
      if (message.sensor) {
        $('speech').textContent = message.sensor.status === 'unavailable' ? '语音活动检测暂不可用，转录继续。' : (message.sensor.probability >= .5 ? 'Silero 检测到说话声。' : 'Silero 暂未检测到说话声。');
        return;
      }
      if (message.error) { finish(s, (audioErrors[message.error] || '语音服务连接失败。') + ' 麦克风已关闭，请回到聊天告诉我。'); return; }
      if (message.type === 'completed') { finish(s, '测试完成，麦克风已关闭。结果保留在下方。'); return; }
      showUpdate(s, message);
    };
    await new Promise((resolve,reject) => {
      const timer = setTimeout(() => reject(new Error('connect-timeout')), 10000);
      s.ws.onopen = () => { clearTimeout(timer); resolve(); };
      s.ws.onerror = () => { clearTimeout(timer); reject(new Error('connect')); };
      s.ws.onclose = () => { clearTimeout(timer); reject(new Error('closed')); finish(s, '连接已关闭，麦克风已关闭。可重新测试。'); };
    });
    if (active !== s) return;
    s.source = s.context.createMediaStreamSource(s.stream);
    s.node = new AudioWorkletNode(s.context,'pcm-recorder');
    s.node.port.onmessage = ({data}) => {
      if (data.flushed) { s.flushed?.(); return; }
      if (active !== s) return;
      if (data.level !== undefined && !s.stopping) $('level').value = data.level;
      if (data.pcm && s.ws.readyState === WebSocket.OPEN) {
        if (s.ws.bufferedAmount > 64000) { finish(s,'网络传输太慢，测试已停止。请重试。'); return; }
        s.ws.send(data.pcm);
      }
    };
    s.node.onprocessorerror = () => finish(s,'麦克风处理失败，已停止。请重试。');
    s.source.connect(s.node); s.node.connect(s.context.destination);
    $('stop').disabled = false; $('status').textContent = '正在录音，请读上面的英文。说完停顿两秒。';
    s.timer = setTimeout(stop,60000);
  } catch (error) {
    const hint = error.name === 'NotAllowedError' ? '麦克风权限未允许。请允许后再试。' : error.name === 'NotFoundError' ? '没有找到麦克风，请检查设备。' : '无法开始测试。请用 Chrome 或 Edge 打开本页后重试。';
    finish(s,hint);
  }
};
window.addEventListener('pagehide', () => { if (active) finish(active,'测试已关闭。'); });
