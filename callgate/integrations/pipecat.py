"""Pipecat 1.8.1 evidence-to-policy boundary, intended immediately after STT.

Only bounded risk decisions pass downstream; transcripts/raw audio do not.
"""
from dataclasses import dataclass
from pipecat.frames.frames import Frame, DataFrame, TextFrame, TranscriptionFrame, InterimTranscriptionFrame, InputAudioRawFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from callgate.assemblyai import AssemblyTurns
from callgate.engine import Conversation


@dataclass
class RiskDecisionFrame(DataFrame):
    decision: dict


class CallGateProcessor(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation = Conversation()
        self.turns = AssemblyTurns()

    def analyze(self, frame):
        message = frame.result
        if hasattr(message, "model_dump"):
            message = message.model_dump(by_alias=True)
        if not isinstance(message, dict) or message.get("type") != "Turn":
            raise ValueError("AssemblyAI Turn metadata is required for revision-safe processing")
        if message.get("transcript") != frame.text:
            raise ValueError("Frame text does not match evidence")
        segment = self.turns.normalize(message)
        return None if segment is None else self.conversation.ingest(segment)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)):
            result = self.analyze(frame)
            if result is not None:
                await self.push_frame(RiskDecisionFrame(result), direction)
            return
        if isinstance(frame, (TextFrame, InputAudioRawFrame)):
            return
        await self.push_frame(frame, direction)
