from callgate.bench import evaluate


def test_reports_failures_without_hiding_them():
    report = evaluate("scambench/scenarios.jsonl")
    assert report["cases"] == 25
    rows = {r["id"]: r for r in report["rows"]}
    assert rows["paraphrase-miss"]["state_pass"]
    assert not rows["quoted-warning"]["false_intervention"]
    assert rows["family-secrecy"]["first_alert_audio_ms"] == 1000
    assert report["alert_confusion"] == {"tp": 15, "fp": 0, "fn": 1, "tn": 9}
    assert report["alert_recall"] == 15 / 16
    assert report["specificity"] == 1
    assert report["alert_recall_wilson95"][0] < report["alert_recall"] < report["alert_recall_wilson95"][1]
    assert report["calibration"].startswith("not_applicable")
    assert report["by_slice"]["credentials"]["cases"] == 3
    assert report["engine_p95_ms"] >= 0
