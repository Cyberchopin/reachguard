import asyncio
from pathlib import Path
import pytest


def test_silero_real_model_silence_and_isolation():
    pytest.importorskip("onnxruntime")
    from callgate.integrations.silero import SileroSensor
    first, second = SileroSensor(), SileroSensor()
    assert first.feed(b'\0' * 400) == []
    events = first.feed(b'\0' * 6400)
    assert events and all(0 <= e["probability"] < .5 for e in events)
    assert all(not e["identity_verified"] for e in events)
    assert second.frames == 0
    with pytest.raises(ValueError): first.feed(b'x')


def test_pipecat_actual_pipeline_and_transcript_boundary():
    pytest.importorskip("pipecat")
    from pipecat.frames.frames import TranscriptionFrame, InterimTranscriptionFrame, EndFrame, TextFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineWorker
    from pipecat.workers.runner import WorkerRunner
    from pipecat.processors.frame_processor import FrameProcessor
    from callgate.integrations.pipecat import CallGateProcessor, RiskDecisionFrame
    results = []
    raw = []
    class Sink(FrameProcessor):
        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if isinstance(frame, RiskDecisionFrame): results.append(frame.decision)
            if isinstance(frame, TextFrame): raw.append(frame)
            await self.push_frame(frame, direction)
    async def run():
        processor = CallGateProcessor()
        task = PipelineWorker(Pipeline([processor, Sink()]))
        message = dict(type="Turn", turn_order=0, transcript="Send money. Do not tell anyone.", end_of_turn=False)
        partial = InterimTranscriptionFrame(text=message["transcript"], user_id="unknown", timestamp="test", result=message)
        final = TranscriptionFrame(text=message["transcript"], user_id="unknown", timestamp="test", result=dict(message,end_of_turn=True))
        await task.queue_frames([partial, final, final, EndFrame()])
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(task)
        await asyncio.wait_for(runner.run(),10)
    asyncio.run(run())
    assert [r["state"] for r in results] == ["UNVERIFIED", "COOLING_OFF"]
    assert not raw
    assert all(not r["protected_actions_allowed"] for r in results)

def test_sensor_failure_preserves_audio(monkeypatch):
    pytest.importorskip('onnxruntime')
    from fastapi.testclient import TestClient
    from callgate.api import app
    from callgate.integrations.silero import SileroSensor
    monkeypatch.setenv('ASSEMBLYAI_API_KEY', 'test-key')
    monkeypatch.setenv('CALLGATE_VAD', 'silero')
    def fail(self, pcm): raise RuntimeError('private-error')
    monkeypatch.setattr(SileroSensor, 'feed', fail)
    async def provider(chunks, on_segment, **kwargs):
        assert [chunk async for chunk in chunks] == [bytes(3200), bytes(3200)]
    monkeypatch.setattr('callgate.api.stream_pcm', provider)
    with TestClient(app).websocket_connect('/v1/stream/audio') as ws:
        ws.send_bytes(bytes(3200))
        ws.send_bytes(bytes(3200))
        ws.send_text('{"type":"stop"}')
        assert ws.receive_json()['sensor']['status'] == 'unavailable'
        assert ws.receive_json() == {'type': 'completed'}
