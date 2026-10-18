import copy
import importlib.util
from pathlib import Path
import pytest


def verifier():
    path = Path(__file__).parents[1]/'evaluation_v2/verify_inputs.py'
    spec = importlib.util.spec_from_file_location('v2_inputs', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def data():
    v = verifier()
    return v, v.load_rows(v.ROOT/'blind/scenarios.jsonl'), v.load_rows(v.ROOT/'author_labels.jsonl')


def test_input_schema_and_manifest():
    verifier().main()


def test_duplicate_scenario_rejected():
    v, rows, labels = data()
    with pytest.raises(ValueError, match='duplicate'):
        v.validate(rows+[copy.deepcopy(rows[0])], labels)


def test_blind_package_rejects_label_leak():
    v, rows, labels = data()
    rows[0]['label'] = 'scam'
    with pytest.raises(ValueError, match='fields'):
        v.validate(rows, labels)


def test_missing_label_link_rejected():
    v, rows, labels = data()
    with pytest.raises(ValueError, match='mismatch'):
        v.validate(rows, labels[:-1])
