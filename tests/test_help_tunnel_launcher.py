"""A missing separate domain must fail before any account/network operation."""
from pathlib import Path
import subprocess
import sys


def test_ngrok_help_requires_explicit_available_domain():
    script=Path(__file__).parents[1]/'scripts/start_help_tunnel.py'
    result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=5)
    assert result.returncode==2
    assert '--url' in result.stderr
    assert result.stdout==''
