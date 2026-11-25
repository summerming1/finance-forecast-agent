"""Focused research must not eagerly import unrelated native paper training."""
import os
import subprocess
import sys


def test_focused_package_import_keeps_public_names_without_loading_torch():
    code = ("import sys; import finance_forecast_agent as p; "
            "assert 'torch' not in sys.modules; "
            "assert 'run_harness' in p.__all__; "
            "assert 'MethodCard' in dir(p); "
            "from finance_forecast_agent import focused_methods; "
            "assert focused_methods.TrainingPolicy().mode == 'expanding'")
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                            env=os.environ.copy(), timeout=30, check=False)
    assert result.returncode == 0, result.stderr
