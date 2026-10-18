"""Unvalidated pilot only. run preserves first results; render reuses raw timings."""
import argparse
from collections import Counter, defaultdict
import hashlib
import html
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import time

from callgate.engine import Conversation, HIGH_IMPACT
from callgate.models import Transcript
from callgate.bench import wilson
from evaluation_v1.baseline import predict
from evaluation_v1.run_dev_sanity import DISCLOSURE

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'pilot_results'
STATES = ['UNVERIFIED', 'CHALLENGED', 'COOLING_OFF', 'BLOCKED']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows):
    c = Counter()
    for r in rows:
        if r['label'] == 'ambiguous':
            continue
        c[('t' if r['prediction'] == int(r['label'] == 'scam') else 'f') +
          ('p' if r['prediction'] else 'n')] += 1
    tp, fp, fn, tn = (c[k] for k in ['tp', 'fp', 'fn', 'tn'])
    out = {'confusion': dict(tp=tp, fp=fp, fn=fn, tn=tn)}
    for name, n, d in [('precision', tp, tp+fp), ('recall', tp, tp+fn),
                        ('fpr', fp, fp+tn), ('fnr', fn, fn+tp)]:
        out[name] = {'value': n/d if d else None, 'ci95': wilson(n, d),
                     'numerator': n, 'denominator': d}
    interval = wilson(tp, tp+fp+fn)
    out['f1'] = {'value': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                 'ci95': None if interval is None else [2*q/(1+q) for q in interval],
                 'method': 'monotone transform of Wilson TP/(TP+FP+FN)'}
    return out


class PolicyAblation(Conversation):
    """Evaluation-only policy override; production scoring/extraction are unchanged."""
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.transition_ns = 0

    def ingest(self, segment):
        previous = self.state
        result = super().ingest(segment)
        begin = time.perf_counter_ns()
        committed = {e.kind for sid, evs in self.events.items()
                     if self.segments[sid].final for e in evs}
        old = 'UNVERIFIED' if self.mode == 'no_sticky' else previous
        if 'credentials' in committed and self.mode != 'no_credential_block':
            state = 'BLOCKED'
        elif old != 'BLOCKED' and 'secrecy' in committed and HIGH_IMPACT & committed and self.mode != 'no_secrecy_cooling':
            state = 'COOLING_OFF'
        elif old in {'BLOCKED', 'COOLING_OFF'}:
            state = old
        else:
            state = 'CHALLENGED' if HIGH_IMPACT & committed else 'UNVERIFIED'
        self.transition_ns += time.perf_counter_ns()-begin
        self.state = state
        self.timeline[-1]['state'] = state
        self.intervention_key = state
        return self.snapshot(result['status'])


def run_call(case, engine):
    start = time.perf_counter_ns()
    segments = [Transcript(segment_id=f't{i}', text=t['text'], role=t['role'],
                 language=case['language'], final=True, start_ms=i, end_ms=i+1)
                for i, t in enumerate(case['turns'])]
    ingested = time.perf_counter_ns()
    trace = []
    for segment in segments:
        result = engine.ingest(segment)
        trace.append(result['state'])
    end = time.perf_counter_ns()
    return {'id': case['id'], 'state': result['state'],
            'prediction': int(result['state'] != 'UNVERIFIED'), 'score': result['score'],
            'trace': trace, 'events': sorted({e['kind'] for e in result['events']}),
            'max_state': max(trace, key=STATES.index),
            'timing_ns': {'input_construction': ingested-start,
                          'engine_ingest_combined': end-ingested, 'total': end-start,
                          'evaluation_policy_transition': getattr(engine, 'transition_ns', None),
                          'production_gate_isolated': None,
                          'production_risk_scoring_isolated': None},
            'cost_usd': None, 'cost_scope': 'local_compute_unmeasured_no_provider_call'}


def collect():
    if (OUTPUT/'raw.json').exists():
        raise SystemExit('First run exists. Use render; do not overwrite or retune on this set.')
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for ledger in ['freeze.sha256.json', 'step3.freeze.sha256.json']:
        frozen = json.loads((ROOT/ledger).read_text())
        for name, expected in frozen['files'].items():
            assert digest(ROOT/name) == expected, f'Frozen file changed: {name}'
    paths = {k: ROOT.parent/k for k in manifest['files']}
    for k, path in paths.items():
        assert digest(path) == manifest['files'][k]['sha256'], k
    inputs = next(p for p in paths.values() if p.name == 'test.inputs.jsonl')
    labels_path = next(p for p in paths.values() if p.name == 'test.labels.jsonl')
    cases = [json.loads(s) for s in inputs.read_text().splitlines()]
    labels = [json.loads(s) for s in labels_path.read_text().splitlines()]
    assert len({c['id'] for c in cases}) == len(cases)
    assert len({l['id'] for l in labels}) == len(labels)
    assert {c['id'] for c in cases} == {l['id'] for l in labels}
    truth = {l['id']: l for l in labels}
    assert all(l['label'] in {'scam', 'benign', 'ambiguous'} for l in labels)
    assert all(c['language'] == 'en' and c['turns'] for c in cases)
    modes = ['full', 'baseline', 'no_credential_block', 'no_secrecy_cooling', 'no_sticky']
    rows = {mode: [] for mode in modes}
    for case in cases:
        full = run_call(case, Conversation())
        check = run_call(case, PolicyAblation('full'))
        assert (full['state'], full['score'], full['trace']) == (check['state'], check['score'], check['trace'])
        for mode in modes:
            row = (full if mode == 'full' else predict(json.dumps(case)) if mode == 'baseline'
                   else run_call(case, PolicyAblation(mode)))
            row.update(label=truth[case['id']]['label'], category=truth[case['id']]['category'])
            rows[mode].append(row)
    sources = [Path(__file__), ROOT/'baseline.py', ROOT/'EXECUTION_AMENDMENT.md',
               ROOT.parent/'callgate/engine.py', ROOT.parent/'callgate/models.py',
               ROOT.parent/'callgate/bench.py', ROOT/'prediction_mapping.v1.json']
    raw = {'status': 'UNVALIDATED_SYNTHETIC_PILOT_TEST_NOW_REVEALED',
           'disclosure': DISCLOSURE, 'cases': cases, 'labels': labels, 'rows': rows,
           'dataset_seed': manifest['seed'], 'timing_protocol': 'single_pass_no_warmup_fixed_order',
           'source_hashes': {str(p.relative_to(ROOT.parent)): digest(p) for p in sources},
           'input_hashes': {k: digest(p) for k, p in paths.items()},
           'environment': {'python': sys.version, 'platform': platform.platform(),
              'packages': sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions())}}
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT/'raw.json').write_text(json.dumps(raw, indent=2)+'\n', encoding='utf-8')
    (OUTPUT/'raw.sha256').write_text(digest(OUTPUT/'raw.json')+'\n')


def svg(name, title, elements):
    disclosure = 'UNVALIDATED synthetic pilot; same-author labels; no real-world accuracy claim.'
    content = ('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600">'
        '<rect width="900" height="600" fill="white"/>'
        f'<title>{html.escape(title)}</title><desc>{html.escape(DISCLOSURE)}</desc>'
        f'<text x="30" y="30" font-size="19">{html.escape(title)}</text>'
        f'<text x="30" y="55" font-size="12">{disclosure}</text>'+elements+'</svg>')
    (OUTPUT/name).write_text(content, encoding='utf-8')


def render():
    assert digest(OUTPUT/'raw.json') == (OUTPUT/'raw.sha256').read_text().strip()
    raw = json.loads((OUTPUT/'raw.json').read_text())
    all_metrics = {mode: metrics(rows) for mode, rows in raw['rows'].items()}
    full = raw['rows']['full']
    table = {label: dict(Counter(r['state'] for r in full if r['label'] == label))
             for label in ['scam', 'benign', 'ambiguous']}
    benign = [r for r in full if r['label'] == 'benign']
    burden = {str(weights): sum(weights[STATES.index(r['state'])] for r in benign)/len(benign)
              if benign else None for weights in [(0,1,2,3), (0,1,1,1), (0,1,3,5)]}
    c = all_metrics['full']['confusion']
    cells = ''
    for i, (label, value) in enumerate([('TN',c['tn']),('FP',c['fp']),('FN',c['fn']),('TP',c['tp'])]):
        x,y = 150+(i%2)*220, 160+(i//2)*150
        cells += f'<rect x="{x}" y="{y}" width="200" height="130" fill="#d9eafa"/><text x="{x+30}" y="{y+65}" font-size="25">{label}: {value}</text>'
    cells += '<text x="150" y="125">Predicted negative              Predicted positive</text><text x="30" y="220">Benign</text><text x="30" y="370">Scam</text>'
    svg('confusion.svg', 'CallGate confusion matrix (ambiguous excluded)', cells)
    binary = [r for r in full if r['label'] != 'ambiguous']
    points = []
    for threshold in sorted({r['score'] for r in binary}, reverse=True):
        m = metrics([{**r, 'prediction': int(r['score'] >= threshold)} for r in binary])
        points.append({'threshold': threshold, 'precision': m['precision']['value'], 'recall': m['recall']['value']})
    coords = ' '.join(f'{100+600*r["recall"]},{470-340*r["precision"]}' for r in points if r['precision'] is not None and r['recall'] is not None)
    primary = all_metrics['full']
    plot = '<path d="M100 100 V470 H750" fill="none" stroke="black"/><text x="380" y="510">Recall (0 to 1)</text><text x="20" y="100">Precision 1</text><text x="20" y="470">0</text>'
    plot += f'<polyline points="{coords}" fill="none" stroke="steelblue" stroke-width="3"/>'
    if primary['precision']['value'] is not None and primary['recall']['value'] is not None:
        plot += f'<circle cx="{100+600*primary["recall"]["value"]}" cy="{470-340*primary["precision"]["value"]}" r="7" fill="red"/>'
    plot += '<text x="100" y="545">Blue: secondary score sweep. Red: frozen primary state mapping. No threshold selection.</text>'
    svg('precision_recall.svg', 'Secondary score-based precision–recall curve', plot)
    values = [r['timing_ns']['total']/1e6 for r in full]
    upper = max(values) or 1
    bins = [0]*8
    for v in values:
        bins[min(7, int(v/upper*8))] += 1
    bars = '<text x="50" y="90">Count per bin; local text only, one pass, no SLA or bimodality claim</text>'
    for i,n in enumerate(bins):
        h = 300*n/max(bins)
        bars += f'<rect x="{70+i*90}" y="{450-h}" width="70" height="{h}" fill="steelblue"/><text x="{70+i*90}" y="{440-h}">{n}</text><text x="{70+i*90}" y="475" font-size="11">{upper*i/8:.3f}</text>'
    bars += f'<text x="70" y="510">Total call processing ms; final bin upper edge {upper:.3f}; n={len(values)}</text>'
    svg('latency_histogram.svg', 'CallGate local processing latency distribution', bars)
    failures = defaultdict(list)
    lookup = {c['id']: c for c in raw['cases']}
    # Post-hoc attribution of observed errors, not a new prediction rule.
    # Frozen raw predictions remain untouched.
    root_causes = {
        '93fa1ff9a2826553': 'FN: credential wording outside lexical coverage',
        '98d1a6cd9ec3b2a9': 'FN: credential wording outside lexical coverage',
        '029134f95c5f45bf': 'FN: payment morphology or fee wording outside lexical coverage',
        'c9926ad55a2f1a60': 'FN: payment morphology or fee wording outside lexical coverage',
        'ab1e388773ecedd7': 'FN: payment morphology or fee wording outside lexical coverage',
        'a18961d128281751': 'FN: access/coercion request without supported remote-access terms',
        '99a12318f8b07129': 'FN: access/coercion request without supported remote-access terms',
    }
    for r in binary:
        if r['prediction'] == int(r['label'] == 'scam'):
            continue
        group = ('FP: legitimate caller request triggers context-limited rules'
                 if r['prediction'] else root_causes.get(r['id'], 'FN: unattributed; needs review'))
        failures[group].append(r)
    for r in raw['rows']['baseline']:
        if r['label'] == 'benign' and r['prediction']:
            failures['Baseline FP: context-free financial/access keywords'].append(
                {**r, 'state': 'not_applicable', 'events': ['keyword_match']})
    results = {'metrics': all_metrics, 'state_table': table, 'benign_burden': burden,
               'pr_points': points, 'histogram': {'counts': bins, 'upper_ms': upper},
               'failure_ids': {g: [r['id'] for r in rs] for g,rs in failures.items()},
               'disclosure': DISCLOSURE}
    (OUTPUT/'results.json').write_text(json.dumps(results, indent=2)+'\n')
    lines = ['# Unvalidated synthetic pilot — first held-out run', '', DISCLOSURE, '',
        'This set is now revealed. No tuning was performed after opening it.',
        'Intervals assume independent synthetic calls under a working sampling model; they do not establish real-world validity.',
        '', '| Variant | Precision | Recall | F1 | FPR | FNR |', '|---|---|---|---|---|---|']
    def fmt(v):
        return 'undefined' if v is None else f'{v:.4f}'
    for mode,m in all_metrics.items():
        cells = [f'{fmt(m[k]["value"])} [{", ".join(fmt(x) for x in m[k]["ci95"])}]' if m[k]['ci95'] else 'undefined'
                 for k in ['precision','recall','f1','fpr','fnr']]
        lines.append('| '+mode+' | '+' | '.join(cells)+' |')
    lines += ['', '### Paired metric deltas versus full CallGate (descriptive, no significance claim)', '',
              '| Ablation | Precision delta | Recall delta | F1 delta | FPR delta | FNR delta |',
              '|---|---|---|---|---|---|']
    for mode in ['no_credential_block','no_secrecy_cooling','no_sticky']:
        delta = []
        for key in ['precision','recall','f1','fpr','fnr']:
            a,b = all_metrics[mode][key]['value'], all_metrics['full'][key]['value']
            delta.append('undefined' if a is None or b is None else fmt(a-b))
        lines.append('| '+mode+' | '+' | '.join(delta)+' |')
    lines += ['', 'Ablation state counts: '+json.dumps({
        mode: dict(Counter(r['state'] for r in rows)) for mode,rows in raw['rows'].items() if mode != 'baseline'})]
    lines += ['', 'Intervals: 95% Wilson; F1 uses the preregistered monotone Wilson transform.',
        '', '## Counts and severity', '', json.dumps(table), '', 'Benign burden by prespecified weights: '+json.dumps(burden),
        '', 'All per-call traces, maximum states, stage timings and costs are in raw.json.',
        'Costs are unknown/not applicable as specified; no ASR or paid provider was invoked.',
        '', '## Ablation limits', '',
        'These are evaluation-only policy removals, not production feature deployments. Binary-positive states can change severity without changing binary metrics.',
        'Contradiction-check ablation: unavailable; no such gate exists. Human-confirmation ablation: unavailable in this transcript-only corpus; no action outcomes or approval trials.',
        'No-sticky may be inert because this corpus only adds final turns, never transcript revisions. A zero delta is not evidence that the gate is unnecessary.',
        '', '## Failure analysis — post-hoc hypotheses, not proven causal diagnoses']
    for group, members in failures.items():
        lines += ['', f'### {group} (n={len(members)})', '', 'All IDs: '+', '.join(r['id'] for r in members)]
        for r in members[:3]:
            lines += ['', f'Case {r["id"]}; label={r["label"]}; state={r["state"]}; events={r["events"]}']
            lines += ['> '+t['role']+': '+t['text'] for t in lookup[r['id']]['turns']]
        if len(members) < 2:
            lines += ['Only one observed example; no extra examples invented.']
    ambiguous = [r for r in full if r['label'] == 'ambiguous']
    lines += ['', '## Archived latency and cost', '',
        'Nearest-rank percentiles of the original 24 per-call wall-clock samples; milliseconds. No inference rerun.',
        '| Mode/stage | n | P50 ms | P95 ms | Maximum ms |',
        '|---|---|---|---|---|']
    for mode in ['full', 'baseline']:
        for stage in raw['rows'][mode][0]['timing_ns']:
            samples = sorted(r['timing_ns'][stage]/1e6 for r in raw['rows'][mode]
                             if r['timing_ns'][stage] is not None)
            if samples:
                lines.append(f'| {mode}/{stage} | {len(samples)} | {samples[math.ceil(.5*len(samples))-1]:.4f} | {samples[math.ceil(.95*len(samples))-1]:.4f} | {samples[-1]:.4f} |')
    lines += ['', 'Input construction is not network ingestion; combined engine ingest includes extraction, scoring, policy and snapshots.',
        'Isolated production scoring and gate latency were NOT recorded. Evaluation-subclass policy timing is not a substitute.',
        'The first full-call sample is included with no warm-up or outlier removal. Scheduling/initialization causes were not measured.',
        'Stage percentiles need not add up to total percentiles. Fixed execution order and different implementations prevent a causal speed comparison.',
        'No provider was called; ASR/API billing is not applicable. Per-call local compute, electricity, amortization and human-review costs are unknown, not zero.',
        '', '## Ambiguous tier', '',
        'Provisional ambiguous cases are never counted as binary successes or errors.',
        'Final state counts: '+json.dumps(dict(Counter(r['state'] for r in ambiguous))),
        'Baseline prediction counts: '+json.dumps(dict(Counter(r['prediction'] for r in raw['rows']['baseline'] if r['label']=='ambiguous'))),
        '| Case | Context | State | Score | Transcript |',
        '|---|---|---|---|---|']
    for r in ambiguous:
        transcript = ' / '.join(t['role']+': '+t['text'] for t in lookup[r['id']]['turns'])
        lines.append(f'| {r["id"]} | {r["category"]} | {r["state"]} | {r["score"]} | {transcript} |')
    lines += ['', 'Qualitative review: payment-detail updates and an unrecognized fraud-desk caller leave bank identity unresolved; neither asks for a covered high-impact action.',
        'The inspection contractor and administrative-fee cases lack verifiable authority or transaction detail; negative predictions do not resolve that uncertainty.',
        'Dinner repayment and a private medical bill permit both ordinary and deceptive readings; no correctness claim is assigned to their negative predictions.',
        'File recovery and administrator-access cases lack confirmed ticket/maintenance provenance; the latter illustrates that an access request can remain below fixed lexical triggers.',
        'All eight remain UNVERIFIED with score zero and no extracted events throughout; this is absence of matched rules, NOT explicit ambiguity detection, abstention, or successful safety verification.',
        'The baseline is also negative on all eight. No human approval or real action was attempted; only advisory LISTEN follows from the recorded state.',
        '', '## Figures', '', '![Confusion](confusion.svg)', '![PR](precision_recall.svg)', '![Latency](latency_histogram.svg)',
        '', '## Reproduction', '', 'Run python -m evaluation_v1.evaluate_pilot render to reproduce numbers and figures from saved raw measurements.',
        'Fresh wall-clock measurements will differ. To perform a fresh run, use a separate checkout without pilot_results; preserve this first run.',
        'Exact environment, package versions, source hashes and input hashes are recorded in raw.json. Original local held-out files are required for a fresh run and are git-ignored.',
        '', '## Resume draft — limitations must remain attached', '', DISCLOSURE, '',
        f'- Built a reproducible voice-risk pilot on {len(binary)} binary-labeled synthetic held-out calls plus {len(full)-len(binary)} ambiguous calls, exposing CallGate F1 of {100*primary["f1"]["value"]:.1f}% versus {100*all_metrics["baseline"]["f1"]["value"]:.1f}% for a keyword baseline; labels were author-provided and not independently validated.',
        '- Audited all 7 observed scam false negatives and grouped them into credential wording (2), payment wording (3), and access/coercion coverage (2), identifying lexical-coverage hypotheses from an unvalidated pilot rather than claiming a demonstrated improvement.',
        f'- Preserved per-call wall-clock traces and reproducible confusion, precision-recall and latency figures for {len(values)} synthetic test calls; measurements cover local text processing, excluding ASR, isolated production gate latency and unmeasured costs.']
    (OUTPUT/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'full': all_metrics['full'], 'failures': results['failure_ids']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['run', 'render'])
    args = parser.parse_args()
    if args.mode == 'run':
        collect()
    render()
