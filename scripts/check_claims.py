"""Fail closed for uncovered, changed, or unverified numeric README claims.

This is a pre-event evidence checker, not a risk or authorization feature.
Run from any directory: python scripts/check_claims.py.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def numeric_lines(readme):
    # Deliberately includes dates, versions, ports, paths and numbered steps.
    # False positives must be explicitly reviewed, never silently excluded.
    return [line for line in readme.splitlines() if re.search(r'\d', line)]


def coverage_errors(readme, entries):
    quotes = {e['quote'] for e in entries}
    return [f'UNREGISTERED: {line}' for line in numeric_lines(readme) if line not in quotes]


def validate_entry(entry, readme, root):
    prefix = entry['id']
    quote = entry['quote']
    if quote not in readme.splitlines():
        return [f'{prefix}: original README sentence changed or missing']
    if entry['check'] == 'pending':
        return [f'{prefix}: UNVERIFIED; {entry.get("reason", "needs an executable evidence binding")}']
    if entry['check'] == 'source_literals':
        try:
            for evidence in entry['sources']:
                text = (root / evidence['path']).read_text(encoding='utf-8')
                for literal in evidence['literals']:
                    if literal not in text:
                        return [f'{prefix}: source literal missing: {literal}']
            return []
        except (OSError, KeyError, TypeError) as exc:
            return [f'{prefix}: cannot verify source: {exc}']
    if entry['check'] == 'nonmetric_reference':
        # Only explicitly classified identifiers, instruction numbering and
        # dates. Performance quantities must use a measurement validator.
        if '%' in quote or not entry.get('reason'):
            return [f'{prefix}: invalid nonmetric classification']
        missing = [path for path in entry.get('references', []) if not (root / path).exists()]
        return [f'{prefix}: missing reference {p}' for p in missing]
    if entry['check'] in {'pilot_scope', 'state_counts', 'binary_counts', 'intervals', 'historical_tests'}:
        try:
            raw = json.loads((root / 'evaluation_v1/pilot_results/raw.json').read_text())
            metrics = json.loads((root / 'evaluation_v1/pilot_results/results.json').read_text())
            kind = entry['check']
            if kind == 'pilot_scope':
                manifest = json.loads((root / 'evaluation_v1/manifest.json').read_text())
                dev = manifest['files']['evaluation_v1/dev.inputs.jsonl']['rows']
                cases = raw['rows']['full']
                actual = [int(v) for v in re.findall(r'\d+', quote)]
                expected = [dev+len(cases), dev, len(cases)] + [sum(r['label']==label for r in cases) for label in ('scam','benign','ambiguous')] + [600]
                # Last quantity is explicitly an uncompleted plan, not a metric.
                if 'planned, not completed' not in quote:
                    return [f'{prefix}: expansion must remain explicitly uncompleted']
            elif kind == 'state_counts':
                rows = raw['rows']['full']
                actual = [int(v) for v in re.findall(r'\d+', quote)]
                expected = [sum(r['state']=='UNVERIFIED' for r in rows), sum(r['state']=='CHALLENGED' for r in rows), len(rows)]
            elif kind == 'binary_counts':
                rows = raw['rows']['full']
                ambiguous = [r for r in rows if r['label']=='ambiguous']
                actual = [int(v) for v in re.findall(r'\d+', quote)]
                expected = [len(rows)-len(ambiguous), len(ambiguous), len(ambiguous)]
                if any(r['prediction'] for mode in ('full','baseline') for r in raw['rows'][mode] if r['label']=='ambiguous'):
                    return [f'{prefix}: ambiguous negative prediction claim inconsistent']
            elif kind == 'intervals':
                actual = [float(v) for v in re.findall(r'(\d+(?:\.\d+)?)%', quote)]
                full = metrics['metrics']['full']
                expected = [95] + [round(v*100,1) for name in ('precision','recall') for v in full[name]['ci95']]
            else:
                historical = json.loads((root / 'scambench/local-check.json').read_text())
                actual = [int(v) for v in re.findall(r'\*\*(\d+) Python tests and (\d+) Node', quote)[0]]
                expected = [historical['tests']['tests'], entry['node_test_record']]
                if any(historical['tests'][k] for k in ('failures','errors','skipped')):
                    return [f'{prefix}: historical complete-pass claim inconsistent']
            return [] if actual == expected else [f'{prefix}: numeric values {actual} != evidence {expected}']
        except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
            return [f'{prefix}: cannot validate archive: {exc}']
    if entry['check'] != 'metric_row':
        return [f'{prefix}: unknown validator; cannot claim verification']
    try:
        data = json.loads((root / entry['evidence']).read_text(encoding='utf-8'))
        metric = entry['metric']
        actual = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)%', quote)]
        expected = [round(data['metrics'][mode][metric]['value'] * 100, 1)
                    for mode in ('full', 'baseline')]
        if actual != expected:
            return [f'{prefix}: README percentages {actual} != evidence {expected}']
        # Validate the stated raw denominators in the two rows that contain them.
        full = data['metrics']['full']
        if metric == 'recall':
            pair = re.search(r'(\d+) of (\d+) scam calls', quote)
            if not pair or [int(x) for x in pair.groups()] != [full['recall']['numerator'], full['recall']['denominator']]:
                return [f'{prefix}: recall numerator/denominator mismatch']
        if metric == 'fpr':
            pair = re.search(r'(\d+) of (\d+) benign calls', quote)
            if pair and [int(x) for x in pair.groups()] != [full['fpr']['numerator'], full['fpr']['denominator']]:
                return [f'{prefix}: FPR numerator/denominator mismatch']
        if metric == 'precision':
            positive = re.search(r'(\d+) predicted positive', quote)
            if positive and int(positive.group(1)) != full['precision']['denominator']:
                return [f'{prefix}: predicted-positive count mismatch']
        return []
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return [f'{prefix}: cannot validate evidence: {exc}']


def main():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    ledger = (ROOT / 'CLAIMS.md').read_text(encoding='utf-8')
    block = re.search(r'```json\n(.*?)\n```', ledger, re.S)
    if not block:
        print('CLAIMS.md missing machine-readable ledger')
        return 1
    entries = json.loads(block.group(1))
    errors = coverage_errors(readme, entries)
    if len({e['id'] for e in entries}) != len(entries):
        errors.append('Duplicate claim IDs')
    raw = ROOT / 'evaluation_v1/pilot_results/raw.json'
    expected_hash = (raw.parent / 'raw.sha256').read_text().strip()
    if hashlib.sha256(raw.read_bytes()).hexdigest() != expected_hash:
        errors.append('Frozen raw archive hash mismatch')
    freeze = json.loads((ROOT / 'docs/immutable-evidence.json').read_text())
    for path, digest in freeze.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            errors.append(f'Frozen evidence changed: {path}')
    for entry in entries:
        errors.extend(validate_entry(entry, readme, ROOT))
    for error in errors:
        print(error)
    print(f'registered={len(entries)} unresolved_or_inconsistent={len(errors)}')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
