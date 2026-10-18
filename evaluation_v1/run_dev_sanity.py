"""DEV-only sanity output. No configurable input path or test execution mode."""
import hashlib
import json
import platform
import sys
from pathlib import Path

from evaluation_v1.baseline import predict, VERSION, PATTERN

DISCLOSURE = (
    'This evaluation uses synthetic transcripts with provisional labels supplied by '
    'the same project assistant that authored the cases and had prior access to the '
    'CallGate implementation. Labels were not derived from CallGate predictions. '
    'No independent human annotation, adjudication, or inter-rater reliability study '
    'has been completed. A frozen holdout limits later tuning exposure but does not '
    'establish author independence or real-world validity.'
)


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root/'manifest.json').read_text())
    payload = (root/'dev.inputs.jsonl').read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest == manifest['files']['evaluation_v1/dev.inputs.jsonl']['sha256']
    # No labels are read and no held-out file is opened.
    samples = [predict(line) for line in payload.decode().splitlines() if line]
    report = {
        'status': 'DEV_SANITY_NOT_HELDOUT_EVALUATION',
        'disclosure': DISCLOSURE, 'baseline_version': VERSION, 'pattern': PATTERN,
        'python': sys.version, 'platform': platform.platform(),
        'data_sha256': digest,
        'source_sha256': hashlib.sha256((root/'baseline.py').read_bytes()).hexdigest(),
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'seed': None, 'deterministic_classifier': True,
        'measurement_protocol': 'one_unwarmed_pass_file_order_regex_precompiled_ns',
        'calls': len(samples), 'samples': samples
    }
    (root/'DEV_SANITY.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(f"DEV sanity completed: {len(samples)} calls; no labels or held-out inputs read.")


if __name__ == '__main__':
    main()
