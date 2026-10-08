import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import eval.run_eval as run_eval


def test_eval_script_runs_without_real_model():
    assert run_eval.main() == 0
