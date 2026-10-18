"""Internal synthetic split validation. Structural checks cannot prove independence."""
import hashlib
import json
import re
from pathlib import Path

LABEL_FIELDS = {"benign", "expected_alert", "expected_events", "expected_state", "risk_onset_ms"}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized(text):
    text = re.sub(r"\d+", "<number>", text.casefold())
    return " ".join(re.findall(r"[\w<>]+", text))


def fingerprint(text):
    return hashlib.sha256(normalized(text).encode("utf-8")).hexdigest()


def merge_blind_labels(inputs_path, labels_path):
    cases = read_jsonl(inputs_path)
    labels = json.loads(Path(labels_path).read_text(encoding="utf-8"))
    if not isinstance(labels, dict):
        raise ValueError("labels must be an object keyed by case id")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("input case ids must be non-empty and unique")
    if set(ids) != set(labels):
        raise ValueError("input and label ids must match exactly")
    merged = []
    for case in cases:
        if LABEL_FIELDS & case.keys():
            raise ValueError("blind inputs must not contain labels")
        label = labels[case["id"]]
        if not isinstance(label, dict) or not {"benign", "expected_events", "expected_state"} <= label.keys():
            raise ValueError("each case needs benign, expected_events and expected_state labels")
        if set(label) - LABEL_FIELDS:
            raise ValueError("label files may contain answer fields only")
        merged.append({**case, **label})
    return merged


def validate_holdout(dev_path, inputs_path, labels_path=None):
    dev, heldout = read_jsonl(dev_path), read_jsonl(inputs_path)
    required_meta = {"author_id", "authored_at", "source"}
    heldout_ids = [case.get("id") for case in heldout]
    if len(heldout_ids) != len(set(heldout_ids)) or any(not value for value in heldout_ids):
        raise ValueError("held-out case ids must be non-empty and unique")
    for case in heldout:
        if LABEL_FIELDS & case.keys():
            raise ValueError("held-out inputs contain answer fields")
        annotation = case.get("annotation", {})
        if not required_meta <= set(annotation) or any(not annotation[key] for key in required_meta):
            raise ValueError("held-out cases require annotation author_id, authored_at and source")
    dev_spans = {fingerprint(s["text"]):(c["id"], s["segment_id"]) for c in dev for s in c["segments"]}
    overlaps, heldout_spans = [], {}
    for case in heldout:
        for segment in case["segments"]:
            digest = fingerprint(segment["text"])
            if digest in heldout_spans:
                raise ValueError("normalized transcript duplicate inside held-out split")
            heldout_spans[digest] = (case["id"], segment["segment_id"])
            if digest in dev_spans:
                overlaps.append({"dev":dev_spans[digest][0], "heldout":case["id"], "fingerprint":digest})
    if overlaps:
        raise ValueError("normalized transcript overlap between development and held-out splits")
    if labels_path is not None:
        merge_blind_labels(inputs_path, labels_path)
    return {
        "status":"valid_structure_not_proof_of_independence",
        "dev_cases":len(dev), "heldout_cases":len(heldout), "normalized_overlaps":0,
        "dev_sha256":hashlib.sha256(Path(dev_path).read_bytes()).hexdigest(),
        "inputs_sha256":hashlib.sha256(Path(inputs_path).read_bytes()).hexdigest(),
        "labels_sha256":None if labels_path is None else hashlib.sha256(Path(labels_path).read_bytes()).hexdigest(),
    }
