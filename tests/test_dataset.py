import json
import pytest
from callgate.bench import evaluate
from callgate.dataset import merge_blind_labels, validate_holdout


def write(path, value):
    path.write_text(value, encoding="utf-8")
    return path


def heldout(text="Please wire 42 dollars."):
    return {"id":"h1", "slice":"payment", "annotation":{"author_id":"reviewer-1",
        "authored_at":"2026-09-09", "source":"independent_synthetic"},
        "segments":[{"segment_id":"s1", "text":text, "start_ms":0, "end_ms":1000, "final":True}]}


def test_blind_labels_evaluate_and_validate(tmp_path):
    inputs = write(tmp_path/"inputs.jsonl", json.dumps(heldout())+"\n")
    labels = write(tmp_path/"labels.json", json.dumps({"h1":{"benign":False,
        "expected_events":["money"], "expected_state":"CHALLENGED", "risk_onset_ms":0}}))
    report = validate_holdout("scambench/scenarios.jsonl", inputs, labels)
    assert report["heldout_cases"] == 1 and report["normalized_overlaps"] == 0
    result = evaluate(inputs, labels)
    assert result["cases"] == 1 and result["alert_confusion"]["tp"] == 1


def test_rejects_leakage_and_visible_answers(tmp_path):
    duplicate = heldout("Hello, see you tomorrow.")
    inputs = write(tmp_path/"duplicate.jsonl", json.dumps(duplicate)+"\n")
    with pytest.raises(ValueError, match="overlap"):
        validate_holdout("scambench/scenarios.jsonl", inputs)
    duplicate["benign"] = True
    write(inputs, json.dumps(duplicate)+"\n")
    with pytest.raises(ValueError, match="answer"):
        validate_holdout("scambench/scenarios.jsonl", inputs)


def test_labels_must_match_ids(tmp_path):
    inputs = write(tmp_path/"inputs.jsonl", json.dumps(heldout())+"\n")
    labels = write(tmp_path/"labels.json", json.dumps({"other":{}}))
    with pytest.raises(ValueError, match="match exactly"):
        merge_blind_labels(inputs, labels)
    labels = write(tmp_path/"labels.json", json.dumps({"h1":{"benign":False,
        "expected_events":[], "expected_state":"UNVERIFIED", "segments":[]}}))
    with pytest.raises(ValueError, match="answer fields only"):
        merge_blind_labels(inputs, labels)
