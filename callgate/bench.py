"""Synthetic development smoke benchmark, not a generalization claim."""
import argparse
import hashlib
import json
import math
import platform
import time
from collections import defaultdict
from pathlib import Path
from .models import Transcript
from .engine import Conversation, EXTRACTOR_VERSION
from .dataset import merge_blind_labels, read_jsonl


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def wilson(successes, total, z=1.96):
    """95% Wilson score interval; descriptive only for this synthetic corpus."""
    if not total:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - margin), min(1, center + margin)]


def evaluate(path, labels_path=None):
    raw = Path(path).read_bytes()
    bound_bytes = raw + (b"\0" + Path(labels_path).read_bytes() if labels_path else b"")
    cases = merge_blind_labels(path, labels_path) if labels_path else read_jsonl(path)
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("benchmark must contain unique cases")
    rows, latencies = [], []
    event_tp = event_fp = event_fn = 0
    alert_tp = alert_fp = alert_fn = alert_tn = 0
    for case in cases:
        engine = Conversation()
        first_alert = None
        actual = set()
        for data in case["segments"]:
            start = time.perf_counter()
            result = engine.ingest(Transcript.model_validate(data))
            latencies.append((time.perf_counter()-start)*1000)
            actual = {e["kind"] for e in result["events"]}
            if first_alert is None and result["state"] != "UNVERIFIED":
                first_alert = data["end_ms"]
        expected = set(case["expected_events"])
        event_tp += len(actual & expected)
        event_fp += len(actual-expected)
        event_fn += len(expected-actual)
        predicted_alert = result["state"] != "UNVERIFIED"
        expected_alert = case.get("expected_alert", not case["benign"])
        if expected_alert:
            alert_tp += int(predicted_alert)
            alert_fn += int(not predicted_alert)
        else:
            alert_fp += int(predicted_alert)
            alert_tn += int(not predicted_alert)
        rows.append(dict(id=case["id"], slice=case["slice"], state=result["state"],
            expected_state=case["expected_state"], state_pass=result["state"] == case["expected_state"],
            expected_alert=expected_alert,
            missing_events=sorted(expected-actual), extra_events=sorted(actual-expected),
            benign=case["benign"], false_intervention=case["benign"] and predicted_alert,
            first_alert_audio_ms=first_alert,
            detection_delay_ms=None if first_alert is None or case.get("risk_onset_ms") is None else first_alert-case["risk_onset_ms"]))
    benign = [r for r in rows if r["benign"]]
    delays = sorted(r["detection_delay_ms"] for r in rows if r["detection_delay_ms"] is not None)
    slices = defaultdict(list)
    for row in rows:
        slices[row["slice"]].append(row)
    by_slice = {}
    for name, members in sorted(slices.items()):
        by_slice[name] = {
            "cases": len(members),
            "state_pass_rate": ratio(sum(r["state_pass"] for r in members), len(members)),
            "alerts": sum(r["state"] != "UNVERIFIED" for r in members),
            "false_interventions": sum(r["false_intervention"] for r in members),
        }
    return dict(dataset_sha256=hashlib.sha256(bound_bytes).hexdigest(), cases=len(rows),
        corpus="synthetic-dev-smoke-v2", limitations="Same-author development cases; Wilson intervals describe only this small corpus; no held-out accuracy or audio latency claim.",
        extractor=EXTRACTOR_VERSION, policy="v2-phase1", python=platform.python_version(), platform=platform.platform(),
        event_precision=ratio(event_tp, event_tp+event_fp),
        event_recall=ratio(event_tp, event_tp+event_fn),
        alert_confusion=dict(tp=alert_tp, fp=alert_fp, fn=alert_fn, tn=alert_tn),
        alert_precision=ratio(alert_tp, alert_tp+alert_fp),
        alert_recall=ratio(alert_tp, alert_tp+alert_fn),
        alert_recall_wilson95=wilson(alert_tp, alert_tp+alert_fn),
        specificity=ratio(alert_tn, alert_tn+alert_fp),
        specificity_wilson95=wilson(alert_tn, alert_tn+alert_fp),
        false_intervention_rate=sum(r["false_intervention"] for r in benign)/len(benign) if benign else None,
        calibration="not_applicable: score is a heuristic, not a probability",
        detection_delay_p50_ms=delays[len(delays)//2] if delays else None,
        detection_delay_p95_ms=delays[math.ceil(.95*len(delays))-1] if delays else None,
        by_slice=by_slice,
        state_passes=sum(r["state_pass"] for r in rows),
        engine_p95_ms=sorted(latencies)[math.ceil(.95*len(latencies))-1], rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="scambench/scenarios.jsonl")
    parser.add_argument("--output", default="scambench/results.json")
    parser.add_argument("--labels", help="private JSON labels for a blind input JSONL")
    args = parser.parse_args()
    result = evaluate(args.dataset, args.labels)
    Path(args.output).write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "rows"}, indent=2))
