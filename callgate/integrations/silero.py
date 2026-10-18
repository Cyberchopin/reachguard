"""MIT Silero VAD model, CPU ONNX inference. Speech evidence never authorizes actions.

State/context layout follows snakers4/silero-vad utils_vad.OnnxWrapper.
See third_party/silero/LICENSE and THIRD_PARTY.md.
"""
import hashlib
from pathlib import Path
import numpy as np
import onnxruntime as ort

MODEL = Path(__file__).resolve().parents[2] / "third_party/silero/model.onnx"
MODEL_SHA256 = "7ed98ddbad84ccac4cd0aeb3099049280713df825c610a8ed34543318f1b2c49"


class SileroSensor:
    def __init__(self, model_path=MODEL):
        if hashlib.sha256(Path(model_path).read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError("Silero model checksum mismatch")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)
        self.pending = np.empty(0, dtype=np.float32)
        self.frames = 0

    def feed(self, pcm: bytes):
        if not pcm or len(pcm) % 2 or len(pcm) > 32000:
            raise ValueError("Expected bounded PCM16 bytes")
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
        self.pending = np.concatenate((self.pending, samples))
        events = []
        while self.pending.size >= 512:
            frame, self.pending = self.pending[:512], self.pending[512:]
            data = np.concatenate((self.context, frame.reshape(1, -1)), axis=1)
            probability, self.state = self.session.run(None, {"input":data, "state":self.state, "sr":np.array(16000,dtype=np.int64)})
            self.context = data[:, -64:].copy()
            self.frames += 1
            events.append({"type":"speech_activity", "audio_ms":self.frames*32,
                           "probability":float(probability[0][0]), "model":"silero-vad",
                           "identity_verified":False})
        return events
