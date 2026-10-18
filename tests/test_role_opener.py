from pathlib import Path
import pytest
from scripts.open_fusion_page import role_entry


def test_role_files_never_cross_authority(tmp_path):
    (tmp_path/'participant-link.txt').write_text('http://127.0.0.1:8781/#token=participant-fixture')
    (tmp_path/'reviewer-saved-family-link.txt').write_text('http://127.0.0.1:8782/#token=reviewer-fixture')
    assert role_entry(tmp_path,'operator','saved-family')[1]=='http://127.0.0.1:8781/fusion#token=participant-fixture'
    assert role_entry(tmp_path,'participant','saved-family')[1].endswith('participant-fixture')
    assert role_entry(tmp_path,'reviewer','saved-family')[1].endswith('reviewer-fixture')


@pytest.mark.parametrize('entry', ['https://example.com/#token=x','http://127.0.0.1:8782/','http://user:pass@127.0.0.1:8782/#token=x','http://127.0.0.1:8782/other#token=x'])
def test_nonlocal_or_incomplete_entry_rejected(tmp_path,entry):
    (tmp_path/'reviewer-saved-family-link.txt').write_text(entry)
    with pytest.raises(ValueError):role_entry(tmp_path,'reviewer','saved-family')
