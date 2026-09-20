"""Run the permanent focused regressions and all delivered Mission stage tests."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", default="")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tests = ["tests/test_focused_data_research.py", "tests/test_focused_streamlit_page.py"]
    tests += sorted(str(p.relative_to(root)) for p in (root / "tests").glob("test_mission*.py"))
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "pytest", "-q", *tests]
    if args.junit:
        cmd.append(f"--junitxml={args.junit}")
    result = subprocess.run(cmd, cwd=root, env=env, check=False)
    if result.returncode:
        return result.returncode
    lint = sorted({str(p.relative_to(root)) for pattern in ("focused*.py", "research_mission.py", "mission*.py")
                   for p in (root / "src/finance_forecast_agent").glob(pattern)})
    lint += ["apps/pages/8_Focused_Research.py", "scripts/check_mission_gate.py", *tests]
    lint += sorted(str(p.relative_to(root)) for p in (root / "scripts").glob("*mission*.py"))
    for p in ("scripts/run_research_value_benchmark.py",):
        if (root / p).exists():
            lint.append(p)
    return subprocess.run([sys.executable, "-m", "ruff", "check", *sorted(set(lint))],
                          cwd=root, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
