import json
import pytest
from evaluation_v1.baseline import predict


def call(text, role='caller'):
    return json.dumps({'id': 'fixture', 'language': 'en',
                       'turns': [{'role': role, 'text': text}]})


@pytest.mark.parametrize('text,role,expected', [
    ('Please transfer the money.', 'caller', 1),
    ('Never share your password.', 'caller', 1),
    ('Hello there.', 'caller', 0),
    ('Send me your password.', 'recipient', 0),
])
def test_simple_baseline_contract(text, role, expected):
    result = predict(call(text, role))
    assert result['prediction'] == expected
    timing = result['timing_ns']
    assert all(timing[k] >= 0 for k in ['ingestion', 'keyword_matching', 'binary_decision'])
    assert timing['total'] == sum(timing[k] for k in ['ingestion', 'keyword_matching', 'binary_decision'])
    assert timing['gate_transition'] is None
    assert result['total_cost_usd'] is None


def test_invalid_call_is_an_error_not_negative():
    with pytest.raises(ValueError):
        predict(json.dumps({'id': 'x', 'language': 'en', 'turns': []}))
