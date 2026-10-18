class PCMRecorder extends AudioWorkletProcessor {
  constructor() {
    super(); this.buffer = new Int16Array(1600); this.index = 0; this.active = true;
    this.port.onmessage = ({data}) => {
      if (data === 'flush') {
        this.active = false;
        if (this.index) this.emit();
        this.port.postMessage({flushed: true});
      }
    };
  }
  emit() {
    this.port.postMessage({pcm: this.buffer.buffer}, [this.buffer.buffer]);
    this.buffer = new Int16Array(1600); this.index = 0;
  }
  process(inputs) {
    if (!this.active) return true;
    const input = inputs[0]?.[0];
    if (!input) return true;
    let power = 0;
    for (const sample of input) {
      const value = Math.max(-1, Math.min(1, sample));
      this.buffer[this.index++] = Math.round(value * (value < 0 ? 32768 : 32767));
      power += value * value;
      if (this.index === 1600) this.emit();
    }
    this.port.postMessage({level: Math.min(1, Math.sqrt(power/input.length)*5)});
    return true;
  }
}
registerProcessor('pcm-recorder', PCMRecorder);
