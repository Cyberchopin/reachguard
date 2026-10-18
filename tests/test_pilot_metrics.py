import pytest
from evaluation_v1.evaluate_pilot import metrics


def test_known_confusion_and_ambiguous_exclusion():
    rows = [{'label': label, 'prediction': pred} for label,pred in
            [('scam',1),('scam',1),('scam',0),('benign',1),('benign',0),('ambiguous',1)]]
    m = metrics(rows)
    assert m['confusion'] == {'tp':2,'fp':1,'fn':1,'tn':1}
    assert m['precision']['value'] == pytest.approx(2/3)
    assert m['recall']['value'] == pytest.approx(2/3)
    assert m['f1']['value'] == pytest.approx(2/3)
    assert m['fpr']['value'] == .5
    for key in ['precision','recall','f1','fpr','fnr']:
        lo,hi = m[key]['ci95']
        assert 0 <= lo <= m[key]['value'] <= hi <= 1


def test_undefined_not_reported_as_zero():
    m = metrics([{'label':'benign','prediction':0}])
    assert m['precision']['value'] is None
    assert m['recall']['ci95'] is None
    assert m['f1']['value'] is None
    assert m['fpr']['value'] == 0
