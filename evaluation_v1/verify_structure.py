"""Verify frozen artifacts without printing transcript or label contents."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root/'evaluation_v1/manifest.json').read_text())
rows = {}
for name, expected in manifest['files'].items():
    payload = (root/name).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == expected['sha256'], name
    parsed = [json.loads(line) for line in payload.splitlines()]
    assert len(parsed) == expected['rows']
    assert len({r['id'] for r in parsed}) == len(parsed)
    rows[Path(name).name] = parsed
for split in ['dev', 'test']:
    inputs, labels = rows[f'{split}.inputs.jsonl'], rows[f'{split}.labels.jsonl']
    assert {r['id'] for r in inputs} == {r['id'] for r in labels}
    assert all(set(r) == {'id', 'language', 'turns'} for r in inputs)
    assert all(r['label'] in {'scam', 'benign', 'ambiguous'} for r in labels)
assert {r['family_id'] for r in rows['dev.labels.jsonl']}.isdisjoint(
    r['family_id'] for r in rows['test.labels.jsonl'])
assert {r['id'] for r in rows['dev.inputs.jsonl']}.isdisjoint(
    r['id'] for r in rows['test.inputs.jsonl'])
assert hashlib.sha256((root/'evaluation_v1/DESIGN.md').read_bytes()).hexdigest() == manifest['rubric_sha256']
assert hashlib.sha256((root/'scambench/heldout/private/evaluation_v1/build.py').read_bytes()).hexdigest() == manifest['author_source_sha256']
print('PASS: hashes, counts, unique IDs, separate labels and disjoint families. No predictions evaluated.')
