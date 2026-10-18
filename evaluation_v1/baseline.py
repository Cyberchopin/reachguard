"""Simple lexical floor; deliberately ignores context, negation and credibility."""
import json
import re
import time

VERSION = 'keyword-baseline-v1'
PATTERN = r'\b(?:transfer|wire|zelle|gift cards?|crypto(?:currency)?|password|passcode|otp|verification code|remote access)\b'
RULE = re.compile(PATTERN, re.I)


def predict(raw):
    start = time.perf_counter_ns()
    call = json.loads(raw)
    if not isinstance(call.get('id'), str) or call.get('language') != 'en':
        raise ValueError('invalid call identity or language')
    turns = call.get('turns')
    if not isinstance(turns, list) or not turns:
        raise ValueError('empty call')
    for turn in turns:
        if turn.get('role') not in {'caller', 'recipient'} or not isinstance(turn.get('text'), str):
            raise ValueError('invalid turn')
    caller_text = '\n'.join(t['text'] for t in turns if t['role'] == 'caller')
    ingested = time.perf_counter_ns()
    matched = RULE.search(caller_text) is not None
    scored = time.perf_counter_ns()
    prediction = int(matched)
    decided = time.perf_counter_ns()
    return {
        'id': call['id'], 'prediction': prediction,
        'timing_ns': {
            'ingestion': ingested-start, 'keyword_matching': scored-ingested,
            'binary_decision': decided-scored, 'total': decided-start,
            'gate_transition': None},
        'timing_scope': 'local_text_only_no_asr_or_gate',
        'provider_cost_usd': None, 'provider_cost_status': 'no_provider_invoked',
        'total_cost_usd': None
    }
