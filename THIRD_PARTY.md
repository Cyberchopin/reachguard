# Third-party provenance

CallGate does not claim authorship of upstream code, models or datasets.

## Distributed component: Silero VAD

- Source: https://github.com/snakers4/silero-vad
- Commit: `867c2aa692646a1f1de3e94a15c9dd9f614c0acb`
- Original file: `src/silero_vad/data/silero_vad_16k_op15.onnx`
- Local file: `third_party/silero/model.onnx` (unmodified)
- SHA256: `7ed98ddbad84ccac4cd0aeb3099049280713df825c610a8ed34543318f1b2c49`
- MIT license and Silero Team copyright retained in `third_party/silero/LICENSE`.
- `callgate/integrations/silero.py` adapts the upstream OnnxWrapper state/context protocol to NumPy, without the PyTorch dependency. One instance per audio stream. No speech frames are suppressed before STT.

## Package dependency: Pipecat

- Source: https://github.com/pipecat-ai/pipecat
- Installed release: `pipecat-ai==1.8.1` from PyPI, BSD-2-Clause.
- Used as an optional Python dependency, not copied into CallGate source.
- Source inspection checkout and installed release are recorded separately; the checkout's main commit is not asserted to be the release source.

## Research-only evaluation sources

AASIST's root MIT license does not cover every included subcomponent. Its NOTICE identifies t-DCF/EER code under CC BY-NC-SA 4.0. ASVspoof evaluation scripts are retained in separate unmodified research checkouts. No such evaluation code or dataset is redistributed as part of CallGate's MIT runtime. Commercial incorporation needs a separately suitable implementation or permission.

Other checked-out projects remain independent repositories. A local clone is not a GitHub-hosted fork and does not imply feature integration. See `docs/upstreams.json` and `docs/REUSE_PLAN.md` for exact status and source commits.
