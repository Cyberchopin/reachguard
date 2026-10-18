from pathlib import Path

from evaluation_checkout.run import SCENARIOS, render_markdown, render_svg, run


def test_checkout_rehearsal_reports_raw_safety_and_utility_denominators():
    report = run()
    assert report["schema_version"] == "callgate-checkout-utility-v1"
    assert report["scenario_count"] == len(SCENARIOS)
    assert report["summary"]["deny_all"]["false_execute"]["numerator"] == 0
    assert report["summary"]["deny_all"]["legitimate_completion"] == {
        "numerator": 0,
        "denominator": 3,
        "value": 0.0,
        "wilson95": [0, 0.5615060804490177],
    }
    assert report["summary"]["unguarded_checkout"]["false_execute"]["numerator"] == 3
    assert report["summary"]["otp_step_up"]["false_execute"]["numerator"] == 3
    assert report["summary"]["callgate_p100_fast"]["false_execute"]["numerator"] == 0
    assert report["summary"]["callgate_p100_fast"]["legitimate_completion"]["numerator"] == 3
    assert report["summary"]["callgate_p67_observed"]["legitimate_completion"]["numerator"] == 2
    assert report["summary"]["callgate_p67_observed"]["legitimate_completion"]["denominator"] == 3
    assert report["summary"]["callgate_p67_slow"]["verification_ms_median"] == 84000
    assert report["model_parameters"]["otp_step_up"].startswith("coerced victim")


def test_checkout_report_keeps_disclosure_and_baseline_comparison():
    text = render_markdown(run())
    assert "Synthetic author-provided checkout rehearsal" in text
    assert "safety_utility.svg" in text
    assert "deny_all | 0/3" in text
    assert "callgate_p67_observed | 0/3" in text
    assert "3/3" in text
    assert "not measured human response time" in text
    assert "OTP step-up is modeled as failing under live coercion" in text


def test_checkout_svg_uses_generated_raw_counts():
    svg = render_svg(run())
    assert "<svg" in svg
    assert "CallGate p=1.0: false execute 0/3; legitimate completion 3/3" in svg
    assert "CallGate p=0.67: false execute 0/3; legitimate completion 2/3" in svg
    assert "OTP step-up: false execute 3/3; legitimate completion 3/3" in svg
    assert "deny-all: false execute 0/3; legitimate completion 0/3" in svg
    assert "unguarded: false execute 3/3; legitimate completion 3/3" in svg
    assert "Author-written scenarios" in svg


def test_committed_checkout_results_match_regenerated_report():
    report_path = Path("evaluation_checkout/results.json")
    markdown_path = Path("evaluation_checkout/REPORT.md")
    svg_path = Path("evaluation_checkout/safety_utility.svg")
    if report_path.exists() and markdown_path.exists() and svg_path.exists():
        assert "callgate-checkout-utility-v1" in report_path.read_text()
        assert markdown_path.read_text() == render_markdown(run())
        assert svg_path.read_text() == render_svg(run())
