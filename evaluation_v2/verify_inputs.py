"""Input and hash validation only. Never imports or invokes CallGate."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def validate(rows, labels):
    ids = set()
    required = {'scenario_id', 'family_id', 'language', 'script', 'media_status'}
    scripts = set()
    for row in rows:
        if not required <= row.keys() or set(row)-required-{'planned_synthetic_turn_indexes'}:
            raise ValueError('invalid scenario fields')
        if row['scenario_id'] in ids:
            raise ValueError('duplicate scenario ID')
        ids.add(row['scenario_id'])
        if row['language'] not in {'en','zh','en-zh'} or row['media_status'] != 'synthetic_text_only':
            raise ValueError('invalid language/media status')
        if not isinstance(row['script'], list) or not row['script']:
            raise ValueError('empty script')
        for turn in row['script']:
            if set(turn) != {'role','text'} or turn['role'] not in {'caller','recipient'}:
                raise ValueError('invalid turn schema')
            if not isinstance(turn['text'], str) or not 0 < len(turn['text']) <= 8000:
                raise ValueError('invalid turn text')
        script = json.dumps(row['script'], ensure_ascii=False, sort_keys=True)
        if script in scripts:
            raise ValueError('duplicate exact script')
        scripts.add(script)
        for index in row.get('planned_synthetic_turn_indexes', []):
            if type(index) is not int or not 0 <= index < len(row['script']):
                raise ValueError('invalid synthetic insertion index')
    label_ids = [r['scenario_id'] for r in labels]
    if len(set(label_ids)) != len(label_ids) or set(label_ids) != ids:
        raise ValueError('label/scenario ID mismatch')
    for row in labels:
        if row['label'] not in {'scam','benign','ambiguous'}:
            raise ValueError('invalid label')
        if row['label_source'] not in {'author','independent'}:
            raise ValueError('invalid label source')
        if row['label_source'] == 'author' and row['independent_label'] is not None:
            raise ValueError('unverified independent label present')
    return {'rows':len(rows), 'families':len({r['family_id'] for r in rows}),
            'languages':dict(Counter(r['language'] for r in rows)),
            'slices':dict(Counter(s for r in labels for s in r['slices']))}


def main():
    manifest = json.loads((ROOT/'manifest.sha256.json').read_text())
    for name, expected in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'manifest mismatch: {name}')
    report = validate(load_rows(ROOT/'blind/scenarios.jsonl'), load_rows(ROOT/'author_labels.jsonl'))
    print(json.dumps(report, sort_keys=True))
    print('All slices are small, correlated synthetic inputs: do not report slice F1 as validated evidence.')
    print('No CallGate predictions were run. Independent annotation is pending.')


if __name__ == '__main__':
    main()
