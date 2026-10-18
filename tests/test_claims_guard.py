import importlib.util
from pathlib import Path


def checker():
    path = Path(__file__).parents[1] / 'scripts/check_claims.py'
    spec = importlib.util.spec_from_file_location('claims_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_numeric_readme_line_must_be_registered():
    assert checker().coverage_errors('Recall is 99%.', [])


def test_pending_claim_is_not_a_verified_claim():
    entry = {'id': 'x', 'quote': '99%', 'check': 'pending'}
    assert checker().validate_entry(entry, '99%', Path('.'))


def test_changed_claim_fails_even_when_ledger_is_unchanged():
    entry = {'id': 'x', 'quote': 'Original 99%', 'check': 'pending'}
    assert checker().validate_entry(entry, 'Changed 100%', Path('.'))


def test_verified_metric_must_match_evidence(tmp_path):
    import json
    evidence = tmp_path / 'metrics.json'
    evidence.write_text(json.dumps({'metrics': {'full': {'recall': {'value': 0.125, 'numerator': 1, 'denominator': 8}},
                                              'baseline': {'recall': {'value': 0.25}}}}))
    entry = {'id': 'x', 'quote': '| Recall | 99.0% | 25.0% |',
             'check': 'metric_row', 'metric': 'recall', 'evidence': 'metrics.json'}
    assert checker().validate_entry(entry, entry['quote'], tmp_path)


def test_matching_metric_and_denominator_pass(tmp_path):
    import json
    evidence = tmp_path / 'metrics.json'
    evidence.write_text(json.dumps({'metrics': {'full': {'recall': {'value': 0.125, 'numerator': 1, 'denominator': 8}},
                                              'baseline': {'recall': {'value': 0.25}}}}))
    entry = {'id': 'x', 'quote': '| Recall | 12.5% — 1 of 8 scam calls | 25.0% |',
             'check': 'metric_row', 'metric': 'recall', 'evidence': 'metrics.json'}
    assert not checker().validate_entry(entry, entry['quote'], tmp_path)
