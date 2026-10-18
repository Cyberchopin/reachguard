import asyncio
import json
import pytest
from callgate.assemblyai import AssemblyTurns, stream_pcm


def test_normalizer_revisions():
    adapter = AssemblyTurns()
    message = dict(type="Turn", turn_order=0, transcript="Send", end_of_turn=False)
    assert adapter.normalize(message).revision == 0
    assert adapter.normalize(message) is None
    final = adapter.normalize(dict(message, transcript="Send money", end_of_turn=True))
    assert final.revision == 1 and final.final
    assert adapter.normalize({"type": "Begin"}) is None


def test_transport_contract():
    class Fake:
        def __init__(self):
            self.queue = asyncio.Queue()
            self.sent = []
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def send(self, value):
            self.sent.append(value)
            if isinstance(value, bytes):
                await self.queue.put(json.dumps(dict(type="Turn", turn_order=0, transcript="Send money", end_of_turn=True)))
            else:
                await self.queue.put(json.dumps({"type": "Termination"}))
        def __aiter__(self): return self
        async def __anext__(self): return await self.queue.get()
    fake = Fake()
    seen = []
    def connector(url, **kwargs):
        assert url.startswith("wss://streaming.assemblyai.com/v3/ws?")
        assert kwargs["additional_headers"] == {"Authorization": "test-only"}
        return fake
    async def chunks(): yield b"\0" * 3200
    async def capture(s): seen.append(s)
    timings = {}
    ticks = iter([0, .02, .04, .12])
    asyncio.run(stream_pcm(chunks(), capture, connector=connector, api_key="test-only",
                           timings=timings, clock=lambda: next(ticks)))
    assert timings['provider_connect_ms'] == pytest.approx(20)
    assert timings['provider_first_transcript_ms'] == pytest.approx(80)
    assert seen[0].text == "Send money"
    assert json.loads(fake.sent[-1]) == {"type": "Terminate"}


def test_graceful_termination_racing_sender_is_not_a_failure():
    class Fake:
        def __init__(self):
            self.returned = False
            self.terminating = asyncio.Event()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def send(self, value):
            if isinstance(value, str):
                self.terminating.set()
                await asyncio.sleep(0.001)
        def __aiter__(self): return self
        async def __anext__(self):
            await self.terminating.wait()
            if self.returned:
                await asyncio.Future()
            self.returned = True
            return json.dumps({'type': 'Termination'})

    async def chunks():
        yield b'\0' * 3200

    asyncio.run(stream_pcm(chunks(), lambda _: None,
        connector=lambda *args, **kwargs: Fake(), api_key='test-only'))


def test_provider_close_without_termination_is_a_failure():
    class Fake:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def send(self, value): pass
        def __aiter__(self): return self
        async def __anext__(self): raise StopAsyncIteration

    async def chunks():
        yield b'\0' * 3200

    with pytest.raises(RuntimeError, match='without termination'):
        asyncio.run(stream_pcm(chunks(), lambda _: None,
            connector=lambda *args, **kwargs: Fake(), api_key='test-only'))


def test_missing_key(monkeypatch):
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        asyncio.run(stream_pcm(None, None))


def test_final_drain_timeout_cleans_up_provider():
    closed = []
    class Fake:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): closed.append(True)
        async def send(self, value): pass
        def __aiter__(self): return self
        async def __anext__(self): await asyncio.Future()
    async def chunks(): yield b'\0' * 3200
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(stream_pcm(chunks(), None, connector=lambda *a, **k: Fake(),
                               api_key='test', drain_timeout=.01))
    assert closed == [True]


def test_speaker_labels_are_relative_until_trusted_mapping_exists():
    message = dict(type="Turn", turn_order=1, transcript="Send money", end_of_turn=True,
                   speaker_label="A", words=[])
    unknown = AssemblyTurns().normalize(message)
    assert unknown.provider_speaker == "A" and unknown.role == "unknown"
    mapped = AssemblyTurns({"A":"caller"}).normalize(message)
    assert mapped.provider_speaker == "A" and mapped.role == "caller"
    assert AssemblyTurns({"A":"recipient"}).normalize(message).role == "recipient"


def test_unknown_and_mixed_speakers_are_not_mapped():
    base = dict(type="Turn", turn_order=1, transcript="Hello", end_of_turn=True, words=[])
    assert AssemblyTurns({"A":"caller"}).normalize(dict(base,speaker_label="UNKNOWN")).provider_speaker is None
    assert AssemblyTurns({"A":"caller"}).normalize(dict(base,speaker_label="PENDING")).provider_speaker is None
    words = [{"start":0,"end":100,"word_is_final":True,"speaker":"A"},
             {"start":101,"end":200,"word_is_final":True,"speaker":"B"}]
    mixed = AssemblyTurns({"A":"caller","B":"recipient"}).normalize(dict(base,speaker_label="A",words=words))
    assert mixed.role == "unknown" and mixed.provider_speaker is None
    with pytest.raises(ValueError): AssemblyTurns({"A":"verified"})
    with pytest.raises(ValueError): AssemblyTurns().normalize(dict(base,speaker_label="../A"))
    assert AssemblyTurns().normalize(dict(base, transcript="  ")) is None
